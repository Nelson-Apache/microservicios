# PRD — Proyecto Final Microservicios
## Estado del proyecto: EN DESARROLLO | Fecha: 2026-05-15

---

## 1. Resumen Ejecutivo

Sistema de gestión de empleados basado en microservicios para el ciclo de vida completo:
onboarding → gestión de perfil → vacaciones → offboarding.

**Entrega:** Semana 15 vía Google Classroom  
**Equipo:** Máximo 4 personas  
**Calificación:** Funcionalidad 40% | Calidad Técnica 30% | Observabilidad 15% | DevOps 10% | Documentación 5%

---

## 2. Estado Actual del Proyecto

### 2.1 Microservicios Existentes

| Servicio | Lenguaje | Puerto | Estado |
|---|---|---|---|
| `api-gateway` | Python/FastAPI | 8000 | PRESENTE — faltan: Jenkinsfile, tests, ruta /vacaciones |
| `auth-service` | Python/FastAPI | 8085 | PRESENTE — faltan: Jenkinsfile, tests unitarios |
| `empleados-service` | Python/FastAPI | 8080 | PRESENTE — falta: estados ACTIVO/EN_VACACIONES/RETIRADO, evento empleado.actualizado, Jenkinsfile |
| `perfiles-service` | Node.js/Express | 3000 | PRESENTE — faltan: Swagger, tests, Jenkinsfile |
| `notificaciones-service` | Node.js/Express | 3000 | PRESENTE — Jenkinsfile presente |
| `departamentos-service` | Java/Spring Boot | 8081 | EXTRA (no requerido por PDF) — Jenkinsfile presente, bien implementado |
| `reportes-service` | Go/net-http | 3000 | EXTRA (no requerido por PDF) — falta Jenkinsfile |
| **`vacaciones-service`** | **NINGUNO** | **—** | **AUSENTE — CRÍTICO** |

### 2.2 Infraestructura Existente

| Componente | Estado |
|---|---|
| RabbitMQ | PRESENTE — exchange `rrhh_events` tipo topic |
| PostgreSQL x5 | PRESENTE — authdb, empleadosdb, departamentosdb, notificacionesdb, perfilesdb |
| Prometheus + Grafana | PRESENTE — dashboards y alertas configuradas |
| Loki + Promtail | PRESENTE — logs centralizados de Docker |
| Zipkin | PRESENTE — trazabilidad distribuida |
| Jenkins | PRESENTE — puerto 8090, JCasC configurado |
| SonarQube | PRESENTE — puerto 9000 |
| Docker Registry | PRESENTE — puerto 5000 |
| docker-compose.yml | PRESENTE — 31 servicios |
| README.md | PRESENTE |
| e2e-tests (Cucumber/BDD) | PRESENTE — 6 features: auth, empleados, health, onboarding, offboarding, security |

### 2.3 Lenguajes Utilizados (Restricción: mínimo 4)

- Python — api-gateway, auth-service, empleados-service ✓
- Java — departamentos-service ✓
- Node.js — notificaciones-service, perfiles-service ✓
- Go — reportes-service ✓
- **Total: 4 lenguajes — CUMPLE**

---

## 3. Brechas Críticas a Resolver

### BRECHA 1 — vacaciones-service AUSENTE (CRÍTICO)
**Impacto:** Afecta directamente el 40% de la calificación (Funcionalidad).

El PDF requiere un microservicio completo con:
- CRUD de períodos de vacaciones (fecha_inicio, fecha_fin, empleado_id)
- Validación: no solapamiento de períodos, días disponibles
- Publicar evento `vacaciones.programadas` → consume: auth-service (desactiva cuenta) y notificaciones-service
- Publicar evento `vacaciones.finalizadas` → consume: auth-service (reactiva cuenta)
- Endpoints expuestos vía API Gateway: `POST /vacaciones`, `GET /vacaciones`
- Requiere: Dockerfile, Jenkinsfile, Swagger, tests, health check, métricas Prometheus, logging JSON

**Lenguaje sugerido:** Python/FastAPI (consistente con empleados y auth) o Go (para diversidad).  
**Base de datos:** PostgreSQL nueva instancia `vacacionesdb`.

---

### BRECHA 2 — empleados-service: estados incorrectos

El PDF requiere estados `ACTIVO | EN_VACACIONES | RETIRADO`.  
El servicio actual solo tiene `activo: bool`.

**Cambios requeridos:**
- Agregar campo `estado: Enum(ACTIVO, EN_VACACIONES, RETIRADO)` en el modelo
- Endpoint para marcar como `RETIRADO` (offboarding): debe desactivar credenciales
- Publicar evento `empleado.actualizado` cuando se actualiza cualquier campo (consume: perfiles-service)
- Registro de auditoría al marcar como RETIRADO (timestamp de desactivación)

---

### BRECHA 3 — Eventos faltantes o no confirmados

