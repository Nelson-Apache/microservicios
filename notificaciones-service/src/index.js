const express = require('express');
const swaggerJsdoc = require('swagger-jsdoc');
const swaggerUi = require('swagger-ui-express');
const { v4: uuidv4 } = require('uuid');
const winston = require('winston');

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
        winston.format.json()
      )
    })
  ]
});

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// ─────────────────────────────────────────────
// Base de datos en memoria para notificaciones
// ─────────────────────────────────────────────
let notificaciones = [];

// ─────────────────────────────────────────────
// Configuración OpenAPI / Swagger
// ─────────────────────────────────────────────
const swaggerOptions = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Servicio de Notificaciones',
      version: '1.0.0',
      description:
        '## Microservicio de Notificaciones\n\n' +
        'Gestiona el registro y consulta de notificaciones del sistema.\n\n' +
        'Este servicio simula el envío de notificaciones cuando ocurren eventos\n' +
        'importantes, como el registro de un nuevo empleado.\n\n' +
        '### Tipos de notificación soportados\n' +
        '- `BIENVENIDA`: Notificación al registrar un nuevo empleado\n' +
        '- `ACTUALIZACION`: Cambios en datos de empleados\n' +
        '- `ALERTA`: Eventos críticos del sistema',
      contact: {
        name: 'Equipo de Microservicios',
        email: 'soporte@empresa.com',
      },
      license: { name: 'MIT' },
    },
    servers: [
      {
        url: 'http://localhost:8082',
        description: 'Servidor local de desarrollo',
      },
    ],
    tags: [
      {
        name: 'Diagnóstico',
        description: 'Endpoints de salud y estado del servicio',
      },
      {
        name: 'Notificaciones',
        description: 'Operaciones CRUD sobre notificaciones',
      },
    ],
  },
  apis: ['./src/index.js'],
};

const swaggerSpec = swaggerJsdoc(swaggerOptions);

// Exponer Swagger UI
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec, {
  customCss: '.swagger-ui .topbar { display: none }',
  customSiteTitle: 'Notificaciones API - Swagger UI',
}));

// Exponer spec JSON para integraciones
app.get('/api-docs.json', (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.send(swaggerSpec);
});

// ─────────────────────────────────────────────
// ENDPOINTS
// ─────────────────────────────────────────────

/**
 * @openapi
 * /:
 *   get:
 *     tags: [Diagnóstico]
 *     summary: Health Check
 *     description: Verifica que el servicio de notificaciones está activo y operativo.
 *     responses:
 *       200:
 *         description: Servicio operativo
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 status:
 *                   type: string
 *                   example: ok
 *                 service:
 *                   type: string
 *                   example: notificaciones-service
 *                 version:
 *                   type: string
 *                   example: 1.0.0
 *                 docs:
 *                   type: string
 *                   example: /api-docs
 */
app.get('/', (req, res) => {
  res.json({
    status: 'ok',
    service: 'notificaciones-service',
    version: '1.0.0',
    docs: '/api-docs',
  });
});

/**
 * @openapi
 * /health:
 *   get:
 *     tags: [Diagnóstico]
 *     summary: Health check detallado
 *     description: Verifica el estado del servicio y sus dependencias.
 *     responses:
 *       200:
 *         description: Servicio saludable
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 status:
 *                   type: string
 *                   example: healthy
 *                 service:
 *                   type: string
 *                   example: notificaciones-service
 *                 version:
 *                   type: string
 *                   example: 1.0.0
 *                 checks:
 *                   type: object
 *                   properties:
 *                     memory:
 *                       type: string
 *                       example: ok
 *                     uptime:
 *                       type: string
 *                       example: ok
 */
app.get('/health', (req, res) => {
  const memUsage = process.memoryUsage();
  const memUsedMB = (memUsage.heapUsed / 1024 / 1024).toFixed(2);
  const memTotalMB = (memUsage.heapTotal / 1024 / 1024).toFixed(2);
  const memPercent = ((memUsage.heapUsed / memUsage.heapTotal) * 100).toFixed(2);

  const checks = {
    memory: parseFloat(memPercent) < 95 ? 'ok' : 'warning',
    uptime: process.uptime() > 0 ? 'ok' : 'error',
    notificaciones_count: notificaciones.length,
  };

  const health = {
    status: checks.memory === 'ok' && checks.uptime === 'ok' ? 'healthy' : 'degraded',
    service: 'notificaciones-service',
    version: '1.0.0',
    checks: checks,
    metrics: {
      memory_used_mb: memUsedMB,
      memory_total_mb: memTotalMB,
      memory_percent: memPercent,
      uptime_seconds: Math.floor(process.uptime()),
    },
  };

  const statusCode = health.status === 'healthy' ? 200 : 503;
  res.status(statusCode).json(health);
});

