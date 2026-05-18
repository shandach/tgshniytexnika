"""
Fallback handler — ловит ВСЕ сообщения, которые не обработал ни один другой хендлер.
ВАЖНО: этот роутер должен быть зарегистрирован ПОСЛЕДНИМ в setup_routers().
"""
import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.default import get_main_menu_kb, get_reviewer_l1_menu_kb, get_reviewer_l2_menu_kb
from app.models.telegram_account import TgRole
from app.models.branch import BhmBranch
from app.services.bot_crud import get_or_create_tg_account
from app.bot.utils.texts import _

logger = logging.getLogger(__name__)
router = Router()


@router.message()
async def global_fallback(message: Message, state: FSMContext, session: AsyncSession):
    """
    Последний предохранитель: если ни один хендлер не поймал сообщение,
    восстанавливаем контекст из БД и показываем правильное меню.
    """
    # Игнорируем неизвестные команды (начинающиеся с /)
    if message.text and message.text.startswith("/"):
        await message.answer("❓ Неизвестная команда. Нажмите /start")
        return

    account = await get_or_create_tg_account(session, message.from_user.id)
    lang = account.language or "uz"

    logger.info(
        f"Fallback triggered for user {message.from_user.id} "
        f"role={account.role} branch={account.selected_branch_id} text={message.text!r}"
    )

    # L1 проверяющий
    if account.role == TgRole.reviewer_l1:
        await message.answer(
            "📋 Выберите действие:" if lang == "ru" else "📋 Amalni tanlang:",
            reply_markup=get_reviewer_l1_menu_kb(lang=lang)
        )
        return

    # L2 проверяющий
    if account.role == TgRole.reviewer_l2:
        await message.answer(
            "📋 Выберите действие:" if lang == "ru" else "📋 Amalni tanlang:",
            reply_markup=get_reviewer_l2_menu_kb(lang=lang)
        )
        return

    # Обычный сотрудник — восстанавливаем по филиалу из БД
    if account.selected_branch_id:
        branch = await session.get(BhmBranch, account.selected_branch_id)
        if branch:
            # Восстанавливаем стейт из БД
            await state.update_data(
                branch_id=branch.id,
                bhm_code=branch.bhm_code,
                branch_name=branch.branch_name,
                language=lang
            )
            msg = _("msg_bhm_found", lang,
                    branch=branch.branch_name,
                    region=branch.region_name,
                    city=f"{branch.city_name} BXM" if branch.city_name else "")
            await message.answer(msg, reply_markup=get_main_menu_kb(lang), parse_mode="Markdown")
            return

    # Совсем новый пользователь — просим /start
    await message.answer(
        "👋 Для начала работы нажмите /start" if lang == "ru" else "👋 Boshlash uchun /start bosing"
    )
