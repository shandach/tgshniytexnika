import asyncio
import os
import sys

# Добавляем корень проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete, update
from app.database import async_session
from app.models.branch import BhmBranch
from app.models.inventory import Inventory
from app.models.employee import Employee
from app.models.telegram_account import TelegramAccount
from app.models.request import Request, RequestComment

async def main():
    async with async_session() as session:
        bhm_code = "11200"
        result = await session.execute(select(BhmBranch).where(BhmBranch.bhm_code == bhm_code))
        branch = result.scalar_one_or_none()
        
        if not branch:
            print(f"Филиал с кодом {bhm_code} не найден в базе данных.")
            return

        print(f"Найден филиал: {branch.bhm_code} - {branch.branch_name} (ID: {branch.id})")

        # 1. Сначала отвязываем аккаунты телеграм от этого филиала
        await session.execute(
            update(TelegramAccount)
            .where(TelegramAccount.selected_branch_id == branch.id)
            .values(selected_branch_id=None)
        )
        print("Telegram-аккаунты отвязаны от филиала.")

        # 2. Получаем все заявки этого филиала
        reqs_result = await session.execute(select(Request.id).where(Request.branch_id == branch.id))
        request_ids = [r[0] for r in reqs_result.all()]
        
        if request_ids:
            print(f"Найдено {len(request_ids)} заявок филиала для удаления.")
            
            # Удаляем комментарии к заявкам
            await session.execute(delete(RequestComment).where(RequestComment.request_id.in_(request_ids)))
            print("Удалены комментарии к заявкам.")
            
            # Удаляем сами заявки
            await session.execute(delete(Request).where(Request.id.in_(request_ids)))
            print("Удалены заявки филиала.")

        # 3. Получаем всех сотрудников этого филиала и удаляем их
        emp_result = await session.execute(select(Employee.id).where(Employee.branch_id == branch.id))
        emp_ids = [e[0] for e in emp_result.all()]
        
        if emp_ids:
            print(f"Найдено {len(emp_ids)} сотрудников филиала для удаления.")
            
            # Отвязываем от оставшихся заявок (если вдруг они ссылаются)
            await session.execute(
                update(Request)
                .where(Request.employee_id.in_(emp_ids))
                .values(employee_id=None)
            )
            
            # Удаляем сотрудников
            await session.execute(delete(Employee).where(Employee.id.in_(emp_ids)))
            print("Сотрудники филиала удалены.")

        # 4. Удаляем всю технику (инвентарь) филиала
        inv_result = await session.execute(select(Inventory.id).where(Inventory.branch_id == branch.id))
        inv_ids = [i[0] for i in inv_result.all()]
        
        if inv_ids:
            print(f"Найдено {len(inv_ids)} единиц техники филиала для удаления.")
            await session.execute(delete(Inventory).where(Inventory.id.in_(inv_ids)))
            print("Удалена техника филиала.")

        # 5. Удаляем сам филиал
        await session.delete(branch)
        print(f"Филиал {bhm_code} успешно удален.")

        await session.commit()
        print("База данных успешно обновлена и очищена от моков!")

if __name__ == "__main__":
    asyncio.run(main())
