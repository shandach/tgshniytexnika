import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import select

# Добавляем корень проекта в sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import async_session
from app.models.branch import BhmBranch, LocationType

# 14 стандартных регионов
STANDARD_REGIONS = [
    "Андижон вилояти",
    "Бухоро вилояти",
    "Жиззах вилояти",
    "Қорақалпоғистон Республикаси",
    "Қашқадарё вилояти",
    "Навоий вилояти",
    "Наманган вилояти",
    "Самарқанд вилояти",
    "Сурхондарё вилояти",
    "Сирдарё вилояти",
    "Тошкент вилояти",
    "Тошкент шаҳри",
    "Фарғона вилояти",
    "Хоразм вилояти",
]

# Словарь для маппинга аббревиатур и разных написаний в стандартные регионы
REGION_MAPPING = {
    "анд": "Андижон вилояти",
    "андиж": "Андижон вилояти",
    "бух": "Бухоро вилояти",
    "бухор": "Бухоро вилояти",
    "жиз": "Жиззах вилояти",
    "жиззах": "Жиззах вилояти",
    "ққр": "Қорақалпоғистон Республикаси",
    "ккр": "Қорақалпоғистон Республикаси",
    "қорақалпоғ": "Қорақалпоғистон Республикаси",
    "қаш": "Қашқадарё вилояти",
    "қашқадар": "Қашқадарё вилояти",
    "каш": "Қашқадарё вилояти",
    "нав": "Навоий вилояти",
    "навоий": "Навоий вилояти",
    "нам": "Наманган вилояти",
    "наманган": "Наманган вилояти",
    "сам": "Самарқанд вилояти",
    "самарқанд": "Самарқанд вилояти",
    "самарканд": "Самарқанд вилояти",
    "сурх": "Сурхондарё вилояти",
    "сурхондарё": "Сурхондарё вилояти",
    "сир": "Сирдарё вилояти",
    "сирдарё": "Сирдарё вилояти",
    "тош. в": "Тошкент вилояти",
    "тош.в": "Тошкент вилояти",
    "тошкент вил": "Тошкент вилояти",
    "тош. ш": "Тошкент шаҳри",
    "тош.ш": "Тошкент шаҳри",
    "тошкент ш": "Тошкент шаҳри",
    "г. ташкент": "Тошкент шаҳри",
    "toshkent sh": "Тошкент шаҳри",
    "фар": "Фарғона вилояти",
    "фарғона": "Фарғона вилояти",
    "ферган": "Фарғона вилояти",
    "хор": "Хоразм вилояти",
    "хоразм": "Хоразм вилояти",
}

def map_region(raw_name: str) -> str:
    """Сопоставляет сырое название региона со стандартным."""
    if not isinstance(raw_name, str):
        return None
        
    clean_name = raw_name.lower().strip()
    
    # Прямое совпадение
    for standard in STANDARD_REGIONS:
        if standard.lower() == clean_name:
            return standard
            
    # Поиск по маппингу
    for key, standard in REGION_MAPPING.items():
        if clean_name.startswith(key) or key in clean_name:
            return standard
            
    return None

def clean_address(raw_address: str) -> str:
    """Очищает адрес от почтовых индексов и номеров домов в конце."""
    if not isinstance(raw_address, str):
        return ""
        
    addr = str(raw_address).strip()
    
    # Удаляем 6-значные почтовые индексы (например, 100011)
    addr = re.sub(r'\b\d{6}\b', '', addr)
    
    # Удаляем "уй N", "уй 12", "12-уй", ", 12", " № 12" в конце строки
    # (мусорные цифры, номера домов)
    # Но сохраняем "уй" если это смысловая часть (хотя обычно это просто дом)
    addr = re.sub(r'(?:,\s*|\s+)(?:уй\s*\d+|\d+-уй|№\s*\d+|\d+)\s*$', '', addr, flags=re.IGNORECASE)
    
    # Очищаем двойные пробелы и запятые
    addr = re.sub(r'\s+', ' ', addr)
    addr = re.sub(r',\s*,', ',', addr)
    addr = addr.strip(', ')
    
    return addr