| Evento | Estado | Acción |
|---|---|---|
| `empleado.creado` | CUMPLE | — |
| `empleado.actualizado` | AUSENTE | Agregar en PUT /empleados/{id} |
| `empleado.eliminado` | CUMPLE | — |
| `vacaciones.programadas` | AUSENTE | Requiere vacaciones-service |
| `vacaciones.finalizadas` | AUSENTE | Requiere vacaciones-service |
| `cuenta.activada` | INCIERTO | Verificar y publicar desde auth-service |
| `cuenta.desactivada` | INCIERTO | Verificar y publicar desde auth-service |

---

### BRECHA 4 — Jenkinsfiles ausentes en 5 servicios

El PDF requiere pipeline Jenkins con etapas: build, test, package (Docker build + push registry).

| Servicio | Jenkinsfile |
|---|---|
| `api-gateway` | AUSENTE |
| `auth-service` | AUSENTE |
| `empleados-service` | AUSENTE |
| `perfiles-service` | AUSENTE |
| `reportes-service` | AUSENTE |
| `notificaciones-service` | PRESENTE ✓ |
| `departamentos-service` | PRESENTE ✓ |

**Referencia:** Usar `departamentos-service/Jenkinsfile` como plantilla, adaptar por lenguaje.

---

### BRECHA 5 — Tests unitarios ausentes en 3 servicios

El PDF requiere cobertura ≥ 70%.

| Servicio | Tests unitarios | Estado |
|---|---|---|
| `api-gateway` | No encontrados | AUSENTE |
| `auth-service` | No encontrados | AUSENTE |
| `empleados-service` | `tests/test_empleados.py` | PRESENTE ✓ |
| `perfiles-service` | No encontrados | AUSENTE |
| `notificaciones-service` | `tests/notificaciones.test.js` | PRESENTE ✓ |
| `departamentos-service` | `DepartamentoServiceImplTest.java` | PRESENTE ✓ |
| `reportes-service` | `main_test.go` | PRESENTE ✓ |

---

### BRECHA 6 — perfiles-service: Swagger ausente

El PDF requiere Swagger/OpenAPI en todos los microservicios.  
`perfiles-service` no tiene swagger.js ni openapi.yaml confirmados.

---

### BRECHA 7 — API Gateway: endpoints faltantes o incompletos

| Endpoint del PDF | Estado |
|---|---|
| `POST /auth/login` | CUMPLE |
| `POST /auth/change-password` | INCIERTO — verificar routing |
| `GET /empleados` | CUMPLE (proxy a empleados-service) |
| `POST /empleados` | CUMPLE |
| `GET /empleados/{id}` con composición (datos + perfil) | INCIERTO — ¿hay composición? |
| `PUT /empleados/{id}` | CUMPLE |
| `DELETE /empleados/{id}` | CUMPLE |
| `GET /perfil` | CUMPLE (proxy a perfiles-service) |
| `PUT /perfil` | CUMPLE |
| `POST /vacaciones` | AUSENTE — requiere vacaciones-service |
| `GET /vacaciones` | AUSENTE — requiere vacaciones-service |

---

### BRECHA 8 — Offboarding incompleto

El PDF requiere:
- RRHH marca empleado como `RETIRADO`
- Todas las credenciales se desactivan permanentemente (auth-service escucha evento)
- Registro de auditoría con fecha y hora de desactivación

**Estado actual:** empleados-service solo hace soft delete (activo=False), sin estado RETIRADO ni auditoría.

---

## 4. Plan de Implementación

### Fase 1 — vacaciones-service (CRÍTICA, ~4-6 horas)
1. Crear directorio `vacaciones-service/`
2. Implementar en Python/FastAPI:
   - Modelo: `id, empleado_id, fecha_inicio, fecha_fin, motivo, estado`
   - CRUD completo
   - Validación de solapamiento de períodos
   - Publicar `vacaciones.programadas` y `vacaciones.finalizadas`
3. Crear `vacacionesdb` PostgreSQL
4. Agregar al docker-compose.yml
5. Agregar routing en api-gateway (`/vacaciones/*`)
6. Conectar auth-service para que escuche `vacaciones.programadas` (desactiva) y `vacaciones.finalizadas` (reactiva)
7. Conectar notificaciones-service para que escuche ambos eventos
8. Dockerfile, Jenkinsfile, Swagger, tests, /health, métricas

### Fase 2 — Completar empleados-service (~2-3 horas)
1. Agregar campo `estado: Enum(ACTIVO, EN_VACACIONES, RETIRADO)` al modelo
2. Migración de base de datos
3. Publicar `empleado.actualizado` en PUT /empleados/{id}
4. Endpoint especial para offboarding: marcar como RETIRADO + registro de auditoría
5. Agregar Jenkinsfile
6. Verificar cobertura de tests ≥ 70%

### Fase 3 — Jenkinsfiles faltantes (~1-2 horas)
1. `api-gateway/Jenkinsfile` (Python: pip install, pytest, docker build)
2. `auth-service/Jenkinsfile` (Python: pip install, pytest, docker build)
3. `perfiles-service/Jenkinsfile` (Node.js: npm install, jest, docker build)
4. `reportes-service/Jenkinsfile` (Go: go test, docker build)

