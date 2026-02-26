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
| GET | `/` | Health check | 200 |
| POST | `/empleados` | Registrar empleado | 201, 400, 422, 500 |
| GET | `/empleados` | Listar empleados | 200, 500 |
| GET | `/empleados/{id}` | Obtener por ID | 200, 404, 500 |

## 🔄 Patrones de Resiliencia

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

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | Cadena de conexión PostgreSQL | `postgresql://user:pass@host:5432/db` |

## 🧪 Pruebas rápidas

```bash
# Crear empleado (requiere departamento IT existente)
curl -X POST http://localhost:8080/empleados \
  -H "Content-Type: application/json" \
  -d '{"id":"E001","nombre":"Juan Pérez","email":"juan@empresa.com","departamentoId":"IT","fechaIngreso":"2024-01-15"}'

# Obtener por ID
curl http://localhost:8080/empleados/E001

# Error esperado: departamento inexistente (HTTP 400)
curl -X POST http://localhost:8080/empleados \
  -H "Content-Type: application/json" \
  -d '{"id":"E002","nombre":"Ana García","email":"ana@empresa.com","departamentoId":"INEX","fechaIngreso":"2024-01-15"}'
```
