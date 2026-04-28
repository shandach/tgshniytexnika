import logging
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.default import get_main_menu_kb, get_reviewer_l1_menu_kb, get_reviewer_l2_menu_kb
from app.bot.states.forms import RegistrationForm
from app.services.bot_crud import get_or_create_tg_account, get_branch_by_bhm

logger = logging.getLogger(__name__)
router = Router()

from aiogram.types import ReplyKeyboardRemove
from app.bot.utils.texts import _, get_text_variants
from app.models.telegram_account import TgRole

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    """Вход и приветствие. Разный флоу для сотрудников и проверяющих."""
    # Регистрируем/обновляем TG аккаунт
    account = await get_or_create_tg_account(session, message.from_user.id)
    
    # Сбрасываем любые стейты
    await state.clear()
    
    # Сохраняем язык и роль в state
    await state.update_data(language=account.language, role=account.role)
    lang = account.language or "uz"
    
    # Разделение по ролям
    if account.role == TgRole.reviewer_l1:
        await message.answer(
            "👋 Добро пожаловать, проверяющий L1!\n\n"
            "Используйте меню для работы с заявками.",
            reply_markup=get_reviewer_l1_menu_kb(),
        )
        return
    
    if account.role == TgRole.reviewer_l2:
        await message.answer(
            "👋 Добро пожаловать, проверяющий L2!\n\n"
            "Используйте меню для подтверждения заявок.",
            reply_markup=get_reviewer_l2_menu_kb(),
        )
        return
    
    # Стандартный флоу для сотрудников
    msg_text = _("msg_bhm_req", lang)
        
    await message.answer(
        msg_text,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    await state.set_state(RegistrationForm.waiting_for_bhm)


@router.message(RegistrationForm.waiting_for_bhm)
async def process_bhm_code(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка ввода BXM кода и приветствие с меню."""
    data = await state.get_data()
    lang = data.get("language", "uz")
    
    bhm_code = message.text.strip()
    
    if not bhm_code.isdigit() or len(bhm_code) != 5:
        await message.answer(_("err_bhm_invalid", lang))
        return
        
    branch = await get_branch_by_bhm(session, bhm_code)
    
    if not branch:
        await message.answer(_("err_bhm_not_found", lang))
        return
        
    # Сохраняем филиал в стейт + сохраняем язык в стейт еще раз для надежности
    await state.update_data(branch_id=branch.id, bhm_code=bhm_code, branch_name=branch.branch_name, language=lang)
    
    # Выводим главное меню
    msg = _("msg_bhm_found", lang, branch=branch.branch_name, region=branch.region_name, city=branch.city_name)
    
    await message.answer(msg, reply_markup=get_main_menu_kb(lang), parse_mode="Markdown")
    await state.set_state(None)


from aiogram.filters import Command, StateFilter
from app.bot.keyboards.inline import get_inline_language_kb
from aiogram.types import CallbackQuery

@router.message(Command("language"), StateFilter("*"))
async def cmd_language(message: Message):
    """Смена языка в любой момент, не сбрасывая FSM state."""
    await message.answer(
        "🌐 Tilni tanlang / Выберите язык:",
        reply_markup=get_inline_language_kb()
    )

@router.callback_query(F.data.startswith("lang_"), StateFilter("*"))
async def process_inline_language(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обрабатываем нажатие на кнопку языка откуда угодно."""
    lang = callback.data.split("_")[1]
    
    # Сохраняем в БД
    account = await get_or_create_tg_account(session, callback.from_user.id)
    account.language = lang
    await session.commit()
    
    # Сохраняем в текущий стейт
    await state.update_data(language=lang)
    
    text = "✅ Til o'zgartirildi! Davom etishingiz mumkin." if lang == "uz" else "✅ Язык изменен! Можете продолжать."
    await callback.message.edit_text(text)
    await callback.answer()
