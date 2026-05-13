import asyncio
import sys
import os
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import async_session, engine

async def check_supabase_data():
    async with async_session() as session:
        # Get list of tables
        tables_query = text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        result = await session.execute(tables_query)
        tables = [row[0] for row in result.fetchall()]
        
        print(f"📊 Supabase Table Row Counts:")
        print("-" * 30)
        for table in tables:
            count_query = text(f"SELECT COUNT(*) FROM \"{table}\"")
            try:
                count_result = await session.execute(count_query)
                count = count_result.scalar()
                print(f"  {table:20}: {count}")
            except Exception as e:
                print(f"  {table:20}: Error ({e})")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(check_supabase_data())
