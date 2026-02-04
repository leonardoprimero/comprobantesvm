"""
Integración con Google Sheets para guardar los datos de transferencias.
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
from app.config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME
from app.paths import resolve_appdata_path
from app.validator import identificar_cuenta_destino


# Scopes necesarios para Google Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


def get_sheets_client():
    """
    Obtiene un cliente autenticado de Google Sheets.
    """
    if not SHEETS_AVAILABLE:
        raise ImportError("Librería gspread no instalada (Modo Lite).")

    credentials_path = resolve_appdata_path(GOOGLE_CREDENTIALS_PATH)
    if not credentials_path:
        raise ValueError("GOOGLE_CREDENTIALS_PATH no configurado en .env")
    
    credentials = Credentials.from_service_account_file(
        credentials_path,
        scopes=SCOPES
    )
    return gspread.authorize(credentials)


# Headers definidos
HEADERS = [
    "Fecha Aviso", "Fecha Depósito", "Monto", 
    "Emisor Nombre", "Banco Emisor", 
    "CBU Emisor", "CUIL Emisor", 
    "Cuenta Destino", "WhatsApp", 
    "Referencia", "Confianza"
]

def guardar_transferencia(
    datos: dict,
    whatsapp_from: str,
    timestamp_recepcion: str,
    texto_completo: str = ""
) -> dict:
    """
    Guarda una transferencia en Google Sheets con validaciones y formato.
    """
    try:
        client = get_sheets_client()
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(GOOGLE_SHEET_NAME)
        
        # 0. Verificar/Actualizar Headers
        # Leemos primera fila para ver si coincide
        try:
            first_row = sheet.row_values(1)
            if not first_row or first_row != HEADERS:
                sheet.update('A1:K1', [HEADERS])
        except Exception:
            pass # Si falla lectura, ignoramos y seguimos intentando append
            
        # 1. Preparar datos
        # Identificar cuenta destino
        cuenta_destino = identificar_cuenta_destino(datos.get("receptor_cbu", ""))
        nombre_cuenta_destino = cuenta_destino["nombre"] if cuenta_destino else "Cuenta Desconocida"
        
        # Formatear fecha recepción
        try:
            fecha_recepcion = datetime.fromisoformat(timestamp_recepcion.replace("Z", "+00:00"))
            fecha_formateada = fecha_recepcion.strftime("%d/%m/%Y %H:%M")
        except:
            fecha_formateada = timestamp_recepcion

        # Convertir confianza a etiqueta
        confianza_val = datos.get("confianza", 0)
        confianza_str = "OPTIMA" if confianza_val >= 0.90 else "REVEER"

        monto = datos.get("monto_numerico", 0)
        # Asegurar que fecha deposito sea string limpio
        fecha_deposito = str(datos.get("fecha_operacion", "")).strip()

        # Lógica para nombre de emisor (Manejo de Depósitos)
        emisor_nombre = datos.get("emisor_nombre", "")
        if not emisor_nombre:
            concepto = datos.get("concepto", "").lower()
            if "deposito" in concepto or "efectivo" in concepto:
                emisor_nombre = "DEPÓSITO EN EFECTIVO"

        # 2. Detectar duplicados
        # Traemos todas las filas
        todas_las_filas = sheet.get_all_values()
        es_duplicado = False
        
        # Normalizamos monto nuevo
        try:
            m_new_float = float(monto)
        except:
            m_new_float = 0.0

        # Saltamos header (fila 0)
        for i, row in enumerate(todas_las_filas):
            if i == 0: continue 
            if len(row) >= 3:
                row_fecha = str(row[1]).strip()
                row_monto = row[2]
                
                # Comparación:
                # 1. Fechas coinciden (string exacto por ahora, idealmente parsear)
                # 2. Montos coinciden (parseando a float para evitar dif "$100" vs "100")
                fechas_match = (row_fecha and row_fecha == fecha_deposito)
                
                montos_match = False
                try:
                    # Limpiar monto row: quitar $ , y espacios
                    m_row_clean = str(row_monto).replace('$', '').replace(',', '').strip()
                    if m_row_clean:
                        m_row_float = float(m_row_clean)
                        # Margen de error pequeño por coma flotante
                        if abs(m_row_float - m_new_float) < 1.0:
                            montos_match = True
                except:
                    pass
                
                if fechas_match and montos_match:
                    es_duplicado = True
                    break

        # 3. Preparar fila
        whatsapp_link = ""
        if whatsapp_from:
             numero_limpio = whatsapp_from.replace("@c.us", "")
             whatsapp_link = f'=HYPERLINK("https://wa.me/{numero_limpio}"; "{numero_limpio}")'

        fila = [
            fecha_formateada,               # A: Fecha Aviso
            fecha_deposito,                 # B: Fecha Depósito
            monto,                          # C: Monto
            emisor_nombre,                  # D: Nombre Emisor (Corregido)
            datos.get("banco_emisor", ""),  # E: Banco
            datos.get("emisor_cbu", ""),    # F: CBU Emisor
            datos.get("emisor_cuil", ""),   # G: CUIL Emisor
            nombre_cuenta_destino,          # H: Cuenta Destino
            whatsapp_link,                  # I: WhatsApp
            datos.get("referencia", ""),    # J: Referencia
            confianza_str                   # K: Confianza (OPTIMA/REVEER)
        ]
        
        # 4. Guardar
        sheet.append_row(fila, value_input_option='USER_ENTERED')
        
        # 5. Aplicar formato si es duplicado
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
            "message": "Guardado correctamente" + (" (Duplicado)" if es_duplicado else ""),
            "cuenta_destino": nombre_cuenta_destino,
            "es_duplicado": es_duplicado
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def verificar_conexion() -> dict:
    """
    Verifica que la conexión con Google Sheets funcione.
    """
    try:
        client = get_sheets_client()
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet(GOOGLE_SHEET_NAME)
        # Intentar leer la primera celda
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
