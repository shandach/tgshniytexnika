from aiogram import Router

from app.bot.handlers import start
from app.bot.handlers import main_menu
from app.bot.handlers import error_report
from app.bot.handlers import request_fsm
from app.bot.handlers import status
from app.bot.handlers import reviewer_l1
from app.bot.handlers import reviewer_l2

def setup_routers() -> Router:
    """Собирает все роутеры приложения."""
    router = Router()
    
    # Регистрация роутеров в правильном порядке
    router.include_router(reviewer_l1.router)  # Reviewer перед start, чтобы фильтры работали
    router.include_router(reviewer_l2.router)
    router.include_router(start.router)
    router.include_router(main_menu.router)
    router.include_router(error_report.router)
    router.include_router(request_fsm.router)
    router.include_router(status.router)
    
    return router
