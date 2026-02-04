"""
Storage Manager - Orquestador de almacenamiento.
Decide dónde guardar según configuración: Excel, Sheets, o ambos.
"""
import logging
from typing import Optional
from storage.excel_storage import guardar_en_excel
from storage.sheets_storage import guardar_en_sheets
from app.validator import identificar_cuenta_destino
from app.paths import resolve_appdata_path

logger = logging.getLogger(__name__)


def guardar_transferencia(
    datos: dict,
    config: dict,
    whatsapp_from: str = "",
    timestamp_recepcion: str = ""
) -> dict:
    """
    Guarda una transferencia en los destinos configurados (Excel, Sheets, o ambos).
    
    Args:
        datos: Diccionario con los datos extraídos del comprobante
        config: Diccionario de configuración con opciones de storage
        whatsapp_from: Número de WhatsApp del remitente
        timestamp_recepcion: Timestamp de recepción del comprobante
        
    Returns:
        Dict con resultados de cada destino
    """
    resultados = {
        "excel": None,
        "sheets": None,
        "success": False,
        "message": ""
    }
    
    # Identificar cuenta destino
    cuenta_destino = identificar_cuenta_destino(datos.get("receptor_cbu", ""))
    nombre_cuenta_destino = cuenta_destino["nombre"] if cuenta_destino else "Cuenta Desconocida"
    
    storage_config = config.get("storage", {})
    errores = []
    exitos = []
    
    # Guardar en Excel si está habilitado
    if storage_config.get("excel_enabled", False):
        ruta_excel = storage_config.get("excel_path", "transferencias.xlsx")
        logger.info(f"Guardando en Excel: {ruta_excel}")
        
        resultado_excel = guardar_en_excel(
            datos=datos,
            ruta_excel=ruta_excel,
            whatsapp_from=whatsapp_from,
            timestamp_recepcion=timestamp_recepcion,
            cuenta_destino=nombre_cuenta_destino
        )
        
        resultados["excel"] = resultado_excel
        
        if resultado_excel.get("success"):
            exitos.append("Excel")
        else:
            errores.append(f"Excel: {resultado_excel.get('error', 'Error desconocido')}")
    
    # Guardar en Google Sheets si está habilitado
    if storage_config.get("sheets_enabled", False):
        credentials_path = resolve_appdata_path(config.get("google_credentials_path", ""))
        sheet_id = storage_config.get("sheets_id", "")
        sheet_name = storage_config.get("sheets_name", "Hoja 1")
        
        if not credentials_path or not sheet_id:
            errores.append("Sheets: Credenciales o ID de Sheet no configurados")
        else:
            logger.info(f"Guardando en Google Sheets: {sheet_id}")
            
            resultado_sheets = guardar_en_sheets(
                datos=datos,
                credentials_path=credentials_path,
                sheet_id=sheet_id,
                sheet_name=sheet_name,
                whatsapp_from=whatsapp_from,
                timestamp_recepcion=timestamp_recepcion,
                cuenta_destino=nombre_cuenta_destino
            )
            
            resultados["sheets"] = resultado_sheets
            
            if resultado_sheets.get("success"):
                exitos.append("Google Sheets")
            else:
                errores.append(f"Sheets: {resultado_sheets.get('error', 'Error desconocido')}")
    
    # Determinar resultado final
    if exitos:
        resultados["success"] = True
        resultados["message"] = f"Guardado en: {', '.join(exitos)}"
        if errores:
            resultados["message"] += f" | Errores: {'; '.join(errores)}"
    else:
        if errores:
            resultados["message"] = f"Errores: {'; '.join(errores)}"
        else:
            resultados["message"] = "No hay destinos de almacenamiento habilitados"
    
    resultados["cuenta_destino"] = nombre_cuenta_destino
    
    return resultados
