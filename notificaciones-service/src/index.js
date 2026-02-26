const express = require('express');
const swaggerJsdoc = require('swagger-jsdoc');
const swaggerUi = require('swagger-ui-express');
const { v4: uuidv4 } = require('uuid');

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

  if (!tipo || !destinatario || !mensaje) {
    return res.status(400).json({
      error: 'Campos requeridos faltantes',
      detail: 'Los campos tipo, destinatario y mensaje son obligatorios.',
    });
  }

  const tiposValidos = ['BIENVENIDA', 'ACTUALIZACION', 'ALERTA'];
  if (!tiposValidos.includes(tipo.toUpperCase())) {
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
  console.log(`✅ notificaciones-service corriendo en http://localhost:${PORT}`);
  console.log(`📄 Swagger UI disponible en http://localhost:${PORT}/api-docs`);
});
