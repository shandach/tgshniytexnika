from aiogram import Router

from app.bot.handlers import start
from app.bot.handlers import main_menu
from app.bot.handlers import error_report
from app.bot.handlers import request_fsm
from app.bot.handlers import status
from app.bot.handlers import reviewer_l1
from app.bot.handlers import reviewer_l2
from app.bot.handlers import fallback  # ВСЕГДА ПОСЛЕДНИМ!

def setup_routers() -> Router:
    """Собирает все роутеры приложения."""
    router = Router()
    
    # Регистрация роутеров в правильном порядке.
    # Reviewer роутеры — первые, так как у них строгие фильтры по роли.
    router.include_router(reviewer_l1.router)
    router.include_router(reviewer_l2.router)
    router.include_router(start.router)
    router.include_router(main_menu.router)
    router.include_router(error_report.router)
    router.include_router(request_fsm.router)
    router.include_router(status.router)
    # Fallback — ОБЯЗАТЕЛЬНО последним, чтобы не перехватывать чужие сообщения
    router.include_router(fallback.router)
    
    return router
