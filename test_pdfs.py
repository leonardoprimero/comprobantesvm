#!/usr/bin/env python3
"""Probar todos los PDFs"""
import base64
import httpx
import os

API_URL = "http://localhost:8000"

def test_file(file_path: str):
    print(f"\n{'='*60}")
    print(f"📄 {os.path.basename(file_path)}")
    print('='*60)
    
    with open(file_path, 'rb') as f:
        file_data = base64.b64encode(f.read()).decode('utf-8')
    
    mime_type = "application/pdf" if file_path.endswith(".pdf") else "image/jpeg"
    
    payload = {
        "file_base64": file_data,
        "sender_phone": "+5491112345678",
        "mime_type": mime_type,
        "texto_completo": os.path.basename(file_path)
    }
    
    try:
        response = httpx.post(
            f"{API_URL}/extract-only/",
            json=payload,
            timeout=120.0
        )
        result = response.json()
        
        if result.get('success'):
            data = result.get('data', {})
            print(f"✅ ÉXITO - Confianza: {data.get('confianza', 0):.0%}")
            print(f"   💰 Monto: ${data.get('monto_numerico', 0):,.2f}")
            print(f"   👤 Emisor: {data.get('emisor_nombre', 'N/A')}")
            print(f"   🏦 Banco: {data.get('banco_emisor', 'N/A')}")
            print(f"   📅 Fecha: {data.get('fecha_operacion', 'N/A')}")
            return True
        else:
            print(f"❌ ERROR: {result.get('error', 'Error desconocido')}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

# Probar los 3 PDFs
pdfs = [
    "/Users/leguillo/Downloads/comprobantes/Comprobante_1768312279027 copia.pdf",
    "/Users/leguillo/Downloads/comprobantes/Comprobante de transferencia copia.pdf",
    "/Users/leguillo/Downloads/comprobantes/11012026_nueva_transferencia copia.pdf"
]

success = 0
for pdf in pdfs:
    if test_file(pdf):
        success += 1

print(f"\n{'='*60}")
print(f"📊 RESUMEN PDFs: {success}/{len(pdfs)} procesados correctamente")
print('='*60)
