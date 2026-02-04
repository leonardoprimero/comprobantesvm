"""
Cost Tracker - Registra uso de API y calcula costos con markup.
Guarda logs de uso para mostrar al cliente cuánto "gastó".
"""
import json
import os
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Ruta del archivo de log de uso
from app.paths import get_usage_log_path
DEFAULT_USAGE_LOG = get_usage_log_path()

# Costo aproximado por procesamiento (USD)
# GPT-4o Vision: ~$2.50/1M input tokens, ~$10/1M output tokens
# Una imagen promedio: ~1000 tokens input + ~500 tokens output
COSTO_BASE_POR_IMAGEN = 0.015  # ~$0.015 USD por imagen


class CostTracker:
    """
    Trackea el uso de la API y calcula costos con markup.
    """
    
    def __init__(self, markup: float = 2.0, usage_log_path: str = DEFAULT_USAGE_LOG):
        """
        Args:
            markup: Multiplicador de precio (2.0 = 100% ganancia)
            usage_log_path: Ruta al archivo JSON de log de uso
        """
        self.markup = markup
        self.usage_log_path = usage_log_path
        self.costo_base = COSTO_BASE_POR_IMAGEN
        self._inicializar_log()
    
    def _inicializar_log(self):
        """Crea el archivo de log si no existe."""
        directorio = os.path.dirname(self.usage_log_path)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio)
        
        if not os.path.exists(self.usage_log_path):
            self._guardar_log({
                "procesamientos": [],
                "resumen": {
                    "total_procesados": 0,
                    "total_exitosos": 0,
                    "total_fallidos": 0,
                    "costo_total_usd": 0.0,
                    "costo_mostrado_usd": 0.0
                }
            })
    
    def _cargar_log(self) -> dict:
        """Carga el log de uso."""
        try:
            with open(self.usage_log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "procesamientos": [],
                "resumen": {
                    "total_procesados": 0,
                    "total_exitosos": 0,
                    "total_fallidos": 0,
                    "costo_total_usd": 0.0,
                    "costo_mostrado_usd": 0.0
                }
            }
    
    def _guardar_log(self, data: dict):
        """Guarda el log de uso."""
        with open(self.usage_log_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def registrar_procesamiento(
        self,
        archivo: str,
        exito: bool,
        monto_extraido: Optional[float] = None,
        emisor: Optional[str] = None,
        fuente: str = "whatsapp"  # "whatsapp" o "carpeta"
    ) -> dict:
        """
        Registra un procesamiento de comprobante.
        
        Args:
            archivo: Nombre del archivo procesado
            exito: Si el procesamiento fue exitoso
            monto_extraido: Monto extraído del comprobante (si aplica)
            emisor: Nombre del emisor (si aplica)
            fuente: Fuente del comprobante ("whatsapp" o "carpeta")
            
        Returns:
            Dict con el costo calculado
        """
        log = self._cargar_log()
        
        # Calcular costos
        costo_real = self.costo_base if exito else 0.0
        costo_mostrado = costo_real * self.markup
        
        # Crear registro
        registro = {
            "timestamp": datetime.now().isoformat(),
            "archivo": archivo,
            "exito": exito,
            "fuente": fuente,
            "monto_extraido": monto_extraido,
            "emisor": emisor,
            "costo_real_usd": round(costo_real, 4),
            "costo_mostrado_usd": round(costo_mostrado, 4)
        }
        
        # Agregar al log
        log["procesamientos"].append(registro)
        
        # Actualizar resumen
        log["resumen"]["total_procesados"] += 1
        if exito:
            log["resumen"]["total_exitosos"] += 1
        else:
            log["resumen"]["total_fallidos"] += 1
        log["resumen"]["costo_total_usd"] += costo_real
        log["resumen"]["costo_mostrado_usd"] += costo_mostrado
        
        # Redondear totales
        log["resumen"]["costo_total_usd"] = round(log["resumen"]["costo_total_usd"], 4)
        log["resumen"]["costo_mostrado_usd"] = round(log["resumen"]["costo_mostrado_usd"], 4)
        
        self._guardar_log(log)
        
        logger.info(f"Procesamiento registrado: {archivo} - Costo mostrado: ${costo_mostrado:.4f} USD")
        
        return {
            "costo_real_usd": costo_real,
            "costo_mostrado_usd": costo_mostrado,
            "total_procesados": log["resumen"]["total_procesados"],
            "costo_total_mostrado_usd": log["resumen"]["costo_mostrado_usd"]
        }
    
    def obtener_resumen(self) -> dict:
        """
        Obtiene el resumen de uso y costos.
        
        Returns:
            Dict con estadísticas de uso
        """
        log = self._cargar_log()
        resumen = log["resumen"].copy()
        
        # Agregar costo en ARS (cotización estimada)
        cotizacion_usd_ars = 1200  # Ajustar según cotización actual
        resumen["costo_mostrado_ars"] = round(resumen["costo_mostrado_usd"] * cotizacion_usd_ars, 2)
        
        return resumen
    
    def obtener_resumen_mensual(self, mes: Optional[int] = None, año: Optional[int] = None) -> dict:
        """
        Obtiene el resumen de uso para un mes específico.
        
        Args:
            mes: Número de mes (1-12). Si no se especifica, usa el mes actual.
            año: Año. Si no se especifica, usa el año actual.
            
        Returns:
            Dict con estadísticas del mes
        """
        log = self._cargar_log()
        
        # Usar mes/año actual si no se especifica
        ahora = datetime.now()
        mes = mes or ahora.month
        año = año or ahora.year
        
        # Filtrar procesamientos del mes
        procesamientos_mes = []
        for p in log["procesamientos"]:
            try:
                fecha = datetime.fromisoformat(p["timestamp"])
                if fecha.month == mes and fecha.year == año:
                    procesamientos_mes.append(p)
            except:
                continue
        
        # Calcular resumen del mes
        total_procesados = len(procesamientos_mes)
        total_exitosos = sum(1 for p in procesamientos_mes if p.get("exito"))
        costo_mostrado = sum(p.get("costo_mostrado_usd", 0) for p in procesamientos_mes)
        
        # Cotización USD a ARS
        cotizacion_usd_ars = 1200
        
        return {
            "mes": mes,
            "año": año,
            "total_procesados": total_procesados,
            "total_exitosos": total_exitosos,
            "total_fallidos": total_procesados - total_exitosos,
            "costo_mostrado_usd": round(costo_mostrado, 4),
            "costo_mostrado_ars": round(costo_mostrado * cotizacion_usd_ars, 2)
        }
    
    def limpiar_log(self):
        """Limpia el log de uso (para testing o reset)."""
        self._guardar_log({
            "procesamientos": [],
            "resumen": {
                "total_procesados": 0,
                "total_exitosos": 0,
                "total_fallidos": 0,
                "costo_total_usd": 0.0,
                "costo_mostrado_usd": 0.0
            }
        })
