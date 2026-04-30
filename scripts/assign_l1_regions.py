"""
Скрипт назначения областей L1-проверяющим (mintaqaviy).

Использование:
    python scripts/assign_l1_regions.py <telegram_user_id> <номер_области>

Пример:
    python scripts/assign_l1_regions.py 123456789 1    # Андижон вилояти
    python scripts/assign_l1_regions.py 987654321 12   # Тошкент шаҳри

Для просмотра списка областей:
    python scripts/assign_l1_regions.py --list

Для просмотра текущих назначений:
    python scripts/assign_l1_regions.py --show
"""

import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from app.database import async_session
from app.models.telegram_account import TelegramAccount, TgRole

# ── 14 областей Узбекистана ─────────────────────────────────────────────
# Названия должны совпадать с region_name в таблице bhm_branches.
REGIONS = {
    1:  "Андижон вилояти",
    2:  "Бухоро вилояти",
    3:  "Жиззах вилояти",
    4:  "Қорақалпоғистон Республикаси",
    5:  "Қашқадарё вилояти",
    6:  "Навоий вилояти",
    7:  "Наманган вилояти",
    8:  "Самарқанд вилояти",
    9:  "Сурхондарё вилояти",
    10: "Сирдарё вилояти",
    11: "Тошкент вилояти",
    12: "Тошкент шаҳри",
    13: "Фарғона вилояти",
    14: "Хоразм вилояти",
}


def print_regions():
    print("\n📍 Список областей (mintaqa):\n")
    for num, name in REGIONS.items():
        print(f"  {num:2d}. {name}")
    print()


async def show_assignments():
    async with async_session() as session:
        stmt = select(TelegramAccount).where(
            TelegramAccount.role == TgRole.reviewer_l1
        ).order_by(TelegramAccount.assigned_region)
        result = await session.scalars(stmt)
        reviewers = result.all()

        if not reviewers:
            print("⚠️  Нет L1-проверяющих в системе.")
            return

        print("\n📋 Текущие назначения L1-проверяющих:\n")
        for r in reviewers:
            region = r.assigned_region or "❌ не назначена"
            print(f"  tg_id={r.telegram_user_id}  →  {region}")
        print()


async def assign_region(tg_user_id: int, region_num: int):
    if region_num not in REGIONS:
        print(f"❌ Неверный номер области: {region_num}. Допустимые: 1-14")
        print_regions()
        return

    region_name = REGIONS[region_num]

    async with async_session() as session:
        stmt = select(TelegramAccount).where(
            TelegramAccount.telegram_user_id == tg_user_id
        )
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()

        if not account:
            print(f"❌ Аккаунт с tg_id={tg_user_id} не найден.")
            return

        if account.role != TgRole.reviewer_l1:
            print(f"⚠️  Аккаунт tg_id={tg_user_id} имеет роль '{account.role}', а не reviewer_l1.")
            print(f"    Сначала назначьте роль reviewer_l1.")
            return

        account.assigned_region = region_name
        await session.commit()

        print(f"✅ L1-проверяющий tg_id={tg_user_id} назначен на: {region_name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python scripts/assign_l1_regions.py <tg_user_id> <номер_области>")
        print("  python scripts/assign_l1_regions.py --list")
        print("  python scripts/assign_l1_regions.py --show")
        sys.exit(1)

    if sys.argv[1] == "--list":
        print_regions()
    elif sys.argv[1] == "--show":
        asyncio.run(show_assignments())
    elif len(sys.argv) == 3:
        tg_id = int(sys.argv[1])
        region_num = int(sys.argv[2])
        asyncio.run(assign_region(tg_id, region_num))
    else:
        print("❌ Неверные аргументы. Используйте --list, --show, или <tg_id> <номер>")
