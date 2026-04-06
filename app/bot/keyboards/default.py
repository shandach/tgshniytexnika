from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu_kb() -> ReplyKeyboardMarkup:
    """Главное меню бота."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Компьютер"), KeyboardButton(text="Принтер")],
            [KeyboardButton(text="Статус моей заявки")],
            [KeyboardButton(text="Сообщить об ошибке")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите нужное действие..."
    )
    return kb


def get_request_type_kb() -> ReplyKeyboardMarkup:
    """Меню выбора типа заявки после выбора техники."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Выдача новой")],
            [KeyboardButton(text="Замена")],
            [KeyboardButton(text="Поломка")],
            [KeyboardButton(text="⬅️ Назад в меню")]
        ],
        resize_keyboard=True
    )
    return kb


def get_cancel_kb() -> ReplyKeyboardMarkup:
    """Кнопка отмены/возврата для FSM состояний."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⬅️ Отмена и в меню")]
        ],
        resize_keyboard=True
    )
    return kb


def get_fio_reuse_kb(fio: str, position: str) -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой для использования предыдущих данных."""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"Использовать: {fio} ({position})")],
            [KeyboardButton(text="⬅️ Отмена и в меню")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Введите новые данные или используйте старые"
    )
    return kb
