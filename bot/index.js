/**
 * Bot de WhatsApp para recibir comprobantes de transferencias.
 * Solo recibe imágenes/PDFs y los envía a la API Python para procesar.
 * NO responde al usuario.
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcodeTerminal = require('qrcode-terminal');
const qrcode = require('qrcode');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const logger = require('./logger');

// Configuración
const API_URL = process.env.API_URL || 'http://localhost:8000';
const API_KEY = process.env.API_KEY || '';
const API_TIMEOUT = 120000; // 2 minutos (GPT-4o Vision puede tardar)
const QR_PATH = process.env.QR_PATH || '';
const CHROMIUM_PATH = process.env.CHROMIUM_PATH || '';
const WWEBJS_AUTH_DIR = process.env.WWEBJS_AUTH_DIR || '';
const MAX_QUEUE_LENGTH = Math.max(1, Number(process.env.MAX_QUEUE_LENGTH || 200) || 200);
const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB
const MEDIA_DOWNLOAD_TIMEOUT = 30000; // 30 seconds

// Security: warn if API_KEY travels over plain HTTP to non-localhost
if (
  API_KEY &&
  API_URL.startsWith('http://') &&
  !API_URL.includes('localhost') &&
  !API_URL.includes('127.0.0.1')
) {
  logger.warn(
    'ADVERTENCIA DE SEGURIDAD: API_KEY configurada pero API_URL usa HTTP sin cifrado. En produccion, use HTTPS.'
  );
}

// Debug: mostrar variables de entorno importantes
logger.info('');
logger.info('='.repeat(50));
logger.info('INICIANDO BOT DE COMPROBANTES');
logger.info('='.repeat(50));
logger.info('Variables de entorno:');
logger.info(`   API_URL: ${API_URL}`);
logger.info(`   API_KEY: ${API_KEY ? '***configurada***' : '(NO DEFINIDO - auth deshabilitada)'}`);
logger.info(`   QR_PATH: ${QR_PATH || '(NO DEFINIDO)'}`);
logger.info(`   CHROMIUM_PATH: ${CHROMIUM_PATH || '(NO DEFINIDO)'}`);
logger.info(`   WWEBJS_AUTH_DIR: ${WWEBJS_AUTH_DIR || '(NO DEFINIDO)'}`);
logger.info(`   MAX_QUEUE_LENGTH: ${MAX_QUEUE_LENGTH}`);
logger.info('='.repeat(50));
logger.info('');

// Reconnection state
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;

// Cola de procesamiento
const colaComprobantes = [];
let procesando = false;

/**
 * Procesa la cola de comprobantes uno por uno.
 */
async function procesarCola() {
  if (procesando) return;
  procesando = true;

  try {
    while (colaComprobantes.length > 0) {
      const item = colaComprobantes.shift();
      const nombreArchivo = item.filename || `comprobante_${Date.now()}`;

      logger.info(`Procesando: ${nombreArchivo}`);

      const MAX_RETRIES = 5;
      let retries = 0;
      let success = false;

      while (retries <= MAX_RETRIES && !success) {
        try {
          const requestHeaders = { 'Content-Type': 'application/json' };
          if (API_KEY) {
            requestHeaders['X-API-Key'] = API_KEY;
          }

          const response = await axios.post(
            `${API_URL}/api/v1/process-receipt`,
            {
              file_base64: item.data,
              sender_phone: item.from,
              mime_type: item.mimetype,
              timestamp: new Date().toISOString(),
              texto_completo: item.body,
            },
            {
              timeout: API_TIMEOUT,
              headers: requestHeaders,
            }
          );

          success = true;
          if (response.data.success) {
            const monto = response.data.data?.monto_numerico || 'N/A';
            const emisor = response.data.data?.emisor_nombre || 'Desconocido';
            // PII Redaction: Log only last 4 chars of sender or mask it
            logger.info(`Procesado: $${monto} de ${emisor.substring(0, 3)}...`);
          } else {
            logger.info(`Procesado con advertencia: ${response.data.message}`);
          }
        } catch (error) {
          if (error.code === 'ECONNREFUSED') {
            retries++;
            if (retries <= MAX_RETRIES) {
              const waitSec = Math.min(5 * Math.pow(2, retries - 1), 60);
              logger.warn(`API no disponible, reintentando en ${waitSec}s (${retries}/${MAX_RETRIES})...`);
              await new Promise((r) => setTimeout(r, waitSec * 1000));
            } else {
              logger.error('Error: No se puede conectar a la API Python después de varios intentos. ¿Está corriendo?');
            }
          } else if (error.code === 'ETIMEDOUT') {
            logger.error('Error: Timeout al procesar. El servidor tardó demasiado.');
            break;
          } else {
            logger.error(`Error al procesar: ${error.message}`);
            break;
          }
        }
      }

      // Esperar 2 segundos entre cada procesamiento
      await new Promise((r) => setTimeout(r, 2000));
    }
  } finally {
    procesando = false;
  }
}

