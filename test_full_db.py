#!/usr/bin/env python3
"""
Test COMPLETO: Procesa TODOS los comprobantes y los GUARDA en Google Sheets.
Este script usa el endpoint /process-receipt/ que guarda en la base de datos.
"""
import base64
import httpx
import os
from datetime import datetime

API_URL = "http://localhost:8000"

def test_file_save(file_path: str, index: int, total: int):
    """Procesa un archivo y lo GUARDA en Google Sheets"""
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
        "sender_phone": "+5491123456789",
        "timestamp": datetime.now().isoformat(),
        "mime_type": mime_type,
        "texto_completo": filename
    }
    
    try:
        response = httpx.post(
            f"{API_URL}/process-receipt/",  # Este endpoint GUARDA en Sheets
            json=payload,
            timeout=120.0
        )
        result = response.json()
        
        if result.get('success'):
            data = result.get('data', {})
            confianza_val = data.get('confianza', 0)
            confianza_str = "OPTIMA" if confianza_val >= 0.90 else "REVEER"
            
            return {
                'index': index,
                'tipo': tipo,
                'archivo': filename[:45],
                'monto': data.get('monto_numerico', 0),
                'emisor': data.get('emisor_nombre', '')[:25] if data.get('emisor_nombre') else '-',
                'banco': data.get('banco_emisor', '')[:15] if data.get('banco_emisor') else '-',
                'fecha': data.get('fecha_operacion', ''),
                'confianza_str': confianza_str,
                'es_duplicado': result.get('es_duplicado', False),
                'success': True,
                'guardado': True
            }
        else:
            return {
                'index': index,
                'tipo': tipo,
                'archivo': filename[:45],
                'monto': 0,
                'emisor': 'ERROR',
                'banco': '',
                'fecha': '',
                'confianza_str': 'ERROR',
                'es_duplicado': False,
                'success': False,
                'guardado': False,
                'error': result.get('message', 'Error desconocido')
            }
    except Exception as e:
        return {
            'index': index,
            'tipo': tipo,
            'archivo': filename[:45],
            'monto': 0,
            'emisor': 'ERROR',
            'banco': '',
            'fecha': '',
            'confianza_str': 'ERROR',
            'es_duplicado': False,
            'success': False,
            'guardado': False,
            'error': str(e)
        }


def main():
    comprobantes_dir = "/Users/leguillo/Downloads/comprobantes"
    
    # Verificar conexión con Google Sheets primero
    print("\n" + "="*120)
    print("🔌 VERIFICANDO CONEXIÓN CON GOOGLE SHEETS...")
    try:
        health = httpx.get(f"{API_URL}/health", timeout=10.0).json()
        if health.get('sheets_connection'):
            print("✅ Conexión con Google Sheets: OK")
        else:
            print("❌ ERROR: No hay conexión con Google Sheets")
            return
    except Exception as e:
        print(f"❌ ERROR: Servidor no disponible - {e}")
        return
    
    # Obtener TODOS los archivos (imágenes y PDFs)
    files = [f for f in os.listdir(comprobantes_dir) 
             if f.lower().endswith(('.jpg', '.jpeg', '.png', '.pdf'))]
    
    print(f"\n{'='*120}")
    print(f"🚀 PROCESANDO Y GUARDANDO {len(files)} COMPROBANTES EN GOOGLE SHEETS")
    print(f"   📅 Inicio: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"   📁 Carpeta: {comprobantes_dir}")
    print(f"{'='*120}\n")
    
    results = []
    success_count = 0
    total_monto = 0
    duplicados_detectados = 0
    
    for i, filename in enumerate(sorted(files), 1):
        filepath = os.path.join(comprobantes_dir, filename)
        print(f"[{i:02d}/{len(files)}] 📄 {filename[:50]}...", end=" ", flush=True)
        result = test_file_save(filepath, i, len(files))
        results.append(result)
        
        if result['success']:
            success_count += 1
            total_monto += result['monto']
            dupl_mark = "⚠️ DUPLICADO" if result['es_duplicado'] else ""
            if result['es_duplicado']: duplicados_detectados += 1
            
            print(f"✅ ${result['monto']:,.0f} [{result['confianza_str']}] {dupl_mark}")
        else:
            print(f"❌ {result.get('error', 'Error')[:40]}")
    
    # Resumen final
    print(f"\n{'='*120}")
    print(f"📊 RESUMEN FINAL")
    print(f"{'='*120}")
    
    # Estadísticas
    pdfs = len([r for r in results if r['tipo'] == 'PDF'])
    imgs = len([r for r in results if r['tipo'] == 'IMG'])
    
    print(f"""
🎉 {success_count}/{len(files)} PROCESADOS Y GUARDADOS EN GOOGLE SHEETS ({success_count*100//len(files)}%)

📁 Archivos procesados:
   • Imágenes: {imgs}
   • PDFs: {pdfs}
   • Total: {len(files)}

⚠️ Duplicados detectados HOY: {duplicados_detectados}
💰 Total transferido: ${total_monto:,.0f} ARS
""")
    
    # Tabla de resultados ordenada por fecha
    print(f"{'#':<3} {'TIPO':<4} {'MONTO':>15} {'FECHA/HORA':<20} {'EMISOR':<25} {'BANCO':<15} {'ESTADO':<10}")
    print("-"*110)
    
    for r in sorted(results, key=lambda x: x.get('fecha', '') or ''):
        if r['success']:
            dupl = "*" if r['es_duplicado'] else " "
            print(f"{r['index']:<3} {r['tipo']:<4} ${r['monto']:>13,.0f} {dupl} {r['fecha']:<18} {r['emisor']:<25} {r['banco']:<15} {r['confianza_str']:<10}")
        else:
            print(f"{r['index']:<3} {r['tipo']:<4} {'ERROR':>14}   {'':<18} {r.get('error', '')[:25]:<25} {'':<15} {'ERROR':<10}")
    
    print("-"*110)
    print(f"{'TOTAL':>8} ${total_monto:>13,.0f}")
    print("="*110)
    
    print(f"\n✅ FINALIZADO: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"📊 Verificá tu Google Sheet para confirmar los datos guardados")
    print("="*100 + "\n")


if __name__ == "__main__":
    main()
