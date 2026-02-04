#!/usr/bin/env python3
import base64
import httpx
import os
import json
from datetime import datetime

API_URL = "http://localhost:8000"
FILENAME = "WhatsApp Image 2026-01-22 at 16.25.01.jpeg"
FILEPATH = f"/Users/leguillo/Downloads/comprobantes/{FILENAME}"

def debug_single():
    print(f"🔍 ANALIZANDO: {FILENAME}")
    
    if not os.path.exists(FILEPATH):
        print("❌ ARCHIVO NO ENCONTRADO")
        return

    with open(FILEPATH, 'rb') as f:
        file_data = base64.b64encode(f.read()).decode('utf-8')

    payload = {
        "file_base64": file_data,
        "sender_phone": "+5491199999999", 
        "timestamp": datetime.now().isoformat(),
        "mime_type": "image/jpeg",
        "texto_completo": "DEBUG_VERSION"
    }

    # 1. Extracción PURA (sin guardar)
    print("\n[1] Probando /extract-only/...")
    try:
        resp = httpx.post(f"{API_URL}/extract-only/", json=payload, timeout=60.0)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Error extraction: {e}")

    # 2. Procesamiento COMPLETO (guardar)
    print("\n[2] Probando /process-receipt/ (Guardado)...")
    try:
        resp = httpx.post(f"{API_URL}/process-receipt/", json=payload, timeout=60.0)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Error processing: {e}")

if __name__ == "__main__":
    debug_single()
