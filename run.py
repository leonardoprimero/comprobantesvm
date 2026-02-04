#!/usr/bin/env python3
"""
Script principal para ejecutar el sistema de procesamiento de comprobantes.
Inicia la API Python y opcionalmente el monitor de carpeta.
"""
import os
import sys
import json
import signal
import logging
import threading
import time
import shutil
from datetime import datetime

# Force UTF-8 encoding for Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar módulos del proyecto
from app.extractor import extraer_datos_comprobante
from storage.storage_manager import guardar_transferencia
from billing.cost_tracker import CostTracker
from watcher.folder_watcher import FolderWatcher
from app.license import LicenseManager
from app.paths import get_config_path, get_resource_dir

# Cargar configuración
def _ensure_config_file() -> str:
    """Asegura que exista config.json en el directorio de datos."""
    config_path = get_config_path()
    if os.path.exists(config_path):
        return config_path

    resource_dir = get_resource_dir()
    example_path = os.path.join(resource_dir, "config.example.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    if os.path.exists(example_path):
        shutil.copy2(example_path, config_path)
    else:
        # Crear config mínima si no existe ejemplo
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)

    return config_path


def cargar_config() -> dict:
    """Carga el archivo config.json."""
    config_path = _ensure_config_file()
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"No se encontró config.json en {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Error al parsear config.json: {e}")
        sys.exit(1)

def verificar_licencia(config: dict):
    """Verifica si la licencia es válida."""
    client_id = config.get("client_id", "")
    license_url = config.get("license_url", "")
    
    if not client_id:
        logger.warning("⚠️  Advertencia: No hay Client ID configurado (Modo Developer)")
        return
        
    lm = LicenseManager(client_id, license_url)
    activo, msg = lm.check_license()
    
    if not activo:
        logger.error("="*50)
        logger.error(f"❌ LICENCIA BLOQUEADA: {msg}")
        logger.error("="*50)
        sys.exit(1)
    
    logger.info(f"✅ Licencia verificada para: {client_id}")



# Variable global para control de ejecución
ejecutando = True
config = None
cost_tracker = None


def procesar_archivo(file_base64: str, mime_type: str, nombre_archivo: str) -> dict:
    """
    Procesa un archivo de comprobante.
    Esta función es llamada tanto por el folder watcher como por la API.
    """
    global config, cost_tracker
    
    # 1. Extraer datos con GPT-4o Vision
    resultado_extraccion = extraer_datos_comprobante(
        imagen_base64=file_base64,
        mime_type=mime_type
    )
    
    if not resultado_extraccion.get("success"):
        # Registrar fallo en billing
        if cost_tracker:
            cost_tracker.registrar_procesamiento(
                archivo=nombre_archivo,
                exito=False,
                fuente="carpeta"
            )
        return resultado_extraccion
    
    datos = resultado_extraccion.get("data", {})
    
    # 2. Guardar en storage(s) configurado(s)
    resultado_guardado = guardar_transferencia(
        datos=datos,
        config=config,
        whatsapp_from="",  # Desde carpeta no hay WhatsApp
        timestamp_recepcion=datetime.now().isoformat()
    )
    
    # 3. Registrar en billing
    if cost_tracker:
        cost_tracker.registrar_procesamiento(
            archivo=nombre_archivo,
            exito=resultado_guardado.get("success", False),
            monto_extraido=datos.get("monto_numerico"),
            emisor=datos.get("emisor_nombre"),
            fuente="carpeta"
        )
    
    return {
        "success": resultado_guardado.get("success", False),
        "message": resultado_guardado.get("message", ""),
        "data": datos,
        "storage": resultado_guardado
    }


