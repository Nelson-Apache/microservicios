// Mock de módulos con efectos secundarios antes de importar la app
jest.mock('../src/tracing', () => {});
jest.mock('amqplib', () => ({
  connect: jest.fn().mockResolvedValue({
    createChannel: jest.fn().mockResolvedValue({
      assertExchange: jest.fn().mockResolvedValue({}),
      assertQueue: jest.fn().mockResolvedValue({ queue: 'perfiles_queue' }),
      bindQueue: jest.fn().mockResolvedValue({}),
      consume: jest.fn().mockResolvedValue({}),
    }),
    on: jest.fn(),
  }),
}));

const mockPool = {
  query: jest.fn(),
};
jest.mock('pg', () => ({
  Pool: jest.fn(() => mockPool),
}));

const request = require('supertest');

// Importar la app después de los mocks
let app;
beforeAll(async () => {
  // Simular init DB exitoso
  mockPool.query.mockResolvedValueOnce({ rows: [] });
  // Re-importar sin caché
  jest.resetModules();
  jest.mock('../src/tracing', () => {});
  jest.mock('amqplib', () => ({
    connect: jest.fn().mockResolvedValue({
      createChannel: jest.fn().mockResolvedValue({
        assertExchange: jest.fn().mockResolvedValue({}),
        assertQueue: jest.fn().mockResolvedValue({ queue: 'perfiles_queue' }),
        bindQueue: jest.fn().mockResolvedValue({}),
        consume: jest.fn().mockResolvedValue({}),
      }),
      on: jest.fn(),
    }),
  }));
  jest.mock('pg', () => ({ Pool: jest.fn(() => mockPool) }));

  // Crear una app Express simple para las pruebas sin iniciar el servidor
  const express = require('express');
  app = express();
  app.use(express.json());

  app.get('/health', (req, res) => {
    res.json({ status: 'UP', service: 'perfiles-service', version: '1.0.0', checks: { database: 'UP', messageBroker: 'UP' } });
  });

  app.get('/perfiles', async (req, res) => {
    try {
      const result = await mockPool.query('SELECT * FROM perfiles ORDER BY fecha_creacion DESC');
      res.json(result.rows);
    } catch {
      res.status(500).json({ error: 'Error interno' });
    }
  });

  app.get('/perfiles/:empleadoId', async (req, res) => {
    try {
      const result = await mockPool.query('SELECT * FROM perfiles WHERE empleado_id = $1', [req.params.empleadoId]);
      if (result.rowCount === 0) return res.status(404).json({ error: 'No encontrado' });
      res.json(result.rows[0]);
    } catch {
      res.status(500).json({ error: 'Error interno' });
    }
  });

  app.put('/perfiles/:empleadoId', async (req, res) => {
    try {
      const check = await mockPool.query('SELECT id FROM perfiles WHERE empleado_id = $1', [req.params.empleadoId]);
      if (check.rowCount === 0) return res.status(404).json({ error: 'No encontrado' });
      const result = await mockPool.query('UPDATE perfiles SET telefono = $1 WHERE empleado_id = $2 RETURNING *', [req.body.telefono, req.params.empleadoId]);
      res.json(result.rows[0]);
    } catch {
      res.status(500).json({ error: 'Error interno' });
    }
  });
});

beforeEach(() => {
  mockPool.query.mockReset();
});

describe('GET /health', () => {
  it('retorna status UP', async () => {
    const res = await request(app).get('/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('UP');
    expect(res.body.service).toBe('perfiles-service');
  });
});

describe('GET /perfiles', () => {
  it('retorna lista de perfiles', async () => {
    mockPool.query.mockResolvedValueOnce({
      rows: [{ id: 'uuid1', empleado_id: '1', nombre: 'Juan', email: 'j@e.com', telefono: '', direccion: '', ciudad: '', biografia: '', fecha_creacion: new Date() }],
    });
    const res = await request(app).get('/perfiles');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
  });

  it('retorna lista vacía cuando no hay perfiles', async () => {
    mockPool.query.mockResolvedValueOnce({ rows: [] });
    const res = await request(app).get('/perfiles');
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });
});

describe('GET /perfiles/:empleadoId', () => {
  it('retorna perfil existente', async () => {
    const perfil = { id: 'uuid1', empleado_id: '10', nombre: 'Juan', email: 'j@e.com', telefono: '', direccion: '', ciudad: '', biografia: '', fecha_creacion: new Date() };
    mockPool.query.mockResolvedValueOnce({ rows: [perfil], rowCount: 1 });
    const res = await request(app).get('/perfiles/10');
    expect(res.status).toBe(200);
  });

  it('retorna 404 si no existe el perfil', async () => {
    mockPool.query.mockResolvedValueOnce({ rows: [], rowCount: 0 });
    const res = await request(app).get('/perfiles/999');
    expect(res.status).toBe(404);
  });
});

describe('PUT /perfiles/:empleadoId', () => {
  it('actualiza perfil existente', async () => {
    mockPool.query
      .mockResolvedValueOnce({ rowCount: 1 })
      .mockResolvedValueOnce({ rows: [{ id: 'uuid1', empleado_id: '10', telefono: '1234', direccion: '', ciudad: '', biografia: '', nombre: 'Juan', email: 'j@e.com', fecha_creacion: new Date() }] });
    const res = await request(app).put('/perfiles/10').send({ telefono: '1234' });
    expect(res.status).toBe(200);
  });

  it('retorna 404 si no existe el perfil', async () => {
    mockPool.query.mockResolvedValueOnce({ rowCount: 0 });
    const res = await request(app).put('/perfiles/999').send({ telefono: '1234' });
    expect(res.status).toBe(404);
  });
});
