import asyncio
import sys
from sqlalchemy import select, update, text
from app.database import engine, async_session
from app.models.telegram_account import TelegramAccount, TgRole
from app.models.branch import BhmBranch

async def list_regions():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT DISTINCT region_name FROM bhm_branches ORDER BY region_name"))
        regions = [r[0] for r in res.all()]
        print("\n📍 Available regions in BHM database:")
        for r in regions:
            print(f"  - {r}")
        return regions

async def manage_reviewers():
    async with async_session() as session:
        # Get all L1 reviewers
        stmt = select(TelegramAccount).where(TelegramAccount.role == TgRole.reviewer_l1)
        result = await session.execute(stmt)
        reviewers = result.scalars().all()
        
        if not reviewers:
            print("\n❌ No L1 reviewers found in telegram_accounts table.")
            return

        print("\n👥 Current L1 Reviewers:")
        for r in reviewers:
            print(f"ID: {r.id} | TG: {r.telegram_user_id} | Name: {r.full_name} | Region: {r.assigned_region}")

        if len(sys.argv) < 3:
            print("\nUsage: python scripts/assign_l1_regions.py <tg_user_id> <region_name>")
            print("Example: python scripts/assign_l1_regions.py 12345678 'Тошкент шаҳри'")
            return

        target_tg_id = int(sys.argv[1])
        new_region = sys.argv[2]
        
        # Verify region
        regions = await list_regions()
        if new_region not in regions:
            print(f"\n❌ Error: Region '{new_region}' not found in database.")
            return

        # Update
        stmt = update(TelegramAccount).where(TelegramAccount.telegram_user_id == target_tg_id).values(assigned_region=new_region)
        await session.execute(stmt)
        await session.commit()
        print(f"\n✅ Success: User {target_tg_id} assigned to region '{new_region}'")

if __name__ == "__main__":
    if "--list" in sys.argv:
        asyncio.run(list_regions())
    else:
        asyncio.run(manage_reviewers())
