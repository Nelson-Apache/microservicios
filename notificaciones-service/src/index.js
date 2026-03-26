const express = require('express');
const { v4: uuidv4 } = require('uuid');
const winston = require('winston');
const amqp = require('amqplib');
const { Pool } = require('pg');

// ─────────────────────────────────────────────
// Configuración de logging estructurado (JSON)
// ─────────────────────────────────────────────
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'notificaciones-service' },
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize({ all: false }),
        winston.format.printf(({ timestamp, level, message, ...meta }) => {
          if (message && message.startsWith("[NOTIFICACIÓN]")) {
            return `${message}`;
          }
          return `${timestamp} [${level}]: ${message} ${Object.keys(meta).length && meta.service !== 'notificaciones-service' ? JSON.stringify(meta) : ''}`;
        })
      )
    })
  ]
});

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// ─────────────────────────────────────────────
// Conexión a Base de Datos PostgreSQL
// ─────────────────────────────────────────────
const pool = new Pool({
  connectionString: process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/notificacionesdb'
});

async function initDB() {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS notificaciones (
        id UUID PRIMARY KEY,
        tipo VARCHAR(50) NOT NULL,
        destinatario VARCHAR(100) NOT NULL,
        mensaje TEXT NOT NULL,
        fecha_envio TIMESTAMP NOT NULL,
        empleado_id VARCHAR(50)
      );
    `);
    logger.info('Base de datos inicializada correctamente');
  } catch (error) {
    logger.error('Error inicializando base de datos', { error: error.message });
    process.exit(1);
  }
}

// ─────────────────────────────────────────────
// Conexión a RabbitMQ y Consumo de Eventos
// ─────────────────────────────────────────────
async function initRabbitMQ() {
  try {
    const rabbitUrl = process.env.RABBITMQ_URL || 'amqp://guest:guest@localhost:5672/';
    const connection = await amqp.connect(rabbitUrl);
    const channel = await connection.createChannel();
    const exchange = 'rrhh_events';

    await channel.assertExchange(exchange, 'topic', { durable: true });

    // Cola dedicada exclusivamente a este servicio
    const q = await channel.assertQueue('notificaciones_queue', { durable: true });

    // Eventos de empleados (Reto 3)
    await channel.bindQueue(q.queue, exchange, 'empleado.creado');
    await channel.bindQueue(q.queue, exchange, 'empleado.eliminado');
    // Eventos de seguridad del auth-service (Reto 4)
    await channel.bindQueue(q.queue, exchange, 'usuario.creado');
    await channel.bindQueue(q.queue, exchange, 'usuario.recuperacion');

    logger.info('Conectado a RabbitMQ, esperando mensajes...');

    channel.consume(q.queue, async (msg) => {
      if (!msg) return;

      const routingKey = msg.fields.routingKey;
      const eventData = JSON.parse(msg.content.toString());

      let tipo = "";
      let destinatario = eventData.email || 'soporte@empresa.com';
      let mensajeStr = "";
      // Para eventos de empleados se usa eventData.id; los eventos de usuario no lo tienen
      let empleadoId = eventData.id ? String(eventData.id) : null;

      if (routingKey === 'empleado.creado') {
        // Notificación de bienvenida al incorporarse (Reto 3)
        tipo = "BIENVENIDA";
        mensajeStr = `Bienvenido ${eventData.nombre} al equipo.`;

      } else if (routingKey === 'empleado.eliminado') {
        // Notificación de desvinculación (Reto 3)
        tipo = "DESVINCULACION";
        mensajeStr = `Su cuenta ha sido desvinculada, ${eventData.nombre}.`;

      } else if (routingKey === 'usuario.creado') {
        // Notificación de seguridad: el empleado debe establecer su contraseña (Reto 4)
        tipo = "SEGURIDAD";
        mensajeStr = `Para establecer o recuperar su contraseña, utilice el siguiente token: ${eventData.token}`;

      } else if (routingKey === 'usuario.recuperacion') {
        // Notificación de seguridad: recuperación de contraseña solicitada (Reto 4)
        tipo = "SEGURIDAD";
        mensajeStr = `Para establecer o recuperar su contraseña, utilice el siguiente token: ${eventData.token}`;
      }

      // Simulación de envío de correo electrónico mediante log
      logger.info(`[NOTIFICACIÓN] Tipo: ${tipo} | Para: ${destinatario} | Mensaje: "${mensajeStr}"`);

      // Persistencia en base de datos
      try {
        await pool.query(`
          INSERT INTO notificaciones (id, tipo, destinatario, mensaje, fecha_envio, empleado_id)
          VALUES ($1, $2, $3, $4, $5, $6)
        `, [uuidv4(), tipo, destinatario, mensajeStr, new Date(), empleadoId]);
      } catch (error) {
        logger.error('Error insertando notificacion', { error: error.message });
      }

      channel.ack(msg); // Marcar mensaje como procesado exitosamente
    });
  } catch (error) {
    logger.error('Error conectando a RabbitMQ, reintentando...', { error: error.message });
    setTimeout(initRabbitMQ, 5000);
  }
}

// ─────────────────────────────────────────────
// Swagger Docs
// ─────────────────────────────────────────────
const swaggerUi = require('swagger-ui-express');
const swaggerJsdoc = require('swagger-jsdoc');

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Notificaciones Service API',
      version: '1.0.0',
      description: 'API para la gestión del Historial de Notificaciones',
    },
  },
  apis: ['./src/index.js'], // buscar en este archivo
};
const specs = swaggerJsdoc(options);
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(specs));

// ─────────────────────────────────────────────
// ENDPOINTS REST
// ─────────────────────────────────────────────

/**
 * @swagger
 * /health:
 *   get:
 *     summary: Healthcheck del servicio
 *     responses:
 *       200:
 *         description: Servicio funcionando
 */
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'notificaciones-service',
    version: '1.0.0'
  });
});

/**
 * @swagger
 * /notificaciones:
 *   get:
 *     summary: Lista todas las notificaciones registradas (Historial global)
 *     responses:
 *       200:
 *         description: Lista de notificaciones
 */
app.get('/notificaciones', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM notificaciones ORDER BY fecha_envio DESC LIMIT 100');
    const notificacionesList = result.rows.map(row => ({
      id: row.id,
      tipo: row.tipo,
      destinatario: row.destinatario,
      mensaje: row.mensaje,
      fechaEnvio: row.fecha_envio,
      empleadoId: row.empleado_id
    }));
    res.json(notificacionesList);
  } catch (error) {
    logger.error('Error obteniendo notificaciones', { error: error.message });
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

/**
 * @swagger
 * /notificaciones/{empleadoId}:
 *   get:
 *     summary: Lista notificaciones de un empleado específico
 *     parameters:
 *       - in: path
 *         name: empleadoId
 *         required: true
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: Lista de notificaciones del empleado
 */
app.get('/notificaciones/:empleadoId', async (req, res) => {
  try {
    const { empleadoId } = req.params;
    const result = await pool.query('SELECT * FROM notificaciones WHERE empleado_id = $1 ORDER BY fecha_envio DESC', [empleadoId]);
    const notificacionesList = result.rows.map(row => ({
      id: row.id,
      tipo: row.tipo,
      destinatario: row.destinatario,
      mensaje: row.mensaje,
      fechaEnvio: row.fecha_envio,
      empleadoId: row.empleado_id
    }));
    res.json(notificacionesList);
  } catch (error) {
    logger.error('Error obteniendo notificaciones por empleado', { error: error.message });
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

// ─────────────────────────────────────────────
// Iniciar servidor
// ─────────────────────────────────────────────
async function startServer() {
  await initDB();
  initRabbitMQ();
  app.listen(PORT, () => {
    logger.info(`notificaciones-service corriendo en http://localhost:${PORT}`);
  });
}

startServer();
