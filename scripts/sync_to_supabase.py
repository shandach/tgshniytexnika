import asyncio
import sys
import os
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from app.models import (
    BhmBranch, TelegramAccount, Employee, Inventory,
    Request, RequestComment, User
)

LOCAL_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/tgtexnika"
SUPABASE_URL = "postgresql+asyncpg://postgres.zfgkjuawsqjoawdlqnkz:DMEhIdBYsGuwsFG7@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"

async def sync_table(local_session, sb_session, model, name):
    print(f"🔄 Syncing {name}...")
    
    # Get all from local
    result = await local_session.execute(select(model))
    items = result.scalars().all()
    print(f"  Found {len(items)} items in local.")
    
    if not items:
        return

    # Clear supabase table (optional, but safer for a clean migration)
    # Be careful with foreign keys! We sync in order.
    await sb_session.execute(delete(model))
    
    # Add to supabase
    for item in items:
        # We need to create NEW instances to avoid session conflicts, or just merge
        # Easiest: extract data as dict (excluding state)
        data = {c.name: getattr(item, c.name) for c in model.__table__.columns}
        new_item = model(**data)
        sb_session.add(new_item)
    
    await sb_session.commit()
    print(f"  ✅ {name} synced successfully.")

async def main():
    local_engine = create_async_engine(LOCAL_URL)
    sb_engine = create_async_engine(SUPABASE_URL)
    
    LocalSession = sessionmaker(local_engine, class_=AsyncSession, expire_on_commit=False)
    SbSession = sessionmaker(sb_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with LocalSession() as local_session:
        async with SbSession() as sb_session:
            # Sync order to respect foreign keys
            models = [
                (BhmBranch, "BhmBranch"),
                (User, "User"),
                (TelegramAccount, "TelegramAccount"),
                (Employee, "Employee"),
                (Inventory, "Inventory"),
                (Request, "Request"),
                (RequestComment, "RequestComment"),
            ]
            
            for model, name in models:
                try:
                    await sync_table(local_session, sb_session, model, name)
                except Exception as e:
                    print(f"  ❌ Error syncing {name}: {e}")
                    await sb_session.rollback()

    await local_engine.dispose()
    await sb_engine.dispose()
    print("\n🎉 DATA SYNC COMPLETE!")

if __name__ == "__main__":
    asyncio.run(main())
