import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bot_crud import get_requests_by_tg_account, get_or_create_tg_account
from app.models.request import Request, RequestStatus
from app.models.branch import BhmBranch
from app.bot.utils.texts import _, get_text_variants

logger = logging.getLogger(__name__)
router = Router()

STATUS_EMOJI = {
    "new": {"ru": "🆕 Новая", "uz": "🆕 Yangi"},
    "in_progress": {"ru": "⏳ В обработке / Сломан", "uz": "⏳ Jarayonda / Buzilgan"},
    "approved_l1": {"ru": "⏳ В обработке (L1)", "uz": "⏳ Jarayonda (L1)"},
    "closed": {"ru": "🔒 Закрыта", "uz": "🔒 Yopilgan"}
}

DECISION_EMOJI = {
    "approved": {"ru": "✅ Одобрено", "uz": "✅ Tasdiqlangan"},
    "rejected": {"ru": "❌ Отказано", "uz": "❌ Rad etilgan"},
    "repaired": {"ru": "🔧 Починен", "uz": "🔧 Ta'mirlangan"}
}

TYPE_LABELS = {
    "replacement": {"ru": "Замена", "uz": "Almashtirish"},
    "new_issue": {"ru": "Выдача", "uz": "Ajratish"},
    "repair": {"ru": "Поломка", "uz": "Buzilish"}
}


class EscalationForm(StatesGroup):
    waiting_for_escalation_comment = State()


async def _generate_my_requests_menu(session: AsyncSession, tg_user_id: int, lang: str = "uz"):
    """Генерирует текст и клавиатуру со списком заявок сотрудника."""
    account = await get_or_create_tg_account(session, tg_user_id)
    requests = await get_requests_by_tg_account(session, account.id)

    if not requests:
        return _("status_empty", lang), None

    reqs_to_show = requests[:5]
    builder = InlineKeyboardBuilder()

    for req in reqs_to_show:
        r_type = TYPE_LABELS.get(req.request_type, {}).get(lang, req.request_type)
        if req.request_type == "repair":
            emoji = "🛠"
        else:
            emoji = "💻" if req.equipment_type == "computer" else "🖨"
            
        status_h = STATUS_EMOJI.get(req.status, {}).get(lang, req.status)
        if req.status == "closed" and req.final_decision:
            status_h = DECISION_EMOJI.get(req.final_decision, {}).get(lang, status_h)
            
        btn_text = f"{emoji} {r_type} #{req.request_number} | {status_h}"
        builder.button(text=btn_text, callback_data=f"myreq_{req.id}")

    builder.adjust(1)
    
    text = _("status_header", lang)
    if len(requests) > 5:
        more_text = "Показаны последние 5 из {total} заявок." if lang == "ru" else "Jami {total} tadan so'nggi 5 tasi ko'rsatildi."
        text += f"\n\n{more_text.format(total=len(requests))}"
        
    return text, builder.as_markup()


@router.message(F.text.in_(get_text_variants("btn_status")))
async def check_status(message: Message, session: AsyncSession, state: FSMContext):
    """Показывает список заявок текущего Telegram-аккаунта (менюшка)."""
    data = await state.get_data()
    lang = data.get("language", "ru")
    
    text, kb = await _generate_my_requests_menu(session, message.from_user.id, lang)
    if kb:
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer(text, parse_mode="Markdown")


