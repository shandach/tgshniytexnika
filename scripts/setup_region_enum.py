import asyncio
from sqlalchemy import text
from app.database import engine

async def setup_region_enum():
    """
    Creates a PostgreSQL ENUM for regions and applies it to telegram_accounts.assigned_region.
    This enables a dropdown menu in Supabase/Postgres UI.
    """
    async with engine.begin() as conn:
        # 1. Fetch available regions from branches table
        res = await conn.execute(text("SELECT DISTINCT region_name FROM bhm_branches ORDER BY region_name"))
        regions = [r[0] for r in res.all() if r[0]]
        
        if not regions:
            print("❌ No regions found in bhm_branches. Run branch import first.")
            return

        print(f"📍 Found {len(regions)} regions. Creating ENUM...")
        
        # Format for SQL: 'Region 1', 'Region 2', ...
        enum_values = ", ".join([f"'{r}'" for r in regions])
        
        # 2. Create the TYPE if it doesn't exist
        # We drop and recreate to ensure it's up to date with the branch table
        try:
            await conn.execute(text("DROP TYPE IF EXISTS region_enum CASCADE"))
            await conn.execute(text(f"CREATE TYPE region_enum AS ENUM ({enum_values})"))
            print("✅ Type 'region_enum' created.")
        except Exception as e:
            print(f"⚠️ Warning during type creation: {e}")

        # 3. Alter the table
        try:
            # We use USING to cast current varchar to enum
            await conn.execute(text("""
                ALTER TABLE telegram_accounts 
                ALTER COLUMN assigned_region TYPE region_enum 
                USING assigned_region::region_enum
            """))
            print("✅ telegram_accounts.assigned_region converted to ENUM dropdown.")
        except Exception as e:
            print(f"❌ Error altering table: {e}")

if __name__ == "__main__":
    asyncio.run(setup_region_enum())
