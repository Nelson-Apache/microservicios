# Sistema de Microservicios — Gestión de Empleados y Departamentos

Sistema distribuido para gestionar el ciclo de vida completo del empleado (onboarding, vacaciones y offboarding), implementado con **5 lenguajes de programación**, orquestado con **Docker Compose**, con comunicación sincrónica (HTTP REST), asincrónica (RabbitMQ) y seguridad centralizada mediante **JWT**.

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
       ▼                          │  /vacaciones, /notificaciones,
┌─────────────┐                   │  /perfiles, /reportes  (JWT requerido)
│ auth-service│                   ▼
│   :8085     │   ┌─────────────────────────────────────────┐
│  db-auth    │   │         Microservicios de negocio        │
└──────┬──────┘   │                                         │
       │          │  empleados-service    :8080 (Python)     │
       │ Consume  │  departamentos-service :8081 (Java)      │
       │ Publica  │  notificaciones-service :3002 (Node.js)  │
       │          │  reportes-service     :8083 (Go)          │
       │          │  perfiles-service     :3000 (Node.js)    │
       │          │  vacaciones-service   :8086 (Python)     │
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
                                 empleado.actualizado
                                 empleado.eliminado
                                        │
                     ┌──────────────────┼──────────────────┐
                     ▼                  ▼                   ▼
              notificaciones     perfiles-service     auth-service
               (BIENVENIDA/       (crear perfil/      (crear usuario /
               DESVINCULACION)    actualizar perfil/  inhabilitar usuario)
                                  inactivar perfil)        │
                                                 publica──►  cuenta.activada
                                                 publica──►  cuenta.desactivada
                                                           │
                                                           ▼
                                                   notificaciones
                                                    (SEGURIDAD /
                                                  VACACIONES / etc.)

vacaciones-service ──publica──►  vacaciones.programadas
                                 vacaciones.finalizadas
                                        │
                     ┌──────────────────┘
                     ▼
              auth-service
               (desactiva / reactiva cuenta
                y publica cuenta.desactivada / cuenta.activada)
                     │
                     ▼
              notificaciones-service
               (notifica al empleado)
```

---

## Servicios

| Servicio | Lenguaje | Puerto | Base de datos | Swagger UI |
| --- | --- | --- | --- | --- |
| `api-gateway` | Python / FastAPI | **8000** | — | <http://localhost:8000/docs> |
| `auth-service` | Python / FastAPI | **8085** | PostgreSQL (authdb) | <http://localhost:8085/docs> |
| `empleados-service` | Python / FastAPI | **8080** | PostgreSQL (empleadosdb) | <http://localhost:8080/docs> |
| `departamentos-service` | Java 17 / Spring Boot | **8081** | PostgreSQL (departamentosdb) | <http://localhost:8081/swagger-ui.html> |
| `notificaciones-service` | Node.js / Express | **3002** | PostgreSQL (notificacionesdb) | <http://localhost:3002/api-docs> |
| `reportes-service` | Go / net-http | **8083** | — | <http://localhost:8083/docs/index.html> |
| `perfiles-service` | Node.js / Express | **3000** (interno, sin puerto host) | PostgreSQL (perfilesdb) | vía gateway: <http://localhost:8000/perfiles/> |
| `vacaciones-service` | Python / FastAPI | **8086** | PostgreSQL (vacacionesdb) | <http://localhost:8086/docs> |
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

Se utiliza el patrón **stateless**: el token es un JWT firmado con `HMAC SHA-256`. No requiere tabla adicional en base de datos; su autenticidad y expiración se verifican matemáticamente.

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
curl http://localhost:3002/health          # Notificaciones
curl http://localhost:8083/health          # Reportes
curl http://localhost:8000/perfiles/health  # Perfiles (vía gateway, sin puerto host directo)
curl http://localhost:8086/health          # Vacaciones
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

### 4. Crear un empleado — Onboarding (requiere ADMIN)

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
- `notificaciones-service` consume `usuario.creado` y registra notificación de tipo `SEGURIDAD`
- `perfiles-service` consume `empleado.creado` y crea el perfil del empleado

```bash
# Ver el token de recuperación generado
docker-compose logs notificaciones-service | grep "SEGURIDAD"
```

### 5. Petición denegada sin token (401)

```bash
curl http://localhost:8000/empleados
# Respuesta: 401 Unauthorized
```

### 6. Establecer contraseña con el token de recuperación

```bash
curl -X POST http://localhost:8000/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "<token-de-recuperacion-del-log>",
    "nueva_contrasena": "MiContrasena123"
  }'
