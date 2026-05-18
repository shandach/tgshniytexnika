"""
GET /api/tickets — заявки в формате Ticket-интерфейса для bxm_complete.html.

Маппинг backend status/decision → UI status:
  new + pending       → "pending"
  in_progress + *     → "processing"
  closed + approved   → "approved"
  closed + rejected   → "rejected"
  closed + pending    → "repair"   (repair-заявки без решения)
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database import get_session
from app.models.request import Request, RequestType
from app.models.user import User

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _ui_status(status: str, decision: str) -> str:
    """Маппинг (status, final_decision) → UI-статус для фронтенда."""
    if status == "new":
        return "pending"
    if status in ("in_progress", "approved_l1"):
        return "processing"
    # closed
    if decision == "approved":
        return "approved"
    if decision == "rejected":
        return "rejected"
    return "repair"


def _ui_type(rt: str) -> str:
    """Маппинг RequestType → UI type."""
    mapping = {"replacement": "replacement", "new_issue": "new", "repair": "repair"}
    return mapping.get(rt, rt)


def _initials(fio: str) -> str:
    """Извлекает инициалы из ФИО."""
    parts = fio.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return fio[:2].upper() if fio else "??"


def _format_date_display(dt: datetime) -> str:
    """Формат даты для отображения: '12 Apr 2025'."""
    months = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
    }
    return f"{dt.day} {months[dt.month]} {dt.year}"


def _format_date_filter(dt: datetime) -> str:
    """Формат даты для фильтрации: '2025-04-12'."""
    return dt.strftime("%Y-%m-%d")


@router.get("")
async def get_tickets(
    branch: Optional[str] = None,
    type: Optional[str] = None,
    q: Optional[str] = None,
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Возвращает массив заявок в Ticket-формате для HTML-дашборда.

    Фильтры:
      ?branch=BXM01 — по коду филиала
      &type=replacement|new|repair — по типу заявки
      &from=2025-04-01&to=2025-04-30 — по дате создания
      &q=поиск — по номеру заявки, ФИО или названию филиала
    """
    stmt = select(Request).order_by(Request.created_at.desc()).options(
        selectinload(Request.inventory),
        selectinload(Request.branch)
    )

    filters = []
    if branch:
        filters.append(Request.bhm_code_snapshot == branch)
    if type:
        type_map = {"replacement": "replacement", "new": "new_issue", "repair": "repair"}
        db_type = type_map.get(type, type)
        filters.append(Request.request_type == db_type)
    if date_from:
        filters.append(func.date(Request.created_at) >= date_from)
    if date_to:
        filters.append(func.date(Request.created_at) <= date_to)
    if q:
        q_pattern = f"%{q}%"
        filters.append(
            or_(
                Request.request_number.ilike(q_pattern),
                Request.employee_fio_snapshot.ilike(q_pattern),
                Request.branch_name_snapshot.ilike(q_pattern),
            )
        )

    if filters:
        stmt = stmt.where(*filters)

    rows = (await session.scalars(stmt)).all()

    tickets = []
    for r in rows:
        ui_type = _ui_type(r.request_type)
        device = "Принтер" if r.equipment_type == "printer" else "Компьютер"
        
        region_name = r.branch.region_name if r.branch else ""
        city_name = r.branch.city_name if r.branch else ""
        clean_bn = r.branch.branch_name if r.branch else r.branch_name_snapshot
        
        tickets.append({
            "id": r.id,
            "rn": region_name,
            "city": city_name,
            "bn": clean_bn,
            "bc": r.bhm_code_snapshot,
            "lt": "",  # будет заполнено фронтом из BRANCHES
            "type": ui_type,
            "dev": device,
            "inv": r.inventory_code_snapshot or "—",
            "emp": r.employee_fio_snapshot,
            "pos": r.employee_position_snapshot or "",
            "init": _initials(r.employee_fio_snapshot),
            "year": "—" if r.request_type == "new_issue" else (r.inventory.issue_year if r.inventory and r.inventory.issue_year else "—"),
            "status": _ui_status(r.status, r.final_decision),
            "ds": _format_date_display(r.created_at) if r.created_at else "",
            "dv": _format_date_filter(r.created_at) if r.created_at else "",
        })

    return tickets
