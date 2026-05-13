import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.bot.states.forms import RequestForm
from app.bot.keyboards.default import get_cancel_kb, get_main_menu_kb, get_fio_reuse_kb
from app.services.bot_crud import (
    check_inventory_lock, get_inventory_by_code, 
    create_request, get_previous_employee_data
)
from app.models.request import RequestType
from app.models.inventory import EquipmentType

logger = logging.getLogger(__name__)
router = Router()

from app.bot.utils.texts import _, get_text_variants

@router.message(
    StateFilter(None),  # Только из главного меню (без активного FSM)
    F.text.in_(get_text_variants("btn_new") + get_text_variants("btn_replace") + get_text_variants("btn_repair"))
)
async def start_request_fsm(message: Message, state: FSMContext, session: AsyncSession):
    """Начало заполнения заявки."""
    data = await state.get_data()
    lang = data.get("language", "uz")
    
    if message.text in get_text_variants("btn_new"):
        request_type = RequestType.new_issue
    elif message.text in get_text_variants("btn_replace"):
        request_type = RequestType.replacement
    else:
        request_type = RequestType.repair
        
    await state.update_data(request_type=request_type.value)

    if request_type in [RequestType.replacement, RequestType.repair]:
        await message.answer(
            _("msg_req_inv", lang),
            reply_markup=get_cancel_kb(lang)
        )
        await state.set_state(RequestForm.waiting_for_inventory_code)
    else:
        # Для выдачи новой сразу идем к ФИО
        await proceed_to_fio(message, state, session, lang)


@router.message(RequestForm.waiting_for_inventory_code)
async def process_inventory_code(message: Message, state: FSMContext, session: AsyncSession):
    """Проверка инвентарного номера."""
    inventory_code = message.text.strip()
    data = await state.get_data()
    lang = data.get("language", "uz")
    req_type = data["request_type"]
    branch_id = data.get("branch_id")
    equipment_type = data.get("equipment_type")  # Из главного меню

    # 1. Проверяем наличие активных заявок по коду (Блокировка)
    is_locked = await check_inventory_lock(session, inventory_code)
    if is_locked:
        await message.answer(_("err_inv_locked", lang), reply_markup=get_main_menu_kb(lang))
        await state.clear()
        return

    # 2. Проверяем существование техники в БД
    inventory = await get_inventory_by_code(session, inventory_code)
    if not inventory:
        await message.answer(_("err_inv_not_found", lang))
        return

    # 3. Проверяем филиал
    if inventory.branch_id != branch_id:
        await message.answer(_("err_inv_branch", lang))
        return

    # 4. Проверяем тип
    if inventory.equipment_type.value != equipment_type:
        e_type_str = _("btn_computer", lang) if equipment_type == "computer" else _("btn_printer", lang)
        await message.answer(_("err_inv_type", lang, type=e_type_str))
        return

    # 5. Специфично для Замены: проверка года (< 2024)
    if req_type == RequestType.replacement.value:
        if inventory.issue_year >= 2024:
            await message.answer(
                _("err_rep_year", lang),
                reply_markup=get_main_menu_kb(lang),
                parse_mode="Markdown"
            )
            await state.clear()
            return

    # Сохраняем и идем к ФИО
    await state.update_data(inventory_id=inventory.id, inventory_code=inventory.inventory_code)
    await proceed_to_fio(message, state, session, lang)


