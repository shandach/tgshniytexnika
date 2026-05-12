import asyncio
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session
from app.models.telegram_account import TelegramAccount


def format_dt(dt: datetime) -> str:
    """Форматирует дату: Сегодня/Вчера или 'DD.MM HH:MM'."""
    if dt is None:
        return "—"
    now = datetime.now(timezone.utc)
    delta = now - dt
    if delta.days == 0:
        return f"Сегодня {dt.strftime('%H:%M')}"
    elif delta.days == 1:
        return f"Вчера {dt.strftime('%H:%M')}"
    else:
        return dt.strftime("%d.%m.%Y %H:%M")


async def show_users(days: Optional[int] = None):
    async with async_session() as session:
        stmt = select(TelegramAccount).order_by(TelegramAccount.first_seen_at.desc())
        result = await session.execute(stmt)
        accounts = result.scalars().all()

        if days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            accounts = [a for a in accounts if a.first_seen_at and a.first_seen_at >= cutoff]

        if not accounts:
            print("Нет пользователей за указанный период.")
            return

        # Заголовок таблицы
        print()
        header = f"{'ID':<15} | {'Username':<20} | {'Имя':<25} | {'Роль':<14} | {'Первый вход'}"
        print(header)
        print("-" * len(header))

        for acc in accounts:
            tg_id = str(acc.telegram_user_id)
            username = f"@{acc.username}" if acc.username else "—"
            full_name = (acc.full_name or "—")[:25]
            role = acc.role if isinstance(acc.role, str) else acc.role.value
            first_seen = format_dt(acc.first_seen_at)

            print(f"{tg_id:<15} | {username:<20} | {full_name:<25} | {role:<14} | {first_seen}")

        print()
        total = len(accounts)
        employees = sum(1 for a in accounts if str(a.role) in ("employee", "TgRole.employee"))
        reviewers = total - employees
        print(f"Итого: {total} пользователей (👷 сотрудников: {employees}, 🔍 проверяющих: {reviewers})")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Показать список пользователей бота")
    parser.add_argument("--days", type=int, default=None, help="Только за последние N дней")
    args = parser.parse_args()

    asyncio.run(show_users(days=args.days))
