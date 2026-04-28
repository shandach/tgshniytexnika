from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_inline_language_kb() -> InlineKeyboardMarkup:
    """Инлайн-клавиатура для переключения языка без прерывания FSM."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbek tili", callback_data="lang_uz"),
                InlineKeyboardButton(text="🇷🇺 Русский язык", callback_data="lang_ru")
            ]
        ]
    )
