import enum
import sqlalchemy as sa
from app.database import Base


# ── Enums ───────────────────────────────────────────────────────────────

class RequestType(str, enum.Enum):
    replacement = "replacement"   # Замена
    new_issue = "new_issue"       # Выдача новой
    repair = "repair"             # Поломка


class RequestStatus(str, enum.Enum):
    new = "new"
    in_progress = "in_progress"
    approved_l1 = "approved_l1"
    closed = "closed"


class FinalDecision(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    repaired = "repaired"


# ── Request ─────────────────────────────────────────────────────────────

class Request(Base):
    """
    Основная таблица заявок.

    Хранит snapshot-данные сотрудника и филиала на момент создания,
    чтобы заявка оставалась самодостаточной даже если справочники
    изменятся.
    """

    __tablename__ = "requests"

    id: int = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    request_number: str = sa.Column(sa.String(32), unique=True, nullable=False, index=True)

    # ── Связи ───────────────────────────────────────────────────────
    telegram_account_id: int = sa.Column(
        sa.Integer, sa.ForeignKey("telegram_accounts.id"), nullable=False
    )
    employee_id = sa.Column(
        sa.Integer, sa.ForeignKey("employees.id"), nullable=True
    )

    # ── Snapshot сотрудника ──────────────────────────────────────────
    employee_fio_snapshot: str = sa.Column(sa.String(512), nullable=False)
    employee_fio_normalized_basic: str = sa.Column(sa.String(512), nullable=False, index=True)
    employee_fio_normalized_translit: str = sa.Column(sa.String(512), nullable=False, index=True)
    employee_position_snapshot: str = sa.Column(sa.Text, nullable=True)

    # ── Snapshot филиала ─────────────────────────────────────────────
    branch_id: int = sa.Column(
        sa.Integer, sa.ForeignKey("bhm_branches.id"), nullable=False
    )
    bhm_code_snapshot: str = sa.Column(sa.String(5), nullable=False)
    branch_name_snapshot: str = sa.Column(sa.String(255), nullable=False)

    # ── Данные заявки ────────────────────────────────────────────────
    request_type: str = sa.Column(
        sa.Enum(RequestType, name="request_type_enum", create_constraint=True),
        nullable=False,
    )
    equipment_type: str = sa.Column(
        sa.Enum("computer", "printer", name="equipment_type_enum", create_constraint=False),
        nullable=False,
    )
    inventory_id = sa.Column(
        sa.Integer, sa.ForeignKey("inventory.id"), nullable=True
    )
    inventory_code_snapshot: str = sa.Column(sa.String(64), nullable=True)

    reason_text: str = sa.Column(sa.Text, nullable=True)
    problem_text: str = sa.Column(sa.Text, nullable=True)

    # ── Статус ───────────────────────────────────────────────────────
    status: str = sa.Column(
        sa.Enum(RequestStatus, name="request_status_enum", create_constraint=True),
        nullable=False,
        default=RequestStatus.new,
    )
    final_decision: str = sa.Column(
        sa.Enum(FinalDecision, name="final_decision_enum", create_constraint=True),
        nullable=False,
        default=FinalDecision.pending,
    )
    reject_reason: str = sa.Column(sa.Text, nullable=True)
    reviewer_comment: str = sa.Column(sa.Text, nullable=True)

    # ── Фото техники (только для replacement) ────────────────────────
    photo_file_id: str = sa.Column(sa.String(512), nullable=True)

    # ── L1/L2 рецензирование ─────────────────────────────────────────
    l1_reviewer_tg_id: int = sa.Column(sa.BigInteger, nullable=True)
    l1_comment: str = sa.Column(sa.Text, nullable=True)
    l2_reviewer_tg_id: int = sa.Column(sa.BigInteger, nullable=True)

    # ── Timestamps & Metadata ────────────────────────────────────────
    sla_escalated: bool = sa.Column(sa.Boolean, nullable=False, server_default=sa.text("false"), default=False)
    created_at = sa.Column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at = sa.Column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )
    closed_at = sa.Column(sa.DateTime(timezone=True), nullable=True)

    # ── Relationships ────────────────────────────────────────────────
    telegram_account = sa.orm.relationship("TelegramAccount")
    employee = sa.orm.relationship("Employee")
    branch = sa.orm.relationship("BhmBranch")
    inventory = sa.orm.relationship("Inventory")
    comments = sa.orm.relationship(
        "RequestComment", back_populates="request", order_by="RequestComment.created_at"
    )

    def __repr__(self) -> str:
        return f"<Request #{self.request_number} ({self.status})>"


# ── RequestComment ──────────────────────────────────────────────────────

class RequestComment(Base):
    """Комментарии проверяющих к заявке. Историю правок не храним."""

    __tablename__ = "request_comments"

    id: int = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    request_id: int = sa.Column(
        sa.Integer, sa.ForeignKey("requests.id", ondelete="CASCADE"), nullable=False
    )
    author_name: str = sa.Column(sa.String(255), nullable=False)
    comment_text: str = sa.Column(sa.Text, nullable=False)
    is_edited: bool = sa.Column(sa.Boolean, default=False, nullable=False)
    created_at = sa.Column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at = sa.Column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    request = sa.orm.relationship("Request", back_populates="comments")

    def __repr__(self) -> str:
        return f"<RequestComment #{self.id} on request={self.request_id}>"
