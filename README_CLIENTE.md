# Sistema de Procesamiento de Comprobantes Automatizado

Este sistema permite recibir comprobantes de transferencia (imágenes o PDF) por WhatsApp o desde una carpeta local, extraer automáticamente los datos importantes (monto, fecha, emisor, cuenta) y guardarlos en un archivo Excel o Google Sheets.

## Requisitos

- Windows 10/11
- Conexión a Internet

## Instalación

1.  **Ejecutar el instalador**: Abra el archivo `SistemaComprobantes_Setup.exe`.
2.  **Seguir el asistente**: Use “Siguiente” hasta finalizar.
3.  **Abrir el programa**: Desde el acceso directo “Sistema de Comprobantes”.

## Configuración y Uso (Modo Fácil)

El sistema ahora cuenta con una interfaz gráfica moderna para facilitar todo.

### 1. Abrir el Launcher

Abra “Sistema de Comprobantes”. Se abrirá una ventana con el panel de control.

### 2. Pestaña "Configuración"

- Vaya a la pestaña "Configuración".
- Active/Desactive **WhatsApp** o **Carpeta Local**.
- Elija si quiere guardar en **Excel** o **Google Sheets**.
- Haga clic en **Guardar Configuración**.

### 3. Pestaña "Dashboard"

- Haga clic en el botón verde **INICIAR SISTEMA**.
- El estado cambiará a "EJECUTANDO" y verá los logs en tiempo real.
- Verá el **Costo Estimado** actualizado en pantalla.
- Puede hacer clic en **"Abrir Excel"** para ver sus comprobantes procesados al instante.

### 4. Conectar WhatsApp

Si activó WhatsApp, el sistema mostrará el QR dentro del programa. Escanéelo la primera vez y listo.

### 5. Control de Licencias

El sistema verifica periódicamente su licencia. Si su licencia expira o es revocada por falta de pago, el sistema se detendrá automáticamente y mostrará un mensaje de bloqueo.
Su ID de cliente: (ver en `config.json`)

## Opción Manual (Terminal)

Si prefiere usar la terminal clásica:

- Configurar: `python setup.py`
- Ejecutar: `python run.py`
- Bot WhatsApp: `node bot/index.js` (en otra terminal)

## Funcionamiento

1.  **Envío**: Envíe un comprobante por WhatsApp o pegue el archivo en la carpeta monitoreada.
2.  **Procesamiento**: El sistema detectará el archivo, extraerá los datos usando inteligencia artificial.
3.  **Guardado**:
    - Si es **Excel**: Se agregará una fila al archivo `transferencias.xlsx`.
    - Si es **Google Sheets**: Se agregará una fila a la hoja configurada.
4.  **Duplicados**: Si envía el mismo comprobante dos veces, el sistema lo detectará y lo marcará en amarillo en el Excel/Sheet (o lo ignorará si es desde carpeta).

## Costos

El sistema utiliza inteligencia artificial avanzada para leer los comprobantes. Cada imagen procesada tiene un costo asociado por el uso del servicio de IA.
Puede ver el costo estimado acumulado en la pantalla del programa `run.py`.

## Solución de Problemas

- **"No se puede conectar a la API Python"**: Asegúrese de que `python run.py` esté ejecutándose antes de iniciar el bot de WhatsApp.
- **El QR no se lee bien**: Htsga click en el enlace que aparece debajo del QR para verlo más grande en el navegador.
- **Errores de dependencias**: Asegúrese de haber instalado todo con `pip install -r requirements.txt`.