@router.callback_query(F.data == "myreqs_list")
async def back_to_my_reqs(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Возврат к списку своих заявок."""
    data = await state.get_data()
    lang = data.get("language", "ru")
    text, kb = await _generate_my_requests_menu(session, callback.from_user.id, lang)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("myreq_"))
async def my_req_detail(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Открывает детальную карточку заявки сотрудника."""
    data = await state.get_data()
    lang = data.get("language", "ru")
    
    req_id = int(callback.data.split("_")[1])
    stmt = select(Request).where(Request.id == req_id)
    req = await session.scalar(stmt)
    
    if not req:
        await callback.answer(_("alert_already_processed", lang))
        return
        
    r_type = TYPE_LABELS.get(req.request_type, {}).get(lang, req.request_type)
    status_h = STATUS_EMOJI.get(req.status, {}).get(lang, req.status)
    if req.status == "closed" and req.final_decision:
        status_h += f" -> {DECISION_EMOJI.get(req.final_decision, {}).get(lang, status_h)}"
        
    comp_text = "Компьютер" if lang == "ru" else "Kompyuter"
    prin_text = "Принтер" if lang == "ru" else "Printer"
    type_text = comp_text if req.equipment_type == 'computer' else prin_text
    
    req_word = "Заявка" if lang == "ru" else "Ariza"
    type_word = "Тип" if lang == "ru" else "Turi"
    tech_word = "Техника" if lang == "ru" else "Texnika"
    branch_word = "Филиал" if lang == "ru" else "Filial"
    status_word = "Статус" if lang == "ru" else "Holati"
    
    branch = await session.get(BhmBranch, req.branch_id)
    if branch:
        parts = [branch.region_name, branch.city_name, branch.branch_name]
        branch_info = ", ".join([p for p in parts if p])
    else:
        branch_info = req.branch_name_snapshot

    bxm_num_label = "Номер BXM" if lang == "ru" else "BXM raqami"

    text = (
        f"📄 *{req_word} #{req.request_number}*\n\n"
        f"🔸 *{type_word}:* {r_type}\n"
        f"🔸 *{tech_word}:* {type_text}\n"
        f"🔸 *{branch_word}:* {branch_info}\n"
        f"🔸 *{bxm_num_label}:* {req.bhm_code_snapshot}\n"
        f"🔸 *{status_word}:* {status_h}\n"
    )
    if req.inventory_code_snapshot:
        inv_word = "Инвентарник" if lang == "ru" else "Inventar"
        text += f"🔸 *{inv_word}:* {req.inventory_code_snapshot}\n"
    if req.reason_text:
        reas_word = "Причина/Комментарий" if lang == "ru" else "Sabab/Izoh"
        text += f"🔸 *{reas_word}:* _{req.reason_text}_\n"
    if req.problem_text:
        prob_word = "Проблема" if lang == "ru" else "Muammo"
        text += f"🔸 *{prob_word}:* _{req.problem_text}_\n"
    if req.reject_reason:
        rej_word = "Причина отказа" if lang == "ru" else "Rad etish sababi"
        text += f"🔸 *{rej_word}:* ❌ {req.reject_reason}\n"

    builder = InlineKeyboardBuilder()

    btn_back = _("btn_back_list", lang)

    # Точка входа для самоподтверждения ремонта!
    if req.request_type == "repair" and req.status == "in_progress":
        text += "\n\n🛠 *Проверьте, пожалуйста, всё ли работает?*" if lang == "ru" else "\n\n🛠 *Iltimos, tekshiring, hammasi ishlavotimi?*"
        btn_yes = "👍 Да, всё работает" if lang == "ru" else "👍 Ha, hammasi ishlavoti"
        btn_no = "👎 Нет, проблема осталась" if lang == "ru" else "👎 Yo'q, muammo qoldi"
        builder.button(text=btn_yes, callback_data=f"rep_yes_{req.id}")
        builder.button(text=btn_no, callback_data=f"rep_no_{req.id}")
        builder.adjust(1)
        # Отдельный Row для "Назад"
        builder.row(InlineKeyboardButton(text=btn_back, callback_data="myreqs_list"))
    else:
        builder.row(InlineKeyboardButton(text=btn_back, callback_data="myreqs_list"))

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("rep_yes_"))
async def repair_confirmed_yes(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Сотрудник подтвердил починку."""
    data = await state.get_data()
    lang = data.get("language", "ru")
    req_id = int(callback.data.split("_")[2])
    stmt = select(Request).where(Request.id == req_id)
    req = await session.scalar(stmt)
    
    if req and req.status == "in_progress":
        req.status = RequestStatus.closed
        req.final_decision = "repaired"
        await session.commit()
        
        try:
            from app.services.notifications import notify_reviewers_repair_closed
            await notify_reviewers_repair_closed(callback.bot, session, req)
        except Exception as e:
            logger.error(f"Failed to notify reviewers: {e}")
        
        msg = f"✅ *Супер!* Рады слышать, что всё работает.\n\nЗаявка #{req.request_number} успешно закрыта." if lang == "ru" else f"✅ *Zo'r!* Hammasi ishlayotganidan xursandmiz.\n\nAriza #{req.request_number} muvaffaqiyatli yopildi."
        btn_back = _("btn_back_list", lang)
        
        await callback.message.edit_text(
            msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_back, callback_data="myreqs_list")]])
        )
    else:
        await callback.answer(_("alert_already_processed", lang))


@router.callback_query(F.data.startswith("rep_no_"))
async def repair_escalate_no(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Сотрудник нажал 'Нет', требуем коммент."""
    data = await state.get_data()
    lang = data.get("language", "ru")
    req_id = int(callback.data.split("_")[2])
    
    await state.update_data(escalate_req_id=req_id)
    await state.set_state(EscalationForm.waiting_for_escalation_comment)
    
    btn_cancel = "Отмена" if lang == "ru" else "Bekor qilish"
    msg = "📝 Опишите, пожалуйста, подробно: что именно до сих пор беспокоит или осталась сломано?" if lang == "ru" else "📝 Iltimos, batafsil yozing: aynan nima haligacha bezovta qilyapti yoki buzilganicha qoldi?"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_cancel, callback_data=f"myreq_{req_id}")]])
    await callback.message.edit_text(msg, reply_markup=kb)


@router.message(EscalationForm.waiting_for_escalation_comment)
async def process_escalation_comment(message: Message, state: FSMContext, session: AsyncSession):
    """Сотрудник ввёл комментарий по поводу 'Поломка осталась' — шлем алёрт L1."""
    data = await state.get_data()
    req_id = data.get("escalate_req_id")
    comment = message.text.strip()
    
    stmt = select(Request).where(Request.id == req_id)
    req = await session.scalar(stmt)
    
    if req:
        # Уведомляем L1 через новый алиас
        try:
            from app.services.notifications import notify_l1_escalation
            await notify_l1_escalation(message.bot, session, req, comment)
        except Exception as e:
            logger.error(f"Failed to send escalation: {e}")

    await state.clear()
    
    # Чтобы вернуть контекст, нам нужен lang
    lang = data.get("language", "ru") 
    await state.update_data(language=lang)

    msg = f"🚨 Спасибо! Информация по заявке #{req.request_number if req else ''} передана руководителям.\nС вами свяжутся в ближайшее время." if lang == "ru" else f"🚨 Rahmat! Ariza #{req.request_number if req else ''} bo'yicha ma'lumot rahbarlarga yetkazildi.\nTez orada siz bilan bog'lanishadi."
    await message.answer(msg, reply_markup=None)
