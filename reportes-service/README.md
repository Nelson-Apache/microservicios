# 📊 Reportes Service

Microservicio de reportes y estadísticas del sistema. Implementado en **Go** con `net/http` y documentación **OpenAPI** con Swagger generado por `swaggo`.

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Go 1.21 |
| Router | net/http (stdlib) |
| Logging | uber/zap (JSON format) |
| OpenAPI | swaggo/swag + swaggo/http-swagger |
| HTTP Client | net/http (stdlib) con timeout 5s |
| Testing | Go testing package (stdlib) |
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
| GET | `/` | Health check básico | 200 |
| GET | `/health` | Health check con conectividad | 200, 503 |
| GET | `/reportes/resumen` | Resumen del sistema | 200, 500 |
| GET | `/docs/*` | Swagger UI | 200 |

### Health Check Detallado (`/health`)

Verifica la conectividad con los servicios dependientes:

```json
{
  "status": "healthy",
  "service": "reportes-service",
  "version": "1.0.0",
  "checks": {
    "empleados_service": "ok",
    "departamentos_service": "ok"
  }
}
```

**Estado**: `healthy` (200) si todos los servicios responden, `degraded` (503) si alguno falla.

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

| Variable | Default | Descripción | Requerido |
|----------|---------|-------------|-----------|
| `PORT` | `3000` | Puerto del servidor | ❌ No |
| `EMPLEADOS_SERVICE_URL` | `http://empleados-service:8000` | URL del servicio de empleados | ✅ Sí |
| `DEPARTAMENTOS_SERVICE_URL` | `http://departamentos-service:8080` | URL del servicio de departamentos | ✅ Sí |

## 📊 JSON Logging

El servicio utiliza **uber/zap** para generar logs estructurados en formato JSON:

```json
{
  "level": "info",
  "ts": 1705320000.123,
  "caller": "main.go:123",
  "msg": "Resumen generado exitosamente",
  "event": "resumen_created",
  "total_empleados": 15,
  "total_departamentos": 3
}
```

Configuración de logger:
- **Production mode**: JSON estructurado con sampling
- **Events tracked**: server_started, resumen_request, empleados_fetch_error, departamentos_fetch_error

## 🧪 Testing

### Ejecutar tests

```bash
# Ejecutar todos los tests
go test -v

# Ejecutar con coverage
go test -cover

# Ver reporte de coverage detallado
go test -coverprofile=coverage.out
go tool cover -html=coverage.out

# Ejecutar tests específicos
go test -v -run TestResumenHandler
```

### Tests implementados

El servicio incluye **tests unitarios con Go testing package**:

- ✅ **TestHealthHandler**: Health check básico
- ✅ **TestDetailedHealthHandler**: Conectividad con servicios (healthy + degraded)
- ✅ **TestResumenHandler**: Generación de resumen (success + error cases)
- ✅ **TestGetEmpleadosURL**: Variables de entorno (custom + default)
- ✅ **TestGetDepartamentosURL**: Variables de entorno (custom + default)
- ✅ **TestTestConnection**: Validación de conectividad

**Ejemplo de test**:
```go
func TestResumenHandler(t *testing.T) {
    t.Run("debe generar resumen correctamente", func(t *testing.T) {
        // Mock servers
        empleadosServer := httptest.NewServer(...)
        departamentosServer := httptest.NewServer(...)
        
        // Test request
        req := httptest.NewRequest(http.MethodGet, "/reportes/resumen", nil)
        rec := httptest.NewRecorder()
        
        resumenHandler(rec, req)
        
        if rec.Code != http.StatusOK {
            t.Errorf("esperaba 200, obtuvo %d", rec.Code)
        }
    })
}
```

## 🔧 Pruebas rápidas con curl

```bash
# Health check básico
curl http://localhost:3000/

# Health check con conectividad
curl http://localhost:3000/health

# Resumen del sistema (requiere los otros servicios corriendo)
curl http://localhost:3000/reportes/resumen

# Ver documentación Swagger
open http://localhost:3000/docs/index.html
```

**Ejemplo de respuesta del resumen**:
```json
{
  "totalDepartamentos": 3,
  "totalEmpleados": 15,
  "fechaConsulta": "2024-01-15T10:30:00Z",
  "fuenteEmpleados": "http://empleados-service:8000",
  "fuenteDepartamentos": "http://departamentos-service:8080"
}
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
