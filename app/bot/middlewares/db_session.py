from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import engine

# Создаем фабрику сессий на основе глобального engine
async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

class DbSessionMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Инжектим сессию БД в каждый обработчик
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)
