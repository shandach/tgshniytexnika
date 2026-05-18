import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.zfgkjuawsqjoawdlqnkz:DMEhIdBYsGuwsFG7@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        # Сначала изменим тип колонки
        await conn.execute(text("ALTER TABLE telegram_accounts ALTER COLUMN assigned_region TYPE VARCHAR(255);"))
        print("Column assigned_region successfully altered to VARCHAR(255)")

asyncio.run(main())
