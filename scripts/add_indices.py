import asyncio
from sqlalchemy import text
from app.database import engine

async def add_performance_indices():
    """Add critical indices for bot performance."""
    queries = [
        # Request status is used in almost every reviewer query
        "CREATE INDEX IF NOT EXISTS idx_requests_status ON requests (status);",
        # Request created_at is used for sorting in queues
        "CREATE INDEX IF NOT EXISTS idx_requests_created_at ON requests (created_at);",
        # branch_id is used for joins
        "CREATE INDEX IF NOT EXISTS idx_requests_branch_id ON requests (branch_id);",
        # telegram_account_id is used for 'My Requests' view
        "CREATE INDEX IF NOT EXISTS idx_requests_tg_account_id ON requests (telegram_account_id);",
        # region_name is used for L1 regional filtering
        "CREATE INDEX IF NOT EXISTS idx_bhm_branches_region_name ON bhm_branches (region_name);",
        # role is used for permissions/filtering
        "CREATE INDEX IF NOT EXISTS idx_tg_accounts_role ON telegram_accounts (role);",
    ]
    
    print("🚀 Adding performance indices...")
    async with engine.begin() as conn:
        for q in queries:
            print(f"Executing: {q}")
            await conn.execute(text(q))
    print("✅ Done!")

if __name__ == "__main__":
    asyncio.run(add_performance_indices())
