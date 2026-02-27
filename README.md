# 🐳 Sistema de Microservicios — Gestión de Personas

Sistema de microservicios para la gestión de empleados y departamentos, implementado con **4 lenguajes de programación** distintos y orquestado con **Docker Compose**.

## 🗺️ Arquitectura

```
🌐 Cliente HTTP (curl / Postman / Bruno)
            │
            ├── POST/GET :8080 ──────────────────────┐
            ├── POST/GET :8081 ──────────────────────┤
            ├── POST/GET :8082 ──────────────────────┤
            └── GET :8083 ───────────────────────────┘
                                                     │
                        🐳 Docker Network (microservices-network)
            ┌───────────────────────────────────────────────────────┐
            │                                                       │
            │  👥 empleados-service    🏢 departamentos-service     │
            │     (Python/FastAPI)        (Java/Spring Boot)        │
            │          :8080                   :8081                │
            │          │  │ HTTP REST           │                   │
            │          │  └── valida dept ──────┘                   │
            │          │                                            │
            │  🔔 notificaciones-service  📊 reportes-service       │
            │     (Node.js/Express)          (Go/net-http)          │
            │          :8082                   :8083                │
            │                                                       │
            └───────────────────────────────────────────────────────┘
                         │                    │
              🗄️ database-empleados  🗄️ database-departamentos
              (PostgreSQL :5432)     (PostgreSQL :5433)
                         │                    │
               💾 vol-empleados        💾 vol-departamentos
```

## 📦 Microservicios

| Servicio | Lenguaje | Puerto | Base de Datos | Swagger UI |
|----------|----------|--------|---------------|------------|
| `empleados-service` | Python 3.11 / FastAPI | :8000 | PostgreSQL (empleadosdb) | http://localhost:8000/docs |
| `departamentos-service` | Java 17 / Spring Boot 3 | :8080 | PostgreSQL (departamentosdb) | http://localhost:8080/swagger-ui.html |
| `notificaciones-service` | Node.js 18 / Express | :3000 | In-memory | http://localhost:3000/api-docs |
| `reportes-service` | Go 1.21 / net/http | :3000 (Go) | - | http://localhost:3000/docs/index.html |

### Funcionalidades por Servicio

#### 👥 empleados-service (Python)
- **CRUD completo**: POST, GET, PUT, DELETE con soft delete
- **Persistencia**: PostgreSQL con SQLAlchemy ORM
- **Validación inter-servicios**: Valida existencia de departamentos con reintentos (tenacity)
- **Paginación y filtros**: `?pagina=1&por_pagina=10&departamento_id=IT&activo=true`
- **Validación**: Email válido con pydantic, campos requeridos
- **Logging**: JSON estructurado con python-json-logger
- **Health check**: `/health` con estado de DB y métricas

#### 🏢 departamentos-service (Java)
- **CRUD completo**: POST, GET, PUT, DELETE
- **Arquitectura**: Service Layer con @Transactional
- **Persistencia**: PostgreSQL con Spring Data JPA / Hibernate
- **Observabilidad**: Spring Boot Actuator (`/actuator/health`, `/actuator/metrics`)
- **Logging**: JSON estructurado con logstash-logback-encoder
- **Testing**: JUnit 5 + Mockito + AssertJ

#### 🔔 notificaciones-service (Node.js)
- **Tipos**: BIENVENIDA, ACTUALIZACION, ALERTA
- **Almacenamiento**: In-memory (simula bus de eventos)
- **Logging**: winston con formato JSON
- **Health check**: `/health` con métricas de memoria y uptime
- **Testing**: Jest + supertest

#### 📊 reportes-service (Go)
- **Agregación**: Consulta empleados y departamentos en tiempo real
- **Logging**: uber/zap con JSON estructurado
- **Health check**: `/health` con conectividad a servicios dependientes
- **Testing**: Go testing package (stdlib)

## ✅ Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (incluye Docker Compose v2)
- Git
- (Opcional) Make, curl, o Postman para probar los endpoints

## ⚙️ Configuración

