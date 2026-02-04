#!/usr/bin/env python3
"""
Script de configuración interactiva para el cliente.
Genera el archivo config.json basado en las respuestas del usuario.
"""
import os
import json
import sys
from app.paths import get_config_path

def clear_screen():
    os.system('cls' if os.path.name == 'nt' else 'clear')

def input_default(prompt, default):
    response = input(f"{prompt} [{default}]: ").strip()
    return response if response else default

def input_yes_no(prompt, default_yes=True):
    default_str = "S/n" if default_yes else "s/N"
    response = input(f"{prompt} ({default_str}): ").strip().lower()
    if not response:
        return default_yes
    return response.startswith('s')

def save_config(config):
    config_path = get_config_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print(f"\n✅ Configuración guardada en {config_path}")

def main():
    clear_screen()
    print("=" * 60)
    print(" 🛠️  CONFIGURACIÓN DEL SISTEMA DE COMPROBANTES")
    print("=" * 60)
    print("\nEste asistente le ayudará a configurar las opciones del sistema.\n")

    # Cargar config actual si existe
    config = {}
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            pass
    
    # Fuentes de datos
    print("\n--- FUENTES DE DATOS ---")
    whatsapp_enabled = input_yes_no("¿Activar recepción por WhatsApp?", 
                                  config.get('fuentes', {}).get('whatsapp_enabled', True))
    
    carpeta_enabled = input_yes_no("¿Activar lectura desde carpeta local?", 
                                 config.get('fuentes', {}).get('carpeta_enabled', False))
    
    carpeta_ruta = ""
    if carpeta_enabled:
        default_path = config.get('fuentes', {}).get('carpeta_ruta', 'C:\\Comprobantes')
        carpeta_ruta = input_default("Ruta de la carpeta a monitorear", default_path)

    # Almacenamiento
    print("\n--- ALMACENAMIENTO ---")
    excel_enabled = input_yes_no("¿Guardar en Excel local?", 
                               config.get('storage', {}).get('excel_enabled', True))
    
    excel_path = "transferencias.xlsx"
    if excel_enabled:
        excel_path = input_default("Nombre/Ruta del archivo Excel", 
                                 config.get('storage', {}).get('excel_path', 'transferencias.xlsx'))

    sheets_enabled = input_yes_no("¿Guardar en Google Sheets?", 
                                config.get('storage', {}).get('sheets_enabled', False))
    
    sheets_id = ""
    sheets_name = "Hoja 1"
    google_creds = ""
    
    if sheets_enabled:
        print("\n⚠️  Para Google Sheets necesita credenciales de servicio.")
        sheets_id = input_default("ID de la Hoja de Cálculo (Spreadsheet ID)", 
                                config.get('storage', {}).get('sheets_id', ''))
        sheets_name = input_default("Nombre de la pestaña", 
                                  config.get('storage', {}).get('sheets_name', 'Hoja 1'))
        google_creds = input_default("Ruta al archivo de credenciales JSON", 
                                   config.get('google_credentials_path', 'credentials.json'))

    # Billing (Opcional, visible para cliente si quiere ocultar costos)
    print("\n--- VISUALIZACIÓN ---")
    mostrar_costos = input_yes_no("¿Mostrar costos estimados en consola?", 
                                config.get('billing', {}).get('mostrar_costos', True))

    # Credenciales
    print("\n--- CREDENCIALES ---")
    openai_api_key = input_default("OpenAI API Key", config.get('openai_api_key', ''))

    # Construir config final
    final_config = {
        "fuentes": {
            "whatsapp_enabled": whatsapp_enabled,
            "carpeta_enabled": carpeta_enabled,
            "carpeta_ruta": carpeta_ruta
        },
        "storage": {
            "excel_enabled": excel_enabled,
            "excel_path": excel_path,
            "sheets_enabled": sheets_enabled,
            "sheets_id": sheets_id,
            "sheets_name": sheets_name
        },
        "billing": {
            "markup": config.get('billing', {}).get('markup', 2.0), # Mantener valor oculto
            "mostrar_costos": mostrar_costos
        },
        "google_credentials_path": google_creds,
        "openai_api_key": openai_api_key
    }

    save_config(final_config)
    
    print("\n" + "=" * 60)
    print("🚀 INSTALACIÓN COMPLETADA")
    print("=" * 60)
    print("\nPara iniciar el sistema:")
    print("1. Ejecute: python run.py")
    if whatsapp_enabled:
        print("2. En otra ventana, inicie el bot: node bot/index.js")
    print("\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Configuración cancelada.")
