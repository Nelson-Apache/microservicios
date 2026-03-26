# Sistema de Microservicios — Gestión de Empleados y Departamentos

Sistema distribuido de onboarding y offboarding de empleados implementado con **5 lenguajes de programación**, orquestado con **Docker Compose**, con comunicación sincrónica (HTTP REST), asincrónica (RabbitMQ) y seguridad centralizada mediante **JWT**.

---

## Arquitectura General

```text
Cliente HTTP (Postman / curl / Swagger UI)
              │
              │  Todas las peticiones pasan por el Gateway
              ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway :8000                          │
│         Valida JWT · Verifica Rol · Enruta petición          │
└──────┬──────────────────────────────────────────────────────┘
       │                          │
       │  /auth/*  (sin JWT)      │  /empleados, /departamentos,
       ▼                          │  /notificaciones, /perfiles,
┌─────────────┐                   │  /reportes  (JWT requerido)
│ auth-service│                   ▼
│   :8085     │   ┌─────────────────────────────────────────┐
│  db-auth    │   │         Microservicios de negocio        │
└──────┬──────┘   │                                         │
       │          │  empleados-service   :8080 (Python)      │
       │ Consume  │  departamentos-service :8081 (Java)      │
       │ Publica  │  notificaciones-service :8082 (Node.js)  │
       │          │  reportes-service    :8083 (Go)           │
       │          │  perfiles-service    :8084 (Node.js)      │
       │          └──────────────────┬──────────────────────┘
       │                             │
       └──────────┐                  │
                  ▼                  ▼
         ┌─────────────────────────────────┐
         │     RabbitMQ Message Broker      │
         │   Exchange: rrhh_events (topic)  │
         │   :5672 (AMQP) · :15672 (Admin) │
         └─────────────────────────────────┘
```

### Flujo de eventos entre servicios

```text
empleados-service  ──publica──►  empleado.creado
                                 empleado.eliminado
                                        │
                     ┌──────────────────┼──────────────────┐
                     ▼                  ▼                   ▼
              notificaciones     perfiles-service     auth-service
               (BIENVENIDA/       (crear perfil/      (crear usuario /
               DESVINCULACION)    inactivar perfil)   inhabilitar usuario)
                                                           │
                                         publica──►  usuario.creado
                                         publica──►  usuario.recuperacion
                                                           │
                                                           ▼
                                                   notificaciones
                                                    (SEGURIDAD:
                                                   token de acceso)
```

---

## Servicios

| Servicio | Lenguaje | Puerto | Base de datos | Swagger UI |
| --- | --- | --- | --- | --- |
| `api-gateway` | Python / FastAPI | **8000** | — | <http://localhost:8000/docs> |
| `auth-service` | Python / FastAPI | 8085 | PostgreSQL (authdb) | <http://localhost:8085/docs> |
| `empleados-service` | Python / FastAPI | 8080 | PostgreSQL (empleadosdb) | <http://localhost:8080/docs> |
| `departamentos-service` | Java 17 / Spring Boot | 8081 | PostgreSQL (departamentosdb) | <http://localhost:8081/swagger-ui.html> |
| `notificaciones-service` | Node.js / Express | 8082 | PostgreSQL (notificacionesdb) | <http://localhost:8082/api-docs> |
| `reportes-service` | Go / net-http | 8083 | — | <http://localhost:8083/docs/index.html> |
| `perfiles-service` | Node.js / Express | 8084 | PostgreSQL (perfilesdb) | — |
| `rabbitmq` | RabbitMQ | 5672 / 15672 | — | <http://localhost:15672> |

> Nota: Los puertos individuales están expuestos para desarrollo y depuración. En uso normal, todas las peticiones deben ir a través del **API Gateway en :8000**.

---

## Seguridad JWT

### Estrategia de validación: API Gateway

Se eligió el patrón **API Gateway** sobre la alternativa de middleware por servicio por las siguientes razones:

