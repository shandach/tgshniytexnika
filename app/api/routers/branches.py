"""GET /api/branches — список филиалов для дропдауна дашборда."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.branch import BhmBranch
from app.models.user import User

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get("")
async def list_branches(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Возвращает все активные филиалы в формате {n, c, lt} для фронта."""
    stmt = (
        select(BhmBranch)
        .where(BhmBranch.is_active == True)
        .order_by(BhmBranch.branch_name)
    )
    rows = (await session.scalars(stmt)).all()
    return [
        {"n": b.branch_name, "c": b.bhm_code, "lt": b.location_type, "rn": b.region_name}
        for b in rows
    ]