/**
 * @openapi
 * /notificaciones:
 *   post:
 *     tags: [Notificaciones]
 *     summary: Registrar una notificación
 *     description: >
 *       Registra una nueva notificación en el sistema.
 *       El campo `id` y `fechaCreacion` son generados automáticamente.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             $ref: '#/components/schemas/NotificacionInput'
 *           example:
 *             tipo: BIENVENIDA
 *             destinatario: juan@empresa.com
 *             mensaje: Bienvenido al equipo, Juan Pérez
 *     responses:
 *       201:
 *         description: Notificación registrada exitosamente
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Notificacion'
 *       400:
 *         description: Datos inválidos o campos requeridos faltantes
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       500:
 *         description: Error interno del servidor
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
app.post('/notificaciones', (req, res) => {
  const { tipo, destinatario, mensaje } = req.body;

  logger.info('Solicitud de creación de notificación', {
    event: 'notificacion_create_request',
    tipo,
    destinatario
  });

  if (!tipo || !destinatario || !mensaje) {
    logger.warn('Campos requeridos faltantes en solicitud', {
      event: 'validation_error',
      missing_fields: { tipo: !tipo, destinatario: !destinatario, mensaje: !mensaje }
    });
    return res.status(400).json({
      error: 'Campos requeridos faltantes',
      detail: 'Los campos tipo, destinatario y mensaje son obligatorios.',
    });
  }

  const tiposValidos = ['BIENVENIDA', 'ACTUALIZACION', 'ALERTA'];
  if (!tiposValidos.includes(tipo.toUpperCase())) {
    logger.warn('Tipo de notificación inválido', {
      event: 'invalid_notification_type',
      tipo_recibido: tipo
    });
    return res.status(400).json({
      error: 'Tipo de notificación inválido',
      detail: `El tipo debe ser uno de: ${tiposValidos.join(', ')}`,
    });
  }

  const nuevaNotificacion = {
    id: uuidv4(),
    tipo: tipo.toUpperCase(),
    destinatario,
    mensaje,
    fechaCreacion: new Date().toISOString(),
    estado: 'ENVIADO',
  };

  notificaciones.push(nuevaNotificacion);
  
  logger.info('Notificación creada exitosamente', {
    event: 'notificacion_created',
    notificacion_id: nuevaNotificacion.id,
    tipo: nuevaNotificacion.tipo
  });
  
  return res.status(201).json(nuevaNotificacion);
});

/**
 * @openapi
 * /notificaciones:
 *   get:
 *     tags: [Notificaciones]
 *     summary: Listar todas las notificaciones
 *     description: Retorna la lista completa de todas las notificaciones registradas en el sistema.
 *     responses:
 *       200:
 *         description: Lista de notificaciones obtenida exitosamente
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 $ref: '#/components/schemas/Notificacion'
 *       500:
 *         description: Error interno del servidor
 */
app.get('/notificaciones', (req, res) => {
  res.json(notificaciones);
});

/**
 * @openapi
 * /notificaciones/{id}:
 *   get:
 *     tags: [Notificaciones]
 *     summary: Obtener una notificación por ID
 *     description: Busca y retorna una notificación específica mediante su identificador UUID.
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: string
 *           format: uuid
 *         description: UUID de la notificación a buscar
 *         example: "550e8400-e29b-41d4-a716-446655440000"
 *     responses:
 *       200:
 *         description: Notificación encontrada y retornada exitosamente
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Notificacion'
 *       404:
 *         description: No existe ninguna notificación con el ID proporcionado
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       500:
 *         description: Error interno del servidor
 */
app.get('/notificaciones/:id', (req, res) => {
  const notificacion = notificaciones.find((n) => n.id === req.params.id);
  if (!notificacion) {
    return res.status(404).json({
      error: 'Notificación no encontrada',
      detail: `No existe una notificación con ID '${req.params.id}'.`,
    });
  }
  res.json(notificacion);
});

// ─────────────────────────────────────────────
// Schemas OpenAPI (componentes reutilizables)
// ─────────────────────────────────────────────
/**
 * @openapi
 * components:
 *   schemas:
 *     NotificacionInput:
 *       type: object
 *       required:
 *         - tipo
 *         - destinatario
 *         - mensaje
 *       properties:
 *         tipo:
 *           type: string
 *           enum: [BIENVENIDA, ACTUALIZACION, ALERTA]
 *           description: Tipo de notificación
 *           example: BIENVENIDA
 *         destinatario:
 *           type: string
 *           description: Email o identificador del destinatario
 *           example: juan@empresa.com
 *         mensaje:
 *           type: string
 *           description: Contenido del mensaje de la notificación
 *           example: Bienvenido al equipo, Juan Pérez
 *     Notificacion:
 *       type: object
 *       properties:
 *         id:
 *           type: string
 *           format: uuid
 *           description: Identificador único generado automáticamente
 *           example: "550e8400-e29b-41d4-a716-446655440000"
 *         tipo:
 *           type: string
 *           enum: [BIENVENIDA, ACTUALIZACION, ALERTA]
 *           example: BIENVENIDA
 *         destinatario:
 *           type: string
 *           example: juan@empresa.com
 *         mensaje:
 *           type: string
 *           example: Bienvenido al equipo, Juan Pérez
 *         fechaCreacion:
 *           type: string
 *           format: date-time
 *           example: "2024-01-15T10:30:00.000Z"
 *         estado:
 *           type: string
 *           example: ENVIADO
 *     Error:
 *       type: object
 *       properties:
 *         error:
 *           type: string
 *           description: Descripción corta del error
 *         detail:
 *           type: string
 *           description: Detalle adicional del error
 */

// ─────────────────────────────────────────────
// Iniciar servidor
// ─────────────────────────────────────────────
app.listen(PORT, () => {
  logger.info(`notificaciones-service corriendo en http://localhost:${PORT}`, {
    event: 'server_started',
    port: PORT
  });
  logger.info(`Swagger UI disponible en http://localhost:${PORT}/api-docs`, {
    event: 'swagger_ready',
    swagger_url: `http://localhost:${PORT}/api-docs`
  });
});
