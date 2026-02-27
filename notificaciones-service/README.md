# 🔔 Notificaciones Service

Microservicio de notificaciones del sistema. Implementado en **Node.js** con **Express** y documentación **OpenAPI** con Swagger UI Express.

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Node.js 18 |
| Framework | Express.js 4 |
| OpenAPI | swagger-jsdoc + swagger-ui-express |
| Logging | winston (JSON format) |
| ID único | uuid v4 |
| Testing | Jest + supertest |
| Almacenamiento | En memoria (in-memory) |
| Dockerfile | Multi-stage (Alpine) |

## 📁 Estructura

```
notificaciones-service/
├── src/
│   ├── index.js       # Servidor Express + endpoints + Swagger config
│   └── swagger.js     # Módulo de configuración Swagger
├── package.json
├── Dockerfile         # Multi-stage build
├── .dockerignore
└── README.md
```

## 🚀 Endpoints

| Método | Ruta | Descripción | Códigos |
|--------|------|-------------|---------|
| GET | `/health` | Health check con métricas | 200, 503 |
| POST | `/notificaciones` | Registrar notificación | 201, 400, 500 |
| GET | `/notificaciones` | Listar notificaciones | 200, 500 |
| GET | `/notificaciones/:id` | Obtener por UUID | 200, 404, 500 |

### Health Check Detallado

El endpoint `/health` retorna métricas del sistema:

```json
{
  "status": "healthy",
  "service": "notificaciones-service",
  "uptime": 3600.5,
  "memory": {
    "used_mb": "45.23",
    "total_mb": "512.00",
    "percent": "8.83"
  }
}
```

**Estado**: `healthy` si uso de memoria < 80%, `degraded` si ≥ 80%

## 📋 Tipos de Notificación

| Tipo | Descripción |
|------|-------------|
| `BIENVENIDA` | Al registrar un nuevo empleado |
| `ACTUALIZACION` | Cambios en datos de empleados |
| `ALERTA` | Eventos críticos del sistema |

## 📖 Documentación OpenAPI

- **Swagger UI**: `http://localhost:8082/api-docs`
- **JSON spec**: `http://localhost:8082/api-docs.json`

## 🐳 Docker

```bash
docker build -t notificaciones-service .

docker run -p 8082:3000 \
  -e PORT=3000 \
  -e NODE_ENV=production \
  notificaciones-service
```

## 🔌 Variables de Entorno

| Variable | Default | Descripción | Requerido |
|----------|---------|-------------|-----------|
| `PORT` | `3000` | Puerto del servidor | ❌ No |
| `NODE_ENV` | `development` | Entorno (`production` / `development`) | ❌ No |
| `LOG_LEVEL` | `info` | Nivel de logging (error, warn, info, debug) | ❌ No |

## 📊 JSON Logging

El servicio utiliza **winston** para generar logs en formato JSON estructurado:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "info",
  "message": "Notificación creada",
  "notificacion_id": "550e8400-e29b-41d4-a716-446655440000",
  "tipo": "BIENVENIDA",
  "destinatario": "juan@empresa.com"
}
```

Niveles de log configurados:
- **Production**: `info` (INFO, WARN, ERROR)
- **Development**: `debug` (DEBUG, INFO, WARN, ERROR)

## 🧪 Testing

### Ejecutar tests

```bash
# Instalar dependencias
npm install

# Ejecutar tests con coverage
npm test

# Ver coverage en HTML
open coverage/index.html
```

### Tests implementados

El servicio incluye **tests de integración con Jest + supertest**:

- ✅ Health check con métricas de memoria
- ✅ Creación de notificaciones (success + validation errors)
- ✅ Validación de tipos (BIENVENIDA, ACTUALIZACION, ALERTA)
- ✅ Listado de notificaciones
- ✅ Búsqueda por ID (found + not found)
- ✅ Validación de campos requeridos

**Ejemplo de test**:
```javascript
it('debe crear una notificación de BIENVENIDA exitosamente', async () => {
  const response = await request(app)
    .post('/notificaciones')
    .send({
      tipo: 'BIENVENIDA',
      destinatario: 'juan@empresa.com',
      mensaje: 'Bienvenido al equipo'
    })
    .expect(201);

  expect(response.body.tipo).toBe('BIENVENIDA');
  expect(response.body.estado).toBe('ENVIADO');
});
```

## 🔧 Pruebas rápidas con curl

```bash
# Health check con métricas
curl http://localhost:3000/health

# Crear notificación de BIENVENIDA
curl -X POST http://localhost:3000/notificaciones \
  -H "Content-Type: application/json" \
  -d '{"tipo":"BIENVENIDA","destinatario":"juan@empresa.com","mensaje":"Bienvenido al equipo, Juan Pérez"}'

# Crear notificación de ACTUALIZACION
curl -X POST http://localhost:3000/notificaciones \
  -H "Content-Type: application/json" \
  -d '{"tipo":"ACTUALIZACION","destinatario":"admin@empresa.com","mensaje":"Se actualizó el empleado E001"}'

# Crear notificación de ALERTA
curl -X POST http://localhost:3000/notificaciones \
  -H "Content-Type: application/json" \
  -d '{"tipo":"ALERTA","destinatario":"soporte@empresa.com","mensaje":"Error crítico en el sistema"}'

# Listar notificaciones
curl http://localhost:3000/notificaciones

# Obtener por UUID (reemplazar con UUID real del paso anterior)
curl http://localhost:3000/notificaciones/550e8400-e29b-41d4-a716-446655440000

# Error esperado: tipo inválido (HTTP 400)
curl -X POST http://localhost:3000/notificaciones \
  -H "Content-Type: application/json" \
  -d '{"tipo":"INVALIDO","destinatario":"test@empresa.com","mensaje":"Test"}'

# Error esperado: campos faltantes (HTTP 400)
curl -X POST http://localhost:3000/notificaciones \
  -H "Content-Type: application/json" \
  -d '{"tipo":"BIENVENIDA"}'
```

> ⚠️ **Nota**: El almacenamiento es en memoria. Al reiniciar el servicio los datos se pierden (por diseño, simula un bus de eventos).