// Crear cliente de WhatsApp
const authOptions = { clientId: 'bot-comprobantes' };
if (WWEBJS_AUTH_DIR) {
  authOptions.dataPath = WWEBJS_AUTH_DIR;
}

const puppeteerConfig = {
  headless: true,
  args: [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--disable-accelerated-2d-canvas',
    '--no-first-run',
    '--disable-extensions',
  ],
};
// Use the bundled Chromium if CHROMIUM_PATH is provided
if (CHROMIUM_PATH && fs.existsSync(CHROMIUM_PATH)) {
  puppeteerConfig.executablePath = CHROMIUM_PATH;
  logger.info(`Usando Chromium personalizado: ${CHROMIUM_PATH}`);
}

const client = new Client({
  authStrategy: new LocalAuth(authOptions),
  puppeteer: puppeteerConfig,
});

// Evento: QR para escanear
client.on('qr', async (qr) => {
  logger.info('\n'.repeat(2));
  logger.info('='.repeat(50));
  logger.info('ESCANEAR CODIGO QR CON WHATSAPP');
  logger.info('='.repeat(50));
  qrcodeTerminal.generate(qr, { small: true });

  // Marcador para que el Launcher genere y muestre el QR en la interfaz.
  // Va directo a stdout (no al archivo de log) para no persistir el QR.
  console.log(`[QR_DATA]${qr}[/QR_DATA]`);

  logger.info('\nSi el QR no se ve bien en la terminal, revisa el archivo QR guardado localmente.');
  logger.info('='.repeat(50));

  if (QR_PATH) {
    try {
      const qrDir = path.dirname(QR_PATH);
      if (!fs.existsSync(qrDir)) {
        fs.mkdirSync(qrDir, { recursive: true });
      }
      await qrcode.toFile(QR_PATH, qr, { width: 400, margin: 1 });
      logger.info(`QR guardado en: ${QR_PATH}`);
    } catch (error) {
      logger.error(`Error al guardar QR: ${error.message}`);
    }
  } else {
    logger.info('QR_PATH no definido, no se guardara imagen');
  }
});

// Evento: Autenticado (después de escanear QR)
client.on('authenticated', () => {
  logger.info('QR escaneado - Autenticacion exitosa');
});

// Evento: Cambio de estado
client.on('change_state', (state) => {
  logger.info(`Estado cambio a: ${state}`);
});

// Evento: Pantalla de carga
client.on('loading_screen', (percent, message) => {
  logger.info(`Cargando WhatsApp Web: ${percent}% - ${message}`);
  if (percent === 100) {
    logger.info('Carga completa, esperando evento ready...');
  }
});

// Evento: Listo
let readyFired = false;
client.on('ready', () => {
  readyFired = true;
  reconnectAttempts = 0;
  logger.info('\n' + '='.repeat(50));
  logger.info('BOT CONECTADO Y LISTO');
  logger.info('[CONNECTED]'); // Marcador para Python
  logger.info('='.repeat(50));
  logger.info('Esperando comprobantes por WhatsApp...');
  logger.info(`Numero conectado: ${client.info?.wid?.user || 'No disponible'}`);
  logger.info('='.repeat(50) + '\n');
});

