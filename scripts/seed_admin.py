import asyncio
import os
import sys

# Добавляем корень проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session
from app.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

async def seed_admin():
    async with async_session() as session:
        result = await session.execute(select(User).where(User.login == "admin"))
        user = result.scalar_one_or_none()
        
        if not user:
            new_user = User(
                login="admin",
                password_hash=get_password_hash("admin123"),
                role="developer",
                full_name="Администратор",
                is_active=True
            )
            session.add(new_user)
            await session.commit()
            print("Admin created successfully: admin / admin123")
        else:
            print("Admin already exists.")

if __name__ == "__main__":
    asyncio.run(seed_admin())
