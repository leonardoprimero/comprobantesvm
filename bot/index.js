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

// Configuración
const API_URL = process.env.API_URL || 'http://localhost:8000';
const API_TIMEOUT = 120000; // 2 minutos (GPT-4o Vision puede tardar)
const QR_PATH = process.env.QR_PATH || '';
const CHROMIUM_PATH = process.env.CHROMIUM_PATH || '';
const WWEBJS_AUTH_DIR = process.env.WWEBJS_AUTH_DIR || '';

// Debug: mostrar variables de entorno importantes
console.log('');
console.log('='.repeat(50));
console.log('🚀 INICIANDO BOT DE COMPROBANTES');
console.log('='.repeat(50));
console.log('📌 Variables de entorno:');
console.log(`   API_URL: ${API_URL}`);
console.log(`   QR_PATH: ${QR_PATH || '(NO DEFINIDO)'}`);
console.log(`   CHROMIUM_PATH: ${CHROMIUM_PATH || '(NO DEFINIDO)'}`);
console.log(`   WWEBJS_AUTH_DIR: ${WWEBJS_AUTH_DIR || '(NO DEFINIDO)'}`);
console.log('='.repeat(50));
console.log('');

// Cola de procesamiento
const colaComprobantes = [];
let procesando = false;

/**
 * Procesa la cola de comprobantes uno por uno.
 */
async function procesarCola() {
    if (procesando) return;
    procesando = true;

    while (colaComprobantes.length > 0) {
        const { media, msg } = colaComprobantes.shift();
        const nombreArchivo = media.filename || `comprobante_${Date.now()}`;

        console.log(`📄 Procesando: ${nombreArchivo}`);

        try {
            const response = await axios.post(
                `${API_URL}/process-receipt/`,
                {
                    file_base64: media.data,
                    sender_phone: msg.from,
                    mime_type: media.mimetype,
                    timestamp: new Date().toISOString(),
                    texto_completo: msg.body || ''
                },
                {
                    timeout: API_TIMEOUT,
                    headers: { 'Content-Type': 'application/json' }
                }
            );

            if (response.data.success) {
                const monto = response.data.data?.monto_numerico || 'N/A';
                const emisor = response.data.data?.emisor_nombre || 'Desconocido';
                console.log(`✅ Procesado: $${monto} de ${emisor}`);
            } else {
                console.log(`⚠️  Procesado con advertencia: ${response.data.message}`);
            }

        } catch (error) {
            let errorMsg = '❌ Error al procesar comprobante.';
            if (error.code === 'ECONNREFUSED') {
                errorMsg = '❌ Error: El sistema principal no está respondiendo (API caída).';
                console.error('❌ Error: No se puede conectar a la API Python. ¿Está corriendo?');
            } else if (error.code === 'ETIMEDOUT') {
                errorMsg = '❌ Error: Tiempo de espera agotado al procesar.';
                console.error('❌ Error: Timeout al procesar. El servidor tardó demasiado.');
            } else {
                console.error('❌ Error al procesar:', error.message);
            }
            try { await msg.reply(errorMsg); } catch (e) { }
        }

        // Esperar 2 segundos entre cada procesamiento
        await new Promise(r => setTimeout(r, 2000));
    }

    procesando = false;
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
        '--disable-extensions'
    ],
};
// Use the bundled Chromium if CHROMIUM_PATH is provided
if (CHROMIUM_PATH && fs.existsSync(CHROMIUM_PATH)) {
    puppeteerConfig.executablePath = CHROMIUM_PATH;
    console.log(`🔧 Usando Chromium personalizado: ${CHROMIUM_PATH}`);
}

const client = new Client({
    authStrategy: new LocalAuth(authOptions),
    puppeteer: puppeteerConfig,
});

// Evento: QR para escanear
client.on('qr', async qr => {
    console.log('\n'.repeat(2));
    console.log('='.repeat(50));
    console.log('📱 ESCANEAR CÓDIGO QR CON WHATSAPP');
    console.log('='.repeat(50));
    qrcodeTerminal.generate(qr, { small: true });

    // Marcador especial para que Python pueda parsear el QR
    console.log(`[QR_DATA]${qr}[/QR_DATA]`);

    console.log('\nSi el QR no se ve bien, abrir este link:');
    console.log(`https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${encodeURIComponent(qr)}`);
    console.log('='.repeat(50));

    if (QR_PATH) {
        try {
            const qrDir = path.dirname(QR_PATH);
            if (!fs.existsSync(qrDir)) {
                fs.mkdirSync(qrDir, { recursive: true });
            }
            await qrcode.toFile(QR_PATH, qr, { width: 400, margin: 1 });
            console.log('📁 QR guardado en:', QR_PATH);
        } catch (error) {
            console.error('❌ Error al guardar QR:', error.message);
        }
    } else {
        console.log('⚠️ QR_PATH no definido, no se guardará imagen');
    }
});

