# 📊 Reportes Service

Microservicio de reportes y estadísticas del sistema. Implementado en **Go** con `net/http` y documentación **OpenAPI** con Swagger generado por `swaggo`.

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Go 1.21 |
| Router | gorilla/mux |
| OpenAPI | swaggo/swag + swaggo/http-swagger |
| HTTP Client | net/http (stdlib) con timeout 5s |
| Dockerfile | Multi-stage (golang:alpine → alpine) |

## 📁 Estructura

```
reportes-service/
├── main.go            # Servidor Go + handlers + anotaciones Swagger
├── docs/
│   └── docs.go        # Generado automáticamente por swag init
├── go.mod
├── go.sum
├── Dockerfile         # Multi-stage build
├── .dockerignore
└── README.md
```

## 🚀 Endpoints

| Método | Ruta | Descripción | Códigos |
|--------|------|-------------|---------|
| GET | `/` | Health check | 200 |
| GET | `/reportes/resumen` | Resumen del sistema | 200, 500 |
| GET | `/docs/*` | Swagger UI | 200 |

## 📊 Resumen del Sistema (`/reportes/resumen`)

Consulta en tiempo real los servicios de empleados y departamentos para retornar:
- Total de empleados registrados
- Total de departamentos registrados
- Fecha/hora de la consulta
- URLs de los servicios fuente

## 📖 Documentación OpenAPI

- **Swagger UI**: `http://localhost:8083/docs/index.html`
- **JSON spec**: `http://localhost:8083/docs/doc.json`

## 🐳 Docker

```bash
# El Dockerfile genera los docs de Swagger automáticamente durante el build
docker build -t reportes-service .

docker run -p 8083:3000 \
  -e PORT=3000 \
  -e EMPLEADOS_SERVICE_URL=http://empleados-service:8000 \
  -e DEPARTAMENTOS_SERVICE_URL=http://departamentos-service:8000 \
  reportes-service
```

## 🔌 Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `PORT` | `3000` | Puerto del servidor |
| `EMPLEADOS_SERVICE_URL` | `http://empleados-service:8000` | URL del servicio de empleados |
| `DEPARTAMENTOS_SERVICE_URL` | `http://departamentos-service:8000` | URL del servicio de departamentos |

## 🧪 Pruebas rápidas

```bash
# Health check
curl http://localhost:8083/

# Resumen del sistema (requiere los otros servicios corriendo)
curl http://localhost:8083/reportes/resumen
```

## 🔨 Desarrollo local (requiere Go 1.21+)

```bash
# Instalar swag CLI
go install github.com/swaggo/swag/cmd/swag@latest

# Generar documentación Swagger
swag init

# Descargar dependencias
go mod tidy

# Ejecutar
go run main.go
```