// Evento: Cualquier mensaje (incluyendo propios) - para debug
client.on('message_create', async (msg) => {
  const maskedFrom = msg.from.replace(/\d(?=\d{4})/g, '*'); // Show only last 4 digits
  logger.info(`[DEBUG] Mensaje detectado de ${maskedFrom} - hasMedia: ${msg.hasMedia}`);

  // Si es mensaje enviado por nosotros, ignorar
  if (msg.fromMe) return;

  // Ignorar mensajes de estado/broadcast
  if (msg.from === 'status@broadcast') return;

  // Ignorar mensajes de grupos
  if (msg.from.endsWith('@g.us')) return;

  // Si es texto (sin media), ignorar o avisar
  if (!msg.hasMedia) {
    const texto = (msg.body || '').trim();
    if (texto.length > 0) {
      logger.info(`Texto recibido de ${maskedFrom}: "..." (contenido redactado)`);
      try {
        await msg.reply('Este número solo recibe comprobantes (imagen JPG/PNG o PDF).');
      } catch (error) {
        logger.error(`Error al responder: ${error.message}`);
      }
    }
    return;
  }

  // Solo procesar si tiene media
  try {
    logger.info(`Descargando media de ${maskedFrom}...`);

    // Fix 9: Timeout de 30 segundos para descarga de media
    const media = await Promise.race([
      msg.downloadMedia(),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Timeout: descarga de media excedio 30 segundos')), MEDIA_DOWNLOAD_TIMEOUT)
      ),
    ]);

    if (!media) {
      logger.info('No se pudo descargar el archivo');
      return;
    }

    // Fix 3: Verificar tamano del archivo antes de continuar
    const fileSizeBytes = media.data ? Buffer.byteLength(media.data, 'base64') : 0;
    if (fileSizeBytes > MAX_FILE_SIZE) {
      logger.warn(`Archivo demasiado grande (${(fileSizeBytes / 1024 / 1024).toFixed(1)} MB) de ${maskedFrom}`);
      try {
        await msg.reply('⚠️ El archivo es demasiado grande (max 20 MB). Envía un archivo más pequeño.');
      } catch (replyErr) {
        logger.error(`Error al enviar aviso de archivo grande: ${replyErr.message}`);
      }
      return;
    }

    // Tipos válidos
    const tiposValidos = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];

    if (tiposValidos.includes(media.mimetype)) {
      logger.info(
        `Recibido: ${media.filename || 'archivo'} (${media.mimetype}) de ${maskedFrom}`
      );

      // Agregar a la cola
      if (colaComprobantes.length >= MAX_QUEUE_LENGTH) {
        logger.warn(
          `Cola llena (${MAX_QUEUE_LENGTH}). Se rechaza: ${media.filename || 'archivo'}`
        );
        try {
          await msg.reply(
            '⚠️ Hay demasiados comprobantes en cola. Intenta nuevamente en unos minutos.'
          );
        } catch (replyErr) {
          logger.error(`Error al enviar aviso de cola llena: ${replyErr.message}`);
        }
        return;
      }

      // Fix 2: Solo almacenar los campos necesarios para evitar retener objetos grandes en memoria
      colaComprobantes.push({
        data: media.data,
        mimetype: media.mimetype,
        filename: media.filename || '',
        from: msg.from,
        body: (msg.body || '').substring(0, 500),
      });
      procesarCola();
    } else {
      logger.info(`Tipo no soportado: ${media.mimetype}`);
    }
  } catch (error) {
    logger.error(`Error al procesar mensaje: ${error.message}`);
    logger.error(`Stack: ${error.stack}`);
  }
});

// Evento: Desconectado (con exponential backoff)
client.on('disconnected', (reason) => {
  logger.info(`Desconectado: ${reason}`);

  reconnectAttempts++;
  if (reconnectAttempts > MAX_RECONNECT_ATTEMPTS) {
    logger.error(
      `Maximo de reintentos alcanzado (${MAX_RECONNECT_ATTEMPTS}). Deteniendo bot.`
    );
    process.exit(1);
  }

  const delay = Math.min(5000 * Math.pow(2, reconnectAttempts - 1), 60000);
  logger.info(
    `Intentando reconectar en ${delay / 1000}s (intento ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`
  );
  setTimeout(async () => {
    try {
      await client.destroy();
      logger.info('Cliente destruido antes de reconectar.');
    } catch (err) {
      logger.error(`Error al destruir cliente antes de reconectar: ${err.message}`);
    }
    client.initialize();
  }, delay);
});

// Evento: Error de autenticación
client.on('auth_failure', (msg) => {
  logger.error(`Error de autenticacion: ${msg}`);
  // Attempt to delete the auth directory so a fresh QR is generated on restart
  const authDir = WWEBJS_AUTH_DIR || path.join(process.cwd(), '.wwebjs_auth');
  try {
    if (fs.existsSync(authDir)) {
      fs.rmSync(authDir, { recursive: true, force: true });
      logger.info(`Directorio de autenticacion eliminado: ${authDir}`);
    }
  } catch (err) {
    logger.error(`No se pudo eliminar directorio de auth: ${err.message}`);
  }
  process.exit(1);
});