```

Respuesta esperada: `HTTP 200` — la cuenta queda activada.

### 7. Login como usuario normal (rol USER)

```bash
TOKEN_USER=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"nombre_usuario": "juan@empresa.com", "contrasena": "MiContrasena123"}' \
  | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
```

### 8. Cambiar contraseña (usuario autenticado)

```bash
curl -X POST http://localhost:8000/auth/change-password \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN_USER" \
  -d '{
    "contrasena_actual": "MiContrasena123",
    "nueva_contrasena": "NuevaContrasena456"
  }'
```

Respuesta esperada: `HTTP 200`

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

# Repetir paso 6 con el nuevo token para cambiar la contraseña
```

### 12. Gestión de vacaciones

#### Programar vacaciones (requiere ADMIN)

```bash
curl -X POST http://localhost:8000/vacaciones \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "id": 1,
    "empleado_id": 1,
    "fecha_inicio": "2025-07-01",
    "fecha_fin": "2025-07-15",
    "motivo": "Vacaciones de verano"
  }'
```

Respuesta esperada: `HTTP 201`

Al programar vacaciones:

- `vacaciones-service` publica `vacaciones.programadas`
- `auth-service` consume el evento y desactiva la cuenta del empleado
- `auth-service` publica `cuenta.desactivada`
- `notificaciones-service` notifica al empleado

```bash
# Verificar que la cuenta está desactivada (login debe retornar 401)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"nombre_usuario": "juan@empresa.com", "contrasena": "MiContrasena123"}'
# Respuesta: 401 — "Usuario inhabilitado"
```

#### Consultar vacaciones por empleado

```bash
curl "http://localhost:8000/vacaciones?empleado_id=1" \
  -H "Authorization: Bearer $TOKEN"
# Respuesta: 200 OK con lista paginada de vacaciones
```

#### Finalizar vacaciones (reactiva la cuenta)

```bash
curl -X PUT http://localhost:8000/vacaciones/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"estado": "FINALIZADA"}'
```

Respuesta esperada: `HTTP 200`

Al finalizar:

- `vacaciones-service` publica `vacaciones.finalizadas`
- `auth-service` reactiva la cuenta del empleado
- `auth-service` publica `cuenta.activada`
- `notificaciones-service` notifica al empleado

### 13. Offboarding — Retirar empleado (requiere ADMIN)

```bash
# Opción A: Retiro definitivo (cambia estado a RETIRADO, desactiva cuenta permanentemente)
curl -X PUT http://localhost:8000/empleados/1/retirar \
  -H "Authorization: Bearer $TOKEN"
```

Respuesta esperada: `HTTP 200`

Al retirar el empleado:

- `empleados-service` cambia el estado a `RETIRADO` y guarda `fecha_retiro`
- `empleados-service` publica `empleado.eliminado`
- `auth-service` inhabilita la cuenta de forma permanente
- `perfiles-service` marca el perfil como inactivo
- `notificaciones-service` registra notificación de tipo `DESVINCULACION`

```bash
# Verificar que el usuario inhabilitado no puede hacer login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"nombre_usuario": "juan@empresa.com", "contrasena": "MiContrasena123"}'
# Respuesta: 401 Unauthorized — Usuario inhabilitado
```

