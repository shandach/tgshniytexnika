import aiosmtplib
from email.message import EmailMessage
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.bot.states.forms import ErrorReportForm
from app.bot.keyboards.default import get_cancel_kb, get_main_menu_kb
from app.config import settings

logger = logging.getLogger(__name__)
router = Router()


from app.bot.utils.texts import _, get_text_variants


@router.message(F.text.in_(get_text_variants("btn_error")))
async def start_error_report(message: Message, state: FSMContext):
    """Начало FSM для отправки отчета об ошибке."""
    data = await state.get_data()
    lang = data.get("language", "ru")
    await message.answer(
        _("rep_start", lang),
        reply_markup=get_cancel_kb(lang)
    )
    await state.set_state(ErrorReportForm.waiting_for_error_text)


@router.message(ErrorReportForm.waiting_for_error_text)
async def process_error_text(message: Message, state: FSMContext):
    """Отправка email с описанием ошибки."""
    data = await state.get_data()
    lang = data.get("language", "ru")
    
    error_text = message.text
    user = message.from_user
    username = f"@{user.username}" if user.username else str(user.id)
    content = f"Пользователь: {username} (ID: {user.id})\nСообщение об ошибке:\n\n{error_text}"
    
    await message.answer(_("rep_sending", lang), reply_markup=get_main_menu_kb(lang))

    try:
        # Формируем Email
        email_msg = EmailMessage()
        email_msg.set_content(content)
        email_msg["Subject"] = "TgTexnika: Сообщение об ошибке от пользователя"
        email_msg["From"] = settings.SMTP_USERNAME
        email_msg["To"] = settings.DEVELOPER_EMAIL

        # Если SMTP не настроен (для тестирования)
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            logger.warning(f"Simulated Error Email sent: {content}")
            await message.answer(_("rep_no_mail", lang))
        else:
            await aiosmtplib.send(
                email_msg,
                hostname=settings.SMTP_SERVER,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                use_tls=True
            )
            await message.answer(_("rep_sent", lang))
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        await message.answer(_("rep_fail", lang))

    await state.set_state(None)