### 1. Variables de Entorno

El proyecto usa variables de entorno para configuración sensible. Copia el archivo de ejemplo:

```bash
cp .env.example .env
```

El archivo `.env` contiene configuración para:
- Credenciales de bases de datos (usuarios, contraseñas)
- URLs de servicios
- Puertos
- Niveles de logging

**Importante**: El archivo `.env` está en `.gitignore` para proteger credenciales.

### 2. Estructura de Configuración

```
microservicios/
├── .env                    # Variables de entorno (NO commitear)
├── .env.example            # Template de configuración
├── .gitignore              # Protege .env y secretos
└── docker-compose.yml      # Usa ${VAR:-default} syntax
```

## 🚀 Despliegue rápido

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd microservicios

# 2. Configurar variables de entorno
cp .env.example .env
# (Opcional) Editar .env con tus credenciales

# 3. Construir e iniciar todos los servicios
docker-compose up --build

# 4. Verificar que todos los servicios están corriendo
docker-compose ps
```

Los servicios estarán disponibles después de ~30-60 segundos (tiempo de inicio de las bases de datos).

### Health Checks

Verificar el estado de todos los servicios:

```bash
# Empleados (Python)
curl http://localhost:8000/health

# Departamentos (Java)
curl http://localhost:8080/actuator/health

# Notificaciones (Node.js)
curl http://localhost:3000/health

# Reportes (Go)
curl http://localhost:3000/health
```

## 🧪 Flujo de prueba completo

### 1. Verificar que todos los servicios están saludables

```bash
curl http://localhost:8000/health      # Empleados (Python)
curl http://localhost:8080/actuator/health  # Departamentos (Java)
curl http://localhost:3000/health      # Notificaciones (Node.js)
curl http://localhost:3000/health      # Reportes (Go) - puerto configurado
```

### 2. Crear un departamento

```bash
curl -X POST http://localhost:8080/departamentos \
  -H "Content-Type: application/json" \
  -d '{"id": "IT", "nombre": "Tecnología", "descripcion": "Departamento de TI"}'
```
**Respuesta esperada**: `HTTP 201` con el departamento creado.

### 3. Crear varios empleados asociados al departamento

```bash
# Empleado 1
curl -X POST http://localhost:8000/empleados \
  -H "Content-Type: application/json" \
  -d '{"id": "E001", "nombre": "Juan Pérez", "email": "juan@empresa.com", "departamentoId": "IT", "fechaIngreso": "2024-01-15"}'

# Empleado 2
curl -X POST http://localhost:8000/empleados \
  -H "Content-Type: application/json" \
  -d '{"id": "E002", "nombre": "María García", "email": "maria@empresa.com", "departamentoId": "IT", "fechaIngreso": "2024-01-20"}'
```
**Respuesta esperada**: `HTTP 201` con cada empleado creado.

### 4. Listar empleados con paginación

```bash
# Primera página (10 resultados)
curl "http://localhost:8000/empleados?pagina=1&por_pagina=10"

# Filtrar por departamento
curl "http://localhost:8000/empleados?departamento_id=IT"

# Solo empleados activos (default)
curl "http://localhost:8000/empleados?activo=true"
```

### 5. Actualizar un empleado

```bash
curl -X PUT http://localhost:8000/empleados/E001 \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Juan Carlos Pérez", "email": "juanc@empresa.com"}'
```
**Respuesta esperada**: `HTTP 200` con empleado actualizado.

### 6. Verificar que el empleado existe

```bash
curl http://localhost:8000/empleados/E001
```
**Respuesta esperada**: `HTTP 200` con datos del empleado actualizado.

### 7. Intentar crear empleado con departamento inexistente (debe fallar)

```bash
curl -X POST http://localhost:8000/empleados \
  -H "Content-Type: application/json" \
  -d '{"id": "E003", "nombre": "Ana García", "email": "ana@empresa.com", "departamentoId": "INEX", "fechaIngreso": "2024-01-15"}'
