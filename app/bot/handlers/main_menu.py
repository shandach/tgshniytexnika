import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.default import get_request_type_kb, get_main_menu_kb

logger = logging.getLogger(__name__)
router = Router()

from app.bot.utils.texts import _, get_text_variants


@router.message(
    StateFilter(None),  # ВАЖНО: только когда нет активного FSM-состояния
    F.text.in_(get_text_variants("btn_computer") + get_text_variants("btn_printer"))
)
async def select_equipment_type(message: Message, state: FSMContext, session: AsyncSession):
    """Выбор типа техники из главного меню."""
    data = await state.get_data()
    lang = data.get("language", "uz")

    if "branch_id" not in data:
        await message.answer(_(  "msg_not_auth", lang))
        return

    equipment_type = "computer" if message.text in get_text_variants("btn_computer") else "printer"
    await state.update_data(equipment_type=equipment_type)

    await message.answer(
        _(  "msg_select_equip", lang, equip=message.text),
        reply_markup=get_request_type_kb(lang),
        parse_mode="Markdown"
    )


@router.message(F.text.in_(get_text_variants("btn_back")))
async def back_to_main_menu(message: Message, state: FSMContext):
    """Возврат в главное меню (работает из любого состояния)."""
    data = await state.get_data()
    lang = data.get("language", "uz")
    branch_id = data.get("branch_id")
    bhm_code = data.get("bhm_code")
    branch_name = data.get("branch_name")

    await state.clear()

    if branch_id:
        await state.update_data(
            branch_id=branch_id,
            bhm_code=bhm_code,
            branch_name=branch_name,
            language=lang
        )

    await message.answer(
        _(  "msg_back_main", lang),
        reply_markup=get_main_menu_kb(lang)
    )


@router.message(F.text.in_(get_text_variants("btn_cancel")))
async def cancel_fsm(message: Message, state: FSMContext):
    """Прерывание FSM (работает из любого состояния)."""
    current_state = await state.get_state()
    if current_state is None:
        # Уже в главном меню — просто показываем меню
        return await back_to_main_menu(message, state)
    # Есть активный FSM — очищаем и возвращаем в меню
    await back_to_main_menu(message, state)
