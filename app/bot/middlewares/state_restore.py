"""
StateRestoreMiddleware — резервное восстановление данных из telegram_accounts.
С PostgresFSMStorage это нужно только для совсем новых пользователей,
у которых нет строки в fsm_state, но есть selected_branch_id в telegram_accounts.
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
            # Быстрая проверка: если данные уже есть — пропускаем
            fsm_data = await state.get_data()
            if not fsm_data.get("language") or not fsm_data.get("branch_id"):
                # Данных нет — пробуем восстановить из таблицы telegram_accounts
                stmt = select(TelegramAccount).where(
                    TelegramAccount.telegram_user_id == user.id
                )
                result = await session.execute(stmt)
                account = result.scalar_one_or_none()

                if account:
                    update = {"language": account.language, "role": account.role}

                    if account.selected_branch_id and not fsm_data.get("branch_id"):
                        branch = await session.get(BhmBranch, account.selected_branch_id)
                        if branch:
                            update.update(
                                branch_id=branch.id,
                                bhm_code=branch.bhm_code,
                                branch_name=branch.branch_name,
                            )

                    await state.update_data(**update)

        return await handler(event, data)