async def proceed_to_fio(message: Message, state: FSMContext, session: AsyncSession, lang: str = "uz"):
    """Переход к вводу ФИО с возможностью автоподстановки."""
    from app.services.bot_crud import get_or_create_tg_account
    tg_account = await get_or_create_tg_account(session, message.from_user.id)
    prev_data = await get_previous_employee_data(session, tg_account.id)
    if prev_data:
        kb = get_fio_reuse_kb(prev_data["fio"], prev_data["position"], lang)
        msg_text = _("msg_fio_use", lang)
    else:
        kb = get_cancel_kb(lang)
        msg_text = _("msg_fio_req", lang)

    await message.answer(msg_text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(RequestForm.waiting_for_fio)


@router.message(RequestForm.waiting_for_fio)
async def process_fio(message: Message, state: FSMContext, session: AsyncSession):
    text = message.text.strip()
    data = await state.get_data()
    lang = data.get("language", "uz")
    
    # Обработка автоподстановки "Использовать: ФИО (Должность)"
    if any(text.startswith(pref) for pref in ["Использовать: ", "Foydalanish: "]):
        try:
            content = text.replace("Использовать: ", "").replace("Foydalanish: ", "")
            fio, pos_part = content.rsplit(" (", 1)
            pos = pos_part.rstrip(")")
            
            await state.update_data(fio=fio, position=pos)
            await proceed_to_reason_or_problem(message, state, lang)
            return
        except Exception:
            pass  # Fallback to normal flow if parsing fails

    await state.update_data(fio=text)
    await message.answer(_("msg_pos_req", lang), reply_markup=get_cancel_kb(lang))
    await state.set_state(RequestForm.waiting_for_position)


@router.message(RequestForm.waiting_for_position)
async def process_position(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("language", "uz")
    await state.update_data(position=message.text.strip())
    await proceed_to_reason_or_problem(message, state, lang)


async def proceed_to_reason_or_problem(message: Message, state: FSMContext, lang: str = "uz"):
    data = await state.get_data()
    req_type = data["request_type"]

    if req_type == RequestType.repair.value:
        await message.answer(_("msg_prob_req", lang), reply_markup=get_cancel_kb(lang))
        await state.set_state(RequestForm.waiting_for_problem)
    elif req_type == RequestType.new_issue.value:
        await message.answer(_("msg_reas_new", lang), reply_markup=get_cancel_kb(lang))
        await state.set_state(RequestForm.waiting_for_reason)
    else:  # replacement
        await message.answer(_("msg_reas_rep", lang), reply_markup=get_cancel_kb(lang))
        await state.set_state(RequestForm.waiting_for_reason)


@router.message(RequestForm.waiting_for_reason)
async def process_reason(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "uz")
    await state.update_data(reason=message.text)
    await finalize_request(message, state, session)


@router.message(RequestForm.waiting_for_problem)
async def process_problem(message: Message, state: FSMContext, session: AsyncSession):
    await state.update_data(problem=message.text)
    await finalize_request(message, state, session)


async def finalize_request(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    lang = data.get("language", "uz")
    
    # Извлекаем объекты
    from app.services.bot_crud import get_branch_by_bhm, get_or_create_tg_account
    branch = await get_branch_by_bhm(session, data["bhm_code"])
    
    # Получаем аккаунт TG из БД (нужен его id, а не telegram_user_id!)
    tg_account = await get_or_create_tg_account(session, message.from_user.id)
    
    inventory = None
    if "inventory_code" in data:
        inventory = await get_inventory_by_code(session, data["inventory_code"])
        
    equipment_type = EquipmentType.computer if data["equipment_type"] == "computer" else EquipmentType.printer

    try:
        from app.models.request import RequestStatus
        req_status = RequestStatus.new
        final_decision = None
        
        is_auto_approved = False
        is_auto_rejected = False

        if data["request_type"] == RequestType.repair.value:
            req_status = RequestStatus.in_progress
        elif data["request_type"] == RequestType.replacement.value and equipment_type == EquipmentType.computer and inventory:
            current_yr = datetime.now(timezone.utc).year
            if inventory.issue_year <= (current_yr - 5):
                req_status = RequestStatus.closed
                final_decision = "approved"
                is_auto_approved = True
            else:
                req_status = RequestStatus.closed
                final_decision = "rejected"
                is_auto_rejected = True

        req = await create_request(
            session=session,
            tg_account_id=tg_account.id,  # DB primary key, NOT telegram user id
            request_type=RequestType(data["request_type"]),
            equipment_type=equipment_type,
            fio_raw=data["fio"],
            position=data["position"],
            branch=branch,
            inventory=inventory,
            reason=data.get("reason"),
            problem=data.get("problem"),
            status=req_status,
            final_decision=final_decision
        )
        
        # Google Sheets Sync
        try:
            from app.services.gsheets import sync_request_to_sheets
            await sync_request_to_sheets(req)
        except Exception as g_err:
            logger.error(f"GSheets sync error: {g_err}")
            
        # Уведомления
        try:
            from app.services.notifications import notify_l1_new_request, notify_auto_approved_pc
            if is_auto_approved:
                await notify_auto_approved_pc(message.bot, session, req)
            elif not is_auto_rejected:
                # Если заявка стандартная (new или repair)
                await notify_l1_new_request(message.bot, session, req)
        except Exception as l1_err:
            logger.error(f"Notification error: {l1_err}")

        # Сообщение сотруднику (если авто-отказ, выводим другой текст)
        if is_auto_rejected:
            if lang == "ru":
                msg_text = f"❌ *Ваша заявка #{req.request_number} отклонена!*\n\nЗамена ПК невозможна, так как компьютеру менее 5 лет (год выпуска: {inventory.issue_year})."
            else:
                msg_text = f"❌ *Arizangiz #{req.request_number} rad etildi!*\n\nShK 5 yildan kam bo'lganligi sababli (ishlab chiqarilgan yili: {inventory.issue_year}) almashtirish mumkin emas."
        elif is_auto_approved:
            if lang == "ru":
                msg_text = f"✅ *Ваша заявка #{req.request_number} АВТОМАТИЧЕСКИ ОДОБРЕНА!*\n\nВашему ПК 5 лет и более. Заявка сразу направлена в отдел выдачи."
            else:
                msg_text = f"✅ *Arizangiz #{req.request_number} AVTOMATIK TASDIQLANDI!*\n\nKompyuteringiz 5 yosh yoki undan katta. Ariza darhol ajratish bo'limiga yuborildi."
        else:
            msg_text = _("msg_success", lang, req_id=req.request_number)

        await message.answer(
            msg_text,
            parse_mode="Markdown",
            reply_markup=get_main_menu_kb(lang)
        )
    except Exception as e:
        logger.error(f"Error creating request: {e}")
        await message.answer(
            _("err_fail", lang),
            reply_markup=get_main_menu_kb(lang)
        )
    finally:
        # Очищаем форму, но держим branch_id в данных!
        branch_id = data.get("branch_id")
        bhm_code = data.get("bhm_code")
        branch_name = data.get("branch_name")
        await state.clear()
        await state.update_data(branch_id=branch_id, bhm_code=bhm_code, branch_name=branch_name, language=lang)
    
