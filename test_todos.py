#!/usr/bin/env python3
"""Probar TODOS los comprobantes (imágenes y PDFs) juntos con fecha/hora"""
import base64
import httpx
import os
from datetime import datetime

API_URL = "http://localhost:8000"

def test_file(file_path: str, index: int):
    """Prueba un archivo y devuelve los datos"""
    filename = os.path.basename(file_path)
    
    with open(file_path, 'rb') as f:
        file_data = base64.b64encode(f.read()).decode('utf-8')
    
    # Detectar tipo MIME
    if file_path.lower().endswith('.pdf'):
        mime_type = 'application/pdf'
        tipo = 'PDF'
    elif file_path.lower().endswith('.png'):
        mime_type = 'image/png'
        tipo = 'IMG'
    else:
        mime_type = 'image/jpeg'
        tipo = 'IMG'
    
    payload = {
        "file_base64": file_data,
        "sender_phone": "+5491112345678",
        "mime_type": mime_type,
        "texto_completo": filename
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
            return {
                'index': index,
                'tipo': tipo,
                'archivo': filename[:40],
                'monto': data.get('monto_numerico', 0),
                'emisor': data.get('emisor_nombre', '')[:30] if data.get('emisor_nombre') else '',
                'banco': data.get('banco_emisor', '')[:20] if data.get('banco_emisor') else '',
                'fecha': data.get('fecha_operacion', ''),
                'confianza': data.get('confianza', 0),
                'success': True
            }
        else:
            return {
                'index': index,
                'tipo': tipo,
                'archivo': filename[:40],
                'monto': 0,
                'emisor': 'ERROR',
                'banco': '',
                'fecha': '',
                'confianza': 0,
                'success': False,
                'error': result.get('error', 'Error desconocido')
            }
    except Exception as e:
        return {
            'index': index,
            'tipo': tipo,
            'archivo': filename[:40],
            'monto': 0,
            'emisor': 'ERROR',
            'banco': '',
            'fecha': '',
            'confianza': 0,
            'success': False,
            'error': str(e)
        }

def main():
    comprobantes_dir = "/Users/leguillo/Downloads/comprobantes"
    
    # Obtener TODOS los archivos (imágenes y PDFs)
    files = [f for f in os.listdir(comprobantes_dir) 
             if f.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf'))]
    
    print(f"\n{'='*120}")
    print(f"🔍 PROCESANDO {len(files)} COMPROBANTES (Imágenes + PDFs)")
    print(f"   Hora de inicio: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*120}\n")
    
    results = []
    success_count = 0
    total_monto = 0
    
    for i, filename in enumerate(sorted(files), 1):
        filepath = os.path.join(comprobantes_dir, filename)
        print(f"[{i:02d}/{len(files)}] Procesando: {filename[:50]}...", end=" ", flush=True)
        result = test_file(filepath, i)
        results.append(result)
        
        if result['success']:
            success_count += 1
            total_monto += result['monto']
            print(f"✅ ${result['monto']:,.0f}")
        else:
            print(f"❌ {result.get('error', 'Error')[:30]}")
    
    # Mostrar tabla de resultados
    print(f"\n{'='*120}")
    print(f"📊 RESULTADOS: {success_count}/{len(files)} procesados correctamente")
    print(f"{'='*120}")
    print(f"{'#':>3} {'TIPO':<4} {'MONTO':>15} {'FECHA/HORA':<20} {'EMISOR':<30} {'BANCO':<20}")
    print(f"{'-'*120}")
    
    # Ordenar por fecha para detectar duplicados
    for r in sorted(results, key=lambda x: x.get('fecha', '') or ''):
        if r['success']:
            print(f"{r['index']:>3} {r['tipo']:<4} ${r['monto']:>13,.0f} {r['fecha']:<20} {r['emisor']:<30} {r['banco']:<20}")
        else:
            print(f"{r['index']:>3} {r['tipo']:<4} {'ERROR':>14} {'':<20} {r.get('error', 'Error')[:30]:<30} {'':<20}")
    
    print(f"{'-'*120}")
    print(f"{'TOTAL':>8} ${total_monto:>13,.0f}")
    print(f"{'='*120}")

if __name__ == "__main__":
    main()
