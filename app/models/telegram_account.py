import sqlalchemy as sa
from app.database import Base


class TelegramAccount(Base):
    """Telegram-аккаунты, подающие заявки."""

    __tablename__ = "telegram_accounts"

    id: int = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    telegram_user_id: int = sa.Column(sa.BigInteger, unique=True, nullable=False, index=True)
    first_seen_at = sa.Column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    last_seen_at = sa.Column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<TelegramAccount tg_id={self.telegram_user_id}>"
