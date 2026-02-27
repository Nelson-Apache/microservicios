# 👥 Empleados Service

Microservicio para la gestión de empleados. Implementado en **Python** con **FastAPI** y persistencia en **PostgreSQL**. Incluye patrones de resiliencia para la comunicación con el servicio de departamentos.

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11 |
| Framework | FastAPI |
| Base de datos | PostgreSQL 15 |
| ORM | SQLAlchemy |
| HTTP Client | httpx (async) |
| Resiliencia | tenacity (retries + backoff) |
| Documentación | OpenAPI 3.0 (nativa de FastAPI) |

## 📁 Estructura

```
empleados-service/
├── app/
│   ├── main.py        # Endpoints FastAPI + lógica de negocio
│   ├── models.py      # Modelo SQLAlchemy (tabla empleados)
│   ├── schemas.py     # Esquemas Pydantic (validación)
│   ├── database.py    # Configuración de conexión a BD
│   └── __init__.py
├── Dockerfile
└── requirements.txt
```

## 🚀 Endpoints

| Método | Ruta | Descripción | Códigos |
|--------|------|-------------|---------|
| GET | `/health` | Health check detallado (DB + metrics) | 200, 503 |
| POST | `/empleados` | Registrar empleado | 201, 400, 422, 500 |
| GET | `/empleados` | Listar empleados (con paginación y filtros) | 200, 500 |
| GET | `/empleados/{id}` | Obtener por ID | 200, 404, 500 |
| PUT | `/empleados/{id}` | Actualizar empleado | 200, 400, 404, 422, 500 |
| DELETE | `/empleados/{id}` | Eliminar empleado (soft delete) | 204, 404, 500 |

### Paginación y Filtros

El endpoint `GET /empleados` soporta los siguientes parámetros:
- `pagina` (default: 1): Número de página
- `por_pagina` (default: 10): Resultados por página
- `departamento_id`: Filtrar por departamento específico
- `activo` (default: true): Incluir solo empleados activos

**Ejemplo**:
```bash
GET /empleados?pagina=2&por_pagina=5&departamento_id=IT&activo=true
```

## 🔄 Patrones de Resiliencia

### Validación con Departamentos

- **Reintentos automáticos**: Hasta 3 intentos con espera exponencial (2s → 4s → 8s)
- **Timeout**: 5 segundos máximo por solicitud al servicio de departamentos
- **Validación previa**: Verifica existencia del departamento antes de crear empleado

## 📖 Documentación OpenAPI

- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`
- **JSON spec**: `http://localhost:8080/openapi.json`

## 🐳 Docker

```bash
docker build -t empleados-service .

docker run -p 8080:8000 \
  -e DATABASE_URL=postgresql://postgres:postgres@host:5432/empleadosdb \
  empleados-service
```

## 🔌 Variables de Entorno

| Variable | Descripción | Ejemplo | Requerido |
|----------|-------------|---------|-----------|
| `DATABASE_URL` | Cadena de conexión PostgreSQL | `postgresql://user:pass@host:5432/db` | ✅ Sí |
| `DEPARTAMENTOS_SERVICE_URL` | URL del servicio de departamentos | `http://departamentos-service:8080` | ✅ Sí |
| `LOG_LEVEL` | Nivel de logging | `INFO`, `DEBUG`, `WARNING`, `ERROR` | ❌ No (default: INFO) |

### Configuración de Pool de Conexiones

SQLAlchemy está configurado con:
- **Pool size**: 10 conexiones
- **Max overflow**: 5 conexiones adicionales
- **Pool timeout**: 30 segundos
- **Pool recycle**: 3600 segundos (1 hora)

## 📊 Logging

El servicio utiliza **JSON logging estructurado** con `python-json-logger`:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "message": "Empleado creado exitosamente",
  "empleado_id": "E001",
  "departamento_id": "IT"
}
```

## 🧪 Testing

### Ejecutar tests

```bash
# Instalar dependencias de testing
pip install -r requirements.txt

# Ejecutar todos los tests
pytest tests/ -v

# Ejecutar con coverage
pytest tests/ --cov=app --cov-report=html

# Ejecutar tests específicos
pytest tests/test_empleados.py::test_validar_departamento_existe_exitoso -v
```

### Tests incluidos

- ✅ Validación de existencia de departamentos
- ✅ Creación de empleados (success + error cases)
- ✅ Búsqueda y filtrado
- ✅ Actualización parcial
- ✅ Soft delete
- ✅ Validación de email con pydantic

## 🔧 Pruebas rápidas con curl

```bash
# Health check
curl http://localhost:8000/health

# Crear empleado (requiere departamento IT existente)
curl -X POST http://localhost:8000/empleados \
  -H "Content-Type: application/json" \
  -d '{"id":"E001","nombre":"Juan Pérez","email":"juan@empresa.com","departamentoId":"IT","fechaIngreso":"2024-01-15"}'

# Listar empleados con paginación
curl "http://localhost:8000/empleados?pagina=1&por_pagina=10"

# Filtrar empleados por departamento
curl "http://localhost:8000/empleados?departamento_id=IT"

# Obtener por ID
curl http://localhost:8000/empleados/E001

# Actualizar empleado
curl -X PUT http://localhost:8000/empleados/E001 \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Juan Carlos Pérez","email":"juanc@empresa.com"}'

# Eliminar empleado (soft delete - marca activo=false)
curl -X DELETE http://localhost:8000/empleados/E001

# Incluir empleados inactivos en la búsqueda
curl "http://localhost:8000/empleados?activo=false"

# Error esperado: departamento inexistente (HTTP 400)
curl -X POST http://localhost:8000/empleados \
  -H "Content-Type: application/json" \
  -d '{"id":"E002","nombre":"Ana García","email":"ana@empresa.com","departamentoId":"INEX","fechaIngreso":"2024-01-15"}'

# Error esperado: email inválido (HTTP 422)
curl -X POST http://localhost:8000/empleados \
  -H "Content-Type: application/json" \
  -d '{"id":"E003","nombre":"Carlos Lopez","email":"invalido","departamentoId":"IT","fechaIngreso":"2024-01-15"}'
```

## 🗑️ Soft Delete

El endpoint `DELETE /empleados/{id}` implementa **soft delete**:
- No elimina físicamente el registro de la base de datos
- Marca el campo `activo` como `false`
- Por defecto, `GET /empleados` solo retorna empleados activos
- Usar `?activo=false` para incluir empleados inactivos
