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

| Servicio | Lenguaje | Puerto | Swagger UI |
|----------|----------|--------|------------|
| `empleados-service` | Python 3.11 / FastAPI | :8080 | http://localhost:8080/docs |
| `departamentos-service` | Java 17 / Spring Boot 3 | :8081 | http://localhost:8081/docs |
| `notificaciones-service` | Node.js 18 / Express | :8082 | http://localhost:8082/api-docs |
| `reportes-service` | Go 1.21 / net/http | :8083 | http://localhost:8083/docs/index.html |

## ✅ Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (incluye Docker Compose v2)
- Git

## 🚀 Despliegue rápido

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd microservicios

# 2. Construir e iniciar todos los servicios
docker-compose up --build

# 3. Verificar que todos los servicios están corriendo
docker-compose ps
```

Los servicios estarán disponibles después de ~30 segundos (tiempo de inicio de las bases de datos).

## 🧪 Flujo de prueba completo

### 1. Crear un departamento

```bash
curl -X POST http://localhost:8081/departamentos \
  -H "Content-Type: application/json" \
  -d '{"id": "IT", "nombre": "Tecnología", "descripcion": "Departamento de TI"}'
```
**Respuesta esperada**: `HTTP 201` con el departamento creado.

### 2. Crear un empleado asociado al departamento

```bash
curl -X POST http://localhost:8080/empleados \
  -H "Content-Type: application/json" \
  -d '{"id": "E001", "nombre": "Juan Pérez", "email": "juan@empresa.com", "departamentoId": "IT", "fechaIngreso": "2024-01-15"}'
```
**Respuesta esperada**: `HTTP 201` con el empleado creado.

### 3. Verificar que el empleado existe

```bash
curl http://localhost:8080/empleados/E001
```
**Respuesta esperada**: `HTTP 200` con datos del empleado.

### 4. Intentar crear empleado con departamento inexistente (debe fallar)

```bash
curl -X POST http://localhost:8080/empleados \
  -H "Content-Type: application/json" \
  -d '{"id": "E002", "nombre": "Ana García", "email": "ana@empresa.com", "departamentoId": "INEX", "fechaIngreso": "2024-01-15"}'
```
**Respuesta esperada**: `HTTP 400` — "El departamento con ID 'INEX' no existe."

### 5. Registrar una notificación

```bash
curl -X POST http://localhost:8082/notificaciones \
  -H "Content-Type: application/json" \
  -d '{"tipo": "BIENVENIDA", "destinatario": "juan@empresa.com", "mensaje": "Bienvenido al equipo, Juan Pérez"}'
```
**Respuesta esperada**: `HTTP 201` con notificación y UUID generado.

### 6. Ver reportes del sistema

```bash
curl http://localhost:8083/reportes/resumen
```
**Respuesta esperada**: `HTTP 200` con conteo de empleados y departamentos.

### 7. Verificar persistencia

```bash
# Reiniciar contenedores (sin eliminar volúmenes)
docker-compose restart

# Verificar que los datos persisten
curl http://localhost:8080/empleados/E001
curl http://localhost:8081/departamentos/IT
```

## 🛑 Comandos útiles

```bash
# Detener todos los servicios
docker-compose down

# Detener y eliminar volúmenes (borra datos)
docker-compose down -v

# Ver logs de un servicio específico
docker-compose logs -f empleados-service

# Reconstruir un solo servicio
docker-compose up --build empleados-service

# Ver estado de todos los servicios
docker-compose ps
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

- ✅ Usuarios no-root en todos los contenedores
- ✅ Healthchecks en las bases de datos PostgreSQL
- ✅ Reintentos automáticos (tenacity) en empleados-service
- ✅ Timeouts en comunicación entre servicios
- ✅ Validación de datos con Pydantic / Jakarta Validation
- ✅ Multi-stage builds para imágenes más pequeñas y seguras