### Fase 4 — Tests y Swagger faltantes (~2-3 horas)
1. `api-gateway/tests/` — tests unitarios con pytest (mock httpx)
2. `auth-service/tests/` — tests unitarios (login, JWT, activación)
3. `perfiles-service/tests/` — tests con Jest
4. `perfiles-service/src/swagger.js` — documentación OpenAPI
5. Verificar cobertura ≥ 70% en todos

### Fase 5 — Eventos y flujos incompletos (~1-2 horas)
1. Confirmar y completar `cuenta.activada` y `cuenta.desactivada` en auth-service
2. Confirmar que notificaciones-service escucha todos los eventos requeridos
3. Verificar flujo onboarding end-to-end
4. Verificar flujo offboarding end-to-end

### Fase 6 — API Gateway composición (~1 hora)
1. `GET /empleados/{id}` debe retornar datos del empleado + perfil combinados
2. Agregar routing `/vacaciones/*` → vacaciones-service
3. Verificar `POST /auth/change-password`

### Fase 7 — README y documentación final (~1 hora)
1. Actualizar README.md con instrucciones completas
2. Credenciales por defecto de todas las herramientas
3. Ejemplos con curl para cada endpoint principal

---

## 5. Arquitectura de Eventos Final Esperada

```
empleados-service  →  empleado.creado       →  auth-service (crea credenciales)
                                             →  notificaciones-service (envía email bienvenida)

empleados-service  →  empleado.actualizado  →  perfiles-service (sincroniza datos)

empleados-service  →  empleado.eliminado    →  auth-service (desactiva cuenta)
                                             →  perfiles-service (elimina perfil)

vacaciones-service →  vacaciones.programadas → auth-service (desactiva cuenta en fecha inicio)
                                             → notificaciones-service (envía confirmación)

vacaciones-service →  vacaciones.finalizadas → auth-service (reactiva cuenta)

auth-service       →  cuenta.activada       →  notificaciones-service (notifica activación)
auth-service       →  cuenta.desactivada    →  notificaciones-service (notifica desactivación/salida)
```

---

## 6. Estructura de Directorios Esperada al Finalizar

```
microservicios/
├── README.md
├── docker-compose.yml
├── PRD.md
├── CLAUDE.md
├── api-gateway/              Python/FastAPI — JWT validation + proxy
├── auth-service/             Python/FastAPI — autenticación + activación por eventos
├── empleados-service/        Python/FastAPI — CRUD + estados + eventos
├── perfiles-service/         Node.js        — perfil personal + sync empleados
├── notificaciones-service/   Node.js        — emails por eventos RabbitMQ
├── vacaciones-service/       Python/FastAPI — CRUD vacaciones + eventos (CREAR)
├── departamentos-service/    Java           — gestión departamentos (EXTRA)
├── reportes-service/         Go             — reportes (EXTRA)
├── e2e-tests/                Java/Cucumber  — tests BDD end-to-end
├── jenkins/                  Dockerfile + casc.yaml + setup-sonarqube.sh
├── observability/
│   ├── grafana/provisioning/ — dashboards, alertas, datasources
│   ├── loki/                 — configuración Loki
│   ├── prometheus/           — prometheus.yml
│   └── promtail/             — promtail-config.yml
└── scripts/
    ├── init-db.sql
    └── seed-data.sql
```

---

## 7. Criterios de Aceptación por Brecha

### vacaciones-service
- [ ] CRUD completo funciona vía Postman/curl
- [ ] Evento `vacaciones.programadas` llega a auth-service y desactiva cuenta
- [ ] Evento `vacaciones.finalizadas` llega a auth-service y reactiva cuenta
- [ ] Notificaciones-service envía email al programar vacaciones
- [ ] No se permiten solapamientos de períodos para el mismo empleado
- [ ] `GET /health` responde `{"status": "UP"}`
- [ ] Swagger disponible en `/docs`
- [ ] Tests con cobertura ≥ 70%
- [ ] Jenkinsfile con etapas build/test/package

### empleados-service (estados)
- [ ] Campo `estado` con valores ACTIVO / EN_VACACIONES / RETIRADO
- [ ] Marcar como RETIRADO dispara desactivación permanente de credenciales
- [ ] Registro de auditoría con timestamp al retirar empleado
- [ ] Evento `empleado.actualizado` se publica en cada PUT

### Jenkinsfiles
- [ ] Cada Jenkinsfile tiene etapas: Checkout → Build → Test → Quality Gate → Package → Push Registry
- [ ] Jenkins ejecuta los pipelines correctamente desde el docker-compose

### Tests
- [ ] Cada microservicio tiene tests unitarios corriendo con `npm test` / `pytest` / `go test`
- [ ] Cobertura reportada ≥ 70%

### API Gateway
- [ ] `GET /empleados/{id}` retorna datos del empleado + datos del perfil en una sola respuesta
- [ ] `POST /vacaciones` y `GET /vacaciones` funcionan correctamente
