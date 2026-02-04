"""
Validación de datos extraídos de comprobantes bancarios argentinos.
"""
import re
from typing import Optional, Tuple
from app.config import BANCOS_ARGENTINOS, CUENTAS_DESTINO
from datetime import datetime


def validar_cbu(cbu: str) -> Tuple[bool, str]:
    """
    Valida un CBU/CVU argentino.
    
    Args:
        cbu: String con el CBU/CVU
        
    Returns:
        Tuple (es_valido, mensaje)
    """
    if not cbu:
        return False, "CBU vacío"
    
    # Limpiar espacios y caracteres no numéricos
    cbu_limpio = re.sub(r'\D', '', cbu)
    
    if len(cbu_limpio) != 22:
        return False, f"CBU debe tener 22 dígitos, tiene {len(cbu_limpio)}"
    
    return True, "CBU válido"


def validar_cuil(cuil: str) -> Tuple[bool, str]:
    """
    Valida un CUIL/CUIT argentino.
    
    Args:
        cuil: String con el CUIL/CUIT
        
    Returns:
        Tuple (es_valido, mensaje)
    """
    if not cuil:
        return False, "CUIL vacío"
    
    # Limpiar espacios y guiones
    cuil_limpio = re.sub(r'[\s\-]', '', cuil)
    
    if len(cuil_limpio) != 11:
        return False, f"CUIL debe tener 11 dígitos, tiene {len(cuil_limpio)}"
    
    if not cuil_limpio.isdigit():
        return False, "CUIL debe contener solo números"
    
    # Validar prefijo (20, 23, 24, 27, 30, 33, 34)
    prefijo = int(cuil_limpio[:2])
    prefijos_validos = [20, 23, 24, 27, 30, 33, 34]
    if prefijo not in prefijos_validos:
        return False, f"Prefijo CUIL inválido: {prefijo}"
    
    return True, "CUIL válido"


def validar_monto(monto: str) -> Tuple[bool, float, str]:
    """
    Valida y convierte un monto a número.
    
    Args:
        monto: String con el monto (ej: "$1.000.000,50")
        
    Returns:
        Tuple (es_valido, monto_numerico, mensaje)
    """
    if not monto:
        return False, 0.0, "Monto vacío"
    
    # Limpiar símbolos de moneda y espacios
    monto_limpio = re.sub(r'[$\s]', '', str(monto))
    
    # Formato argentino: puntos como separador de miles, coma como decimal
    # Convertir a formato estándar
    if ',' in monto_limpio and '.' in monto_limpio:
        # Tiene ambos: quitar puntos de miles, cambiar coma por punto
        monto_limpio = monto_limpio.replace('.', '').replace(',', '.')
    elif ',' in monto_limpio:
        # Solo coma: probablemente decimal
        monto_limpio = monto_limpio.replace(',', '.')
    elif monto_limpio.count('.') > 1:
        # Múltiples puntos: son separadores de miles
        monto_limpio = monto_limpio.replace('.', '')
    
    try:
        monto_float = float(monto_limpio)
        if monto_float <= 0:
            return False, 0.0, "Monto debe ser positivo"
        return True, monto_float, "Monto válido"
    except ValueError:
        return False, 0.0, f"No se pudo convertir monto: {monto}"


def detectar_banco_por_cbu(cbu: str) -> str:
    """
    Detecta el banco a partir del CBU (primeros 3 dígitos).
    
    Args:
        cbu: String con el CBU
        
    Returns:
        Nombre del banco o "Desconocido"
    """
    if not cbu or len(cbu) < 3:
        return "Desconocido"
    
    codigo = cbu[:3]
    return BANCOS_ARGENTINOS.get(codigo, "Desconocido")


def identificar_cuenta_destino(cbu_receptor: str) -> Optional[dict]:
    """
    Identifica si el CBU del receptor corresponde a una cuenta destino configurada.
    
    Args:
        cbu_receptor: CBU del receptor
        
    Returns:
        Dict con info de la cuenta o None
    """
    if not cbu_receptor:
        return None
    
    cbu_limpio = re.sub(r'\D', '', cbu_receptor)
    return CUENTAS_DESTINO.get(cbu_limpio)


def normalizar_fecha_operacion(fecha: str) -> str:
    """Normaliza fechas que vienen en formatos comunes de comprobantes.

    Objetivo: devolver "DD/MM/YYYY HH:mm" en 24h cuando sea posible.

    Soporta, por ejemplo:
    - "21 ene 2026, 04:54 p. m." -> "21/01/2026 16:54"
    - "21/01/2026 4:54 PM" -> "21/01/2026 16:54"
    - "21/01/2026 16:54" -> se deja igual
    """
    if not fecha:
        return ""

    s = str(fecha).strip()
    s = s.replace("\u00a0", " ")  # nbsp

    # 1) DD/MM/YYYY HH:mm con o sin AM/PM
    s_norm = s.lower()
    s_norm = re.sub(r"\b(p\.?\s*m\.?)\b", "pm", s_norm)
    s_norm = re.sub(r"\b(a\.?\s*m\.?)\b", "am", s_norm)

    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})\s*(am|pm)?\b", s_norm)
    if m:
        d, mo, y, hh, mm, ap = m.groups()
        hh_i = int(hh)
        mm_i = int(mm)
        if ap == "pm" and hh_i < 12:
            hh_i += 12
        if ap == "am" and hh_i == 12:
            hh_i = 0
        try:
            dt = datetime(int(y), int(mo), int(d), hh_i, mm_i)
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return s

    # 2) Formato con mes en español: "21 ene 2026, 04:54 p. m." (muy típico)
    meses = {
        "ene": 1,
        "feb": 2,
        "mar": 3,
        "abr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "ago": 8,
        "sep": 9,
        "set": 9,
        "oct": 10,
        "nov": 11,
        "dic": 12,
    }

    # Normalizar am/pm estilo "p. m." / "a. m." / "pm" / "am" (s_norm ya está arriba)

    m = re.search(r"\b(\d{1,2})\s+([a-záéíóú]{3})\w*\s+(\d{4})\s*,?\s*(\d{1,2}):(\d{2})\s*(am|pm)?\b", s_norm)
    if m:
        d, mes_txt, y, hh, mm, ap = m.groups()
        mes_txt = mes_txt[:3]
        mo = meses.get(mes_txt)
        if mo:
            hh_i = int(hh)
            mm_i = int(mm)
            if ap == "pm" and hh_i < 12:
                hh_i += 12
            if ap == "am" and hh_i == 12:
                hh_i = 0
            try:
                dt = datetime(int(y), int(mo), int(d), hh_i, mm_i)
                return dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                return s

    # 3) Intento con formatos comunes en inglés (por si aparece)
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})\s*(am|pm)\b", s_norm)
    if m:
        d, mo, y, hh, mm, ap = m.groups()
        hh_i = int(hh)
        mm_i = int(mm)
        if ap == "pm" and hh_i < 12:
            hh_i += 12
        if ap == "am" and hh_i == 12:
            hh_i = 0
        try:
            dt = datetime(int(y), int(mo), int(d), hh_i, mm_i)
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return s

    return s


def formatear_cuil(cuil: str) -> str:
    """
    Formatea un CUIL al formato estándar XX-XXXXXXXX-X.
    
    Args:
        cuil: CUIL sin formato
        
    Returns:
        CUIL formateado
    """
    cuil_limpio = re.sub(r'\D', '', cuil)
    if len(cuil_limpio) == 11:
        return f"{cuil_limpio[:2]}-{cuil_limpio[2:10]}-{cuil_limpio[10]}"
    return cuil
