"""
Rutas y directorios de datos del sistema.
Mantiene los archivos de configuración y datos fuera de la carpeta instalada.
"""
import os
import sys
from pathlib import Path

APP_NAME = "SistemaComprobantes"


def get_app_data_dir() -> str:
    """Obtiene el directorio de datos del usuario según el sistema operativo."""
    override = os.environ.get("APP_DATA_DIR")
    if override:
        return override
    if sys.platform == "win32":
        base_dir = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base_dir = os.path.expanduser("~/Library/Application Support")
    else:
        base_dir = os.path.expanduser("~/.local/share")

    return os.path.join(base_dir, APP_NAME)


def ensure_dir(path: str) -> str:
    """Crea un directorio si no existe y devuelve la ruta."""
    os.makedirs(path, exist_ok=True)
    return path


def get_data_dir() -> str:
    return ensure_dir(os.path.join(get_app_data_dir(), "data"))


def get_config_path() -> str:
    return os.path.join(get_app_data_dir(), "config.json")


def get_usage_log_path() -> str:
    return os.path.join(get_data_dir(), "usage_log.json")


def get_processed_files_path() -> str:
    return os.path.join(get_data_dir(), "processed_files.json")


def get_qr_path() -> str:
    return os.path.join(get_app_data_dir(), "whatsapp_qr.png")


def resolve_appdata_path(path: str, fallback_name: str = "") -> str:
    """Resuelve un path relativo dentro de AppData."""
    if not path:
        if fallback_name:
            return os.path.join(get_app_data_dir(), fallback_name)
        return get_app_data_dir()
    if os.path.isabs(path):
        return path
    return os.path.join(get_app_data_dir(), path)


def get_resource_dir() -> str:
    """Ruta base donde viven los recursos del programa."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return str(Path(__file__).resolve().parents[1])
