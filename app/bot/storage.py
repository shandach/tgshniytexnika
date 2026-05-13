"""
PostgreSQL-backed FSM Storage for aiogram 3.
Replaces MemoryStorage — state survives Railway restarts.
"""
import json
import logging
from typing import Any, Dict, Optional

from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class PostgresFSMStorage(BaseStorage):
    """
    Production-safe FSM storage backed by PostgreSQL (Supabase).
    Each user's (bot_id, chat_id, user_id) gets their own row.
    """

    def __init__(self, engine: AsyncEngine):
        self._engine = engine

    def _key(self, key: StorageKey) -> dict:
        return {
            "bot_id": key.bot_id,
            "chat_id": key.chat_id,
            "user_id": key.user_id,
            "destiny": key.destiny or "default",
        }

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        state_str = state.state if hasattr(state, "state") else state
        params = {**self._key(key), "state": state_str}
        async with self._engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO fsm_state (bot_id, chat_id, user_id, destiny, state)
                    VALUES (:bot_id, :chat_id, :user_id, :destiny, :state)
                    ON CONFLICT (bot_id, chat_id, user_id, destiny)
                    DO UPDATE SET state = EXCLUDED.state, updated_at = NOW()
                """),
                params,
            )

    async def get_state(self, key: StorageKey) -> Optional[str]:
        async with self._engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT state FROM fsm_state
                    WHERE bot_id = :bot_id AND chat_id = :chat_id
                      AND user_id = :user_id AND destiny = :destiny
                """),
                self._key(key),
            )
            row = result.fetchone()
            return row[0] if row else None

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        # NOTE: Use CAST(:data AS jsonb) — asyncpg does not support :name::type syntax
        data_json = json.dumps(data, default=str)
        params = {**self._key(key), "data": data_json}
        async with self._engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO fsm_state (bot_id, chat_id, user_id, destiny, data)
                    VALUES (:bot_id, :chat_id, :user_id, :destiny, CAST(:data AS jsonb))
                    ON CONFLICT (bot_id, chat_id, user_id, destiny)
                    DO UPDATE SET data = CAST(EXCLUDED.data AS jsonb), updated_at = NOW()
                """),
                params,
            )

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        async with self._engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT data FROM fsm_state
                    WHERE bot_id = :bot_id AND chat_id = :chat_id
                      AND user_id = :user_id AND destiny = :destiny
                """),
                self._key(key),
            )
            row = result.fetchone()
            if row and row[0]:
                return row[0] if isinstance(row[0], dict) else json.loads(row[0])
            return {}

    async def close(self) -> None:
        pass  # Engine is managed globally by the application
