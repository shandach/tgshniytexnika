import asyncio
import os
import sys

# Добавляем корень проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session
from app.models.branch import BhmBranch
from app.models.inventory import Inventory

async def seed_test_data():
    async with async_session() as session:
        # 1. Создаем филиал Чиланзар
        result = await session.execute(select(BhmBranch).where(BhmBranch.bhm_code == "11673"))
        branch = result.scalar_one_or_none()
        
        if not branch:
            branch = BhmBranch(
                bhm_code="11673",
                branch_name="Qatartol",
                region_name="Ташкент",
                city_name="Чиланзар",
                is_active=True
            )
            session.add(branch)
            await session.flush() # Получаем ID
            print("Branch 11673 (Qatartol) created.")
        else:
            print("Branch 11673 already exists.")

        # 2. Создаем инвентарь для этого филиала
        # Компьютер
        res_comp = await session.execute(select(Inventory).where(Inventory.inventory_code == "10722505"))
        comp = res_comp.scalar_one_or_none()
        if not comp:
            comp = Inventory(
                inventory_code="10722505",
                branch_id=branch.id,
                equipment_type="computer",
                issue_year=2023,
                status="active"
            )
            session.add(comp)
            print("Computer 10722505 created with year 2023.")
        else:
            comp.issue_year = 2023
            print("Computer 10722505 year updated to 2023.")
        
        # Принтер
        res_print = await session.execute(select(Inventory).where(Inventory.inventory_code == "20722505"))
        printer = res_print.scalar_one_or_none()
        if not printer:
            printer = Inventory(
                inventory_code="20722505",
                branch_id=branch.id,
                equipment_type="printer",
                issue_year=2025,
                status="active"
            )
            session.add(printer)
            print("Printer 20722505 created with year 2025.")
        else:
            printer.issue_year = 2025
            print("Printer 20722505 year updated to 2025.")

        await session.commit()
        print("✅ Тестовые данные успешно добавлены!")

if __name__ == "__main__":
    asyncio.run(seed_test_data())
