/**
 * Pruebas unitarias para el servicio de notificaciones.
 * Utiliza Jest y supertest para pruebas de integración.
 */

const request = require('supertest');
const express = require('express');

// Mock de la aplicación (simplificada para tests)
const createApp = () => {
  const app = express();
  app.use(express.json());

  // Base de datos en memoria (mock)
  let notificaciones = [];

  // Endpoint para crear notificación
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
      id: `test-${Date.now()}`,
      tipo: tipo.toUpperCase(),
      destinatario,
      mensaje,
      fechaCreacion: new Date().toISOString(),
      estado: 'ENVIADO',
    };

    notificaciones.push(nuevaNotificacion);
    return res.status(201).json(nuevaNotificacion);
  });

  // Endpoint para listar notificaciones
  app.get('/notificaciones', (req, res) => {
    res.json(notificaciones);
  });

  // Endpoint para obtener notificación por ID
  app.get('/notificaciones/:id', (req, res) => {
    const notificacion = notificaciones.find(n => n.id === req.params.id);
    
    if (!notificacion) {
      return res.status(404).json({
        error: 'Notificación no encontrada',
        detail: `No existe notificación con ID ${req.params.id}`,
      });
    }
    
    res.json(notificacion);
  });

  // Endpoint de health check
  app.get('/health', (req, res) => {
    const memoryUsage = process.memoryUsage();
    const memoryUsedMB = memoryUsage.heapUsed / 1024 / 1024;
    const memoryTotalMB = memoryUsage.heapTotal / 1024 / 1024;
    const memoryPercent = (memoryUsedMB / memoryTotalMB) * 100;

    const health = {
      status: memoryPercent > 80 ? 'degraded' : 'healthy',
      service: 'notificaciones-service',
      uptime: process.uptime(),
      memory: {
        used_mb: memoryUsedMB.toFixed(2),
        total_mb: memoryTotalMB.toFixed(2),
        percent: memoryPercent.toFixed(2),
      },
    };

    const statusCode = health.status === 'healthy' ? 200 : 503;
    res.status(statusCode).json(health);
  });

  // Helper para limpiar notificaciones (útil para tests)
  app.delete('/test/clear', (req, res) => {
    notificaciones = [];
    res.status(204).send();
  });

  return app;
};

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('Servicio de Notificaciones - API Tests', () => {
  let app;

  beforeEach(() => {
    app = createApp();
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Tests de health check
  // ───────────────────────────────────────────────────────────────────────────

  describe('GET /health', () => {
    it('debe retornar el estado de salud del servicio', async () => {
      const response = await request(app).get('/health');

      expect(response.status).toBe(200);
      expect(response.body).toHaveProperty('status');
      expect(response.body).toHaveProperty('service', 'notificaciones-service');
      expect(response.body).toHaveProperty('uptime');
      expect(response.body).toHaveProperty('memory');
    });

    it('debe incluir métricas de memoria', async () => {
      const response = await request(app).get('/health');

      expect(response.body.memory).toHaveProperty('used_mb');
      expect(response.body.memory).toHaveProperty('total_mb');
      expect(response.body.memory).toHaveProperty('percent');
    });
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Tests de creación de notificaciones
  // ───────────────────────────────────────────────────────────────────────────

  describe('POST /notificaciones', () => {
    it('debe crear una notificación de BIENVENIDA exitosamente', async () => {
      const notificacion = {
        tipo: 'BIENVENIDA',
        destinatario: 'juan@empresa.com',
        mensaje: 'Bienvenido al equipo',
      };

      const response = await request(app)
        .post('/notificaciones')
        .send(notificacion)
        .expect(201);

      expect(response.body).toHaveProperty('id');
      expect(response.body.tipo).toBe('BIENVENIDA');
      expect(response.body.destinatario).toBe('juan@empresa.com');
      expect(response.body.mensaje).toBe('Bienvenido al equipo');
      expect(response.body.estado).toBe('ENVIADO');
      expect(response.body).toHaveProperty('fechaCreacion');
    });

    it('debe crear una notificación de ACTUALIZACION', async () => {
      const notificacion = {
        tipo: 'ACTUALIZACION',
        destinatario: 'admin@empresa.com',
        mensaje: 'Se actualizó un empleado',
      };

      const response = await request(app)
        .post('/notificaciones')
        .send(notificacion)
        .expect(201);

      expect(response.body.tipo).toBe('ACTUALIZACION');
    });

    it('debe crear una notificación de ALERTA', async () => {
      const notificacion = {
        tipo: 'ALERTA',
        destinatario: 'soporte@empresa.com',
        mensaje: 'Error crítico detectado',
      };

      const response = await request(app)
        .post('/notificaciones')
        .send(notificacion)
        .expect(201);

      expect(response.body.tipo).toBe('ALERTA');
    });

    it('debe retornar 400 si faltan campos requeridos', async () => {
      const notificacionIncompleta = {
        tipo: 'BIENVENIDA',
        // Falta destinatario y mensaje
      };

      const response = await request(app)
        .post('/notificaciones')
        .send(notificacionIncompleta)
        .expect(400);

      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('Campos requeridos faltantes');
    });

    it('debe retornar 400 si el tipo es inválido', async () => {
      const notificacionInvalida = {
        tipo: 'TIPO_INVALIDO',
        destinatario: 'test@empresa.com',
        mensaje: 'Mensaje de prueba',
      };

      const response = await request(app)
        .post('/notificaciones')
        .send(notificacionInvalida)
        .expect(400);

      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('Tipo de notificación inválido');
    });

    it('debe convertir el tipo a mayúsculas', async () => {
      const notificacion = {
        tipo: 'bienvenida',
        destinatario: 'test@empresa.com',
        mensaje: 'Test',
      };

      const response = await request(app)
        .post('/notificaciones')
        .send(notificacion)
        .expect(201);

      expect(response.body.tipo).toBe('BIENVENIDA');
    });
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Tests de consulta de notificaciones
  // ───────────────────────────────────────────────────────────────────────────

  describe('GET /notificaciones', () => {
    it('debe retornar una lista vacía inicialmente', async () => {
      const response = await request(app)
        .get('/notificaciones')
        .expect(200);

      expect(Array.isArray(response.body)).toBe(true);
      expect(response.body).toHaveLength(0);
    });

    it('debe retornar todas las notificaciones creadas', async () => {
      // Crear dos notificaciones
      await request(app)
        .post('/notificaciones')
        .send({
          tipo: 'BIENVENIDA',
          destinatario: 'user1@empresa.com',
          mensaje: 'Mensaje 1',
        });

      await request(app)
        .post('/notificaciones')
        .send({
          tipo: 'ALERTA',
          destinatario: 'user2@empresa.com',
          mensaje: 'Mensaje 2',
        });

      const response = await request(app)
        .get('/notificaciones')
        .expect(200);

      expect(response.body).toHaveLength(2);
      expect(response.body[0].tipo).toBe('BIENVENIDA');
      expect(response.body[1].tipo).toBe('ALERTA');
    });
  });

  describe('GET /notificaciones/:id', () => {
    it('debe retornar una notificación por ID', async () => {
      // Crear notificación
      const createResponse = await request(app)
        .post('/notificaciones')
        .send({
          tipo: 'BIENVENIDA',
          destinatario: 'test@empresa.com',
          mensaje: 'Test mensaje',
        });

      const notificacionId = createResponse.body.id;

      // Consultar por ID
      const response = await request(app)
        .get(`/notificaciones/${notificacionId}`)
        .expect(200);

      expect(response.body.id).toBe(notificacionId);
      expect(response.body.tipo).toBe('BIENVENIDA');
    });

    it('debe retornar 404 si la notificación no existe', async () => {
      const response = await request(app)
        .get('/notificaciones/id-inexistente')
        .expect(404);

      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('no encontrada');
    });
  });

  // ───────────────────────────────────────────────────────────────────────────
  // Tests de validaciones
  // ───────────────────────────────────────────────────────────────────────────

  describe('Validaciones', () => {
    it('debe rechazar peticiones sin Content-Type application/json', async () => {
      const response = await request(app)
        .post('/notificaciones')
        .send('invalid data');

      expect(response.status).toBeGreaterThanOrEqual(400);
    });

    it('debe aceptar todos los tipos válidos', async () => {
      const tiposValidos = ['BIENVENIDA', 'ACTUALIZACION', 'ALERTA'];

      for (const tipo of tiposValidos) {
        const response = await request(app)
          .post('/notificaciones')
          .send({
            tipo,
            destinatario: 'test@empresa.com',
            mensaje: `Mensaje de tipo ${tipo}`,
          });

        expect(response.status).toBe(201);
        expect(response.body.tipo).toBe(tipo);
      }
    });
  });
});
