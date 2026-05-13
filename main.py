import asyncio
import logging
from contextlib import asynccontextmanager
from aiogram import Bot, Dispatcher
from app.bot.storage import PostgresFSMStorage
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from app.config import settings
from app.database import engine
from app.bot.handlers import setup_routers
from app.bot.middlewares.db_session import DbSessionMiddleware
from app.bot.middlewares.state_restore import StateRestoreMiddleware

# Подключение API роутеров
from app.api.routers import auth, requests, dashboard, inventory
from app.api.routers import tickets, branches, export

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_bot_and_dp():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=PostgresFSMStorage(engine))
    
    # Регистрируем как outer_middleware, чтобы сессия была доступна в фильтрах (RoleFilter)
    dp.update.outer_middleware(DbSessionMiddleware())
    dp.update.outer_middleware(StateRestoreMiddleware())
    
    dp.include_router(setup_routers())
    return bot, dp

bot, dp = None, None

from aiogram.types import BotCommand
from app.services.scheduler import sla_scheduler_loop
from app.database import async_session

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом (запуск бота параллельно с FastAPI)."""
    global bot, dp
    bot, dp = get_bot_and_dp()
    
    # Startup
    logger.info("Starting Telegram Bot...")
    
    # Установка меню команд
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать работу / Сменить филиал"),
        BotCommand(command="language", description="Сменить язык / Tilni o'zg.")
    ])
    
    await bot.delete_webhook(drop_pending_updates=True)
    polling_task = asyncio.create_task(dp.start_polling(bot))
    sla_task = asyncio.create_task(sla_scheduler_loop(async_session, bot))
    
    yield  # Сервер работает
    
    # Shutdown
    logger.info("Stopping Bot...")
    polling_task.cancel()
    sla_task.cancel()
    await bot.session.close()
    await engine.dispose()

app = FastAPI(title="TgTexnika API", lifespan=lifespan)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Подключение API роутеров FastAPI
app.include_router(auth.router)
app.include_router(requests.router)
app.include_router(dashboard.router)
app.include_router(inventory.router)
app.include_router(tickets.router)
app.include_router(branches.router)
app.include_router(export.router)


@app.get("/", include_in_schema=False)
async def serve_index():
    """Раздаёт bxm_complete.html как главную страницу."""
    return FileResponse("bxm_complete.html")


import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