// Windows: matar Chromium huérfanos de sesiones anteriores que retienen el perfil
// (si quedan vivos, el nuevo arranque no puede reutilizar la sesión y pide QR de nuevo)
if (process.platform === 'win32') {
  try {
    const { execSync } = require('child_process');
    execSync(
      'powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'chrome.exe\'\\" | Where-Object { $_.CommandLine -like \'*wwebjs_auth*\' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"',
      { stdio: 'ignore', timeout: 30000 }
    );
    logger.info('Limpieza de Chromium huérfanos de sesiones anteriores completada.');
  } catch (err) {
    logger.warn('No se pudieron limpiar procesos Chromium previos: ' + err.message);
  }
}

// Limpiar lockfile huérfano antes de iniciar (Windows: Chrome zombie deja locks)
const sessionDir = path.join(
  WWEBJS_AUTH_DIR || path.join(process.cwd(), '.wwebjs_auth'),
  'session-bot-comprobantes'
);
const lockfilePath = path.join(sessionDir, 'lockfile');
if (fs.existsSync(lockfilePath)) {
  try {
    fs.unlinkSync(lockfilePath);
    logger.info('Lockfile huérfano eliminado: ' + lockfilePath);
  } catch (err) {
    logger.warn('No se pudo eliminar lockfile: ' + err.message);
  }
}
// También eliminar SingletonLock si existe
const singletonLock = path.join(sessionDir, 'SingletonLock');
if (fs.existsSync(singletonLock)) {
  try {
    fs.unlinkSync(singletonLock);
    logger.info('SingletonLock huérfano eliminado');
  } catch (err) {
    logger.warn('No se pudo eliminar SingletonLock: ' + err.message);
  }
}

// Iniciar cliente
client.initialize().catch((err) => {
  logger.error(`FATAL ERROR al iniciar cliente: ${err}`);
  logger.error(`Stack: ${err.stack}`);
});

// Timeout handler: if ready doesn't fire in 120 seconds, log a warning
setTimeout(() => {
  if (!readyFired) {
    logger.info('ADVERTENCIA: El evento "ready" no se disparo en 120 segundos.');
    logger.info('   Esto puede indicar que WhatsApp Web esta cargando lentamente.');
    logger.info('   Si el problema persiste, reinicia la aplicacion.');
  }
}, 120000);

// --- Graceful shutdown ---
async function gracefulShutdown(signal) {
  logger.info(`Recibida señal ${signal}. Cerrando bot...`);
  try {
    await client.destroy();
    logger.info('Cliente destruido correctamente.');
  } catch (err) {
    logger.error(`Error al destruir cliente durante shutdown: ${err.message}`);
  }
  process.exit(0);
}

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));
// Windows: el Launcher envía CTRL_BREAK para pedir cierre ordenado
process.on('SIGBREAK', () => gracefulShutdown('SIGBREAK'));
// Cierre ordenado cooperativo: el Launcher crea este archivo para pedir shutdown
// (más confiable que señales en Windows; preserva la sesión de WhatsApp)
const shutdownFlag = path.join(
  process.env.APP_DATA_DIR || process.cwd(),
  'bot_shutdown.flag'
);
setInterval(() => {
  try {
    if (fs.existsSync(shutdownFlag)) {
      try {
        fs.unlinkSync(shutdownFlag);
      } catch (_) {
        // se borra igual al reiniciar
      }
      gracefulShutdown('shutdown-flag');
    }
  } catch (_) {
    // nunca romper por el polling
  }
}, 2000);
// Windows: detect parent process death via periodic check
if (process.platform === 'win32') {
  const parentPid = process.ppid;
  if (parentPid) {
    setInterval(() => {
      try {
        process.kill(parentPid, 0); // signal 0 = check if alive
      } catch (_) {
        // Parent died — shut down gracefully
        gracefulShutdown('parent-exit');
      }
    }, 5000);
  }
}
process.on('uncaughtException', async (err) => {
  logger.error(`Excepcion no capturada: ${err.message}`);
  logger.error(`Stack: ${err.stack}`);
  try {
    await client.destroy();
  } catch (_) {
    // Best effort
  }
  process.exit(1);
});
process.on('unhandledRejection', (reason, promise) => {
  logger.error(`Promise no manejada: ${reason}`);
  // No exit - log and continue, the bot can recover from most rejected promises
});
