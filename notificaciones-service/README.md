# 🔔 Notificaciones Service

Microservicio de notificaciones del sistema. Implementado en **Node.js** con **Express** y documentación **OpenAPI** con Swagger UI Express.

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Node.js 18 |
| Framework | Express.js 4 |
| OpenAPI | swagger-jsdoc + swagger-ui-express |
| ID único | uuid v4 |
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
| GET | `/` | Health check | 200 |
| POST | `/notificaciones` | Registrar notificación | 201, 400, 500 |
| GET | `/notificaciones` | Listar notificaciones | 200, 500 |
| GET | `/notificaciones/:id` | Obtener por UUID | 200, 404, 500 |

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

| Variable | Default | Descripción |
|----------|---------|-------------|
| `PORT` | `3000` | Puerto del servidor |
| `NODE_ENV` | — | Entorno (`production` / `development`) |

## 🧪 Pruebas rápidas

```bash
# Crear notificación
curl -X POST http://localhost:8082/notificaciones \
  -H "Content-Type: application/json" \
  -d '{"tipo":"BIENVENIDA","destinatario":"juan@empresa.com","mensaje":"Bienvenido al equipo, Juan Pérez"}'

# Listar notificaciones
curl http://localhost:8082/notificaciones

# Obtener por UUID (reemplazar con UUID real del paso anterior)
curl http://localhost:8082/notificaciones/550e8400-e29b-41d4-a716-446655440000
```

> ⚠️ **Nota**: El almacenamiento es en memoria. Al reiniciar el servicio los datos se pierden (por diseño, simula un bus de eventos).
