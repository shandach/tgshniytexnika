from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from aiogram import Bot
from app.config import settings

from app.api.deps import get_current_user
from app.api.schemas.pydantic_models import (
    RequestResponse, RequestListResponse, 
    RequestStatusUpdate, CommentCreate, CommentResponse
)
from app.database import get_session
from app.models.user import User
from app.models.request import Request, RequestComment, RequestStatus, FinalDecision
from app.models.inventory import Inventory, InventoryStatus

router = APIRouter(prefix="/requests", tags=["requests"])


@router.get("", response_model=RequestListResponse)
async def get_requests(
    bhm_code: Optional[str] = None,
    status: Optional[str] = None,
    equipment_type: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Список заявок с фильтрацией и пагинацией."""
    stmt = select(Request)
    
    # Считаем общее количество для пагинации (до лимитов/офсетов, но после фильтров)
    count_stmt = select(func.count(Request.id))

    filters = []
    if bhm_code:
        filters.append(Request.bhm_code_snapshot == bhm_code)
    if status:
        filters.append(Request.status == status)
    if equipment_type:
        filters.append(Request.equipment_type == equipment_type)

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    # Сортировка - новые сверху
    stmt = stmt.order_by(Request.created_at.desc()).limit(limit).offset(offset)
    
    # Eager loading комментариев
    stmt = stmt.options(selectinload(Request.comments))

    total_reqs = await session.scalar(count_stmt)
    reqs = await session.scalars(stmt)

    return RequestListResponse(
        items=list(reqs),
        total=total_reqs or 0
    )


@router.get("/{request_id}", response_model=RequestResponse)
async def get_request(
    request_id: int, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Детали одной заявки вместе с комментариями."""
    stmt = select(Request).where(Request.id == request_id).options(selectinload(Request.comments))
    req = await session.scalar(stmt)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


@router.patch("/{request_id}/status", response_model=RequestResponse)
async def update_request_status(
    request_id: int,
    payload: RequestStatusUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Смена статуса, итогового решения или причины отказа заявки."""
    stmt = select(Request).where(Request.id == request_id).options(selectinload(Request.comments))
    req = await session.scalar(stmt)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # TODO: Google Sheets sync here (Variant A)
    # from app.services.gsheets import ...

    # Обновляем поля
    if payload.status:
        req.status = payload.status
        if payload.status == RequestStatus.closed:
            req.closed_at = func.now()

    if payload.final_decision:
        req.final_decision = payload.final_decision
        
    if payload.reject_reason is not None:
        req.reject_reason = payload.reject_reason

    if req.status == RequestStatus.closed and req.final_decision == FinalDecision.approved and req.request_type == "repair":
        if req.inventory_id:
            inv_stmt = select(Inventory).where(Inventory.id == req.inventory_id)
            inv = await session.scalar(inv_stmt)
            if inv:
                inv.status = InventoryStatus.repair

    # Send Telegram notification if closed
    if payload.status == RequestStatus.closed and req.telegram_account:
        try:
            temp_bot = Bot(token=settings.BOT_TOKEN)
            decision_text = "Одобрено" if req.final_decision == FinalDecision.approved else "Отклонено"
            msg = f"🔔 Ваша заявка #{req.request_number} была закрыта.\n\nРешение: **{decision_text}**"
            if payload.reject_reason:
                msg += f"\nПричина: {payload.reject_reason}"
            await temp_bot.send_message(chat_id=req.telegram_account.telegram_user_id, text=msg, parse_mode="Markdown")
            await temp_bot.session.close()
        except Exception as e:
            import logging
            logging.error(f"Failed to send TG notification: {e}")

    await session.commit()
    await session.refresh(req)
    return req


@router.post("/{request_id}/comments", response_model=CommentResponse)
async def add_comment(
    request_id: int,
    payload: CommentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Добавить комментарий от проверяющего."""
    # Проверяем что заявка есть
    req = await session.get(Request, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    comment = RequestComment(
        request_id=request_id,
        author_name=current_user.full_name,
        comment_text=payload.comment_text
    )
    
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    return comment
