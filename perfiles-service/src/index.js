// Tracing debe ser el primero — instrumenta http y express antes de que se carguen
require('./tracing');

const express = require('express');
const { v4: uuidv4 } = require('uuid');
const winston = require('winston');
const amqp = require('amqplib');
const { Pool } = require('pg');
const client = require('prom-client');

// ─────────────────────────────────────────────
// Configuración de Logging
// ─────────────────────────────────────────────
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  defaultMeta: { service: 'perfiles-service' },
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize({ all: false }),
        winston.format.printf(({ timestamp, level, message, ...meta }) => {
          return `${timestamp} [${level}]: ${message} ${Object.keys(meta).length && meta.service !== 'perfiles-service' ? JSON.stringify(meta) : ''}`;
        })
      )
    })
  ]
});

const app = express();
const PORT = process.env.PORT || 3000;

// ── Métricas Prometheus ──
client.collectDefaultMetrics({ prefix: 'perfiles_' });

const duracionHttp = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duración de peticiones HTTP en segundos',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.05, 0.1, 0.5, 1, 2, 5],
});

const totalHttp = new client.Counter({
  name: 'http_requests_total',
  help: 'Total de peticiones HTTP recibidas',
  labelNames: ['method', 'route', 'status_code'],
});

const servicioSaludable = new client.Gauge({
  name: 'servicio_saludable',
  help: 'Servicio y dependencias operativas: 1=sí, 0=no',
  labelNames: ['service'],
});

app.use(express.json());

// Middleware de métricas HTTP
app.use((req, res, next) => {
  const inicio = Date.now();
  res.on('finish', () => {
    const ruta = req.route ? req.route.path : req.path;
    const duracion = (Date.now() - inicio) / 1000;
    duracionHttp.observe({ method: req.method, route: ruta, status_code: res.statusCode }, duracion);
    totalHttp.inc({ method: req.method, route: ruta, status_code: res.statusCode });
  });
  next();
});

// ─────────────────────────────────────────────
// Conexión a Base de Datos PostgreSQL
// ─────────────────────────────────────────────
const pool = new Pool({
  connectionString: process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/perfilesdb'
});

