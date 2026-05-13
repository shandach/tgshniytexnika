"""
StateRestoreMiddleware — резервное восстановление данных из telegram_accounts.
Запускается только когда FSM-кэш пустой (cold start после рестарта Railway).
Для L1/L2 проверяющих: они не имеют branch_id, поэтому проверяем role тоже.
"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from app.models.telegram_account import TelegramAccount
from app.models.branch import BhmBranch


class StateRestoreMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        state: FSMContext = data.get("state")
        session = data.get("session")
        user = event.from_user

        if state and session and user:
            fsm_data = await state.get_data()

            # Если уже есть данные о языке (значит кэш не пустой) — пропускаем
            # Это ключевая проверка: не гонять в БД на каждый запрос
            if fsm_data.get("language"):
                return await handler(event, data)

            # Холодный старт: данных в FSM нет — восстанавливаем из telegram_accounts
            stmt = select(TelegramAccount).where(
                TelegramAccount.telegram_user_id == user.id
            )
            result = await session.execute(stmt)
            account = result.scalar_one_or_none()

            if account:
                update: Dict[str, Any] = {
                    "language": account.language or "uz",
                    "role": account.role,
                }

                # Для обычных сотрудников — восстанавливаем филиал
                if account.selected_branch_id:
                    branch = await session.get(BhmBranch, account.selected_branch_id)
                    if branch:
                        update.update(
                            branch_id=branch.id,
                            bhm_code=branch.bhm_code,
                            branch_name=branch.branch_name,
                        )

                await state.update_data(**update)

        return await handler(event, data)