```bash
# Opción B: Eliminación física (soft delete, mantiene datos para auditoría)
curl -X DELETE http://localhost:8000/empleados/1 \
  -H "Authorization: Bearer $TOKEN"
# Respuesta: 204 No Content
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
| `/vacaciones/*` | vacaciones-service | Si |
| `/notificaciones/*` | notificaciones-service | Si |
| `/perfiles/*` | perfiles-service | Si |
| `/reportes/*` | reportes-service | Si |

### Auth Service (:8085)

| Método | Ruta | Descripción | Auth |
| --- | --- | --- | --- |
| POST | `/auth/login` | Verificar credenciales y obtener JWT | No |
| POST | `/auth/recover-password` | Solicitar recuperación de contraseña | No |
| POST | `/auth/reset-password` | Establecer nueva contraseña con token de recuperación | No |
| POST | `/auth/change-password` | Cambiar contraseña (usuario autenticado) | Bearer JWT |
| GET | `/health` | Estado del servicio | No |

### Empleados Service (:8080)

| Método | Ruta | Descripción | Rol mínimo |
| --- | --- | --- | --- |
| GET | `/empleados` | Listar empleados (paginado, con filtros) | USER |
| GET | `/empleados/{id}` | Consultar empleado por ID | USER |
| POST | `/empleados` | Registrar nuevo empleado | ADMIN |
| PUT | `/empleados/{id}` | Actualizar empleado (publica `empleado.actualizado`) | ADMIN |
| PUT | `/empleados/{id}/retirar` | Retirar empleado (cambia estado a RETIRADO) | ADMIN |
| DELETE | `/empleados/{id}` | Eliminar empleado (soft delete) | ADMIN |
| GET | `/health` | Estado del servicio | No |

Filtros disponibles: `?nombre=&cargo=&departamento_id=&email=&pagina=1&por_pagina=10`

Estados del empleado: `ACTIVO`, `EN_VACACIONES`, `RETIRADO`

### Departamentos Service (:8081)

| Método | Ruta | Descripción | Rol mínimo |
| --- | --- | --- | --- |
| GET | `/departamentos` | Listar departamentos | USER |
| GET | `/departamentos/{id}` | Consultar departamento por ID | USER |
| POST | `/departamentos` | Crear departamento | ADMIN |
| PUT | `/departamentos/{id}` | Actualizar departamento | ADMIN |
| DELETE | `/departamentos/{id}` | Eliminar departamento | ADMIN |

### Vacaciones Service (:8086)

| Método | Ruta | Descripción | Rol mínimo |
| --- | --- | --- | --- |
| GET | `/vacaciones` | Listar vacaciones (con filtro por `empleado_id`) | USER |
| GET | `/vacaciones/{id}` | Consultar vacación por ID | USER |
| POST | `/vacaciones` | Programar vacaciones (publica `vacaciones.programadas`) | ADMIN |
| PUT | `/vacaciones/{id}` | Actualizar / finalizar vacaciones | ADMIN |
| DELETE | `/vacaciones/{id}` | Cancelar vacaciones | ADMIN |
| GET | `/health` | Estado del servicio | No |

Estados de vacación: `PROGRAMADA`, `ACTIVA`, `FINALIZADA`, `CANCELADA`

Validaciones:

- No se permiten solapamientos de períodos para el mismo empleado
- `fecha_fin` debe ser mayor o igual a `fecha_inicio`

### Notificaciones Service (:3002)

| Método | Ruta | Descripción | Rol mínimo |
| --- | --- | --- | --- |
| GET | `/notificaciones` | Historial global de notificaciones | USER |
| GET | `/notificaciones/{empleadoId}` | Notificaciones de un empleado | USER |
| GET | `/health` | Estado del servicio | No |

Tipos de notificación registrados:

- `BIENVENIDA` — al crear empleado
- `DESVINCULACION` — al retirar o eliminar empleado
- `SEGURIDAD` — al crear usuario o solicitar recuperación de contraseña
- `VACACIONES` — al programar o finalizar vacaciones

### Reportes Service (:8083)

| Método | Ruta | Descripción | Rol mínimo |
| --- | --- | --- | --- |
| GET | `/reportes/resumen` | Resumen de empleados y departamentos | USER |
| GET | `/health` | Estado del servicio y sus dependencias | No |

### Perfiles Service (interno :3000, acceso vía gateway :8000)

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
├── .env                            # Variables de entorno (no subir al repo)
├── .env.example                    # Template de variables de entorno
├── .gitignore
├── README.md
├── CLAUDE.md                       # Instrucciones para Claude Code
├── PRD.md                          # Análisis de brechas y plan de implementación
│
├── api-gateway/                    # Python/FastAPI — Proxy con JWT y RBAC
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── Jenkinsfile
│   └── tests/
│       └── test_gateway.py
│
├── auth-service/                   # Python/FastAPI — Identidad y autenticación
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── Jenkinsfile
│   ├── tests/
│   │   └── test_auth.py
│   └── app/
│       ├── database.py             # Modelo Usuario con empleado_id (SQLAlchemy)
│       ├── jwt_utils.py            # Crear/decodificar tokens JWT
│       ├── broker.py               # Consume empleado.*, vacaciones.*; publica cuenta.*
│       └── routes/
│           └── auth.py             # /login, /recover-password, /reset-password, /change-password
│
├── empleados-service/              # Python/FastAPI — CRUD y ciclo de vida de empleados
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── Jenkinsfile
│   ├── tests/
│   │   └── test_empleados.py
│   └── app/
│       ├── database.py             # EstadoEmpleadoDB, campo fecha_retiro
│       ├── broker.py               # Publica empleado.creado/actualizado/eliminado
│       ├── models/empleado.py      # EstadoEmpleado enum: ACTIVO/EN_VACACIONES/RETIRADO
│       ├── routes/empleados.py     # Incluye PUT /empleados/{id}/retirar
│       └── clients/
│           └── departamentos_client.py  # Circuit breaker + retry + cache
│
├── departamentos-service/          # Java 17 / Spring Boot 3 — CRUD de departamentos
│   ├── pom.xml
│   ├── Dockerfile
│   ├── Jenkinsfile
│   └── src/
│
├── notificaciones-service/         # Node.js / Express — Consumidor de eventos
│   ├── src/index.js                # Consume empleado.*, usuario.*, cuenta.*, vacaciones.*
│   ├── package.json
│   ├── Dockerfile
│   └── tests/
│
├── reportes-service/               # Go / net-http — Agregador de datos
│   ├── main.go
│   ├── go.mod
│   ├── Dockerfile
│   └── Jenkinsfile
│
├── perfiles-service/               # Node.js / Express — Gestión de perfiles
│   ├── src/index.js
│   ├── package.json
│   ├── Dockerfile
│   ├── Jenkinsfile
│   └── tests/
│
├── vacaciones-service/             # Python/FastAPI — Gestión de vacaciones
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── Jenkinsfile
│   ├── tests/
│   │   └── test_vacaciones.py
│   └── app/
│       ├── database.py
│       ├── broker.py               # Publica vacaciones.programadas/finalizadas
│       ├── models/vacacion.py
│       └── routes/vacaciones.py
│
├── e2e-tests/                      # Cucumber BDD — Pruebas de integración extremo a extremo
│   ├── pom.xml
│   └── src/test/
│       ├── java/com/empresa/e2e/
│       │   ├── step_definitions/
│       │   │   ├── AuthSteps.java
│       │   │   ├── EmpleadosSteps.java
│       │   │   ├── VacacionesSteps.java
│       │   │   └── OffboardingSteps.java
│       │   ├── support/
│       │   │   ├── ConfiguracionBase.java
│       │   │   ├── TestContext.java
│       │   │   └── WaitUtils.java
│       │   └── runner/
│       │       └── CucumberRunner.java
│       └── resources/features/
│           ├── auth.feature
│           ├── empleados.feature
│           ├── vacaciones.feature
│           └── offboarding.feature
│
└── observability/                  # Prometheus + Grafana + Loki + Zipkin
    ├── prometheus/prometheus.yml
    ├── grafana/provisioning/
    │   ├── dashboards/
    │   └── alerting/
    ├── loki/
    ├── promtail/
    └── blackbox/
```

---

## Eventos RabbitMQ

Exchange: `rrhh_events`, tipo `topic`

| Routing Key | Publicado por | Consumido por |
| --- | --- | --- |
| `empleado.creado` | empleados-service | auth-service, notificaciones-service, perfiles-service |
| `empleado.actualizado` | empleados-service | perfiles-service |
| `empleado.eliminado` | empleados-service | auth-service, perfiles-service, notificaciones-service |
| `vacaciones.programadas` | vacaciones-service | auth-service, notificaciones-service |
| `vacaciones.finalizadas` | vacaciones-service | auth-service, notificaciones-service |
| `cuenta.activada` | auth-service | notificaciones-service |
| `cuenta.desactivada` | auth-service | notificaciones-service |

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
| `ADMIN_USERNAME` | Usuario administrador semilla (auth-service) | `admin` |
| `ADMIN_PASSWORD` | Contraseña del administrador semilla | `admin123` |
| `ADMIN_EMAIL` | Email del administrador semilla | `admin@empresa.com` |
| `ADMIN_USER` | Nombre de usuario para pruebas e2e | `admin` |
| `USER_USER` | Usuario regular para pruebas e2e | `usuario` |
| `USER_PASSWORD` | Contraseña del usuario regular para pruebas e2e | `usuario123` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del token de acceso | `60` |
| `RESET_TOKEN_EXPIRE_MINUTES` | Duración del token de recuperación | `60` |
| `RABBITMQ_URL` | URL de conexión al broker | `amqp://guest:guest@rabbitmq:5672/` |
| `GATEWAY_PORT` | Puerto externo del API Gateway | `8000` |
| `AUTH_SERVICE_PORT` | Puerto externo del auth-service | `8085` |
| `VACACIONES_SERVICE_PORT` | Puerto externo del vacaciones-service | `8086` |

> En producción cambiar `JWT_SECRET` por una cadena aleatoria de al menos 32 caracteres.

---

## Observabilidad

| Herramienta | URL | Usuario | Contraseña |
| --- | --- | --- | --- |
| **Prometheus** | <http://localhost:9090> | — | — |
| **Grafana** | <http://localhost:3001> (**puerto 3001 del host, no perfiles-service**) | `admin` | `admin` |
| **Loki** | <http://localhost:3100> | — | — |
| **Zipkin** | <http://localhost:9411> | — | — |

Todos los servicios exponen `/metrics` para Prometheus y envían logs en formato JSON estructurado (compatibles con Loki). La trazabilidad distribuida está implementada con OpenTelemetry + Zipkin en el API Gateway.

---

## Pruebas automatizadas

### Pruebas unitarias (por servicio)

```bash
# empleados-service
docker-compose run --rm empleados-service pytest tests/ -v

# auth-service
docker-compose run --rm auth-service pytest tests/ -v

# api-gateway
docker-compose run --rm api-gateway pytest tests/ -v

# vacaciones-service
docker-compose run --rm vacaciones-service pytest tests/ -v

# notificaciones-service
docker-compose run --rm notificaciones-service npm test

# perfiles-service
docker-compose run --rm perfiles-service npm test
```

### Pruebas e2e (Cucumber BDD)

Las pruebas e2e se ejecutan contra el sistema completo levantado:

```bash
# Levantar el sistema primero
docker-compose up -d

# Ejecutar pruebas e2e
docker-compose run --rm e2e-tests

# O directamente con Maven
cd e2e-tests
mvn test -DBASE_URL=http://localhost:8000 \
         -DADMIN_USER=admin \
         -DADMIN_PASSWORD=admin123 \
         -DUSER_USER=usuario \
         -DUSER_PASSWORD=usuario123
```

Escenarios cubiertos:

| Feature | Escenarios |
| --- | --- |
| `auth.feature` | Login exitoso, credenciales incorrectas, RBAC |
| `empleados.feature` | Onboarding completo, CRUD, validaciones |
| `vacaciones.feature` | Programar, consultar, solapamiento, cuenta desactivada/reactivada |
| `offboarding.feature` | Retiro definitivo, cuenta permanentemente desactivada |

---

## CI/CD con Jenkins

### URLs de acceso y credenciales

| Servicio | URL | Usuario | Contraseña |
| --- | --- | --- | --- |
| **Jenkins** | <http://localhost:8090> | `admin` | `admin123` |
| **SonarQube** | <http://localhost:9000> | `admin` | `admin123` |
| **Docker Registry** | <http://localhost:5000> | — | — |
| **RabbitMQ Admin** | <http://localhost:15672> | `guest` | `guest` |

### Pipelines disponibles

| Pipeline | Servicio | Lenguaje | Jenkinsfile |
| --- | --- | --- | --- |
| `api-gateway-pipeline` | api-gateway | Python / FastAPI | `api-gateway/Jenkinsfile` |
| `auth-service-pipeline` | auth-service | Python / FastAPI | `auth-service/Jenkinsfile` |
| `empleados-service-pipeline` | empleados-service | Python / FastAPI | `empleados-service/Jenkinsfile` |
| `vacaciones-service-pipeline` | vacaciones-service | Python / FastAPI | `vacaciones-service/Jenkinsfile` |
| `notificaciones-service-pipeline` | notificaciones-service | Node.js / Express | `notificaciones-service/Jenkinsfile` |
| `perfiles-service-pipeline` | perfiles-service | Node.js / Express | `perfiles-service/Jenkinsfile` |
| `departamentos-service-pipeline` | departamentos-service | Java 17 / Spring Boot | `departamentos-service/Jenkinsfile` |
| `reportes-service-pipeline` | reportes-service | Go | `reportes-service/Jenkinsfile` |

### Etapas del pipeline

| # | Etapa | Descripción |
| --- | --- | --- |
| 1 | **Checkout** | Descarga el código del repositorio |
| 2 | **Build** | Instala dependencias |
| 3 | **Test** | Ejecuta pruebas unitarias con cobertura |
| 4 | **Quality Gate** | Verifica cobertura ≥ 70% |
| 5 | **Package** | Construye imagen Docker y la publica en el registry local |

### Cómo levantar el sistema completo (con CI)

```bash
# 1. Levantar TODO el sistema en segundo plano
docker-compose up -d

# 2. Esperar ~2-3 minutos a que todos los servicios estén listos

# 3. Verificar que Jenkins está accesible
curl http://localhost:8090

# 4. Verificar que SonarQube está accesible
curl http://localhost:9000/api/system/status
```

### Configurar SonarQube

```bash
docker cp jenkins/setup-sonarqube.sh jenkins:/tmp/setup-sonarqube.sh
docker exec jenkins bash -c "tr -d '\r' < /tmp/setup-sonarqube.sh > /tmp/setup-sonarqube_unix.sh && SONAR_URL=http://sonarqube:9000 bash /tmp/setup-sonarqube_unix.sh"
```

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
docker-compose up --build vacaciones-service

# Reiniciar un servicio
docker-compose restart api-gateway

# Ver logs en tiempo real
docker-compose logs -f

# Logs de un servicio específico
docker-compose logs -f vacaciones-service

# Ver solo las notificaciones de vacaciones
docker-compose logs notificaciones-service | grep "vacaciones"

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
| Reintentos RabbitMQ | auth-service, empleados-service, vacaciones-service | Hasta 10 reintentos al conectar al broker |
| Polling async e2e | e2e-tests | WaitUtils con 30 reintentos × 2s para eventos asíncronos |

---

## Tecnologías utilizadas

| Categoría | Tecnología |
| --- | --- |
| **Lenguajes** | Python 3.11, Java 17, Node.js 18, Go 1.21 |
| **Frameworks** | FastAPI, Spring Boot 3, Express.js, net/http |
| **Base de datos** | PostgreSQL 15 (6 instancias independientes) |
| **Message Broker** | RabbitMQ 3.13 con management UI |
| **Seguridad** | JWT (HMAC SHA-256), BCrypt, RBAC |
| **ORM** | SQLAlchemy (Python), Spring Data JPA / Hibernate (Java) |
| **Logging** | python-json-logger, logstash-logback-encoder, winston, uber/zap |
| **Observabilidad** | Prometheus, Grafana, Loki, Promtail, Zipkin, OpenTelemetry |
| **Pruebas** | pytest, JUnit 5, Jest, Cucumber BDD, RestAssured |
| **CI/CD** | Jenkins (JCasC), SonarQube, Docker Registry local |
| **Contenedores** | Docker, Docker Compose v2 (multi-stage builds) |
| **Documentación** | OpenAPI / Swagger UI (todos los servicios) |

---

## Desarrollado por

- Salomé Pérez Franco
- Felipe Hurtado
- Nelson Apache Molina
