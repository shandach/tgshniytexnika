from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_user
from app.api.schemas.pydantic_models import DashboardKPI
from app.database import get_session
from app.models.user import User
from app.models.request import Request

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/kpi", response_model=DashboardKPI)
async def get_dashboard_kpi(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Возвращает агрегированную статистику для дашборда."""
    # Получаем все статусы разом
    result = await session.execute(
        select(Request.status, Request.final_decision, func.count(Request.id))
        .group_by(Request.status, Request.final_decision)
    )
    
    rows = result.all()
    
    total = 0
    active = 0
    approved = 0
    rejected = 0
    
    for row in rows:
        status, decision, count = row
        total += count
        
        if status in ["new", "in_progress"]:
            active += count
            
        if status == "closed":
            if decision == "approved":
                approved += count
            elif decision == "rejected":
                rejected += count
                
    return DashboardKPI(
        active_requests=active,
        approved_requests=approved,
        rejected_requests=rejected,
        total_requests=total
    )

@router.get("/analytics")
async def get_analytics(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Возвращает данные для построения графиков."""
    # Заглушка: тут можно собрать агрегации по датам, филиалам и типам техники
    return {"message": "Analytics endpoint ready for implementation"}
