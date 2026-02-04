
import os
from dotenv import load_dotenv
from app.sheets import verificar_conexion

# Cargar variables de entorno
load_dotenv()

print("Verificando conexión con Google Sheets...")
resultado = verificar_conexion()
print(f"Resultado: {resultado}")

if resultado.get("success"):
    print("✅ Conexión exitosa!")
else:
    print("❌ Error de conexión.")
