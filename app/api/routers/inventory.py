from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.api.deps import get_current_user
from app.api.schemas.pydantic_models import InventoryResponse, InventoryStatusUpdate
from app.database import get_session
from app.models.user import User
from app.models.inventory import Inventory
from app.models.branch import BhmBranch

router = APIRouter(prefix="/inventory", tags=["inventory"])

@router.get("/tree")
async def get_inventory_tree(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Возвращает список филиалов (с регионами и городами) и весь привязанный инвентарь.
    Фронтенд может сгруппировать это по Регион -> Улица -> BXM.
    """
    stmt = select(BhmBranch)
    branches_res = await session.scalars(stmt)
    branches = list(branches_res)
    
    stmt_inv = select(Inventory)
    inventories_res = await session.scalars(stmt_inv)
    inventories = list(inventories_res)
    
    # Группируем inventory_list по branch_id
    inv_by_branch = {}
    for inv in inventories:
        inv_by_branch.setdefault(inv.branch_id, []).append({
            "id": inv.id,
            "code": inv.inventory_code,
            "type": inv.equipment_type.value,
            "status": inv.status.value,
            "year": inv.issue_year
        })
        
    result = {}
    for branch in branches:
        region = branch.region_name
        city = branch.city_name
        bhm = branch.bhm_code
        
        if region not in result:
            result[region] = {}
        if city not in result[region]:
            result[region][city] = {}
        if bhm not in result[region][city]:
            result[region][city][bhm] = []
            
        result[region][city][bhm].extend(inv_by_branch.get(branch.id, []))
        
    return result

@router.patch("/{inventory_code}/status", response_model=InventoryResponse)
async def update_inventory_status(
    inventory_code: str,
    payload: InventoryStatusUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Ручное переключение статуса техники проверяющим."""
    stmt = select(Inventory).where(Inventory.inventory_code == inventory_code)
    inventory = await session.scalar(stmt)
    
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
        
    inventory.status = payload.status
    await session.commit()
    await session.refresh(inventory)
    
    return inventory
