"""
Изолированная логика работы с БД для нужд Telegram-бота.
"""

from typing import Optional, Sequence
from datetime import datetime, timezone
from sqlalchemy import select, or_, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.branch import BhmBranch
from app.models.telegram_account import TelegramAccount
from app.models.employee import Employee
from app.models.inventory import Inventory, EquipmentType, InventoryStatus
from app.models.request import Request, RequestStatus, RequestType

from app.utils.fio import compute_fio_fields


async def get_or_create_tg_account(session: AsyncSession, tg_user_id: int) -> TelegramAccount:
    """Получает TelegramAccount по tg_user_id. Если нет — создает."""
    stmt = select(TelegramAccount).where(TelegramAccount.telegram_user_id == tg_user_id)
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if account:
        account.last_seen_at = now
        await session.commit()
    else:
        account = TelegramAccount(
            telegram_user_id=tg_user_id,
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(account)
        await session.commit()
        await session.refresh(account)

    return account


async def get_branch_by_bhm(session: AsyncSession, bhm_code: str) -> Optional[BhmBranch]:
    """Проверяет и возвращает филиал по BXM коду."""
    stmt = select(BhmBranch).where(BhmBranch.bhm_code == bhm_code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def check_inventory_lock(session: AsyncSession, inventory_code: str) -> bool:
    """
    Возвращает True, если инвентарный код ЗАБЛОКИРОВАН
    (уже есть активная заявка new/in_progress по нему).
    """
    stmt = select(Request).where(
        and_(
            Request.inventory_code_snapshot == inventory_code,
            Request.status.in_([RequestStatus.new, RequestStatus.in_progress])
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_inventory_by_code(session: AsyncSession, code: str) -> Optional[Inventory]:
    """Возвращает технику по коду инвентаря вместе с филиалом."""
    stmt = select(Inventory).options(joinedload(Inventory.branch)).where(Inventory.inventory_code == code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def find_employee_by_fio_and_branch(
    session: AsyncSession, fio_raw: str, branch_id: int
) -> Optional[Employee]:
    """Ищет сотрудника (строгое совпадение по нормализованному ФИО)."""
    _, translit = compute_fio_fields(fio_raw)
    stmt = select(Employee).where(
        and_(
            Employee.fio_normalized == translit,
            Employee.branch_id == branch_id
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_employee(
    session: AsyncSession, fio_raw: str, position: str, branch_id: int
) -> Employee:
    """Ищет или создает сотрудника. Если существует — обновляет должность."""
    _, translit = compute_fio_fields(fio_raw)
    
    stmt = select(Employee).where(
        and_(
            Employee.fio_normalized == translit,
            Employee.branch_id == branch_id
        )
    )
    result = await session.execute(stmt)
    emp = result.scalar_one_or_none()

    if emp:
        if position and emp.position != position:
            emp.position = position
        await session.commit()
    else:
        emp = Employee(
            fio_original=fio_raw,
            fio_normalized=translit,
            position=position,
            branch_id=branch_id,
        )
        session.add(emp)
        await session.commit()
        await session.refresh(emp)
        
    return emp


async def generate_request_number(session: AsyncSession) -> str:
    """Генерирует уникальный номер заявки (YMD-xxxx)."""
    date_str = datetime.now().strftime("%Y%m%d")
    # Ищем последнюю заявку за сегодня
    stmt = select(Request).where(Request.request_number.like(f"{date_str}-%")).order_by(Request.id.desc()).limit(1)
    result = await session.execute(stmt)
    last_req = result.scalar_one_or_none()

    if last_req:
        last_num = int(last_req.request_number.split("-")[1])
        new_num = last_num + 1
    else:
        new_num = 1

    return f"{date_str}-{new_num:04d}"


async def create_request(
    session: AsyncSession,
    tg_account_id: int,
    request_type: RequestType,
    equipment_type: EquipmentType,
    fio_raw: str,
    position: str,
    branch: BhmBranch,
    inventory: Optional[Inventory] = None,
    inventory_code_raw: Optional[str] = None,
    reason: Optional[str] = None,
    problem: Optional[str] = None,
    status: RequestStatus = RequestStatus.new,
    final_decision: Optional[str] = None,
) -> Request:
    """Создает новую заявку."""
    # Получаем или создаем сотрудника (чтобы сохранить в справочнике ФИО+должность)
    emp = await get_or_create_employee(session, fio_raw, position, branch.id)
    
    basic, translit = compute_fio_fields(fio_raw)
    req_number = await generate_request_number(session)

    req = Request(
        request_number=req_number,
        telegram_account_id=tg_account_id,
        employee_id=emp.id,
        employee_fio_snapshot=fio_raw,
        employee_fio_normalized_basic=basic,
        employee_fio_normalized_translit=translit,
        employee_position_snapshot=position,
        branch_id=branch.id,
        bhm_code_snapshot=branch.bhm_code,
        branch_name_snapshot=branch.branch_name,
        request_type=request_type,
        equipment_type=equipment_type,
        inventory_id=inventory.id if inventory else None,
        inventory_code_snapshot=inventory.inventory_code if inventory else inventory_code_raw,
        reason_text=reason,
        problem_text=problem,
        status=status,
        final_decision=final_decision,
    )
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return req


async def get_requests_by_tg_account(session: AsyncSession, tg_account_id: int) -> Sequence[Request]:
    """Получает все заявки данного Telegram-аккаунта (для функции 'Статус моей заявки')."""
    from sqlalchemy import case, and_, desc
    
    # Приоритет 0 для активных заявок на поломку, 1 для всех остальных
    priority_expr = case(
        (and_(Request.request_type == "repair", Request.status != "closed"), 0),
        else_=1
    )
    
    stmt = (
        select(Request)
        .where(Request.telegram_account_id == tg_account_id)
        .order_by(priority_expr, Request.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_previous_employee_data(session: AsyncSession, tg_account_id: int) -> Optional[dict]:
    """Пытается получить ФИО и Должность из последней заявки аккаунта для автоподстановки."""
    stmt = select(Request).where(Request.telegram_account_id == tg_account_id).order_by(Request.id.desc()).limit(1)
    result = await session.execute(stmt)
    req = result.scalar_one_or_none()
    
    if req:
        return {
            "fio": req.employee_fio_snapshot,
            "position": req.employee_position_snapshot
        }
    return None