async def import_from_excel(file_path: str, dry_run: bool = False):
    print(f"[{'DRY-RUN' if dry_run else 'IMPORT'}] Чтение файла: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return
        
    try:
        df = pd.read_excel(file_path, header=2, dtype=str)
        df.columns = df.columns.str.strip()
    except Exception as e:
        print(f"❌ Ошибка чтения Excel: {e}")
        return

    # Ожидаемые колонки
    col_region = "Минт. марказ номи"
    col_city = "БХМ номи"
    col_code = "БХМ коди"
    col_address = "012-маълумотлар базаси бўйича БХМ манзили (индекс, туман/шаҳар, мфй, уй)"
    
    missing_cols = [c for c in [col_region, col_city, col_code, col_address] if c not in df.columns]
    if missing_cols:
        print(f"❌ В файле отсутствуют необходимые колонки:\n" + "\n".join(missing_cols))
        print("Доступные колонки:", list(df.columns))
        return

    stats = {
        "total": len(df),
        "valid": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "unmapped_regions": set()
    }
    
    updates_to_db = []
    creates_to_db = []
    
    async with async_session() as session:
        # Загружаем существующие БХМ для проверки
        result = await session.execute(select(BhmBranch))
        existing_branches = {b.bhm_code: b for b in result.scalars().all()}
        
        for idx, row in df.iterrows():
            row_num = idx + 2 # Excel row number (header is 1)
            raw_region = str(row.get(col_region, "")).strip()
            raw_city = str(row.get(col_city, "")).strip()
            raw_code = str(row.get(col_code, "")).strip()
            raw_address = str(row.get(col_address, "")).strip()
            
            # Пропуск пустых строк
            if not raw_code or raw_code == 'nan':
                print(f"⚠️ [Строка {row_num}] Пропуск: пустой БХМ код")
                stats["skipped"] += 1
                continue
                
            # Маппинг региона
            region = map_region(raw_region)
            if not region:
                print(f"❌ [Строка {row_num}] Ошибка: Не удалось сопоставить регион '{raw_region}' (БХМ {raw_code})")
                stats["unmapped_regions"].add(raw_region)
                stats["skipped"] += 1
                continue
                
            # Очистка данных
            branch_name = clean_address(raw_address) or raw_city # фоллбэк если адрес пустой
            city_name = raw_city
            
            # Определение location_type
            location_type = LocationType.city if region == "Тошкент шаҳри" else LocationType.regional
            
            stats["valid"] += 1
            
            # Проверка существования
            if raw_code in existing_branches:
                existing = existing_branches[raw_code]
                # Проверяем, изменилось ли что-то
                if (existing.branch_name != branch_name or 
                    existing.region_name != region or 
                    existing.city_name != city_name or 
                    existing.location_type != location_type):
                    
                    if not dry_run:
                        existing.branch_name = branch_name
                        existing.region_name = region
                        existing.city_name = city_name
                        existing.location_type = location_type
                    updates_to_db.append(raw_code)
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            else:
                if not dry_run:
                    new_branch = BhmBranch(
                        bhm_code=raw_code,
                        branch_name=branch_name,
                        region_name=region,
                        city_name=city_name,
                        location_type=location_type,
                        is_active=True
                    )
                    session.add(new_branch)
                creates_to_db.append(raw_code)
                stats["created"] += 1
                
        if not dry_run and (updates_to_db or creates_to_db):
            await session.commit()
            
    print("\n" + "="*40)
    print("📊 РЕЗУЛЬТАТЫ ИМПОРТА" + (" (DRY RUN)" if dry_run else ""))
    print("="*40)
    print(f"Всего строк прочитано:  {stats['total']}")
    print(f"Валидных строк:         {stats['valid']}")
    print(f"Будет создано:          {stats['created']}")
    print(f"Будет обновлено:        {stats['updated']}")
    print(f"Пропущено/Без измен.:   {stats['skipped']}")
    
    if stats["unmapped_regions"]:
        print("\n⚠️ НЕИЗВЕСТНЫЕ РЕГИОНЫ (добавьте в REGION_MAPPING):")
        for ur in stats["unmapped_regions"]:
            print(f" - '{ur}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Импорт БХМ из Excel в базу данных")
    parser.add_argument("--file", type=str, required=True, help="Путь к Excel файлу")
    parser.add_argument("--dry-run", action="store_true", help="Проверка без сохранения в БД")
    
    args = parser.parse_args()
    
    # В MacOS/Linux pandas требует openpyxl для .xlsx
    try:
        import openpyxl
    except ImportError:
        print("❌ Не установлена библиотека openpyxl. Установите: pip install pandas openpyxl")
        sys.exit(1)
        
    asyncio.run(import_from_excel(args.file, args.dry_run))