// Evento: Autenticado (después de escanear QR)
client.on('authenticated', () => {
    console.log('🔐 QR escaneado - Autenticación exitosa');
});

// Evento: Fallo de autenticación
client.on('auth_failure', msg => {
    console.error('❌ FALLO DE AUTENTICACIÓN:', msg);
});

// Evento: Desconectado
client.on('disconnected', reason => {
    console.log('🔌 Desconectado:', reason);
});

// Evento: Cambio de estado
client.on('change_state', state => {
    console.log('🔄 Estado cambió a:', state);
});

// Evento: Pantalla de carga
client.on('loading_screen', (percent, message) => {
    console.log(`⏳ Cargando WhatsApp Web: ${percent}% - ${message}`);
    if (percent === 100) {
        console.log('🔄 Carga completa, esperando evento ready...');
    }
});

// Evento: Listo
client.on('ready', () => {
    console.log('\n' + '='.repeat(50));
    console.log('✅ BOT CONECTADO Y LISTO');
    console.log('[CONNECTED]');  // Marcador para Python
    console.log('='.repeat(50));
    console.log('Esperando comprobantes por WhatsApp...');
    console.log('📱 Número conectado:', client.info?.wid?.user || 'No disponible');
    console.log('='.repeat(50) + '\n');
});

// Evento: Cualquier mensaje (incluyendo propios) - para debug
client.on('message_create', async msg => {
    console.log(`📨 [DEBUG] Mensaje detectado de ${msg.from} - hasMedia: ${msg.hasMedia}`);

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
            console.log(`💬 Texto recibido de ${msg.from}: "${texto.substring(0, 50)}..."`);
            try {
                await msg.reply('Este número solo recibe comprobantes (imagen JPG/PNG o PDF).');
            } catch (error) {
                console.error('❌ Error al responder:', error.message);
            }
        }
        return;
    }

    // Solo procesar si tiene media
    try {
        console.log(`📎 Descargando media de ${msg.from}...`);
        const media = await msg.downloadMedia();

        if (!media) {
            console.log('⚠️ No se pudo descargar el archivo');
            return;
        }

        // Tipos válidos
        const tiposValidos = [
            'application/pdf',
            'image/jpeg',
            'image/png',
            'image/jpg'
        ];

        if (tiposValidos.includes(media.mimetype)) {
            console.log(`📥 Recibido: ${media.filename || 'archivo'} (${media.mimetype}) de ${msg.from}`);

            // Agregar a la cola
            colaComprobantes.push({ media, msg });
            procesarCola();
        } else {
            console.log(`⚠️ Tipo no soportado: ${media.mimetype}`);
        }

    } catch (error) {
        console.error('❌ Error al procesar mensaje:', error.message);
    }
});

// Evento: Desconectado
client.on('disconnected', (reason) => {
    console.log('🔌 Desconectado:', reason);
    console.log('Intentando reconectar en 5 segundos...');
    setTimeout(() => {
        client.initialize();
    }, 5000);
});

// Evento: Error de autenticación
client.on('auth_failure', (msg) => {
    console.error('❌ Error de autenticación:', msg);
});

// Iniciar cliente
console.log('\n' + '='.repeat(50));
console.log('🚀 INICIANDO BOT DE COMPROBANTES');
console.log('='.repeat(50) + '\n');

client.initialize().catch(err => {
    console.error('❌ FATAL ERROR al iniciar cliente:', err);
    console.error('Stack:', err.stack);
});

// Timeout handler: if ready doesn't fire in 120 seconds, log a warning
let readyFired = false;
client.on('ready', () => { readyFired = true; });

setTimeout(() => {
    if (!readyFired) {
        console.log('⚠️ ADVERTENCIA: El evento "ready" no se disparó en 120 segundos.');
        console.log('   Esto puede indicar que WhatsApp Web está cargando lentamente.');
        console.log('   Si el problema persiste, reinicia la aplicación.');
    }
}, 120000);
