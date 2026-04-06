import asyncio
import logging
from contextlib import asynccontextmanager
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings
from app.database import engine
from app.bot.handlers import setup_routers
from app.bot.middlewares.db_session import DbSessionMiddleware

# Подключение API роутеров
from app.api.routers import auth, requests, dashboard, inventory

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_bot_and_dp():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.include_router(setup_routers())
    return bot, dp

bot, dp = None, None

from aiogram.types import BotCommand

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом (запуск бота параллельно с FastAPI)."""
    global bot, dp
    bot, dp = get_bot_and_dp()
    
    # Startup
    logger.info("Starting Telegram Bot...")
    
    # Установка меню команд
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать работу / Сменить филиал")
    ])
    
    await bot.delete_webhook(drop_pending_updates=True)
    polling_task = asyncio.create_task(dp.start_polling(bot))
    
    yield  # Сервер работает
    
    # Shutdown
    logger.info("Stopping Bot...")
    polling_task.cancel()
    await bot.session.close()
    await engine.dispose()

app = FastAPI(title="TgTexnika API", lifespan=lifespan)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение API роутеров FastAPI
app.include_router(auth.router)
app.include_router(requests.router)
app.include_router(dashboard.router)
app.include_router(inventory.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
