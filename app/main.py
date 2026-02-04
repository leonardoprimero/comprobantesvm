"""
API FastAPI para procesamiento de comprobantes de transferencias bancarias.
Punto de entrada principal del sistema.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

from app.extractor import extraer_datos_comprobante
from storage.storage_manager import guardar_transferencia
from app.sheets import verificar_conexion  # Mantener por retrocompatibilidad o actualizar
from app.config import MIN_CONFIDENCE
from billing.cost_tracker import CostTracker
import json
import os
from app.paths import resolve_appdata_path
import shutil
from app.paths import get_config_path, get_resource_dir

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar configuración
def _ensure_config_file() -> str:
    config_path = get_config_path()
    if os.path.exists(config_path):
        return config_path

    resource_dir = get_resource_dir()
    example_path = os.path.join(resource_dir, "config.example.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    if os.path.exists(example_path):
        shutil.copy2(example_path, config_path)
    else:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)

    return config_path


def cargar_config() -> dict:
    config_path = _ensure_config_file()
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando config: {e}")
        return {}

CONFIG = cargar_config()
COST_TRACKER = CostTracker(markup=CONFIG.get('billing', {}).get('markup', 2.0))

# Crear app FastAPI
app = FastAPI(
    title="Receipt Processing API",
    description="API profesional para procesar comprobantes de transferencias bancarias argentinas",
    version="1.0.0"
)

# Configurar CORS para permitir requests desde n8n
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Modelos de request/response
class ProcessReceiptRequest(BaseModel):
    """Request para procesar un comprobante"""
    file_base64: str  # Imagen o PDF en base64
    sender_phone: str = ""  # Número de WhatsApp del remitente
    timestamp: str = ""  # Timestamp de recepción
    mime_type: str = "image/jpeg"  # Tipo MIME del archivo
    texto_completo: str = ""  # Texto OCR previo (opcional)


class ProcessReceiptResponse(BaseModel):
    """Response del procesamiento"""
    success: bool
    message: str
    data: Optional[dict] = None
    cuenta_destino: Optional[str] = None
    confianza: float = 0.0
    requiere_revision: bool = False
    costo_usd: Optional[float] = None


class HealthResponse(BaseModel):
    """Response del health check"""
    status: str
    sheets_connection: bool
    timestamp: str
    storage_config: dict


@app.get("/", response_model=dict)
async def root():
    """Endpoint raíz"""
    return {
        "service": "Receipt Processing API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verifica el estado del servicio y conexiones"""
    # Verificar Sheet solo si está habilitado
    sheets_status = {"success": False}
    if CONFIG.get("storage", {}).get("sheets_enabled"):
        try:
            from storage.sheets_storage import verificar_conexion_sheets
            sheets_status = verificar_conexion_sheets(
                resolve_appdata_path(CONFIG.get("google_credentials_path", "")),
                CONFIG.get("storage", {}).get("sheets_id", ""),
                CONFIG.get("storage", {}).get("sheets_name", "Hoja 1")
            )
        except Exception:
            pass

    return HealthResponse(
        status="healthy",
        sheets_connection=sheets_status.get("success", False),
        timestamp=datetime.now().isoformat(),
        storage_config=CONFIG.get("storage", {})
    )


@app.post("/process-receipt/", response_model=ProcessReceiptResponse)
async def process_receipt(request: ProcessReceiptRequest):
    """
    Procesa un comprobante de transferencia bancaria.
    
    Recibe una imagen en base64, extrae los datos usando GPT-4o Vision,
    valida la información y la guarda en los destinos configurados.
    """
    logger.info(f"Procesando comprobante de: {request.sender_phone}")
    
    try:
        # 1. Extraer datos del comprobante usando GPT-4o Vision
        resultado_extraccion = extraer_datos_comprobante(
            imagen_base64=request.file_base64,
            mime_type=request.mime_type
        )
        
        datos = resultado_extraccion.get("data", {})
        confianza = datos.get("confianza", 0) if datos else 0
        
        if not resultado_extraccion.get("success"):
            logger.error(f"Error en extracción: {resultado_extraccion.get('error')}")
            # Registrar fallo
            COST_TRACKER.registrar_procesamiento(
                archivo="api_upload",
                exito=False,
                fuente="whatsapp" if request.sender_phone else "api"
            )
            return ProcessReceiptResponse(
                success=False,
                message=f"Error al extraer datos: {resultado_extraccion.get('error')}",
                requiere_revision=True
            )
        
        # 2. Verificar nivel de confianza
        requiere_revision = confianza < MIN_CONFIDENCE
        
        if requiere_revision:
            logger.warning(f"Baja confianza: {confianza}. Requiere revisión manual.")
        
        # 3. Guardar en destinos configurados
        timestamp = request.timestamp or datetime.now().isoformat()
        
        resultado_guardado = guardar_transferencia(
            datos=datos,
            config=CONFIG,
            whatsapp_from=request.sender_phone,
            timestamp_recepcion=timestamp
        )
        
        exito_guardado = resultado_guardado.get("success", False)
        
        # 4. Registrar costos
        registro_costo = COST_TRACKER.registrar_procesamiento(
            archivo="api_upload",
            exito=exito_guardado,
            monto_extraido=datos.get("monto_numerico"),
            emisor=datos.get("emisor_nombre"),
            fuente="whatsapp" if request.sender_phone else "api"
        )
        
        if not exito_guardado:
            logger.error(f"Error al guardar: {resultado_guardado.get('message')}")
            return ProcessReceiptResponse(
                success=False,
                message=resultado_guardado.get("message"),
                data=datos,
                confianza=confianza,
                requiere_revision=True,
                costo_usd=registro_costo.get("costo_mostrado_usd")
            )
        
        # 5. Respuesta exitosa
        logger.info(f"Comprobante procesado. Monto: {datos.get('monto_numerico', 0)}")
        
        return ProcessReceiptResponse(
            success=True,
            message=resultado_guardado.get("message"),
            data=datos,
            cuenta_destino=resultado_guardado.get("cuenta_destino"),
            confianza=confianza,
            requiere_revision=requiere_revision,
            costo_usd=registro_costo.get("costo_mostrado_usd")
        )
        
    except Exception as e:
        logger.exception("Error inesperado al procesar comprobante")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@app.post("/extract-only/", response_model=dict)
async def extract_only(request: ProcessReceiptRequest):
    """
    Solo extrae datos del comprobante sin guardar en Google Sheets.
    Útil para testing y debugging.
    """
    resultado = extraer_datos_comprobante(
        imagen_base64=request.file_base64,
        mime_type=request.mime_type
    )
    return resultado


# Para ejecutar directamente con: python -m app.main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
