import os
import sys

# Добавляем корень проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.gsheets import append_row_to_sheet

try:
    append_row_to_sheet(["TEST", "TEST", "TEST", "TEST", "TEST"])
    print("Success!")
except Exception as e:
    print(f"ERROR: {e}")
