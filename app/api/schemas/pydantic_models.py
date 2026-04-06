from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.inventory import EquipmentType, InventoryStatus
from app.models.request import RequestType, RequestStatus, FinalDecision
from app.models.user import UserRole


# ── Auth ────────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    login: str
    role: UserRole
    full_name: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


# ── Comments ────────────────────────────────────────────────────────────
class CommentCreate(BaseModel):
    comment_text: str

class CommentResponse(BaseModel):
    id: int
    author_name: str
    comment_text: str
    is_edited: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Inventory ───────────────────────────────────────────────────────────
class InventoryStatusUpdate(BaseModel):
    status: InventoryStatus


class InventoryResponse(BaseModel):
    id: int
    inventory_code: str
    equipment_type: EquipmentType
    issue_year: int
    status: InventoryStatus
    model_config = ConfigDict(from_attributes=True)


# ── Requests ────────────────────────────────────────────────────────────
class RequestStatusUpdate(BaseModel):
    status: Optional[RequestStatus] = None
    final_decision: Optional[FinalDecision] = None
    reject_reason: Optional[str] = None


class RequestResponse(BaseModel):
    id: int
    request_number: str
    employee_fio_snapshot: str
    employee_position_snapshot: Optional[str]
    bhm_code_snapshot: str
    branch_name_snapshot: str
    request_type: RequestType
    equipment_type: str
    inventory_code_snapshot: Optional[str]
    reason_text: Optional[str]
    problem_text: Optional[str]
    status: RequestStatus
    final_decision: FinalDecision
    reject_reason: Optional[str]
    reviewer_comment: Optional[str]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    
    comments: List[CommentResponse] = []
    model_config = ConfigDict(from_attributes=True)


class RequestListResponse(BaseModel):
    items: List[RequestResponse]
    total: int
    

# ── Dashboard KPI ───────────────────────────────────────────────────────
class DashboardKPI(BaseModel):
    active_requests: int
    approved_requests: int
    rejected_requests: int
    total_requests: int
