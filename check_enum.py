import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres.zfgkjuawsqjoawdlqnkz:DMEhIdBYsGuwsFG7@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT enum_range(NULL::region_enum);"))
        print(result.scalar())

asyncio.run(main())
