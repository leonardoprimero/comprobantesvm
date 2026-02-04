#!/usr/bin/env python3
"""Probar el PDF problemático de Naranja X"""
import base64
import httpx
import os

API_URL = "http://localhost:8000"

def test_pdf(file_path: str):
    print(f"\n📄 Probando: {os.path.basename(file_path)}")
    
    with open(file_path, 'rb') as f:
        file_data = base64.b64encode(f.read()).decode('utf-8')
    
    payload = {
        "file_base64": file_data,
        "sender_phone": "+5491112345678",
        "mime_type": "application/pdf",
        "texto_completo": os.path.basename(file_path)
    }
    
    response = httpx.post(
        f"{API_URL}/extract-only/",
        json=payload,
        timeout=120.0
    )
    result = response.json()
    
    print(f"Resultado: {result}")
    
    if result.get('success'):
        data = result.get('data', {})
        print(f"\n✅ ÉXITO")
        print(f"   Monto: ${data.get('monto_numerico', 0):,.2f}")
        print(f"   Emisor: {data.get('emisor_nombre', 'N/A')}")
        print(f"   Banco: {data.get('banco_emisor', 'N/A')}")
        print(f"   CUIL: {data.get('emisor_cuil', 'N/A')}")
        print(f"   CBU: {data.get('emisor_cbu', 'N/A')}")
        print(f"   Fecha: {data.get('fecha_operacion', 'N/A')}")

# Probar el PDF de Comprobante_1768312279027
test_pdf("/Users/leguillo/Downloads/comprobantes/Comprobante_1768312279027 copia.pdf")