- **Un único punto de control**: La validación del JWT vive en un solo lugar. Si se necesita cambiar el algoritmo de firma, la librería o la lógica de roles, solo se modifica el gateway.
- **Servicios desacoplados**: Los microservicios de negocio no conocen nada de autenticación. Reciben peticiones ya verificadas y se enfocan en su lógica de dominio.
- **Reducción de dependencias**: No fue necesario agregar librerías JWT a los servicios en Java, Go ni Node.js, reduciendo el tamaño de las imágenes y el riesgo de inconsistencias.
- **Simplicidad operativa**: Con interceptores por servicio, cada uno habría necesitado la misma `JWT_SECRET`, validación idéntica y manejo de errores duplicado en 4 lenguajes distintos.

### Clave secreta JWT

La clave está definida en `.env.example` con fines académicos:

```env
JWT_SECRET=changeme-super-secret-key-for-dev
```

Esta misma clave es inyectada via `docker-compose.yml` tanto al `auth-service` (que firma los tokens) como al `api-gateway` (que los verifica).

### Reglas de autorización (RBAC)

| Rol | Métodos permitidos | Respuesta si viola |
| --- | --- | --- |
| `ADMIN` | GET, POST, PUT, DELETE, PATCH | — |
| `USER` | Solo GET | `403 Forbidden` |
| Sin token | — | `401 Unauthorized` |
| Token inválido/expirado | — | `401 Unauthorized` |

### Tipos de token

**Token de acceso** (retornado por `/auth/login`):

```json
{
  "sub": "nombre_usuario",
  "role": "ADMIN | USER",
  "iat": 1712345678,
  "exp": 1712349278
}
```

**Token de recuperación** (generado al crear empleado o al llamar `/auth/recover-password`):

```json
{
  "sub": "nombre_usuario",
  "type": "RESET_PASSWORD",
  "iat": 1712345678,
  "exp": 1712349278
}
```

Se utiliza la **Opción A (stateless)**: el token es un JWT firmado con `HMAC SHA-256`. No requiere tabla adicional en base de datos; su autenticidad y expiración se verifican matemáticamente.

---

## Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (incluye Docker Compose v2)
- Git

---

## Inicio rápido

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd microservicios

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env si se desean cambiar credenciales o la JWT_SECRET

# 3. Construir e iniciar todos los servicios
docker-compose up --build

# 4. Verificar estado (esperar ~60 segundos al primer arranque)
docker-compose ps
```

Los servicios están listos cuando todos muestran estado `healthy` en `docker-compose ps`.

---

## Cómo autenticarse (obtener un token JWT)

### Paso 1 — Obtener el token del administrador

El sistema crea automáticamente un usuario **ADMIN** semilla con las credenciales definidas en `.env` (por defecto `admin` / `admin123`).

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"nombre_usuario": "admin", "contrasena": "admin123"}'
```

Respuesta:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "rol": "ADMIN"
}
```

### Paso 2 — Usar el token en cada petición

```bash
# Guardar el token en una variable
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Incluirlo en el header Authorization
curl http://localhost:8000/empleados \
  -H "Authorization: Bearer $TOKEN"
```

### Uso desde Swagger UI

1. Abrir <http://localhost:8000/docs> o <http://localhost:8085/docs>
2. Llamar `POST /auth/login` para obtener el token
3. Hacer clic en el botón **Authorize** (candado)
4. Ingresar el token en el campo `BearerAuth` y confirmar
5. Todas las peticiones siguientes incluirán el header automáticamente

---

## Flujo de prueba completo

### 1. Verificar que todos los servicios están saludables

```bash
curl http://localhost:8000/health          # API Gateway
curl http://localhost:8085/health          # Auth service
curl http://localhost:8080/health          # Empleados
curl http://localhost:8081/actuator/health # Departamentos
curl http://localhost:8082/health          # Notificaciones
curl http://localhost:8083/health          # Reportes
curl http://localhost:8084/health          # Perfiles
```

### 2. Obtener token de administrador

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"nombre_usuario": "admin", "contrasena": "admin123"}' \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
```

### 3. Crear un departamento (requiere ADMIN)

```bash
curl -X POST http://localhost:8000/departamentos \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"id": "IT", "nombre": "Tecnología", "descripcion": "Departamento de TI"}'
```

Respuesta esperada: `HTTP 201`

### 4. Crear un empleado (requiere ADMIN)

