"""
Módulo de gestión de licencias.
Verifica remotamente si el cliente tiene permiso para usar el software.
"""
import requests
import json
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# URL por defecto para verificación de licencias (Gist de ejemplo o raw JSON)
# EL VENDEDOR DEBE CAMBIAR ESTO POR SU PROPIA URL (Gist raw, S3, etc.)
DEFAULT_LICENSE_URL = "https://gist.githubusercontent.com/user/gist_id/raw/licenses.json"

class LicenseManager:
    def __init__(self, client_id: str, license_url: str = ""):
        self.client_id = client_id
        self.license_url = license_url or DEFAULT_LICENSE_URL
        
    def check_license(self) -> Tuple[bool, str]:
        """
        Verifica si la licencia está activa.
        
        Returns:
            Tuple (is_active, message)
        """
        if not self.client_id:
            return False, "ID de cliente no configurado."
            
        try:
            logger.info(f"Verificando licencia para {self.client_id}...")
            response = requests.get(self.license_url, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"No se pudo contactar servidor de licencias (HTTP {response.status_code})")
                # FAIL-OPEN: Si servidor cae, permitir uso temporalmente (opcional)
                # O FAIL-CLOSED: return False, "Error de conexión con servidor de licencias"
                return True, "Modo offline (servidor no responde)" 
                
            data = response.json()
            
            # Verificar status global
            if data.get("status") != "active":
                return False, "Sistema desactivado temporalmente por mantenimiento."
                
            # Verificar cliente específico
            clients = data.get("clients", {})
            client_data = clients.get(self.client_id)
            
            if not client_data:
                return False, "Licencia no válida o ID de cliente incorrecto."
                
            if not client_data.get("active", False):
                msg = client_data.get("message", "Licencia suspendida. Contacte a soporte.")
                return False, msg
                
            return True, "Licencia activa."
            
        except Exception as e:
            logger.error(f"Error verificando licencia: {e}")
            # En caso de error de red, decidimos si bloquear o permitir
            # Por seguridad "kill switch", ante error permitimos (para no bloquear por falta de internet)
            # PERO si el objetivo es cobro estricto, mejor retornar False o reintentar.
            return True, "Verificación omitida por error de red."

