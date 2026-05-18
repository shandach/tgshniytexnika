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


async def _get_l1_ids_by_region(session: AsyncSession, region_name: str) -> list[int]:
    """Получить Telegram ID L1-проверяющих, привязанных к указанной области."""
    stmt = select(TelegramAccount.telegram_user_id).where(
        TelegramAccount.role == TgRole.reviewer_l1,
        TelegramAccount.assigned_region == region_name,
    )
    result = await session.scalars(stmt)
    return list(result.all())


async def notify_l1_new_request(bot: Bot, session: AsyncSession, request: Request):
    """Уведомить L1-проверяющего области о новой заявке."""
    # Определяем область филиала заявки
    from app.models.branch import BhmBranch
    stmt = select(BhmBranch.region_name).where(BhmBranch.id == request.branch_id)
    region = await session.scalar(stmt)

    # Ищем L1 проверяющих этой области
    l1_ids = []
    if region:
        l1_ids = await _get_l1_ids_by_region(session, region)
    # Fallback: если нет регионального проверяющего — отправляем всем L1
    if not l1_ids:
        l1_ids = await _get_tg_ids_by_role(session, TgRole.reviewer_l1)
    if not l1_ids:
        logger.warning("Нет L1-проверяющих для уведомления!")
        return

    equip = EQUIP_LABELS.get(request.equipment_type, request.equipment_type)
    
    if request.request_type == "repair":
        text = (
            f"🛠 *Уведомление о поломке #{request.request_number}*\n\n"
            f"Филиал: {request.branch_name_snapshot} ({request.bhm_code_snapshot})\n"
            f"Сотрудник: {request.employee_fio_snapshot}\n"
            f"Устройство: {equip}\n\n"
            f"ℹ️ _Заявка уже в работе у специалистов. От вас действий не требуется._"
        )
    else:
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
    """Уведомить L1 области о том, что сотрудник не подтвердил починку (Сломан)."""
    from app.models.branch import BhmBranch
    stmt = select(BhmBranch.region_name).where(BhmBranch.id == request.branch_id)
    region = await session.scalar(stmt)

    l1_ids = []
    if region:
        l1_ids = await _get_l1_ids_by_region(session, region)
    if not l1_ids:
        l1_ids = await _get_tg_ids_by_role(session, TgRole.reviewer_l1)
        
    if not l1_ids:
        return

    # Получаем языки проверяющих
    stmt_lang = select(TelegramAccount.telegram_user_id, TelegramAccount.language).where(
        TelegramAccount.telegram_user_id.in_(l1_ids)
    )
    langs = dict((await session.execute(stmt_lang)).all())

    for tg_id in l1_ids:
        lang = langs.get(tg_id, "ru")
        
        if lang == "uz":
            equip = "Kompyuter" if request.equipment_type == "computer" else "Printer"
            text = (
                f"🔴 *Ta'mirlash bo'yicha eskalatsiya!*\n\n"
                f"Ariza: #{request.request_number}\n"
                f"Filial: {request.branch_name_snapshot} ({request.bhm_code_snapshot})\n"
                f"Xodim: {request.employee_fio_snapshot}\n"
                f"Texnika: {equip} ({request.inventory_code_snapshot})\n\n"
                f"📝 *Xodimning izohi:*\n_{comment}_"
            )
        else:
            equip = "Компьютер" if request.equipment_type == "computer" else "Принтер"
            text = (
                f"🔴 *Эскалация по ремонту!*\n\n"
                f"Заявка: #{request.request_number}\n"
                f"Филиал: {request.branch_name_snapshot} ({request.bhm_code_snapshot})\n"
                f"Сотрудник: {request.employee_fio_snapshot}\n"
                f"Техника: {equip} ({request.inventory_code_snapshot})\n\n"
                f"📝 *Комментарий сотрудника:*\n_{comment}_"
            )

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


async def notify_reviewers_repair_closed(bot: Bot, session: AsyncSession, request: Request):
    """Уведомить L1 и L2, что сотрудник подтвердил починку техники."""
    from app.models.branch import BhmBranch
    stmt = select(BhmBranch.region_name).where(BhmBranch.id == request.branch_id)
    region = await session.scalar(stmt)

    l1_ids = []
    if region:
        l1_ids = await _get_l1_ids_by_region(session, region)
    if not l1_ids:
        l1_ids = await _get_tg_ids_by_role(session, TgRole.reviewer_l1)
    
    l2_ids = await _get_tg_ids_by_role(session, TgRole.reviewer_l2)
    all_reviewer_ids = list(set(l1_ids + l2_ids))
    
    if not all_reviewer_ids:
        return

    # Получаем языки проверяющих
    stmt_lang = select(TelegramAccount.telegram_user_id, TelegramAccount.language).where(
        TelegramAccount.telegram_user_id.in_(all_reviewer_ids)
    )
    langs = dict((await session.execute(stmt_lang)).all())

    for tg_id in all_reviewer_ids:
        lang = langs.get(tg_id, "ru")
        equip = "Компьютер" if request.equipment_type == "computer" else "Принтер"
        if lang == "uz":
            equip = "Kompyuter" if request.equipment_type == "computer" else "Printer"
            text = (
                f"✅ *Ta'mirlash tasdiqlandi!*\n\n"
                f"Ariza #{request.request_number} yopildi.\n"
                f"Filial: {request.branch_name_snapshot} ({request.bhm_code_snapshot})\n"
                f"Xodim: {request.employee_fio_snapshot}\n"
                f"Texnika: {equip} ({request.inventory_code_snapshot})\n\n"
                f"Xodim texnika ishlashini tasdiqladi."
            )
        else:
            text = (
                f"✅ *Починка подтверждена!*\n\n"
                f"Заявка #{request.request_number} закрыта.\n"
                f"Филиал: {request.branch_name_snapshot} ({request.bhm_code_snapshot})\n"
                f"Сотрудник: {request.employee_fio_snapshot}\n"
                f"Техника: {equip} ({request.inventory_code_snapshot})\n\n"
                f"Сотрудник подтвердил, что техника работает."
            )
            
        try:
            await bot.send_message(tg_id, text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to notify reviewer about repair confirmation (tg_id={tg_id}): {e}")