```bash
curl -X POST http://localhost:8000/empleados \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "id": 1,
    "nombre": "Juan Pérez",
    "email": "juan@empresa.com",
    "cargo": "Desarrollador",
    "departamento_id": "IT"
  }'
```

Respuesta esperada: `HTTP 201`

Al crear el empleado ocurre la siguiente cadena de eventos:

- `empleados-service` publica `empleado.creado`
- `auth-service` consume el evento y crea un usuario inhabilitado para `juan@empresa.com`
- `auth-service` publica `usuario.creado` con el token de establecimiento de contraseña
- `notificaciones-service` consume `usuario.creado` e imprime en los logs:

```text
[NOTIFICACIÓN] Tipo: SEGURIDAD | Para: juan@empresa.com | Mensaje: "Para establecer o recuperar su contraseña, utilice el siguiente token: eyJ..."
```

### 5. Petición denegada sin token (401)

```bash
curl http://localhost:8000/empleados
# Respuesta: 401 Unauthorized
```

### 6. Extraer el token de recuperación de los logs

```bash
docker-compose logs auth-service | grep "usuario.creado"
# O también:
docker-compose logs notificaciones-service | grep "SEGURIDAD"
```

Copiar el token JWT que aparece en el mensaje de notificación.

### 7. Establecer contraseña con el token de recuperación

```bash
curl -X POST http://localhost:8000/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "<token-de-recuperacion-del-log>",
    "nueva_contrasena": "MiContrasena123"
  }'
```

Respuesta esperada: `HTTP 200` — la cuenta queda activada.

### 8. Login como usuario normal (rol USER)

```bash
TOKEN_USER=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"nombre_usuario": "juan@empresa.com", "contrasena": "MiContrasena123"}' \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
```

### 9. Lectura exitosa con rol USER (200)

```bash
curl http://localhost:8000/empleados \
  -H "Authorization: Bearer $TOKEN_USER"
# Respuesta: 200 OK con lista de empleados
```

### 10. Escritura denegada con rol USER (403)

```bash
curl -X DELETE http://localhost:8000/empleados/1 \
  -H "Authorization: Bearer $TOKEN_USER"
# Respuesta: 403 Forbidden
```

### 11. Flujo de recuperación de contraseña

```bash
curl -X POST http://localhost:8000/auth/recover-password \
  -H "Content-Type: application/json" \
  -d '{"email": "juan@empresa.com"}'

# Revisar logs de notificaciones para obtener el nuevo token
docker-compose logs notificaciones-service | grep "SEGURIDAD"

# Repetir paso 7 con el nuevo token para cambiar la contraseña
```

### 12. Offboarding — eliminar empleado (requiere ADMIN)

```bash
curl -X DELETE http://localhost:8000/empleados/1 \
  -H "Authorization: Bearer $TOKEN"
# Respuesta: 204 No Content
```

Al eliminar el empleado ocurre la siguiente cadena:

- `empleados-service` publica `empleado.eliminado`
- `auth-service` consume el evento e inhabilita el usuario
- `perfiles-service` consume el evento y marca el perfil como inactivo
- `notificaciones-service` registra una notificación de tipo `DESVINCULACION`

