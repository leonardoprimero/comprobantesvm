"""
Folder Watcher - Monitorea una carpeta y procesa archivos nuevos de comprobantes.
Usa hash SHA256 para evitar reprocesar archivos ya vistos.
"""
import os
import json
import hashlib
import base64
import time
import logging
from datetime import datetime
from typing import Optional, List, Callable
from pathlib import Path

logger = logging.getLogger(__name__)

# Ruta del archivo de archivos procesados
from app.paths import get_processed_files_path
DEFAULT_PROCESSED_FILE = get_processed_files_path()

# Extensiones válidas
EXTENSIONES_VALIDAS = ['.jpg', '.jpeg', '.png', '.pdf']


class FolderWatcher:
    """
    Monitorea una carpeta y procesa archivos de comprobantes nuevos.
    Evita duplicados usando hash SHA256.
    """
    
    def __init__(
        self,
        carpeta: str,
        processed_file: str = DEFAULT_PROCESSED_FILE,
        extensiones: Optional[List[str]] = None
    ):
        """
        Args:
            carpeta: Ruta a la carpeta a monitorear
            processed_file: Ruta al JSON que guarda archivos ya procesados
            extensiones: Lista de extensiones a procesar (default: jpg, png, pdf)
        """
        self.carpeta = carpeta
        self.processed_file = processed_file
        self.extensiones = extensiones or EXTENSIONES_VALIDAS
        self._inicializar()
    
    def _inicializar(self):
        """Crea archivos/directorios necesarios."""
        # Crear directorio de datos si no existe
        directorio = os.path.dirname(self.processed_file)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio)
        
        # Crear archivo de procesados si no existe
        if not os.path.exists(self.processed_file):
            self._guardar_procesados({
                "archivos": {},
                "ultimo_escaneo": None
            })
    
    def _cargar_procesados(self) -> dict:
        """Carga la lista de archivos procesados."""
        try:
            with open(self.processed_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"archivos": {}, "ultimo_escaneo": None}
    
    def _guardar_procesados(self, data: dict):
        """Guarda la lista de archivos procesados."""
        with open(self.processed_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _calcular_hash(self, ruta_archivo: str) -> str:
        """Calcula el hash SHA256 de un archivo."""
        sha256 = hashlib.sha256()
        with open(ruta_archivo, 'rb') as f:
            for bloque in iter(lambda: f.read(65536), b''):
                sha256.update(bloque)
        return sha256.hexdigest()
    
    def _archivo_a_base64(self, ruta_archivo: str) -> str:
        """Lee un archivo y lo convierte a base64."""
        with open(ruta_archivo, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def _obtener_mime_type(self, ruta_archivo: str) -> str:
        """Obtiene el MIME type basado en la extensión."""
        ext = Path(ruta_archivo).suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.pdf': 'application/pdf'
        }
        return mime_types.get(ext, 'application/octet-stream')
    
    def ya_procesado(self, ruta_archivo: str) -> bool:
        """
        Verifica si un archivo ya fue procesado (por hash).
        
        Args:
            ruta_archivo: Ruta al archivo
            
        Returns:
            True si ya fue procesado, False si es nuevo
        """
        hash_archivo = self._calcular_hash(ruta_archivo)
        procesados = self._cargar_procesados()
        return hash_archivo in procesados["archivos"]
    
    def marcar_procesado(self, ruta_archivo: str, exito: bool = True, datos: Optional[dict] = None):
        """
        Marca un archivo como procesado.
        
        Args:
            ruta_archivo: Ruta al archivo
            exito: Si el procesamiento fue exitoso
            datos: Datos adicionales a guardar (opcional)
        """
        hash_archivo = self._calcular_hash(ruta_archivo)
        procesados = self._cargar_procesados()
        
        procesados["archivos"][hash_archivo] = {
            "nombre": os.path.basename(ruta_archivo),
            "ruta_original": ruta_archivo,
            "procesado_en": datetime.now().isoformat(),
            "exito": exito,
            "datos": datos
        }
        
        self._guardar_procesados(procesados)
        logger.info(f"Archivo marcado como procesado: {ruta_archivo}")
    
    def listar_archivos_nuevos(self) -> List[str]:
        """
        Lista archivos nuevos (no procesados) en la carpeta.
        
        Returns:
            Lista de rutas de archivos nuevos
        """
        if not os.path.exists(self.carpeta):
            logger.warning(f"La carpeta no existe: {self.carpeta}")
            return []
        
        archivos_nuevos = []
        
        for nombre in os.listdir(self.carpeta):
            ruta = os.path.join(self.carpeta, nombre)
            
            # Solo archivos (no directorios)
            if not os.path.isfile(ruta):
                continue
            
            # Verificar extensión
            ext = Path(nombre).suffix.lower()
            if ext not in self.extensiones:
                continue
            
            # Verificar si ya fue procesado
            if self.ya_procesado(ruta):
                continue
            
            archivos_nuevos.append(ruta)
        
        return archivos_nuevos
    
    def escanear_y_procesar(
        self,
        procesar_fn: Callable[[str, str, str], dict],
        intervalo_segundos: float = 2.0
    ) -> List[dict]:
        """
        Escanea la carpeta y procesa todos los archivos nuevos.
        
        Args:
            procesar_fn: Función que procesa un archivo.
                         Recibe: (file_base64, mime_type, nombre_archivo)
                         Retorna: dict con resultado
            intervalo_segundos: Segundos a esperar entre cada archivo
            
        Returns:
            Lista de resultados de procesamiento
        """
        archivos_nuevos = self.listar_archivos_nuevos()
        resultados = []
        
        logger.info(f"Encontrados {len(archivos_nuevos)} archivos nuevos en {self.carpeta}")
        
        for ruta in archivos_nuevos:
            nombre = os.path.basename(ruta)
            logger.info(f"Procesando: {nombre}")
            
            try:
                # Convertir a base64
                file_base64 = self._archivo_a_base64(ruta)
                mime_type = self._obtener_mime_type(ruta)
                
                # Procesar
                resultado = procesar_fn(file_base64, mime_type, nombre)
                
                # Marcar como procesado
                exito = resultado.get("success", False)
                self.marcar_procesado(ruta, exito=exito, datos=resultado.get("data"))
                
                resultados.append({
                    "archivo": nombre,
                    "ruta": ruta,
                    "resultado": resultado
                })
                
            except Exception as e:
                logger.error(f"Error procesando {nombre}: {e}")
                self.marcar_procesado(ruta, exito=False, datos={"error": str(e)})
                resultados.append({
                    "archivo": nombre,
                    "ruta": ruta,
                    "resultado": {"success": False, "error": str(e)}
                })
            
            # Esperar entre archivos
            if archivos_nuevos.index(ruta) < len(archivos_nuevos) - 1:
                time.sleep(intervalo_segundos)
        
        # Actualizar último escaneo
        procesados = self._cargar_procesados()
        procesados["ultimo_escaneo"] = datetime.now().isoformat()
        self._guardar_procesados(procesados)
        
        return resultados
    
    def obtener_estadisticas(self) -> dict:
        """
        Obtiene estadísticas de archivos procesados.
        
        Returns:
            Dict con estadísticas
        """
        procesados = self._cargar_procesados()
        archivos = procesados.get("archivos", {})
        
        total = len(archivos)
        exitosos = sum(1 for a in archivos.values() if a.get("exito", False))
        
        return {
            "total_procesados": total,
            "exitosos": exitosos,
            "fallidos": total - exitosos,
            "ultimo_escaneo": procesados.get("ultimo_escaneo"),
            "carpeta": self.carpeta
        }
    
    def limpiar_historial(self):
        """Limpia el historial de archivos procesados (para testing o reset)."""
        self._guardar_procesados({
            "archivos": {},
            "ultimo_escaneo": None
        })
        logger.info("Historial de archivos procesados limpiado")
