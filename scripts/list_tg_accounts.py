import asyncio
import sys
import os
from sqlalchemy import select

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from app.database import async_session
from app.models.telegram_account import TelegramAccount

async def list_tg_accounts():
    async with async_session() as session:
        stmt = select(TelegramAccount)
        result = await session.execute(stmt)
        accounts = result.scalars().all()
        
        print(f"{'ID':<15} | {'Username':<15} | {'Role':<15} | {'Full Name'}")
        print("-" * 60)
        for a in accounts:
            print(f"{a.telegram_user_id:<15} | {str(a.username):<15} | {str(a.role):<15} | {a.full_name}")

if __name__ == "__main__":
    asyncio.run(list_tg_accounts())