### 13. Verificar que el usuario inhabilitado no puede hacer login (401)

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"nombre_usuario": "juan@empresa.com", "contrasena": "MiContrasena123"}'
# Respuesta: 401 Unauthorized — Usuario inhabilitado
```

---

## Endpoints por servicio

### API Gateway (:8000)

Enruta todas las peticiones. El prefijo de la ruta determina el servicio destino.

| Prefijo | Servicio destino | Auth requerida |
| --- | --- | --- |
| `/auth/*` | auth-service | No |
| `/empleados/*` | empleados-service | Si |
| `/departamentos/*` | departamentos-service | Si |
| `/notificaciones/*` | notificaciones-service | Si |
| `/perfiles/*` | perfiles-service | Si |
| `/reportes/*` | reportes-service | Si |

### Auth Service (:8085)

| Método | Ruta | Descripción | Auth |
| --- | --- | --- | --- |
| POST | `/auth/login` | Verificar credenciales y obtener JWT | No |
| POST | `/auth/recover-password` | Solicitar recuperación de contraseña | No |
| POST | `/auth/reset-password` | Establecer nueva contraseña con token | No |
| GET | `/health` | Estado del servicio | No |

### Empleados Service (:8080)

| Método | Ruta | Descripción | Rol mínimo |
| --- | --- | --- | --- |
| GET | `/empleados` | Listar empleados (paginado, con filtros) | USER |
| GET | `/empleados/{id}` | Consultar empleado por ID | USER |
| POST | `/empleados` | Registrar nuevo empleado | ADMIN |
| PUT | `/empleados/{id}` | Actualizar empleado | ADMIN |
| DELETE | `/empleados/{id}` | Eliminar empleado (soft delete) | ADMIN |

Filtros disponibles: `?nombre=&cargo=&departamento_id=&email=&pagina=1&por_pagina=10`

### Departamentos Service (:8081)

| Método | Ruta | Descripción | Rol mínimo |
| --- | --- | --- | --- |
| GET | `/departamentos` | Listar departamentos | USER |
| GET | `/departamentos/{id}` | Consultar departamento por ID | USER |
| POST | `/departamentos` | Crear departamento | ADMIN |
| PUT | `/departamentos/{id}` | Actualizar departamento | ADMIN |
| DELETE | `/departamentos/{id}` | Eliminar departamento | ADMIN |

### Notificaciones Service (:8082)

| Método | Ruta | Descripción | Rol mínimo |
| --- | --- | --- | --- |
| GET | `/notificaciones` | Historial global de notificaciones | USER |
| GET | `/notificaciones/{empleadoId}` | Notificaciones de un empleado | USER |
| GET | `/health` | Estado del servicio | No |

Tipos de notificación registrados:

- `BIENVENIDA` — al crear empleado
- `DESVINCULACION` — al eliminar empleado
- `SEGURIDAD` — al crear usuario o solicitar recuperación de contraseña

### Reportes Service (:8083)

| Método | Ruta | Descripción | Rol mínimo |
| --- | --- | --- | --- |
| GET | `/reportes/resumen` | Resumen de empleados y departamentos | USER |
| GET | `/health` | Estado del servicio y sus dependencias | No |

### Perfiles Service (:8084)

| Método | Ruta | Descripción | Rol mínimo |
| --- | --- | --- | --- |
| GET | `/perfiles` | Listar perfiles | USER |
| GET | `/perfiles/{empleadoId}` | Perfil de un empleado | USER |
| GET | `/health` | Estado del servicio | No |

---

## Estructura del proyecto

```text
microservicios/
├── docker-compose.yml              # Orquestación de todos los servicios
├── .env.example                    # Template de variables de entorno
├── .gitignore                      # Excluye .env y archivos sensibles
├── README.md                       # Este archivo
│
├── api-gateway/                    # Python/FastAPI — Proxy con JWT y RBAC
│   ├── main.py                     # Lógica de proxy, validación JWT, RBAC
│   ├── requirements.txt
│   └── Dockerfile
│
├── auth-service/                   # Python/FastAPI — Identidad y autenticación
│   ├── main.py                     # App principal, seed de admin, ciclo de vida
│   ├── requirements.txt
│   ├── Dockerfile
│   └── app/
│       ├── database.py             # Modelo Usuario (SQLAlchemy)
│       ├── jwt_utils.py            # Crear/decodificar tokens JWT
│       ├── broker.py               # Consume empleado.*, publica usuario.*
│       └── routes/
│           └── auth.py             # /auth/login, /recover-password, /reset-password
│
├── empleados-service/              # Python/FastAPI — CRUD de empleados
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── app/
│       ├── database.py
│       ├── broker.py               # Publica empleado.creado / empleado.eliminado
│       ├── models/empleado.py
│       ├── routes/empleados.py
│       └── clients/
│           └── departamentos_client.py  # Circuit breaker + retry + cache
│
├── departamentos-service/          # Java 17 / Spring Boot 3 — CRUD de departamentos
│   ├── pom.xml
│   ├── Dockerfile
│   └── src/main/java/com/empresa/departamentos/
│       ├── controller/
│       ├── service/
│       ├── model/
│       ├── repository/
│       ├── dto/
│       └── exception/
│
├── notificaciones-service/         # Node.js / Express — Consumidor de eventos
│   ├── src/index.js                # Consume empleado.*, usuario.*
│   ├── package.json
│   └── Dockerfile
│
├── reportes-service/               # Go / net-http — Agregador de datos
│   ├── main.go
│   ├── go.mod
│   └── Dockerfile
│
└── perfiles-service/               # Node.js / Express — Gestión de perfiles
    ├── src/index.js
    ├── package.json
    └── Dockerfile
```

---

## Variables de entorno

Copiar `.env.example` a `.env` y ajustar los valores:

```bash
cp .env.example .env
```

Variables más importantes:

| Variable | Descripción | Valor por defecto |
| --- | --- | --- |
| `JWT_SECRET` | Clave secreta para firmar/verificar tokens JWT | `changeme-super-secret-key-for-dev` |
| `ADMIN_USERNAME` | Usuario administrador semilla | `admin` |
| `ADMIN_PASSWORD` | Contraseña del administrador semilla | `admin123` |
| `ADMIN_EMAIL` | Email del administrador semilla | `admin@empresa.com` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del token de acceso | `60` |
| `RESET_TOKEN_EXPIRE_MINUTES` | Duración del token de recuperación | `60` |
| `GATEWAY_PORT` | Puerto externo del API Gateway | `8000` |
| `AUTH_SERVICE_PORT` | Puerto externo del auth-service | `8085` |

> En producción cambiar `JWT_SECRET` por una cadena aleatoria de al menos 32 caracteres.

---

## Comandos Docker útiles

```bash
# Iniciar todos los servicios (primera vez o después de cambios)
docker-compose up --build

# Iniciar en segundo plano
docker-compose up -d --build

# Ver estado de todos los contenedores
docker-compose ps

# Detener todos los servicios (conserva datos)
docker-compose down

# Detener y eliminar volúmenes (borra todos los datos)
docker-compose down -v

# Reconstruir un solo servicio
docker-compose up --build auth-service

# Reiniciar un servicio
docker-compose restart api-gateway

# Ver logs en tiempo real
docker-compose logs -f

# Logs de un servicio específico
docker-compose logs -f auth-service

# Ver solo las notificaciones de seguridad
docker-compose logs notificaciones-service | grep "SEGURIDAD"

# Acceder a la base de datos de auth
docker-compose exec db-auth psql -U postgres -d authdb

# Ver recursos utilizados
docker stats
```

---

## Patrones de resiliencia implementados

| Patrón | Servicio | Detalle |
| --- | --- | --- |
| Circuit Breaker | empleados-service | Se abre tras 5 fallos consecutivos al llamar departamentos-service. Resetea en 60s. |
| Retry con backoff | empleados-service | 3 reintentos con espera exponencial (1s → 2s → 4s) |
| Cache con TTL | empleados-service | Departamentos cacheados por 5 min como fallback |
| Soft Delete | empleados-service | Empleados marcados como inactivos, no eliminados físicamente |
| Health Checks | Todos | Endpoint `/health` con estado de dependencias |
| Graceful Degradation | reportes-service | Reporta estado `degraded` si empleados o departamentos fallan |
| Reintentos RabbitMQ | auth-service, empleados-service | Hasta 10 reintentos al conectar al broker |

---

## Tecnologías utilizadas

| Categoría | Tecnología |
| --- | --- |
| **Lenguajes** | Python 3.11, Java 17, Node.js 18, Go 1.21 |
| **Frameworks** | FastAPI, Spring Boot 3, Express.js, net/http |
| **Base de datos** | PostgreSQL 15 (5 instancias independientes) |
| **Message Broker** | RabbitMQ 3.13 con management UI |
| **Seguridad** | JWT (HMAC SHA-256), BCrypt, RBAC |
| **ORM** | SQLAlchemy (Python), Spring Data JPA / Hibernate (Java) |
| **Logging** | python-json-logger, logstash-logback-encoder, winston, uber/zap |
| **Contenedores** | Docker, Docker Compose v2 (multi-stage builds) |
| **Documentación** | OpenAPI / Swagger UI (todos los servicios) |

---

## Desarrollado por

- Salomé Pérez Franco
- Felipe
- Nelson Apache Molina