async function initDB() {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS perfiles (
        id UUID PRIMARY KEY,
        empleado_id VARCHAR(50) UNIQUE NOT NULL,
        nombre VARCHAR(150),
        email VARCHAR(150),
        telefono VARCHAR(50) DEFAULT '',
        direccion VARCHAR(255) DEFAULT '',
        ciudad VARCHAR(100) DEFAULT '',
        biografia TEXT DEFAULT '',
        fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW()
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
let estadoRabbitMQ = 'DOWN';

async function initRabbitMQ() {
  try {
    const rabbitUrl = process.env.RABBITMQ_URL || 'amqp://guest:guest@localhost:5672/';
    const connection = await amqp.connect(rabbitUrl);
    estadoRabbitMQ = 'UP';
    const channel = await connection.createChannel();
    const exchange = 'rrhh_events';

    await channel.assertExchange(exchange, 'topic', { durable: true });

    // Cola dedicada exclusivamente a crear perfiles
    const q = await channel.assertQueue('perfiles_queue', { durable: true });

    // Solo escuchamos la creación y eliminación de empleados para generar/borrar el perfil
    await channel.bindQueue(q.queue, exchange, 'empleado.creado');
    await channel.bindQueue(q.queue, exchange, 'empleado.eliminado');

    logger.info('Conectado a RabbitMQ, esperando mensajes de empleados...');

    channel.consume(q.queue, async (msg) => {
      if (!msg) return;

      const routingKey = msg.fields.routingKey;

      if (routingKey === 'empleado.creado') {
        const eventData = JSON.parse(msg.content.toString());
        const empleadoId = String(eventData.id);

        try {
          // Verificamos si ya existe por si llega duplicado
          const exists = await pool.query('SELECT id FROM perfiles WHERE empleado_id = $1', [empleadoId]);
          if (exists.rowCount === 0) {
            await pool.query(`
                            INSERT INTO perfiles (id, empleado_id, nombre, email, telefono, direccion, ciudad, biografia, fecha_creacion) 
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                        `, [
              uuidv4(),
              empleadoId,
              eventData.nombre || '',
              eventData.email || '',
              "", // telefono
              "", // direccion
              "", // ciudad
              ""  // biografia
            ]);
            logger.info(`Perfil creado por defecto para empleado ${empleadoId}`);
          } else {
            logger.info(`Perfil ya existía para empleado ${empleadoId}, ignorando evento.`);
          }
        } catch (error) {
          logger.error('Error insertando perfil desde evento', { error: error.message, empleadoId });
        }
      } else if (routingKey === 'empleado.eliminado') {
        const eventData = JSON.parse(msg.content.toString());
        const empleadoId = String(eventData.id);

        try {
          const result = await pool.query('DELETE FROM perfiles WHERE empleado_id = $1', [empleadoId]);
          if (result.rowCount > 0) {
            logger.info(`Perfil eliminado exitosamente para empleado ${empleadoId}`);
          } else {
            logger.info(`No se encontró perfil para eliminar del empleado ${empleadoId}`);
          }
        } catch (error) {
          logger.error('Error eliminando perfil desde evento', { error: error.message, empleadoId });
        }
      }

      channel.ack(msg); // Marcamos el mensaje como procesado
    });
  } catch (error) {
    estadoRabbitMQ = 'DOWN';
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
      title: 'Perfiles Service API',
      version: '1.0.0',
      description: 'API para la gestión de Perfiles de Empleados',
    },
    components: {
      securitySchemes: {
        BearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT',
          description: 'Token JWT obtenido desde POST /auth/login',
        },
      },
    },
    security: [{ BearerAuth: [] }],
  },
  apis: ['./src/index.js'],
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
app.get('/health', async (req, res) => {
  const estado = {
    status: 'UP',
    service: 'perfiles-service',
    version: '1.0.0',
    checks: {}
  };
  let degradado = false;

  try {
    await pool.query('SELECT 1');
    estado.checks.database = 'UP';
  } catch (err) {
    estado.checks.database = 'DOWN';
    degradado = true;
  }

  estado.checks.messageBroker = estadoRabbitMQ;
  if (estadoRabbitMQ === 'DOWN') degradado = true;

  if (degradado) {
    estado.status = 'DOWN';
    servicioSaludable.labels({ service: 'perfiles-service' }).set(0);
    return res.status(503).json(estado);
  }
  servicioSaludable.labels({ service: 'perfiles-service' }).set(1);
  res.json(estado);
});

app.get('/metrics', async (req, res) => {
  res.set('Content-Type', client.register.contentType);
  res.end(await client.register.metrics());
});

/**
 * @swagger
 * /perfiles:
 *   get:
 *     summary: Lista todos los perfiles
 *     responses:
 *       200:
 *         description: Lista de perfiles
 */
app.get('/perfiles', async (req, res) => {

  try {
    const result = await pool.query('SELECT * FROM perfiles ORDER BY fecha_creacion DESC');
    const perfilesList = result.rows.map(row => ({
      id: row.id,
      empleadoId: row.empleado_id,
      nombre: row.nombre,
      email: row.email,
      telefono: row.telefono,
      direccion: row.direccion,
      ciudad: row.ciudad,
      biografia: row.biografia,
      fechaCreacion: row.fecha_creacion
    }));
    res.json(perfilesList);
  } catch (error) {
    logger.error('Error obteniendo perfiles', { error: error.message });
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

/**
 * @swagger
 * /perfiles/{empleadoId}:
 *   get:
 *     summary: Obtiene el perfil de un empleado
 *     parameters:
 *       - in: path
 *         name: empleadoId
 *         required: true
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: Perfil del empleado
 *       404:
 *         description: Perfil no encontrado
 */
app.get('/perfiles/:empleadoId', async (req, res) => {
  try {
    const { empleadoId } = req.params;
    const result = await pool.query('SELECT * FROM perfiles WHERE empleado_id = $1', [empleadoId]);

    if (result.rowCount === 0) {
      return res.status(404).json({ error: `No se encontró perfil para el empleado: ${empleadoId}` });
    }

    const row = result.rows[0];
    res.json({
      id: row.id,
      empleadoId: row.empleado_id,
      nombre: row.nombre,
      email: row.email,
      telefono: row.telefono,
      direccion: row.direccion,
      ciudad: row.ciudad,
      biografia: row.biografia,
      fechaCreacion: row.fecha_creacion
    });
  } catch (error) {
    logger.error('Error obteniendo perfil por empleado', { error: error.message });
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

/**
 * @swagger
 * /perfiles/{empleadoId}:
 *   put:
 *     summary: Actualiza el perfil de un empleado
 *     parameters:
 *       - in: path
 *         name: empleadoId
 *         required: true
 *         schema:
 *           type: string
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               telefono:
 *                 type: string
 *               direccion:
 *                 type: string
 *               ciudad:
 *                 type: string
 *               biografia:
 *                 type: string
 *     responses:
 *       200:
 *         description: Perfil actualizado
 *       404:
 *         description: Perfil no encontrado
 */
app.put('/perfiles/:empleadoId', async (req, res) => {
  try {
    const { empleadoId } = req.params;
    const { telefono, direccion, ciudad, biografia } = req.body;

    // Verificamos existencia
    const check = await pool.query('SELECT id FROM perfiles WHERE empleado_id = $1', [empleadoId]);
    if (check.rowCount === 0) {
      return res.status(404).json({ error: `No se encontró perfil para el empleado: ${empleadoId}` });
    }

    const result = await pool.query(`
            UPDATE perfiles 
            SET telefono = COALESCE($1, telefono),
                direccion = COALESCE($2, direccion),
                ciudad = COALESCE($3, ciudad),
                biografia = COALESCE($4, biografia)
            WHERE empleado_id = $5
            RETURNING *
        `, [telefono, direccion, ciudad, biografia, empleadoId]);

    const row = result.rows[0];
    res.json({
      id: row.id,
      empleadoId: row.empleado_id,
      nombre: row.nombre,
      email: row.email,
      telefono: row.telefono,
      direccion: row.direccion,
      ciudad: row.ciudad,
      biografia: row.biografia,
      fechaCreacion: row.fecha_creacion
    });
  } catch (error) {
    logger.error('Error actualizando perfil por empleado', { error: error.message });
    res.status(500).json({ error: 'Error interno del servidor' });
  }
});

async function monitorearBD() {
  try {
    await pool.query('SELECT 1');
    const brokerOk = estadoRabbitMQ === 'UP';
    servicioSaludable.labels({ service: 'perfiles-service' }).set(brokerOk ? 1 : 0);
  } catch {
    servicioSaludable.labels({ service: 'perfiles-service' }).set(0);
  }
}

// ─────────────────────────────────────────────
// Iniciar servidor
// ─────────────────────────────────────────────
async function startServer() {
  await initDB();
  initRabbitMQ();
  setInterval(monitorearBD, 30000);
  app.listen(PORT, () => {
    logger.info(`perfiles-service corriendo en http://localhost:${PORT}`);
  });
}

startServer();
