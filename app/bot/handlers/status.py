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
from app.bot.utils.texts import _, get_text_variants

logger = logging.getLogger(__name__)
router = Router()

STATUS_EMOJI = {
    "new": "🆕 Новая",
    "in_progress": "⏳ В обработке / Сломан",
    "approved_l1": "⏳ В обработке (L1)",
    "closed": "🔒 Закрыта"
}

DECISION_EMOJI = {
    "approved": "✅ Одобрено",
    "rejected": "❌ Отказано",
    "repaired": "🔧 Починен"
}

TYPE_LABELS = {
    "replacement": "Замена",
    "new_issue": "Выдача",
    "repair": "Поломка"
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
        r_type = TYPE_LABELS.get(req.request_type, req.request_type)
        if req.request_type == "repair":
            emoji = "🛠"
        else:
            emoji = "💻" if req.equipment_type == "computer" else "🖨"
            
        status_h = STATUS_EMOJI.get(req.status, req.status)
        if req.status == "closed" and req.final_decision:
            status_h = DECISION_EMOJI.get(req.final_decision, status_h)
            
        btn_text = f"{emoji} {r_type} #{req.request_number} | {status_h}"
        builder.button(text=btn_text, callback_data=f"myreq_{req.id}")

    builder.adjust(1)
    
    text = _("status_header", lang)
    if len(requests) > 5:
        text += f"\n\nПоказаны последние 5 из {len(requests)} заявок."
        
    return text, builder.as_markup()


@router.message(F.text.in_(get_text_variants("btn_status")))
async def check_status(message: Message, session: AsyncSession, state: FSMContext):
    """Показывает список заявок текущего Telegram-аккаунта (менюшка)."""
    data = await state.get_data()
    lang = data.get("language", "uz")
    
    text, kb = await _generate_my_requests_menu(session, message.from_user.id, lang)
    if kb:
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer(text, parse_mode="Markdown")


@router.callback_query(F.data == "myreqs_list")
async def back_to_my_reqs(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Возврат к списку своих заявок."""
    data = await state.get_data()
    lang = data.get("language", "uz")
    text, kb = await _generate_my_requests_menu(session, callback.from_user.id, lang)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("myreq_"))
async def my_req_detail(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Открывает детальную карточку заявки сотрудника."""
    req_id = int(callback.data.split("_")[1])
    stmt = select(Request).where(Request.id == req_id)
    req = await session.scalar(stmt)
    
    if not req:
        await callback.answer("Заявка не найдена")
        return
        
    r_type = TYPE_LABELS.get(req.request_type, req.request_type)
    status_h = STATUS_EMOJI.get(req.status, req.status)
    if req.status == "closed" and req.final_decision:
        status_h += f" -> {DECISION_EMOJI.get(req.final_decision)}"
        
    text = (
        f"📄 *Заявка #{req.request_number}*\n\n"
        f"🔸 *Тип:* {r_type}\n"
        f"🔸 *Техника:* {'Компьютер' if req.equipment_type == 'computer' else 'Принтер'}\n"
        f"🔸 *Филиал:* {req.branch_name_snapshot} ({req.bhm_code_snapshot})\n"
        f"🔸 *Статус:* {status_h}\n"
    )
    if req.inventory_code_snapshot:
        text += f"🔸 *Инвентарник:* {req.inventory_code_snapshot}\n"
    if req.reason_text:
        text += f"🔸 *Причина/Комментарий:* _{req.reason_text}_\n"
    if req.problem_text:
        text += f"🔸 *Проблема:* _{req.problem_text}_\n"
    if req.reject_reason:
        text += f"🔸 *Причина отказа:* ❌ {req.reject_reason}\n"

    builder = InlineKeyboardBuilder()

    # Точка входа для самоподтверждения ремонта!
    if req.request_type == "repair" and req.status == "in_progress":
        text += "\n\n🛠 *Проверьте, пожалуйста, всё ли работает?*"
        builder.button(text="👍 Да, всё работает", callback_data=f"rep_yes_{req.id}")
        builder.button(text="👎 Нет, проблема осталась", callback_data=f"rep_no_{req.id}")
        builder.adjust(1)
        # Отдельный Row для "Назад"
        builder.row(InlineKeyboardButton(text="◀ Назад к списку", callback_data="myreqs_list"))
    else:
        builder.row(InlineKeyboardButton(text="◀ Назад к списку", callback_data="myreqs_list"))

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("rep_yes_"))
async def repair_confirmed_yes(callback: CallbackQuery, session: AsyncSession):
    """Сотрудник подтвердил починку."""
    req_id = int(callback.data.split("_")[2])
    stmt = select(Request).where(Request.id == req_id)
    req = await session.scalar(stmt)
    
    if req and req.status == "in_progress":
        req.status = RequestStatus.closed
        req.final_decision = "repaired"
        await session.commit()
        
        await callback.message.edit_text(
            f"✅ *Супер!* Рады слышать, что всё работает.\n\nЗаявка #{req.request_number} успешно закрыта.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀ Назад", callback_data="myreqs_list")]])
        )
    else:
        await callback.answer("Заявка уже закрыта или недоступна.")


@router.callback_query(F.data.startswith("rep_no_"))
async def repair_escalate_no(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Сотрудник нажал 'Нет', требуем коммент."""
    req_id = int(callback.data.split("_")[2])
    
    await state.update_data(escalate_req_id=req_id)
    await state.set_state(EscalationForm.waiting_for_escalation_comment)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=f"myreq_{req_id}")]])
    await callback.message.edit_text(
        "📝 Опишите, пожалуйста, подробно: что именно до сих пор беспокоит или осталась сломано?",
        reply_markup=kb
    )


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
    lang = data.get("language", "uz") 
    await state.update_data(language=lang)

    await message.answer(
        f"🚨 Спасибо! Информация по заявке #{req.request_number if req else ''} передана руководителям.\nС вами свяжутся в ближайшее время.",
        reply_markup=None # Использовать базовую клавиатуру тут не обязательно, она осталась
    )
