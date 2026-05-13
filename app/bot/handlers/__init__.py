from aiogram import Router

from app.bot.handlers import start
from app.bot.handlers import request_fsm   # ← перед main_menu: FSM-handlers с state-filter в приоритете
from app.bot.handlers import main_menu
from app.bot.handlers import error_report
from app.bot.handlers import status
from app.bot.handlers import reviewer_l1
from app.bot.handlers import reviewer_l2
from app.bot.handlers import fallback      # ← всегда последним


def setup_routers() -> Router:
    """Собирает все роутеры приложения в правильном порядке."""
    router = Router()

    # 1. Reviewer handlers — строгие role-filters, приоритет высокий
    router.include_router(reviewer_l1.router)
    router.include_router(reviewer_l2.router)

    # 2. /start и /language команды
    router.include_router(start.router)

    # 3. FSM-шаги заявки — ПЕРЕД main_menu, у них есть state-filter
    #    Это гарантирует, что waiting_for_fio и др. не перехватятся кнопками меню
    router.include_router(request_fsm.router)

    # 4. Главное меню (btn_computer, btn_printer и т.д.) — StateFilter(None)
    router.include_router(main_menu.router)

    # 5. Остальные функциональные хендлеры
    router.include_router(error_report.router)
    router.include_router(status.router)

    # 6. Catch-all — ОБЯЗАТЕЛЬНО последним
    router.include_router(fallback.router)

    return router