def iniciar_folder_watcher():
    """Inicia el monitor de carpeta en un hilo separado."""
    global config, ejecutando
    
    fuentes = config.get("fuentes", {})
    if not fuentes.get("carpeta_enabled", False):
        logger.info("Monitor de carpeta deshabilitado en config.json")
        return
    
    carpeta = fuentes.get("carpeta_ruta", "")
    if not carpeta or not os.path.exists(carpeta):
        logger.warning(f"Carpeta no existe o no configurada: {carpeta}")
        return
    
    watcher = FolderWatcher(carpeta=carpeta)
    logger.info(f"📁 Monitor de carpeta iniciado: {carpeta}")
    
    while ejecutando:
        try:
            # Escanear y procesar archivos nuevos
            resultados = watcher.escanear_y_procesar(
                procesar_fn=procesar_archivo,
                intervalo_segundos=2.0
            )
            
            if resultados:
                exitosos = sum(1 for r in resultados if r["resultado"].get("success"))
                logger.info(f"📊 Carpeta: {len(resultados)} archivos procesados, {exitosos} exitosos")
            
            # Esperar antes de siguiente escaneo
            time.sleep(10)
            
        except Exception as e:
            logger.error(f"Error en folder watcher: {e}")
            time.sleep(30)


def mostrar_resumen_costos():
    """Muestra el resumen de costos actual."""
    global cost_tracker
    
    if not cost_tracker:
        return
    
    resumen = cost_tracker.obtener_resumen()
    print("\n" + "=" * 50)
    print("💰 RESUMEN DE COSTOS")
    print("=" * 50)
    print(f"Total procesados: {resumen['total_procesados']}")
    print(f"Exitosos: {resumen['total_exitosos']}")
    print(f"Fallidos: {resumen['total_fallidos']}")
    print(f"Costo total: ${resumen['costo_mostrado_usd']:.4f} USD")
    print(f"Costo total: ${resumen.get('costo_mostrado_ars', 0):.2f} ARS (estimado)")
    print("=" * 50 + "\n")


def signal_handler(sig, frame):
    """Maneja señales de interrupción."""
    global ejecutando
    print("\n\n⚠️  Deteniendo sistema...")
    ejecutando = False
    mostrar_resumen_costos()
    sys.exit(0)


def main():
    """Función principal."""
    global config, cost_tracker, ejecutando
    
    # Registrar handler de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("\n" + "=" * 50)
    print("🚀 SISTEMA DE COMPROBANTES")
    print("=" * 50)
    
    # Cargar configuración
    config = cargar_config()
    logger.info("Configuración cargada correctamente")
    
    # Verificar licencia
    verificar_licencia(config)
    
    # Inicializar cost tracker
    billing_config = config.get("billing", {})
    markup = billing_config.get("markup", 2.0)
    cost_tracker = CostTracker(markup=markup)
    logger.info(f"Cost tracker iniciado (markup: {markup}x)")
    
    # Mostrar configuración
    fuentes = config.get("fuentes", {})
    storage = config.get("storage", {})
    
    print(f"\n📥 FUENTES:")
    print(f"   WhatsApp: {'✅ Habilitado' if fuentes.get('whatsapp_enabled') else '❌ Deshabilitado'}")
    print(f"   Carpeta:  {'✅ ' + fuentes.get('carpeta_ruta', '') if fuentes.get('carpeta_enabled') else '❌ Deshabilitado'}")
    
    print(f"\n📤 ALMACENAMIENTO:")
    print(f"   Excel:    {'✅ ' + storage.get('excel_path', '') if storage.get('excel_enabled') else '❌ Deshabilitado'}")
    print(f"   Sheets:   {'✅ Habilitado' if storage.get('sheets_enabled') else '❌ Deshabilitado'}")
    
    print("\n" + "=" * 50)
    
    # Iniciar folder watcher en hilo separado si está habilitado
    if fuentes.get("carpeta_enabled", False):
        thread_watcher = threading.Thread(target=iniciar_folder_watcher, daemon=True)
        thread_watcher.start()
    
    # Iniciar API FastAPI
    print("\n🌐 Iniciando API en http://localhost:8000")
    print("   Para WhatsApp: Iniciar 'node bot/index.js' en otra terminal")
    print("   Presionar Ctrl+C para detener\n")
    
    import uvicorn
    from app.main import app
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