```
**Respuesta esperada**: `HTTP 400` — "El departamento con ID 'INEX' no existe."

### 8. Registrar notificaciones

```bash
# Notificación de bienvenida
curl -X POST http://localhost:3000/notificaciones \
  -H "Content-Type: application/json" \
  -d '{"tipo": "BIENVENIDA", "destinatario": "juan@empresa.com", "mensaje": "Bienvenido al equipo, Juan Pérez"}'

# Notificación de actualización
curl -X POST http://localhost:3000/notificaciones \
  -H "Content-Type: application/json" \
  -d '{"tipo": "ACTUALIZACION", "destinatario": "admin@empresa.com", "mensaje": "Se actualizó el empleado E001"}'

# Listar notificaciones
curl http://localhost:3000/notificaciones
```

### 9. Ver reportes del sistema

```bash
curl http://localhost:3000/reportes/resumen
```
**Respuesta esperada**: `HTTP 200` con conteo de empleados (2) y departamentos (1).

### 10. Soft delete de un empleado

```bash
# Eliminar (marca activo=false)
curl -X DELETE http://localhost:8000/empleados/E002

# Verificar que no aparece en listado por defecto
curl "http://localhost:8000/empleados?activo=true"

# Incluir empleados inactivos
curl "http://localhost:8000/empleados?activo=false"
```

### 11. Actualizar un departamento

```bash
curl -X PUT http://localhost:8080/departamentos/IT \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Tecnología e Innovación", "descripcion": "Desarrollo de software y soporte técnico"}'
```

### 12. Verificar persistencia

```bash
# Reiniciar contenedores (sin eliminar volúmenes)
docker-compose restart

# Esperar ~30 segundos para que levanten

# Verificar que los datos persisten
curl http://localhost:8000/empleados/E001
curl http://localhost:8080/departamentos/IT
```

## 🛑 Comandos útiles

### Gestión de contenedores

```bash
# Detener todos los servicios
docker-compose down

# Detener y eliminar volúmenes (borra datos)
docker-compose down -v

# Ver estado de todos los servicios
docker-compose ps

# Reconstruir un solo servicio
docker-compose up --build departamentos-service

# Reiniciar un servicio específico
docker-compose restart empleados-service

# Ver recursos utilizados
docker stats
```

### Logs y debugging

```bash
# Ver logs de un servicio específico (modo follow)
docker-compose logs -f empleados-service

# Ver logs de todos los servicios
docker-compose logs -f

# Ver últimas 100 líneas de logs
docker-compose logs --tail=100 departamentos-service

# Ver logs con timestamps
docker-compose logs -t notificaciones-service

# Logs de múltiples servicios
docker-compose logs -f empleados-service departamentos-service
```

### Acceso a contenedores

```bash
# Ejecutar shell en un contenedor
docker-compose exec empleados-service sh
docker-compose exec departamentos-service sh
docker-compose exec database-empleados psql -U postgres -d empleadosdb

# Ver variables de entorno de un servicio
docker-compose exec empleados-service env

# Inspeccionar red
docker network inspect microservicios_microservices-network
```

### Testing

```bash
# Ejecutar tests de Python (empleados)
docker-compose exec empleados-service pytest tests/ -v

# Ejecutar tests de Java (departamentos)
docker-compose exec departamentos-service mvn test

# Ejecutar tests de Node.js (notificaciones)
docker-compose exec notificaciones-service npm test

# Ejecutar tests de Go (reportes)
docker-compose exec reportes-service go test -v
```

## 📂 Estructura del proyecto

```
microservicios/
├── docker-compose.yml
├── README.md                              ← Este archivo
├── empleados-service/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── database.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── departamentos-service/
│   ├── src/main/java/com/empresa/departamentos/
│   │   ├── DepartamentosServiceApplication.java
│   │   ├── model/Departamento.java
│   │   ├── dto/DepartamentoRequest.java
│   │   ├── dto/DepartamentoResponse.java
│   │   ├── repository/DepartamentoRepository.java
│   │   ├── controller/DepartamentoController.java
│   │   ├── config/OpenApiConfig.java
│   │   └── exception/GlobalExceptionHandler.java
│   ├── src/main/resources/application.properties
│   ├── pom.xml
│   ├── Dockerfile                         ← Multi-stage (Maven → JRE)
│   └── README.md
├── notificaciones-service/
│   ├── src/
│   │   └── index.js
│   ├── package.json
│   ├── Dockerfile                         ← Multi-stage build
│   └── README.md
└── reportes-service/
    ├── main.go
    ├── docs/
    │   └── docs.go
    ├── go.mod
    ├── go.sum
    ├── Dockerfile                         ← Multi-stage build
    └── README.md
