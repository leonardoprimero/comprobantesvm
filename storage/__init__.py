"""
Módulo de almacenamiento para comprobantes procesados.
Soporta Excel local y Google Sheets.
"""

from storage.excel_storage import guardar_en_excel
from storage.sheets_storage import guardar_en_sheets
from storage.storage_manager import guardar_transferencia

__all__ = ['guardar_en_excel', 'guardar_en_sheets', 'guardar_transferencia']
