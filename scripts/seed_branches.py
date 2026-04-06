"""
Seed-скрипт: загружает филиалы из data/branches.json в таблицу bhm_branches.

Использование:
    python -m scripts.seed_branches
"""

import asyncio
import json
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from app.database import async_session, engine, Base
from app.models.branch import BhmBranch


DATA_FILE = PROJECT_ROOT / "data" / "branches.json"


async def seed_branches() -> None:
    # Загружаем JSON
    if not DATA_FILE.exists():
        print(f"❌ Файл {DATA_FILE} не найден!")
        return

    with open(DATA_FILE, encoding="utf-8") as f:
        branches_data = json.load(f)

    async with async_session() as session:
        inserted = 0
        skipped = 0

        for item in branches_data:
            # Проверяем, есть ли уже такой BXM
            stmt = select(BhmBranch).where(BhmBranch.bhm_code == item["bhm_code"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                skipped += 1
                continue

            branch = BhmBranch(
                bhm_code=item["bhm_code"],
                branch_name=item["branch_name"],
                region_name=item["region_name"],
                city_name=item["city_name"],
                is_active=True,
            )
            session.add(branch)
            inserted += 1

        await session.commit()

    print(f"✅ Филиалы загружены: {inserted} добавлено, {skipped} пропущено (уже существуют).")


async def main() -> None:
    await seed_branches()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
