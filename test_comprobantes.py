#!/usr/bin/env python3
"""Script para probar la API con comprobantes locales"""
import base64
import httpx
import sys
import os
import json

API_URL = "http://localhost:8000"

def test_receipt(file_path: str):
    """Prueba un comprobante"""
    print(f"\n{'='*60}")
    print(f"📄 Procesando: {os.path.basename(file_path)}")
    print('='*60)
    
    # Leer y convertir a base64
    with open(file_path, 'rb') as f:
        file_data = base64.b64encode(f.read()).decode('utf-8')
    
    # Detectar tipo MIME
    if file_path.lower().endswith('.pdf'):
        mime_type = 'application/pdf'
    elif file_path.lower().endswith('.png'):
        mime_type = 'image/png'
    else:
        mime_type = 'image/jpeg'
    
    # Enviar a la API
    payload = {
        "file_base64": file_data,
        "sender_phone": "+5491112345678",
        "mime_type": mime_type,
        "texto_completo": os.path.basename(file_path)
    }
    
    try:
        response = httpx.post(
            f"{API_URL}/extract-only/",  # Usamos extract-only para no guardar en sheets
            json=payload,
            timeout=60.0
        )
        result = response.json()
        
        if result.get('success'):
            data = result.get('data', {})
            print(f"✅ ÉXITO - Confianza: {data.get('confianza', 0):.0%}")
            print(f"   💰 Monto: ${data.get('monto_numerico', 0):,.2f}")
            print(f"   👤 Emisor: {data.get('emisor_nombre', 'N/A')}")
            print(f"   🏦 Banco: {data.get('banco_emisor', 'N/A')}")
            print(f"   📋 CBU: {data.get('emisor_cbu', 'N/A')}")
            print(f"   🆔 CUIL: {data.get('emisor_cuil', 'N/A')}")
            print(f"   📅 Fecha: {data.get('fecha_operacion', 'N/A')}")
            return True
        else:
            print(f"❌ ERROR: {result.get('error', 'Error desconocido')}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR DE CONEXIÓN: {e}")
        return False

def main():
    comprobantes_dir = "/Users/leguillo/Downloads/comprobantes"
    
    # Obtener archivos
    files = [f for f in os.listdir(comprobantes_dir) 
             if f.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf'))]
    
    print(f"\n🔍 Encontrados {len(files)} comprobantes")
    
    # Probar TODOS los comprobantes
    test_files = files
    
    success_count = 0
    for filename in test_files:
        filepath = os.path.join(comprobantes_dir, filename)
        if test_receipt(filepath):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN: {success_count}/{len(test_files)} procesados correctamente")
    print('='*60)

if __name__ == "__main__":
    main()