```

## 🔒 Características de seguridad y resiliencia

### Seguridad
- ✅ **Usuarios no-root**: Todos los contenedores ejecutan con usuarios no privilegiados
- ✅ **Secrets management**: Variables de entorno con .env (no commiteado)
- ✅ **Validación de entrada**: Pydantic (Python), Jakarta Validation (Java), validación manual (Node.js, Go)
- ✅ **Multi-stage builds**: Imágenes optimizadas sin herramientas de build en producción

### Resiliencia
- ✅ **Health checks**: Todos los servicios exponen `/health` con métricas detalladas
- ✅ **Database health**: Verificación de conectividad a PostgreSQL
- ✅ **Reintentos automáticos**: tenacity en Python (3 intentos, exponential backoff 1s→2s→4s)
- ✅ **Timeouts**: 5s en llamadas HTTP, 2s en health checks
- ✅ **Graceful degradation**: Servicio de reportes reporta estado degradado si dependencias fallan
- ✅ **Soft delete**: Empleados marcados como inactivos en lugar de eliminación física

### Observabilidad
- ✅ **JSON logging**: Logs estructurados en todos los servicios
  - Python: python-json-logger
  - Java: logstash-logback-encoder
  - Node.js: winston
  - Go: uber/zap
- ✅ **Métricas**: Spring Boot Actuator en Java, métricas de memoria en Node.js
- ✅ **Health checks**: `/health` endpoints con detalles de dependencias
- ✅ **OpenAPI/Swagger**: Documentación interactiva en todos los servicios

### Escalabilidad (Docker Compose)
- ✅ **Resource limits**: CPU y RAM configurados por servicio  
  - empleados-service: 512MB RAM, 1 CPU
  - departamentos-service: 768MB RAM, 1.5 CPU
  - notificaciones-service: 256MB RAM, 0.5 CPU
  - reportes-service: 384MB RAM, 0.75 CPU
  - databases: 512MB RAM, 1 CPU cada una
- ✅ **Restart policies**: `on-failure:5` para servicios, `unless-stopped` para bases de datos
- ✅ **Connection pooling**: SQLAlchemy (pool_size=10, max_overflow=5), HikariCP (Java)

## 🧪 Testing

Cada servicio incluye tests automatizados con coverage reporting.

### Ejecutar tests por servicio

```bash
# Python (empleados-service)
cd empleados-service
pytest tests/ --cov=app --cov-report=html
# Ver coverage: open htmlcov/index.html

# Java (departamentos-service)
cd departamentos-service
mvn test jacoco:report
# Ver coverage: open target/site/jacoco/index.html

# Node.js (notificaciones-service)
cd notificaciones-service
npm test
# Ver coverage: open coverage/index.html

# Go (reportes-service)
cd reportes-service
go test -cover -coverprofile=coverage.out
go tool cover -html=coverage.out
```

### Tests implementados

| Servicio | Framework | Casos de prueba |
|----------|-----------|-----------------|
| empleados-service | pytest + pytest-asyncio | 12+ tests (validación departamentos, CRUD, soft delete, email validation) |
| departamentos-service | JUnit 5 + Mockito | 15+ tests (Service Layer completo con mocks) |
| notificaciones-service | Jest + supertest | 15+ tests (endpoints HTTP, validaciones, health check) |
| reportes-service | Go testing | 10+ tests (handlers, conectividad, configuración) |
