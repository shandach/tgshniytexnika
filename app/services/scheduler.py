"""
Скрипт проверки SLA (24 рабочих часа) по сломанным заявкам.
Запускается как фоновый asyncio процесс вместе с ботом (в main.py).
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.models.request import Request
from app.models.telegram_account import TelegramAccount
from app.services.notifications import notify_l2_sla_breach

logger = logging.getLogger(__name__)

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")

def get_working_hours(start_dt: datetime, end_dt: datetime) -> float:
    """Вычисляет кол-во рабочих часов между двумя датами по Ташкентскому времени (Пн-Пт, 09:00 - 18:00)."""
    start = start_dt.astimezone(TASHKENT_TZ)
    end = end_dt.astimezone(TASHKENT_TZ)
    
    if start >= end:
        return 0.0
        
    current = start
    hours = 0.0
    
    # 15 minute increments to accurately calculate elapsed working time
    while current < end:
        next_dt = min(current + timedelta(minutes=15), end)
        
        # Check if current time is within working hours (Mon-Fri 09:00-18:00)
        if current.weekday() < 5 and 9 <= current.hour < 18:
            delta = (next_dt - current).total_seconds() / 3600.0
            hours += delta
            
        current = next_dt
        
    return hours


def calculate_next_notification_time(base_dt: datetime) -> datetime:
    """
    Рассчитывает время следующего уведомления (через 24 часа от base_dt).
    Если выпадает на выходные -> переносится на Понедельник 09:00.
    Если выпадает на будний день после 19:30 -> переносится на след. рабочий день 09:00.
    Если выпадает на будний день до 09:00 -> переносится на этот же день 09:00.
    """
    target = base_dt + timedelta(hours=24)
    target_tz = target.astimezone(TASHKENT_TZ)
    
    # Суббота (5) или Воскресенье (6)
    if target_tz.weekday() >= 5:
        days_ahead = 7 - target_tz.weekday()
        target_tz = target_tz + timedelta(days=days_ahead)
        target_tz = target_tz.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        # Будние дни
        time_19_30 = target_tz.replace(hour=19, minute=30, second=0, microsecond=0)
        time_09_00 = target_tz.replace(hour=9, minute=0, second=0, microsecond=0)
        
        if target_tz >= time_19_30:
            # Переносим на следующий день 09:00 (если пятница, то на понедельник)
            if target_tz.weekday() == 4: # Пятница
                target_tz = target_tz + timedelta(days=3)
            else:
                target_tz = target_tz + timedelta(days=1)
            target_tz = target_tz.replace(hour=9, minute=0, second=0, microsecond=0)
        elif target_tz < time_09_00:
            # Слишком рано утром, переносим на 09:00 того же дня
            target_tz = time_09_00
            
    return target_tz


async def check_employee_repair_reminders(session_factory: async_sessionmaker, bot):
    """
    Проверяет заявки на поломку (in_progress) и каждые 24ч отправляет
    напоминание сотруднику подтвердить починку техники.
    """
    logger.info("Checking employee repair reminders...")
    async with session_factory() as session:
        stmt = select(Request, TelegramAccount.language).join(
            TelegramAccount, Request.telegram_account_id == TelegramAccount.id
        ).where(
            Request.request_type == "repair",
            Request.status == "in_progress"
        )
        result = await session.execute(stmt)
        rows = result.all()
        
        now = datetime.now(timezone.utc).astimezone(TASHKENT_TZ)
        
        for req, lang in rows:
            # Точка отсчета - либо последнее уведомление, либо создание заявки
            base_time = req.last_notified_at or req.created_at
            next_time = calculate_next_notification_time(base_time)
            
            if now >= next_time:
                # Пора отправлять уведомление
                msg_ru = (
                    f"🔔 *Напоминание по заявке #{req.request_number}*\n\n"
                    f"Ваша техника чинится уже некоторое время. Пожалуйста, зайдите в раздел "
                    f"«Статус заявок / Мои заявки» и проверьте статус.\n\n"
                    f"👉 *Если всё работает* — обязательно подтвердите это в меню заявки, "
                    f"чтобы мы могли её закрыть.\n"
                    f"👉 *Если проблема осталась* — укажите это там же, и мы ускорим процесс."
                )
                msg_uz = (
                    f"🔔 *Ariza #{req.request_number} bo'yicha eslatma*\n\n"
                    f"Texnikangiz bir muddatdan beri ta'mirlanmoqda. Iltimos, «Arizalar holati / Mening arizalarim» "
                    f"bo'limiga kiring va holatni tekshiring.\n\n"
                    f"👉 *Agar hammasi ishlayotgan bo'lsa* — buni ariza menyusida tasdiqlang, "
                    f"shunda biz uni yopishimiz mumkin.\n"
                    f"👉 *Agar muammo qolgan bo'lsa* — buni ham o'sha yerda ko'rsating, jarayonni tezlashtiramiz."
                )
                
                text = msg_ru if lang == "ru" else msg_uz
                
                # Inline-кнопка для быстрого перехода к списку заявок
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                btn_text = "Мои заявки" if lang == "ru" else "Mening arizalarim"
                kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text=btn_text, callback_data="myreqs_list")
                ]])
                
                try:
                    # Получаем ID сотрудника, подавшего заявку
                    stmt_tg = select(TelegramAccount.telegram_user_id).where(TelegramAccount.id == req.telegram_account_id)
                    tg_user_id = await session.scalar(stmt_tg)
                    
                    if tg_user_id:
                        await bot.send_message(tg_user_id, text, parse_mode="Markdown", reply_markup=kb)
                        logger.info(f"Sent repair reminder to user {tg_user_id} for request #{req.request_number}")
                        # Обновляем время последнего уведомления
                        req.last_notified_at = datetime.now(timezone.utc)
                        await session.commit()
                except Exception as e:
                    logger.error(f"Failed to send repair reminder for request #{req.request_number}: {e}")


async def check_slas(session_factory: async_sessionmaker, bot):
    """Проверка всех открытых сломанных заявок на нарушение 24-часового SLA."""
    logger.info("Checking repair SLAs...")
    # use context manager with async session factory
    async with session_factory() as session:
        stmt = select(Request).where(
            Request.request_type == "repair",
            Request.status == "in_progress",
            Request.sla_escalated == False
        )
        result = await session.execute(stmt)
        requests = result.scalars().all()
        
        now = datetime.now(timezone.utc)
        
        for req in requests:
            wh = get_working_hours(req.created_at, now)
            if wh >= 24.0:
                logger.warning(f"SLA breached for Request #{req.request_number} ({wh} hours)")
                req.sla_escalated = True
                await session.commit()
                # Notify L2
                try:
                    await notify_l2_sla_breach(bot, session, req, round(wh, 1))
                except Exception as e:
                    logger.error(f"Failed to notify L2 about SLA breach: {e}")


async def sla_scheduler_loop(session_factory: async_sessionmaker, bot):
    """Бесконечный цикл планировщика (запускается при старте)."""
    # Ждем 1 минуту после старта
    await asyncio.sleep(60)
    
    while True:
        try:
            await check_slas(session_factory, bot)
            await check_employee_repair_reminders(session_factory, bot)
        except Exception as e:
            logger.error(f"Error in SLA scheduler: {e}")
            
        # Проверяем каждые полчаса-час в проде, поставим 30 минут (1800 сек)
        await asyncio.sleep(1800)
