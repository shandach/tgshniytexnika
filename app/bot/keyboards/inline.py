from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_inline_language_kb() -> InlineKeyboardMarkup:
    """Инлайн-клавиатура для переключения языка без прерывания FSM."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 Узбекский", callback_data="lang_uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
            ]
        ]
    )
