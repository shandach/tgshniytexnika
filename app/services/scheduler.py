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
        except Exception as e:
            logger.error(f"Error in SLA scheduler: {e}")
            
        # Проверяем каждые полчаса-час в проде, поставим 30 минут (1800 сек)
        await asyncio.sleep(1800)
