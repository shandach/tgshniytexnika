from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from app.bot.utils.texts import _

def get_main_menu_kb(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Главное меню бота."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_( "btn_computer", lang)), KeyboardButton(text=_( "btn_printer", lang))],
            [KeyboardButton(text=_( "btn_status", lang))],
            [KeyboardButton(text=_( "btn_error", lang))]
        ],
        resize_keyboard=True,
        input_field_placeholder=_( "ph_main", lang)
    )
    return kb


def get_request_type_kb(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Меню выбора типа заявки после выбора техники."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_( "btn_new", lang))],
            [KeyboardButton(text=_( "btn_replace", lang))],
            [KeyboardButton(text=_( "btn_repair", lang))],
            [KeyboardButton(text=_( "btn_back", lang))]
        ],
        resize_keyboard=True
    )
    return kb


def get_cancel_kb(lang: str = "uz") -> ReplyKeyboardMarkup:
    """Кнопка отмены/возврата для FSM состояний."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_( "btn_cancel", lang))]
        ],
        resize_keyboard=True
    )
    return kb


def get_fio_reuse_kb(fio: str, position: str, lang: str = "uz") -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой для использования предыдущих данных."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=_( "btn_use_fio", lang, fio=fio, pos=position))],
            [KeyboardButton(text=_( "btn_cancel", lang))]
        ],
        resize_keyboard=True,
        input_field_placeholder=_( "ph_fio", lang)
    )
    return kb


def get_reviewer_l1_menu_kb(mode: str = "default") -> ReplyKeyboardMarkup:
    """
    Динамическое меню L1-проверяющего.
    mode='queue'  → пользователь в очереди, показываем только "По филиалам"
    mode='branch' → пользователь в филиалах, показываем только "Очередь заявок"
    mode='default'→ показываем обе кнопки (начальный экран)
    """
    if mode == "queue":
        buttons = [[KeyboardButton(text="📊 По филиалам")]]
    elif mode == "branch":
        buttons = [[KeyboardButton(text="📋 Очередь заявок")]]
    else:
        buttons = [[KeyboardButton(text="📋 Очередь заявок"), KeyboardButton(text="📊 По филиалам")]]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def get_reviewer_l2_menu_kb() -> ReplyKeyboardMarkup:
    """Главное меню для L2-проверяющего."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Ожидающие подтверждения")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )

