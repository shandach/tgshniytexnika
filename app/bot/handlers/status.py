import logging
from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bot_crud import get_requests_by_tg_account, get_or_create_tg_account

logger = logging.getLogger(__name__)
router = Router()

STATUS_EMOJI = {
    "new": "🆕 Новая",
    "in_progress": "⏳ В обработке",
    "closed": "🔒 Закрыта"
}

DECISION_EMOJI = {
    "pending": "Ожидает решения",
    "approved": "✅ Одобрено",
    "rejected": "❌ Отказано"
}

@router.message(F.text == "Статус моей заявки")
async def check_status(message: Message, session: AsyncSession):
    """Показывает статус заявок текущего Telegram-аккаунта."""
    account = await get_or_create_tg_account(session, message.from_user.id)
    requests = await get_requests_by_tg_account(session, account.id)

    if not requests:
        await message.answer("У вас пока нет поданных заявок.")
        return

    # У пользователя может быть много заявок, показываем последние 5
    reqs_to_show = requests[:5]
    
    response_lines = ["📋 **Ваши последние заявки:**\n"]
    
    for req in reqs_to_show:
        req_type = "Замена" if req.request_type == "replacement" else "Выдача" if req.request_type == "new_issue" else "Поломка"
        equip = "Компьютер" if req.equipment_type == "computer" else "Принтер"
        
        status_human = STATUS_EMOJI.get(req.status, req.status)
        decision = f" -> {DECISION_EMOJI.get(req.final_decision)}" if req.status == "closed" else ""
        
        line = (f"🔸 #{req.request_number} | {req_type} ({equip})\n"
                f"   ФИО: {req.employee_fio_snapshot}\n"
                f"   Статус: {status_human}{decision}")
        if req.status == "closed" and req.final_decision == "rejected" and req.reject_reason:
            line += f"\n   Причина отказа: {req.reject_reason}"
            
        response_lines.append(line)
        response_lines.append("") # Пустая строка
    
    if len(requests) > 5:
        response_lines.append(f"_Показаны 5 последних заявок из {len(requests)}_")

    await message.answer("\n".join(response_lines), parse_mode="Markdown")
