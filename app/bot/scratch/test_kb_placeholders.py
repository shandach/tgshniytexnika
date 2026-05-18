
import sys
import os

# Добавляем путь к проекту в sys.path
sys.path.append("/Users/beckham/Documents/tgtexnika")

from app.bot.keyboards.default import (
    get_main_menu_kb, get_request_type_kb, 
    get_cancel_kb, get_fio_reuse_kb, get_position_kb
)
from app.bot.utils.texts import _

def test_keyboards():
    print("--- ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ ПЛЕЙСХОЛДЕРОВ ---")
    
    languages = ["uz", "ru"]
    scenarios = [
        ("Новый пользователь", True),
        ("Пользователь с историей", False)
    ]
    
    for lang in languages:
        print(f"\n===== ЯЗЫК: {lang.upper()} =====")
        for label, is_new in scenarios:
            print(f"\n>>> {label}")
            
            # 1. Main Menu
            kb = get_main_menu_kb(lang=lang, is_new=is_new)
            print(f"Main Menu: placeholder = {kb.input_field_placeholder}")
            
            # 2. Position KB
            kb = get_position_kb(lang=lang, is_new=is_new)
            print(f"Position KB: placeholder = {kb.input_field_placeholder}")
            
            # 3. Reason/Problem step (Специальная логика)
            placeholder = _("ph_reason", lang) if not is_new else " "
            print(f"Reason/Problem step: placeholder = {placeholder}")
            
            if not is_new:
                # 4. FIO Reuse
                kb = get_fio_reuse_kb(fio="Test", position="Dev", lang=lang)
                print(f"FIO Reuse: placeholder = {kb.input_field_placeholder}")

    print("\n--- ТЕСТ ЗАВЕРШЕН ---")

if __name__ == "__main__":
    test_keyboards()
