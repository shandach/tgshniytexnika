"""
Hybrid FSM Storage: Memory cache + PostgreSQL persistence.
- Reads: from memory (~0ms)
- Writes: to memory instantly + to PostgreSQL in background
- On cold start: loads from PostgreSQL on first access
Result: sub-100ms responses instead of 2-5 seconds.
"""
import asyncio
import json
import logging
from typing import Any, Dict, Optional

from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class PostgresFSMStorage(BaseStorage):

    def __init__(self, engine: AsyncEngine):
        self._engine = engine
        self._state_cache: Dict[str, Optional[str]] = {}
        self._data_cache: Dict[str, Dict[str, Any]] = {}

    def _cache_key(self, key: StorageKey) -> str:
        return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.destiny or 'default'}"

    def _sql_params(self, key: StorageKey) -> dict:
        return {
            "bot_id": key.bot_id,
            "chat_id": key.chat_id,
            "user_id": key.user_id,
            "destiny": key.destiny or "default",
        }

    # ── State ────────────────────────────────────────────────────────────

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        state_str = state.state if hasattr(state, "state") else state
        ck = self._cache_key(key)
        self._state_cache[ck] = state_str
        # Persist in background (non-blocking)
        asyncio.create_task(self._persist_state(key, state_str))

    async def get_state(self, key: StorageKey) -> Optional[str]:
        ck = self._cache_key(key)
        if ck in self._state_cache:
            return self._state_cache[ck]
        # Cold start: load from DB
        val = await self._load_state(key)
        self._state_cache[ck] = val
        return val

    # ── Data ─────────────────────────────────────────────────────────────

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        ck = self._cache_key(key)
        self._data_cache[ck] = data
        # Persist in background (non-blocking)
        asyncio.create_task(self._persist_data(key, data))

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        ck = self._cache_key(key)
        if ck in self._data_cache:
            return self._data_cache[ck]
        # Cold start: load from DB
        val = await self._load_data(key)
        self._data_cache[ck] = val
        return val

    # ── DB persistence (background) ─────────────────────────────────────

    async def _persist_state(self, key: StorageKey, state_str: Optional[str]) -> None:
        try:
            params = {**self._sql_params(key), "state": state_str}
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
        except Exception as e:
            logger.error(f"FSM persist state error: {e}")

    async def _persist_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        try:
            data_json = json.dumps(data, default=str)
            params = {**self._sql_params(key), "data": data_json}
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
        except Exception as e:
            logger.error(f"FSM persist data error: {e}")

    # ── DB loading (cold start only) ────────────────────────────────────

    async def _load_state(self, key: StorageKey) -> Optional[str]:
        try:
            async with self._engine.connect() as conn:
                result = await conn.execute(
                    text("""
                        SELECT state FROM fsm_state
                        WHERE bot_id = :bot_id AND chat_id = :chat_id
                          AND user_id = :user_id AND destiny = :destiny
                    """),
                    self._sql_params(key),
                )
                row = result.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"FSM load state error: {e}")
            return None

    async def _load_data(self, key: StorageKey) -> Dict[str, Any]:
        try:
            async with self._engine.connect() as conn:
                result = await conn.execute(
                    text("""
                        SELECT data FROM fsm_state
                        WHERE bot_id = :bot_id AND chat_id = :chat_id
                          AND user_id = :user_id AND destiny = :destiny
                    """),
                    self._sql_params(key),
                )
                row = result.fetchone()
                if row and row[0]:
                    return row[0] if isinstance(row[0], dict) else json.loads(row[0])
                return {}
        except Exception as e:
            logger.error(f"FSM load data error: {e}")
            return {}

    async def close(self) -> None:
        pass
