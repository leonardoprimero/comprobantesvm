"""
Extractor de datos de comprobantes usando GPT-4o Vision.
Envía la imagen directamente al modelo para mejor precisión.
Soporta imágenes (JPEG, PNG) y PDFs.
"""
import base64
import json
import io
import logging
import os
from typing import Optional, Tuple
from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.validator import validar_cbu, validar_cuil, validar_monto, detectar_banco_por_cbu, normalizar_fecha_operacion

logger = logging.getLogger(__name__)

# Cliente OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)


def _convertir_pdf_a_imagen(pdf_base64: str) -> Tuple[str, str]:
    """
    Convierte un PDF en base64 a una imagen JPEG en base64.
    Solo convierte la primera página.
    
    Returns:
        Tuple[str, str]: (imagen_base64, mime_type)
    """
    try:
        from pdf2image import convert_from_bytes
        from PIL import Image
        
        # Decodificar PDF
        pdf_bytes = base64.b64decode(pdf_base64)
        
        poppler_path = os.environ.get("POPPLER_PATH")

        # Convertir primera página a imagen
        if poppler_path:
            images = convert_from_bytes(
                pdf_bytes,
                first_page=1,
                last_page=1,
                dpi=200,
                poppler_path=poppler_path
            )
        else:
            images = convert_from_bytes(
                pdf_bytes,
                first_page=1,
                last_page=1,
                dpi=200
            )
        
        if not images:
            raise ValueError("No se pudo extraer ninguna página del PDF")
        
        # Convertir a JPEG en base64
        img = images[0]
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=95)
        buffer.seek(0)
        
        imagen_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        logger.info(f"PDF convertido a imagen JPEG exitosamente")
        
        return imagen_base64, "image/jpeg"
        
    except ImportError:
        logger.error("pdf2image no está instalado. Ejecutar: pip install pdf2image")
        raise ValueError("Librería pdf2image no disponible")
    except Exception as e:
        logger.error(f"Error al convertir PDF: {e}")
        raise ValueError(f"Error al convertir PDF a imagen: {e}")

# Prompt optimizado para comprobantes argentinos
EXTRACTION_PROMPT = """Sos un experto en extraer datos de comprobantes de transferencias bancarias argentinas.
Analizá la imagen del comprobante y extraé los siguientes datos en formato JSON.

REGLAS CRÍTICAS PARA IDENTIFICAR AL EMISOR (QUIEN ENVÍA):
1. El EMISOR es quien ENVÍA/TRANSFIERE el dinero, NO quien lo recibe
2. Buscar estas palabras clave para el EMISOR:
   - "De:", "Origen", "Envía", "Remitente", "Titular origen"
   - "Ordenante", "Desde cuenta", "Cuenta origen"
   - El nombre que aparece PRIMERO o ARRIBA generalmente es el emisor
   - En apps como Mercado Pago, Brubank, Ualá: el emisor es el dueño de la cuenta de la app
3. El RECEPTOR es quien RECIBE el dinero:
   - "Para:", "Destino", "Recibe", "Beneficiario", "Destinatario"
4. SI NO PODÉS IDENTIFICAR CLARAMENTE al emisor, dejá el campo vacío
5. Si hay CBU de 22 dígitos, extraerlo completo
6. El CUIL/CUIT tiene formato XX-XXXXXXXX-X (11 dígitos total)
7. El monto principal es el que dice "Importe", "Monto", "$" (ignorar comisiones/retenciones)

IDENTIFICACIÓN DE BANCOS POR DISEÑO/LOGO:
- Logo naranja con "NX" o "Naranja X" → Naranja X
- Fondo celeste/azul con logo MP → Mercado Pago
- Fondo morado/violeta con "B" → Brubank
- Fondo rosa/fucsia con "U" → Ualá
- "Personal Pay" o logo de Personal → Personal Pay
- "Cuenta DNI" → Cuenta DNI (Banco Provincia)
- "Macro" o logo verde → Banco Macro
- Rojo con llama → Banco Santander
- Naranja con "G" → Banco Galicia
- "BBVA" azul → BBVA Argentina
- "Supervielle" → Banco Supervielle

Respondé ÚNICAMENTE con un JSON válido, sin explicaciones ni markdown:

{
    "emisor_nombre": "Nombre y apellido completo del que ENVÍA el dinero",
    "emisor_cuil": "XX-XXXXXXXX-X o vacío si no está visible",
    "emisor_cbu": "22 dígitos o vacío si no está visible",
    "banco_emisor": "Nombre del banco/app desde donde se envía",
    "receptor_nombre": "Nombre y apellido del que RECIBE el dinero",
    "receptor_cuil": "XX-XXXXXXXX-X o vacío",
    "receptor_cbu": "22 dígitos o vacío",
    "banco_receptor": "Nombre del banco/app que recibe",
    "monto": "Solo número sin símbolos, ej: 650000",
    "fecha_operacion": "DD/MM/YYYY HH:mm",
    "referencia": "Código/número de operación o vacío",
    "concepto": "Concepto/motivo de la transferencia o vacío",
    "confianza": 0.95
}

NIVEL DE CONFIANZA:
- 0.95-1.0: Todos los datos son claros, legibles y seguros
- 0.7-0.94: Algunos datos incompletos pero el monto es claro
- 0.5-0.69: Datos dudosos, requiere revisión manual
- <0.5: Imagen ilegible o no es un comprobante de transferencia

RECUERDA: Es CRÍTICO identificar correctamente al EMISOR (quien envía). Si no estás seguro, dejalo vacío."""


