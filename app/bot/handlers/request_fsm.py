import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

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

# Map Russian text to enums
REQ_TYPE_MAP = {
    "Выдача новой": RequestType.new_issue,
    "Замена": RequestType.replacement,
    "Поломка": RequestType.repair,
}


@router.message(F.text.in_(["Выдача новой", "Замена", "Поломка"]))
async def start_request_fsm(message: Message, state: FSMContext, session: AsyncSession):
    """Начало заполнения заявки."""
    request_type = REQ_TYPE_MAP[message.text]
    await state.update_data(request_type=request_type.value)

    if request_type in [RequestType.replacement, RequestType.repair]:
        await message.answer(
            "Введите инвентарный номер оборудования:",
            reply_markup=get_cancel_kb()
        )
        await state.set_state(RequestForm.waiting_for_inventory_code)
    else:
        # Для выдачи новой сразу идем к ФИО
        await proceed_to_fio(message, state, session)


@router.message(RequestForm.waiting_for_inventory_code)
async def process_inventory_code(message: Message, state: FSMContext, session: AsyncSession):
    """Проверка инвентарного номера."""
    inventory_code = message.text.strip()
    data = await state.get_data()
    req_type = data["request_type"]
    branch_id = data.get("branch_id")
    equipment_type = data.get("equipment_type")  # Из главного меню

    # 1. Проверяем наличие активных заявок по коду (Блокировка)
    is_locked = await check_inventory_lock(session, inventory_code)
    if is_locked:
        await message.answer(
            "❌ По данной технике уже есть активная заявка (находится в процессе).\n"
            "Дождитесь её закрытия перед подачей новой.",
            reply_markup=get_main_menu_kb()
        )
        await state.clear()
        return

    # 2. Проверяем существование техники в БД
    inventory = await get_inventory_by_code(session, inventory_code)
    if not inventory:
        await message.answer("❌ Техника с таким инвентарным номером не найдена. Проверьте номер и введите снова:")
        return

    # 3. Проверяем филиал
    if inventory.branch_id != branch_id:
        await message.answer("❌ Данная техника не принадлежит вашему филиалу. Проверьте номер.")
        return

    # 4. Проверяем тип
    if inventory.equipment_type.value != equipment_type:
        await message.answer(f"❌ Эта техника не является {equipment_type}. Введите корректный инвентарный номер.")
        return

    # 5. Специфично для Замены: проверка года (< 2024)
    if req_type == RequestType.replacement.value:
        if inventory.issue_year >= 2024:
            await message.answer(
                "❌ В *Замене* отказано!\n"
                "Замена разрешена только для техники, выпущенной до 2024 года.",
                reply_markup=get_main_menu_kb(),
                parse_mode="Markdown"
            )
            await state.clear()
            return

    # Сохраняем и идем к ФИО
    await state.update_data(inventory_id=inventory.id, inventory_code=inventory.inventory_code)
    await proceed_to_fio(message, state, session)


async def proceed_to_fio(message: Message, state: FSMContext, session: AsyncSession):
    """Переход к вводу ФИО с возможностью автоподстановки."""
    from app.services.bot_crud import get_or_create_tg_account
    tg_account = await get_or_create_tg_account(session, message.from_user.id)
    prev_data = await get_previous_employee_data(session, tg_account.id)
    if prev_data:
        kb = get_fio_reuse_kb(prev_data["fio"], prev_data["position"])
        msg_text = "Введите ваше ФИО полностью.\n_Вы можете использовать данные из прошлой заявки (кнопка внизу)_ 👇"
    else:
        kb = get_cancel_kb()
        msg_text = "Введите ваше ФИО полностью:"

    await message.answer(msg_text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(RequestForm.waiting_for_fio)


@router.message(RequestForm.waiting_for_fio)
async def process_fio(message: Message, state: FSMContext, session: AsyncSession):
    text = message.text.strip()
    
    # Обработка автоподстановки "Использовать: ФИО (Должность)"
    if text.startswith("Использовать:"):
        # Парсим из кнопки
        try:
            content = text.replace("Использовать: ", "")
            fio, pos_part = content.rsplit(" (", 1)
            pos = pos_part.rstrip(")")
            
            await state.update_data(fio=fio, position=pos)
            # Если данные введены автоподстановкой, сразу пропускаем ввод должности
            await proceed_to_reason_or_problem(message, state)
            return
        except Exception:
            pass  # Fallback to normal flow if parsing fails

    await state.update_data(fio=text)
    await message.answer("Введите вашу должность:", reply_markup=get_cancel_kb())
    await state.set_state(RequestForm.waiting_for_position)


@router.message(RequestForm.waiting_for_position)
async def process_position(message: Message, state: FSMContext):
    await state.update_data(position=message.text.strip())
    await proceed_to_reason_or_problem(message, state)


async def proceed_to_reason_or_problem(message: Message, state: FSMContext):
    data = await state.get_data()
    req_type = data["request_type"]

    if req_type == RequestType.repair.value:
        await message.answer("Опишите проблему с техникой (что случилось, симптомы):", reply_markup=get_cancel_kb())
        await state.set_state(RequestForm.waiting_for_problem)
    elif req_type == RequestType.new_issue.value:
        await message.answer("Укажите причину для выдачи новой техники:", reply_markup=get_cancel_kb())
        await state.set_state(RequestForm.waiting_for_reason)
    else:  # replacement
        await message.answer("Укажите причину для замены старой техники:", reply_markup=get_cancel_kb())
        await state.set_state(RequestForm.waiting_for_reason)


@router.message(RequestForm.waiting_for_reason)
async def process_reason(message: Message, state: FSMContext, session: AsyncSession):
    await state.update_data(reason=message.text)
    await finalize_request(message, state, session)


@router.message(RequestForm.waiting_for_problem)
async def process_problem(message: Message, state: FSMContext, session: AsyncSession):
    await state.update_data(problem=message.text)
    await finalize_request(message, state, session)


async def finalize_request(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    
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
            problem=data.get("problem")
        )
        
        # Google Sheets Sync
        try:
            from app.services.gsheets import sync_request_to_sheets
            await sync_request_to_sheets(req)
        except Exception as g_err:
            logger.error(f"GSheets sync error: {g_err}")

        await message.answer(
            f"✅ Ваша заявка успешно создана!\n\n"
            f"**Номер заявки:** #{req.request_number}\n"
            f"Статус всегда можно отследить в меню 'Статус моей заявки'.",
            parse_mode="Markdown",
            reply_markup=get_main_menu_kb()
        )
    except Exception as e:
        logger.error(f"Error creating request: {e}")
        await message.answer(
            "❌ Произошла системная ошибка при сохранении заявки. Попробуйте снова или сообщите об ошибке.",
            reply_markup=get_main_menu_kb()
        )
    finally:
        # Очищаем форму, но держим branch_id в данных!
        branch_id = data.get("branch_id")
        bhm_code = data.get("bhm_code")
        branch_name = data.get("branch_name")
        await state.clear()
        await state.update_data(branch_id=branch_id, bhm_code=bhm_code, branch_name=branch_name)
    
