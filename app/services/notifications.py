"""
Сервис уведомлений для L1/L2 проверяющих.

Функции вызываются из хендлеров при смене статусов.
"""

import logging
from typing import Optional

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telegram_account import TelegramAccount, TgRole
from app.models.request import Request, RequestStatus

logger = logging.getLogger(__name__)

# ── Константы ────────────────────────────────────────────────────────────
TYPE_LABELS = {"replacement": "Замена", "new_issue": "Новая выдача", "repair": "Поломка"}
EQUIP_LABELS = {"computer": "ПК", "printer": "Принтер"}


async def _get_tg_ids_by_role(session: AsyncSession, role: TgRole) -> list[int]:
    """Получить все Telegram ID пользователей с заданной ролью."""
    stmt = select(TelegramAccount.telegram_user_id).where(TelegramAccount.role == role)
    result = await session.scalars(stmt)
    return list(result.all())


async def notify_l1_new_request(bot: Bot, session: AsyncSession, request: Request):
    """Уведомить всех L1-проверяющих о новой заявке."""
    l1_ids = await _get_tg_ids_by_role(session, TgRole.reviewer_l1)
    if not l1_ids:
        logger.warning("Нет L1-проверяющих для уведомления!")
        return

    equip = EQUIP_LABELS.get(request.equipment_type, request.equipment_type)
    text = (
        f"🔔 *Новая заявка #{request.request_number}*\n\n"
        f"Филиал: {request.branch_name_snapshot} ({request.bhm_code_snapshot})\n"
        f"Сотрудник: {request.employee_fio_snapshot}\n"
        f"Тип: {TYPE_LABELS.get(request.request_type, request.request_type)}\n"
        f"Устройство: {equip}"
    )

    for tg_id in l1_ids:
        try:
            await bot.send_message(tg_id, text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление L1 (tg_id={tg_id}): {e}")


async def notify_l2_batch_approved(
    bot: Bot,
    session: AsyncSession,
    bhm_code: str,
    branch_name: str,
    count: int,
):
    """Уведомить всех L2-проверяющих что L1 одобрил пачку по филиалу."""
    l2_ids = await _get_tg_ids_by_role(session, TgRole.reviewer_l2)
    if not l2_ids:
        logger.info("Нет L2-проверяющих — уведомление пропущено")
        return

    text = (
        f"📬 *Новые заявки для подтверждения*\n\n"
        f"📍 Филиал: {branch_name} ({bhm_code})\n"
        f"L1 одобрено: {count} заявок\n\n"
        f"📞 _Не забудьте позвонить руководителю филиала_"
    )

    for tg_id in l2_ids:
        try:
            await bot.send_message(tg_id, text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление L2 (tg_id={tg_id}): {e}")


async def notify_auto_approved_pc(bot: Bot, session: AsyncSession, request: Request):
    """Уведомить L1 и L2 об автоматическом одобрении замены ПК (>= 5 лет)."""
    l1_ids = await _get_tg_ids_by_role(session, TgRole.reviewer_l1)
    l2_ids = await _get_tg_ids_by_role(session, TgRole.reviewer_l2)
    
    text = (
        f"🤖 *АВТО-ОДОБРЕНИЕ (Срок службы истек)*\n\n"
        f"Заявка #{request.request_number}\n"
        f"Филиал: {request.branch_name_snapshot} ({request.bhm_code_snapshot})\n"
        f"Сотрудник: {request.employee_fio_snapshot}\n"
        f"Инвентарный код: {request.inventory_code_snapshot}\n"
        f"✅ *Заявка направлена в отдел выдачи.*"
    )
    
    # set чтобы не дублировать если человек и L1 и L2
    for tg_id in set(l1_ids + l2_ids):
        try:
            await bot.send_message(tg_id, text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Не удалось отправить авто-уведомление (tg_id={tg_id}): {e}")


async def notify_employee_result(
    bot: Bot,
    session: AsyncSession,
    request: Request,
    decision: str,
    reason: Optional[str] = None,
):
    """Уведомить сотрудника об итоговом решении по его заявке."""
    # Находим TG ID сотрудника
    stmt = select(TelegramAccount.telegram_user_id).where(
        TelegramAccount.id == request.telegram_account_id
    )
    tg_id = await session.scalar(stmt)
    if not tg_id:
        return

    if decision == "approved":
        text = (
            f"✅ *Ваша заявка #{request.request_number} одобрена!*\n\n"
            f"Техника будет выдана/заменена в ближайшее время."
        )
    else:
        text = (
            f"❌ *Ваша заявка #{request.request_number} отклонена.*\n\n"
            f"Причина: _{reason or 'не указана'}_"
        )

    try:
        await bot.send_message(tg_id, text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Не удалось уведомить сотрудника (tg_id={tg_id}): {e}")


async def notify_l1_escalation(bot: Bot, session: AsyncSession, request: Request, comment: str):
    """Уведомить L1 о том, что сотрудник не подтвердил починку (Сломан)."""
    l1_ids = await _get_tg_ids_by_role(session, TgRole.reviewer_l1)
    
    equip = "Компьютер" if request.equipment_type == "computer" else "Принтер"
    text = (
        f"🔴 *Эскалация по ремонту!*\n\n"
        f"Заявка: #{request.request_number}\n"
        f"Филиал: {request.branch_name_snapshot} ({request.bhm_code_snapshot})\n"
        f"Сотрудник: {request.employee_fio_snapshot}\n"
        f"Техника: {equip} ({request.inventory_code_snapshot})\n\n"
        f"📝 *Комментарий сотрудника:*\n_{comment}_"
    )
    
    for tg_id in l1_ids:
        try:
            await bot.send_message(tg_id, text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление L1 об эскалации (tg_id={tg_id}): {e}")


async def notify_l2_sla_breach(bot: Bot, session: AsyncSession, request: Request, hours_passed: float):
    """Уведомляет L2 об истечении SLA (заявка висит более 24 раб. часов)."""
    l2_ids = await _get_tg_ids_by_role(session, TgRole.reviewer_l2)
    
    equip = "Компьютер" if request.equipment_type == "computer" else "Принтер"
    text = (
        f"🚨 *SLA НАРУШЕН (Более {hours_passed} раб. часов)*\n\n"
        f"Заявка #{request.request_number} на ремонт висит без ответа пользователя!\n"
        f"Филиал: {request.branch_name_snapshot} ({request.bhm_code_snapshot})\n"
        f"Сотрудник: {request.employee_fio_snapshot}\n"
        f"Техника: {equip} ({request.inventory_code_snapshot})\n\n"
        f"⚡ Свяжитесь с сотрудником или IT-отделом для закрытия заявки."
    )
    
    for tg_id in l2_ids:
        try:
            await bot.send_message(tg_id, text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Не удалось отправить SLA alert L2 (tg_id={tg_id}): {e}")
