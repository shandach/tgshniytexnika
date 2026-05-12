"""
scripts/set_role.py
Назначает роль пользователю бота по его Telegram @username.
Использование:
    .venv/bin/python scripts/set_role.py @john_doe reviewer_l1
    .venv/bin/python scripts/set_role.py @john_doe reviewer_l2
    .venv/bin/python scripts/set_role.py @john_doe employee
"""
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session
from app.models.telegram_account import TelegramAccount, TgRole

VALID_ROLES = {
    "reviewer_l1": TgRole.reviewer_l1,
    "reviewer_l2": TgRole.reviewer_l2,
    "employee": TgRole.employee,
    "l1": TgRole.reviewer_l1,  # Алиасы для удобства
    "l2": TgRole.reviewer_l2,
}


async def set_role(username_raw: str, role_str: str):
    # Убираем @ если есть
    username = username_raw.lstrip("@").strip().lower()

    if not username:
        print("❌ Укажите @username пользователя.")
        return

    role_key = role_str.strip().lower()
    if role_key not in VALID_ROLES:
        print(f"❌ Неверная роль '{role_str}'.")
        print(f"   Допустимые роли: {', '.join(VALID_ROLES.keys())}")
        return

    new_role = VALID_ROLES[role_key]

    async with async_session() as session:
        # Поиск без учёта регистра
        stmt = select(TelegramAccount).where(
            TelegramAccount.username.ilike(username)
        )
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()

        if not account:
            print(f"❌ Пользователь @{username} не найден в базе данных.")
            print("   Убедитесь, что пользователь хотя бы раз запускал бота (/start).")
            return

        old_role = account.role if isinstance(account.role, str) else account.role.value
        account.role = new_role
        await session.commit()

        name = account.full_name or f"ID {account.telegram_user_id}"
        print(f"✅ Роль успешно изменена!")
        print(f"   Пользователь: {name} (@{account.username})")
        print(f"   ID: {account.telegram_user_id}")
        print(f"   Роль: {old_role}  →  {new_role.value}")
        print()
        print("   ⚠️  Пользователю нужно отправить /start в боте, чтобы увидеть новое меню.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: .venv/bin/python scripts/set_role.py @username роль")
        print("Пример:        .venv/bin/python scripts/set_role.py @john_doe reviewer_l1")
        print("Роли:          employee | reviewer_l1 | reviewer_l2 | l1 | l2")
        sys.exit(1)

    asyncio.run(set_role(sys.argv[1], sys.argv[2]))
