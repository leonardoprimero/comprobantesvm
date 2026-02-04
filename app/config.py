"""
Configuración del sistema de procesamiento de comprobantes.
Carga variables de entorno y define constantes.
"""
import os
import json
import shutil
from dotenv import load_dotenv
from app.paths import get_config_path, get_resource_dir

# Cargar variables de entorno desde .env
load_dotenv()

def _load_json_config() -> dict:
    config_path = get_config_path()
    try:
        if not os.path.exists(config_path):
            resource_dir = get_resource_dir()
            example_path = os.path.join(resource_dir, "config.example.json")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            if os.path.exists(example_path):
                shutil.copy2(example_path, config_path)
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


CONFIG_JSON = _load_json_config()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or CONFIG_JSON.get("openai_api_key", "")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH") or CONFIG_JSON.get("google_credentials_path", "")

# Google Sheets
_storage = CONFIG_JSON.get("storage", {})
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID") or _storage.get("sheets_id", "")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME") or _storage.get("sheets_name", "Hoja 1")

# Cuentas destino configurables
# Agregar tus cuentas aquí con su CBU como clave
CUENTAS_DESTINO = {
    # "CBU_22_DIGITOS": {"nombre": "Nombre de la cuenta", "alias": "alias.cuenta"},
    # Ejemplo:
    # "0070353430004027919665": {"nombre": "Cuenta Principal", "alias": "fucho.mp"},
}

# Bancos argentinos por código de entidad (primeros 3 dígitos del CBU)
BANCOS_ARGENTINOS = {
    "007": "Banco de Galicia",
    "011": "Banco de la Nación Argentina",
    "014": "Banco de la Provincia de Buenos Aires",
    "015": "ICBC",
    "016": "Citibank",
    "017": "BBVA Argentina",
    "020": "Banco de la Provincia de Córdoba",
    "027": "Banco Supervielle",
    "029": "Banco de la Ciudad de Buenos Aires",
    "034": "Banco Patagonia",
    "044": "Banco Hipotecario",
    "045": "Banco de San Juan",
    "060": "Banco del Tucumán",
    "065": "Banco Municipal de Rosario",
    "072": "Banco Santander Argentina",
    "083": "Banco del Chubut",
    "086": "Banco de Santa Cruz",
    "093": "Banco de la Pampa",
    "094": "Banco de Corrientes",
    "097": "Banco Provincia del Neuquén",
    "143": "Brubank",
    "147": "Banco Interfinanzas",
    "150": "HSBC Bank Argentina",
    "158": "Banco Macro",
    "165": "Banco Comafi",
    "191": "Banco Credicoop",
    "198": "Banco de Valores",
    "247": "Banco Roela",
    "254": "Banco Mariva",
    "259": "Banco Itaú Argentina",
    "266": "BNP Paribas",
    "268": "Banco Provincia de Tierra del Fuego",
    "269": "Banco de la República Oriental del Uruguay",
    "277": "Banco Saenz",
    "281": "Banco Meridian",
    "285": "Banco del Sol",
    "299": "Banco CMF",
    "300": "Banco de Inversión y Comercio Exterior",
    "301": "Banco Piano",
    "305": "Banco Julio",
    "309": "Banco Rioja",
    "310": "Banco del Sol",
    "311": "Nuevo Banco del Chaco",
    "312": "Banco Voii (Naranja X)",
    "315": "Banco de Formosa",
    "319": "Banco Columbia",
    "321": "Banco de Santiago del Estero",
    "322": "Banco Industrial",
    "330": "Nuevo Banco de Santa Fe",
    "331": "Banco Coinag",
    "332": "Banco de Servicios Financieros",
    "338": "Banco de Servicios y Transacciones",
    "341": "Wilobank",
    "386": "Nuevo Banco de Entre Ríos",
    "389": "Banco Columbia",
    "426": "Banco Bica",
    "431": "Banco Coinag",
    "432": "Banco de Comercio",
    "448": "Reba Compañía Financiera (Ualá)",
    "000": "Mercado Pago",  # CVU especial
}

# Modelo de OpenAI a usar
OPENAI_MODEL = "gpt-4o"

# Nivel mínimo de confianza para aceptar extracción automática
MIN_CONFIDENCE = 0.7
