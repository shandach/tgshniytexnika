import enum
import sqlalchemy as sa
from app.database import Base


class TgRole(str, enum.Enum):
    employee = "employee"
    reviewer_l1 = "reviewer_l1"
    reviewer_l2 = "reviewer_l2"


class TelegramAccount(Base):
    """Telegram-аккаунты, подающие заявки."""

    __tablename__ = "telegram_accounts"

    id: int = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    telegram_user_id: int = sa.Column(sa.BigInteger, unique=True, nullable=False, index=True)
    role: str = sa.Column(
        sa.Enum(TgRole, name="tg_role_enum", create_constraint=True),
        nullable=False,
        default=TgRole.employee,
        server_default="employee",
    )
    first_seen_at = sa.Column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    last_seen_at = sa.Column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    language = sa.Column(sa.String(10), server_default="uz", nullable=False)

    # Региональная привязка L1-проверяющего (mintaqaviy).
    # Должна совпадать с BhmBranch.region_name.
    # Для L2 и сотрудников — NULL (L2 видят все области).
    assigned_region = sa.Column(sa.String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<TelegramAccount tg_id={self.telegram_user_id} role={self.role} region={self.assigned_region}>"

