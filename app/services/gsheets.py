import os
import logging
from typing import List, Any
import gspread
from google.oauth2.service_account import Credentials
from app.config import settings

logger = logging.getLogger(__name__)

# Специфические скоупы для Google Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_client() -> gspread.client.Client:
    """Инициализирует и возвращает клиент gspread."""
    creds_path = settings.GOOGLE_SHEETS_CREDENTIALS_FILE
    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Google credentials file not found: {creds_path}")
        
    credentials = Credentials.from_service_account_file(
        creds_path, scopes=SCOPES
    )
    return gspread.authorize(credentials)

def append_row_to_sheet(row_data: List[Any]):
    """
    Добавляет строку в Google Таблицу.
    row_data: [Date, RequestId, FIO, BHM, Type, Status, Decision, Info...]
    """
    if not settings.GOOGLE_SHEETS_SPREADSHEET_ID:
        logger.warning("GOOGLE_SHEETS_SPREADSHEET_ID is not set in config.")
        return
        
    try:
        client = get_client()
        spreadsheet = client.open_by_key(settings.GOOGLE_SHEETS_SPREADSHEET_ID)
        # Получаем самый первый лист независимо от языка (Лист1 или Sheet1)
        worksheet = spreadsheet.get_worksheet(0)
        
        # Записываем строку
        worksheet.append_row(row_data)
        logger.info(f"Row successfully appended to Google Sheets: {row_data[0:2]}...")
    except Exception as e:
        logger.error(f"Failed to append row to Google Sheets: {e}")

async def sync_request_to_sheets(req):
    """
    Форматирует данные заявки (модель Request) и отправляет в GSheets.
    Должно запускаться в фоне или через asyncio.to_thread, чтобы не блочить Event Loop.
    """
    # Если GSheets не настроено, пропускаем
    if not settings.GOOGLE_SHEETS_SPREADSHEET_ID or not os.path.exists(settings.GOOGLE_SHEETS_CREDENTIALS_FILE):
        return

    import asyncio
    from zoneinfo import ZoneInfo
    from datetime import timezone
    
    if req.created_at:
        dt = req.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_tashkent = dt.astimezone(ZoneInfo("Asia/Tashkent"))
        date_str = dt_tashkent.strftime("%Y-%m-%d %H:%M:%S")
    else:
        date_str = ""
    row = [
        date_str,
        req.request_number,
        req.employee_fio_snapshot,
        req.bhm_code_snapshot,
        req.branch_name_snapshot,
        req.request_type,
        req.equipment_type,
        req.status,
        req.final_decision if req.final_decision else "",
        req.reason_text or req.problem_text or ""
    ]
    
    await asyncio.to_thread(append_row_to_sheet, row)
