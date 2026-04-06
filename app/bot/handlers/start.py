import logging
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.default import get_main_menu_kb
from app.bot.states.forms import RegistrationForm
from app.services.bot_crud import get_or_create_tg_account, get_branch_by_bhm

logger = logging.getLogger(__name__)
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    """Вход и приветствие."""
    # Регистрируем/обновляем TG аккаунт
    account = await get_or_create_tg_account(session, message.from_user.id)
    
    # Сбрасываем любые стейты
    await state.clear()
    
    from aiogram.types import ReplyKeyboardRemove
    
    await message.answer(
        "👋 Добро пожаловать!\nДля работы с системой заявок на ИТ-технику, пожалуйста, введите ваш **5-значный BXM код** филиала:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    await state.set_state(RegistrationForm.waiting_for_bhm)


@router.message(RegistrationForm.waiting_for_bhm)
async def process_bhm_code(message: Message, state: FSMContext, session: AsyncSession):
    """Проверка введенного BXM кода."""
    bhm_code = message.text.strip()
    
    if len(bhm_code) != 5:
        await message.answer("BXM код должен состоять ровно из 5 цифр. Попробуйте еще раз:")
        return

    branch = await get_branch_by_bhm(session, bhm_code)
    
    if not branch:
        await message.answer("❌ Филиал с таким BXM кодом не найден. Проверьте правильность и введите снова:")
        return

    # Сохраняем BXM и инфу о филиале в локальный state пользователя
    await state.update_data(
        branch_id=branch.id,
        bhm_code=branch.bhm_code,
        branch_name=branch.branch_name,
        region=branch.region_name
    )
    await state.set_state(None)

    msg = (f"✅ Филиал определен:\n"
           f"🏢 **{branch.branch_name}**\n"
           f"📍 {branch.region_name}, {branch.city_name}\n\n"
           f"Выберите нужное действие в меню ниже 👇")
    
    await message.answer(msg, reply_markup=get_main_menu_kb(), parse_mode="Markdown")
