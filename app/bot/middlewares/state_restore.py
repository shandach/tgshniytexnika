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
        # Работаем только с Message и CallbackQuery
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        state: FSMContext = data.get("state")
        session = data.get("session")
        user = event.from_user

        if state and session and user:
            current_state = await state.get_state()
            
            # Если стейт пустой, пробуем восстановить из БД
            if current_state is None:
                stmt = select(TelegramAccount).where(TelegramAccount.telegram_user_id == user.id)
                result = await session.execute(stmt)
                account = result.scalar_one_or_none()

                if account:
                    # Восстанавливаем базовые данные в FSM
                    await state.update_data(
                        language=account.language,
                        role=account.role,
                    )
                    
                    if account.selected_branch_id:
                        # Если есть выбранный филиал, подтягиваем его данные
                        branch = await session.get(BhmBranch, account.selected_branch_id)
                        if branch:
                            await state.update_data(
                                branch_id=branch.id,
                                bhm_code=branch.bhm_code,
                                branch_name=branch.branch_name
                            )

        return await handler(event, data)
