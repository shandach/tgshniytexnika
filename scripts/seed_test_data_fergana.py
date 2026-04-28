import asyncio
import os
import sys

# Добавляем корень проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session
from app.models.branch import BhmBranch
from app.models.inventory import Inventory, EquipmentType, InventoryStatus

async def main():
    async with async_session() as session:
        # 1. Создаем или находим филиал
        bhm_code = "11200"
        result = await session.execute(select(BhmBranch).where(BhmBranch.bhm_code == bhm_code))
        branch = result.scalar_one_or_none()
        
        if not branch:
            branch = BhmBranch(
                bhm_code=bhm_code,
                branch_name="Талпонов",
                region_name="область Фергана",
                city_name="Карагач",
                is_active=True
            )
            session.add(branch)
            await session.commit()
            await session.refresh(branch)
            print(f"Created branch: {branch.bhm_code} - {branch.branch_name}")
        else:
            print(f"Branch already exists: {branch.bhm_code} - {branch.branch_name}")

        # 2. Компьютер (код 2019090, 2024 год)
        res_comp = await session.execute(select(Inventory).where(Inventory.inventory_code == "2019090"))
        if not res_comp.scalar_one_or_none():
            inv_comp = Inventory(
                inventory_code="2019090",
                branch_id=branch.id,
                equipment_type=EquipmentType.computer,
                issue_year=2024,
                status=InventoryStatus.active
            )
            session.add(inv_comp)
            print("Added Computer 2019090")

        # 3. Принтер (код 1019090, 2025 год)
        res_print = await session.execute(select(Inventory).where(Inventory.inventory_code == "1019090"))
        if not res_print.scalar_one_or_none():
            inv_print = Inventory(
                inventory_code="1019090",
                branch_id=branch.id,
                equipment_type=EquipmentType.printer,
                issue_year=2025,
                status=InventoryStatus.active
            )
            session.add(inv_print)
            print("Added Printer 1019090")

        await session.commit()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
