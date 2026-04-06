import enum
import sqlalchemy as sa
from app.database import Base


class UserRole(str, enum.Enum):
    developer = "developer"
    reviewer = "reviewer"


class User(Base):
    """
    Пользователи внутренней панели (проверяющие / разработчики).

    Вход по логину и паролю. Роль определяет доступ к функциям.
    """

    __tablename__ = "users"

    id: int = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    login: str = sa.Column(sa.String(128), unique=True, nullable=False, index=True)
    password_hash: str = sa.Column(sa.String(512), nullable=False)
    role: str = sa.Column(
        sa.Enum(UserRole, name="user_role_enum", create_constraint=True),
        nullable=False,
        default=UserRole.reviewer,
    )
    full_name: str = sa.Column(sa.String(255), nullable=False)
    is_active: bool = sa.Column(sa.Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<User {self.login} ({self.role})>"