def extraer_datos_comprobante(
    imagen_base64: str,
    mime_type: str = "image/jpeg"
) -> dict:
    """
    Extrae datos de un comprobante usando GPT-4o Vision.
    Soporta imágenes (JPEG, PNG) y PDFs.
    
    Args:
        imagen_base64: Imagen o PDF codificado en base64
        mime_type: Tipo MIME del archivo
        
    Returns:
        Dict con los datos extraídos
    """
    try:
        # Si es PDF, convertir a imagen primero
        if mime_type == "application/pdf" or mime_type.endswith("pdf"):
            logger.info("Detectado PDF, convirtiendo a imagen...")
            imagen_base64, mime_type = _convertir_pdf_a_imagen(imagen_base64)
        
        # Preparar el mensaje con la imagen
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{imagen_base64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.1  # Baja temperatura para respuestas más consistentes
        )
        
        # Extraer el contenido JSON de la respuesta
        content = response.choices[0].message.content
        
        # Intentar parsear el JSON
        datos = _parsear_respuesta_json(content)
        
        # Validar y enriquecer datos
        datos = _validar_y_enriquecer(datos)
        
        return {
            "success": True,
            "data": datos,
            "raw_response": content
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


def _parsear_respuesta_json(content: str) -> dict:
    """
    Parsea la respuesta del modelo intentando extraer JSON válido.
    """
    # Intentar parsear directamente
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Buscar JSON dentro del texto
    import re
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Retornar estructura vacía si no se puede parsear
    return {
        "emisor_nombre": "",
        "emisor_cuil": "",
        "emisor_cbu": "",
        "banco_emisor": "",
        "receptor_nombre": "",
        "receptor_cuil": "",
        "receptor_cbu": "",
        "banco_receptor": "",
        "monto": "",
        "fecha_operacion": "",
        "referencia": "",
        "concepto": "",
        "confianza": 0.0
    }


def _validar_y_enriquecer(datos: dict) -> dict:
    """
    Valida los datos extraídos y enriquece con información adicional.
    """
    # Validar y ajustar monto
    if datos.get("monto"):
        es_valido, monto_num, _ = validar_monto(datos["monto"])
        if es_valido:
            datos["monto_numerico"] = monto_num
        else:
            datos["monto_numerico"] = 0.0
    else:
        datos["monto_numerico"] = 0.0
    
    # Normalizar fecha operación (maneja "p. m." -> 24h, meses en español, etc.)
    if datos.get("fecha_operacion"):
        datos["fecha_operacion"] = normalizar_fecha_operacion(datos.get("fecha_operacion"))

    # Validar CBU emisor
    if datos.get("emisor_cbu"):
        es_valido, msg = validar_cbu(datos["emisor_cbu"])
        datos["emisor_cbu_valido"] = es_valido
        if es_valido and not datos.get("banco_emisor"):
            datos["banco_emisor"] = detectar_banco_por_cbu(datos["emisor_cbu"])
    else:
        datos["emisor_cbu_valido"] = False
    
    # Validar CBU receptor
    if datos.get("receptor_cbu"):
        es_valido, msg = validar_cbu(datos["receptor_cbu"])
        datos["receptor_cbu_valido"] = es_valido
        if es_valido and not datos.get("banco_receptor"):
            datos["banco_receptor"] = detectar_banco_por_cbu(datos["receptor_cbu"])
    else:
        datos["receptor_cbu_valido"] = False
    
    # Validar CUIL emisor
    if datos.get("emisor_cuil"):
        es_valido, msg = validar_cuil(datos["emisor_cuil"])
        datos["emisor_cuil_valido"] = es_valido
    else:
        datos["emisor_cuil_valido"] = False
    
    # Asegurar que confianza sea float
    try:
        datos["confianza"] = float(datos.get("confianza", 0))
    except (ValueError, TypeError):
        datos["confianza"] = 0.0
    
    return datos
