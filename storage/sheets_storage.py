"""
Almacenamiento de transferencias en Google Sheets.
Refactorizado desde app/sheets.py para el nuevo módulo storage.
"""
try:
    import gspread
    from google.oauth2.service_account import Credentials
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False
    gspread = None
    Credentials = None
from datetime import datetime
from typing import Optional


# Scopes necesarios para Google Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Headers definidos
HEADERS = [
    "Fecha Aviso", "Fecha Depósito", "Monto", 
    "Emisor Nombre", "Banco Emisor", 
    "CBU Emisor", "CUIL Emisor", 
    "Cuenta Destino", "WhatsApp", 
    "Referencia", "Confianza"
]


def _get_sheets_client(credentials_path: str):
    """Obtiene un cliente autenticado de Google Sheets."""
    if not SHEETS_AVAILABLE:
        raise ImportError("Librería gspread no instalada (Modo Lite).")
    
    if not credentials_path:
        raise ValueError("credentials_path no configurado")
    
    credentials = Credentials.from_service_account_file(
        credentials_path,
        scopes=SCOPES
    )
    return gspread.authorize(credentials)


def _detectar_duplicado(todas_las_filas: list, fecha_deposito: str, monto: float) -> bool:
    """Detecta si ya existe una transferencia con la misma fecha y monto."""
    for i, row in enumerate(todas_las_filas):
        if i == 0:
            continue  # Saltear header
        if len(row) >= 3:
            row_fecha = str(row[1]).strip()
            row_monto = row[2]
            
            fechas_match = (row_fecha and row_fecha == fecha_deposito)
            
            montos_match = False
            try:
                m_row_clean = str(row_monto).replace('$', '').replace(',', '').strip()
                if m_row_clean:
                    m_row_float = float(m_row_clean)
                    if abs(m_row_float - monto) < 1.0:
                        montos_match = True
            except:
                pass
            
            if fechas_match and montos_match:
                return True
    return False


def guardar_en_sheets(
    datos: dict,
    credentials_path: str,
    sheet_id: str,
    sheet_name: str = "Hoja 1",
    whatsapp_from: str = "",
    timestamp_recepcion: str = "",
    cuenta_destino: str = "Cuenta Desconocida"
) -> dict:
    """
    Guarda una transferencia en Google Sheets.
    
    Args:
        datos: Diccionario con los datos extraídos del comprobante
        credentials_path: Ruta al archivo de credenciales de Google
        sheet_id: ID del Google Sheet
        sheet_name: Nombre de la hoja dentro del Sheet
        whatsapp_from: Número de WhatsApp del remitente
        timestamp_recepcion: Timestamp de recepción del comprobante
        cuenta_destino: Nombre de la cuenta destino identificada
        
    Returns:
        Dict con resultado de la operación
    """
    try:
        client = _get_sheets_client(credentials_path)
        sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
        
        # Verificar/Actualizar Headers
        try:
            first_row = sheet.row_values(1)
            if not first_row or first_row != HEADERS:
                sheet.update('A1:K1', [HEADERS])
        except Exception:
            pass
        
        # Formatear fecha recepción
        try:
            fecha_recepcion = datetime.fromisoformat(timestamp_recepcion.replace("Z", "+00:00"))
            fecha_formateada = fecha_recepcion.strftime("%d/%m/%Y %H:%M")
        except:
            fecha_formateada = timestamp_recepcion or datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # Preparar datos
        monto = datos.get("monto_numerico", 0)
        fecha_deposito = str(datos.get("fecha_operacion", "")).strip()
        
        # Lógica para nombre de emisor
        emisor_nombre = datos.get("emisor_nombre", "")
        if not emisor_nombre:
            concepto = datos.get("concepto", "").lower()
            if "deposito" in concepto or "efectivo" in concepto:
                emisor_nombre = "DEPÓSITO EN EFECTIVO"
        
        # Convertir confianza a etiqueta
        confianza_val = datos.get("confianza", 0)
        confianza_str = "OPTIMA" if confianza_val >= 0.90 else "REVEER"
        
        # Detectar duplicados
        todas_las_filas = sheet.get_all_values()
        es_duplicado = _detectar_duplicado(todas_las_filas, fecha_deposito, monto)
        
        # Preparar link de WhatsApp
        whatsapp_link = ""
        if whatsapp_from:
            numero_limpio = whatsapp_from.replace("@c.us", "")
            whatsapp_link = f'=HYPERLINK("https://wa.me/{numero_limpio}"; "{numero_limpio}")'
        
        # Crear fila
        fila = [
            fecha_formateada,               # A: Fecha Aviso
            fecha_deposito,                 # B: Fecha Depósito
            monto,                          # C: Monto
            emisor_nombre,                  # D: Nombre Emisor
            datos.get("banco_emisor", ""),  # E: Banco
            datos.get("emisor_cbu", ""),    # F: CBU Emisor
            datos.get("emisor_cuil", ""),   # G: CUIL Emisor
            cuenta_destino,                 # H: Cuenta Destino
            whatsapp_link,                  # I: WhatsApp
            datos.get("referencia", ""),    # J: Referencia
            confianza_str                   # K: Confianza
        ]
        
        # Guardar
        sheet.append_row(fila, value_input_option='USER_ENTERED')
        
        # Aplicar formato si es duplicado
        if es_duplicado:
            nueva_fila_idx = len(todas_las_filas) + 1
            rango = f"A{nueva_fila_idx}:K{nueva_fila_idx}"
            sheet.format(rango, {
                "backgroundColor": {
                    "red": 1.0, "green": 1.0, "blue": 0.8
                }
            })
        
        return {
            "success": True,
            "message": "Guardado en Google Sheets" + (" (Duplicado)" if es_duplicado else ""),
            "es_duplicado": es_duplicado
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def verificar_conexion_sheets(credentials_path: str, sheet_id: str, sheet_name: str) -> dict:
    """Verifica que la conexión con Google Sheets funcione."""
    try:
        client = _get_sheets_client(credentials_path)
        sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
        sheet.acell('A1').value
        return {
            "success": True,
            "message": "Conexión exitosa con Google Sheets"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
