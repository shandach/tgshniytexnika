"""Ролевые фильтры для Telegram-бота.

Используются для ограничения доступа к хендлерам по роли пользователя.
"""

from typing import Union

from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telegram_account import TelegramAccount, TgRole


class RoleFilter(Filter):
    """
    Фильтр по роли пользователя в Telegram.

    Использование:
        @router.message(Command("queue"), RoleFilter(TgRole.reviewer_l1))
        @router.callback_query(RoleFilter(TgRole.reviewer_l1, TgRole.reviewer_l2))
    """

    def __init__(self, *allowed_roles: TgRole):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        event: Union[Message, CallbackQuery],
        session: AsyncSession,
    ) -> bool:
        tg_id = event.from_user.id
        stmt = select(TelegramAccount.role).where(
            TelegramAccount.telegram_user_id == tg_id
        )
        result = await session.scalar(stmt)
        if result is None:
            return False
        return result in self.allowed_roles


class IsReviewer(RoleFilter):
    """Пропускает только L1 или L2 проверяющих."""

    def __init__(self):
        super().__init__(TgRole.reviewer_l1, TgRole.reviewer_l2)


class IsReviewerL1(RoleFilter):
    """Пропускает только L1 проверяющих."""

    def __init__(self):
        super().__init__(TgRole.reviewer_l1)


class IsReviewerL2(RoleFilter):
    """Пропускает только L2 проверяющих."""

    def __init__(self):
        super().__init__(TgRole.reviewer_l2)
