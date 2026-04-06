import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.default import get_request_type_kb, get_main_menu_kb
from app.services.bot_crud import get_previous_employee_data

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text.in_(["Компьютер", "Принтер"]))
async def select_equipment_type(message: Message, state: FSMContext, session: AsyncSession):
    """Выбор типа техники из главного меню."""
    data = await state.get_data()
    # Если юзер не авторизован в филиале (нет BXM)
    if "branch_id" not in data:
        await message.answer("Сначала необходимо выбрать филиал. Нажмите /start")
        return

    equipment_type = "computer" if message.text == "Компьютер" else "printer"
    await state.update_data(equipment_type=equipment_type)
    
    await message.answer(
        f"Вы выбрали оборудование: **{message.text}**.\n\nКакую заявку вы хотите подать?",
        reply_markup=get_request_type_kb(),
        parse_mode="Markdown"
    )


@router.message(F.text == "⬅️ Назад в меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    """Возврат в главное меню из подменю."""
    # Очищаем данные о типе, но оставляем branch_id
    data = await state.get_data()
    branch_id = data.get("branch_id")
    bhm_code = data.get("bhm_code")
    branch_name = data.get("branch_name")
    
    await state.clear()
    
    # Восстанавливаем данные филиала
    if branch_id:
        await state.update_data(
            branch_id=branch_id,
            bhm_code=bhm_code,
            branch_name=branch_name
        )    
    
    await message.answer(
        "Вы вернулись в главное меню.",
        reply_markup=get_main_menu_kb()
    )


@router.message(F.text == "⬅️ Отмена и в меню")
async def cancel_fsm(message: Message, state: FSMContext):
    """Прерывание FSM (формы заявки)."""
    current_state = await state.get_state()
    if current_state is None:
        return await back_to_main_menu(message, state)

    await message.answer("Заполнение заявки отменено.", reply_markup=get_main_menu_kb())
    await back_to_main_menu(message, state)
