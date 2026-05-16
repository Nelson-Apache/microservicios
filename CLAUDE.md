# CLAUDE.md — Guía para Claude Code
## Proyecto Final Microservicios — Sistema de Gestión de Empleados

---

## Contexto del Proyecto

Sistema de microservicios universitario para gestionar el ciclo de vida del empleado.
El PDF de requisitos está en `proyectoFinal.pdf`. El análisis completo de brechas está en `PRD.md`.

---

## Reglas de Código

- Nombres de métodos, variables, comentarios y logs en **español**
- Sin comentarios que expliquen qué hace el código — solo el porqué cuando no es obvio
- Sin emojis en el código
- Sin abstracciones preventivas — implementar solo lo que el requisito pide

---

## Stack Tecnológico

| Servicio | Lenguaje | Framework | Puerto | BD |
|---|---|---|---|---|
| api-gateway | Python | FastAPI | 8000 | — |
| auth-service | Python | FastAPI | 8085 | PostgreSQL `authdb` |
| empleados-service | Python | FastAPI | 8080 | PostgreSQL `empleadosdb` |
| perfiles-service | Node.js | Express | 3001 | PostgreSQL `perfilesdb` |
| notificaciones-service | Node.js | Express | 3002 | PostgreSQL `notificacionesdb` |
| vacaciones-service | Python | FastAPI | 8086 | PostgreSQL `vacacionesdb` |
| departamentos-service | Java | Spring Boot | 8081 | PostgreSQL `departamentosdb` |
| reportes-service | Go | net/http | 8083 | — |

**Message broker:** RabbitMQ — exchange `rrhh_events`, tipo `topic`  
**Observabilidad:** Prometheus + Grafana (dashboards en `observability/grafana/`) + Loki + Promtail + Zipkin  
**CI/CD:** Jenkins (puerto 8090) + SonarQube (puerto 9000) + Docker Registry (puerto 5000)

---

## Patrones Establecidos en el Proyecto

### Logging JSON (Python)
```python
from pythonjsonlogger import jsonlogger

class FormateadorJson(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["servicio"] = "nombre-servicio"
        log_record["nivel"] = record.levelname
```

### Logging JSON (Node.js)
```js
const winston = require('winston');
const logger = winston.createLogger({
  format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
  defaultMeta: { servicio: 'nombre-servicio' },
  transports: [new winston.transports.Console()]
});
```

### Publicar evento RabbitMQ (Python con aio-pika)
```python
await rabbitmq_client.publish_event(
    routing_key="empleado.creado",
    event_data={"id": ..., "nombre": ..., "email": ...}
)
```

### Consumir evento RabbitMQ (Python)
Ver `auth-service/app/broker.py` — suscripción a colas con binding keys.

### Health Check estándar
```python
# Python/FastAPI
@app.get("/health")
async def verificar_salud():
    return {"status": "UP", "service": "nombre-servicio", "version": "1.0.0"}
```
```js
// Node.js
app.get('/health', (req, res) => res.json({ status: 'UP', service: 'nombre-servicio' }));
```

### Métricas Prometheus (Python)
```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
```

### Trazabilidad Zipkin (Python)
Ver `api-gateway/main.py` función `_configurar_trazabilidad()`.

### Jenkinsfile plantilla (Python/FastAPI)
Usar `departamentos-service/Jenkinsfile` como referencia estructural, adaptando:
- Stage Build: `pip install -r requirements.txt` en lugar de Maven
- Stage Test: `pytest --cov=app --cov-report=xml tests/`
- Stage Package: `docker build` + `docker push localhost:5000/nombre-service`

---

## Eventos RabbitMQ (Exchange: rrhh_events)

| Routing Key | Publicado por | Consumido por |
|---|---|---|
| `empleado.creado` | empleados-service | auth-service, notificaciones-service |
| `empleado.actualizado` | empleados-service | perfiles-service |
| `empleado.eliminado` | empleados-service | auth-service, perfiles-service |
| `vacaciones.programadas` | vacaciones-service | auth-service, notificaciones-service |
| `vacaciones.finalizadas` | vacaciones-service | auth-service, notificaciones-service |
| `cuenta.activada` | auth-service | notificaciones-service |
| `cuenta.desactivada` | auth-service | notificaciones-service |

---

## Brechas Pendientes (ordenadas por prioridad)

### 1. CREAR vacaciones-service — CRÍTICO
**Directorio:** `vacaciones-service/`  
**Lenguaje:** Python/FastAPI (como empleados-service)  
**Puerto:** 8086  
**BD:** PostgreSQL `vacacionesdb`

Modelo mínimo:
```python
class Vacacion(Base):
    id: int
    empleado_id: int
    fecha_inicio: date
    fecha_fin: date
    motivo: Optional[str]
    estado: Enum("PROGRAMADA", "ACTIVA", "FINALIZADA", "CANCELADA")
    created_at: datetime
```

Endpoints requeridos:
- `POST /vacaciones` — programar vacaciones (publica `vacaciones.programadas`)
- `GET /vacaciones` — listar todas (con filtro por `empleado_id`)
- `GET /vacaciones/{id}` — consultar una
- `PUT /vacaciones/{id}` — actualizar
- `DELETE /vacaciones/{id}` — cancelar
- `GET /health`

Validaciones:
- No solapamiento de períodos para el mismo empleado_id
- fecha_fin >= fecha_inicio

Eventos a publicar:
- Al crear: `vacaciones.programadas` con `{empleado_id, fecha_inicio, fecha_fin}`
- Al finalizar (fecha_fin alcanzada o cancelación): `vacaciones.finalizadas`

Archivos a crear:
- `vacaciones-service/main.py`
- `vacaciones-service/app/database.py`
- `vacaciones-service/app/models/vacacion.py`
- `vacaciones-service/app/routes/vacaciones.py`
- `vacaciones-service/app/broker.py`
- `vacaciones-service/requirements.txt`
- `vacaciones-service/Dockerfile`
- `vacaciones-service/Jenkinsfile`
- `vacaciones-service/tests/test_vacaciones.py`

Agregar al `docker-compose.yml`:
- Servicio `vacaciones-service` con `VACACIONES_SERVICE_URL` en api-gateway
- BD `database-vacaciones` y volumen `vacaciones-data`
- Routing en api-gateway: `"vacaciones": os.environ.get("VACACIONES_SERVICE_URL", "http://vacaciones-service:8086")`

---

### 2. MODIFICAR empleados-service — estados del empleado

**Archivo:** `empleados-service/app/database.py` y `empleados-service/app/models/empleado.py`

Cambiar de `activo: bool` a estado enum:
```python
import enum
class EstadoEmpleado(str, enum.Enum):
    ACTIVO = "ACTIVO"
    EN_VACACIONES = "EN_VACACIONES"
    RETIRADO = "RETIRADO"
```

Agregar en el modelo Pydantic:
```python
estado: EstadoEmpleado = EstadoEmpleado.ACTIVO
```

Agregar campo `fecha_retiro: Optional[datetime]` para auditoría.

Agregar endpoint offboarding en `empleados-service/app/routes/empleados.py`:
```
PUT /empleados/{id}/retirar
```
- Cambia estado a RETIRADO
- Guarda `fecha_retiro = datetime.utcnow()`
- Publica `empleado.eliminado` (para que auth-service desactive la cuenta)

Agregar evento `empleado.actualizado` en el PUT /empleados/{id} existente.

---

### 3. CREAR Jenkinsfiles faltantes

**api-gateway/Jenkinsfile** y **auth-service/Jenkinsfile** — Python:
```groovy
pipeline {
    agent { docker { image 'python:3.11-slim' } }
    stages {
        stage('Build') { steps { sh 'pip install -r requirements.txt' } }
        stage('Test') { steps { sh 'pytest --cov=app --cov-report=xml tests/ -v' } }
        stage('Quality Gate') { steps { sh 'coverage report --fail-under=70' } }
        stage('Package') { steps {
            sh 'docker build -t localhost:5000/nombre-service:${BUILD_NUMBER} .'
            sh 'docker push localhost:5000/nombre-service:${BUILD_NUMBER}'
        }}
    }
}
```

**perfiles-service/Jenkinsfile** — Node.js:
```groovy
pipeline {
    agent { docker { image 'node:18-alpine' } }
    stages {
        stage('Build') { steps { sh 'npm install' } }
        stage('Test') { steps { sh 'npm test -- --coverage' } }
        stage('Quality Gate') { steps { sh 'npx nyc check-coverage --lines 70' } }
        stage('Package') { steps {
            sh 'docker build -t localhost:5000/perfiles-service:${BUILD_NUMBER} .'
            sh 'docker push localhost:5000/perfiles-service:${BUILD_NUMBER}'
        }}
    }
}
```

**reportes-service/Jenkinsfile** — Go:
```groovy
pipeline {
    agent { docker { image 'golang:1.22-alpine' } }
    stages {
        stage('Build') { steps { sh 'go build ./...' } }
        stage('Test') { steps { sh 'go test -v -coverprofile=coverage.out ./...' } }
        stage('Quality Gate') { steps { sh 'go tool cover -func=coverage.out | grep total' } }
        stage('Package') { steps {
            sh 'docker build -t localhost:5000/reportes-service:${BUILD_NUMBER} .'
            sh 'docker push localhost:5000/reportes-service:${BUILD_NUMBER}'
        }}
    }
}
```

---

### 4. CREAR tests faltantes

**api-gateway/tests/test_gateway.py** — Probar:
- Ruta pública `/health` no requiere JWT
- Ruta protegida sin token retorna 401
- Token de rol USER en método POST retorna 403
- Token de rol ADMIN en método POST es enrutado
- Servicio no mapeado retorna 404

**auth-service/tests/test_auth.py** — Probar:
- Login con credenciales correctas retorna JWT
- Login con contraseña incorrecta retorna 401
- Login con usuario inactivo retorna 401
- Token JWT contiene `sub`, `role`, `exp`

**perfiles-service/tests/** — Probar CRUD de perfil con Jest y supertest.

---

### 5. AGREGAR Swagger a perfiles-service

Crear `perfiles-service/src/swagger.js` con el patrón de `notificaciones-service/src/swagger.js`.  
Montar en `app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec))`.

---

### 6. MODIFICAR api-gateway para composición de datos

En `api-gateway/main.py`, agregar endpoint explícito (antes del catch-all proxy):
```python
@app.get("/empleados/{id}", tags=["Empleados"], summary="Obtener empleado con su perfil")
async def obtener_empleado_con_perfil(id: int, request: Request):
    # Llamar en paralelo a empleados-service y perfiles-service
    # Combinar y retornar respuesta unificada
```

---

### 7. VERIFICAR eventos cuenta.activada / cuenta.desactivada

En `auth-service/app/routes/auth.py` o `auth-service/app/broker.py`:
- Al activar cuenta: publicar `cuenta.activada` con `{usuario_id, email}`
- Al desactivar cuenta: publicar `cuenta.desactivada` con `{usuario_id, email, motivo}`

En `notificaciones-service/src/index.js`:
- Verificar binding a `cuenta.activada` y `cuenta.desactivada`
- Enviar email correspondiente para cada evento

---

## Archivos de Referencia Importantes

| Propósito | Archivo |
|---|---|
| Patrón Jenkinsfile completo | `departamentos-service/Jenkinsfile` |
| Patrón publicación RabbitMQ | `empleados-service/app/broker.py` |
| Patrón consumo RabbitMQ | `auth-service/app/broker.py` |
| Patrón logging JSON Python | `api-gateway/main.py` |
| Patrón logging JSON Node.js | `notificaciones-service/src/index.js` |
| Patrón Swagger Node.js | `notificaciones-service/src/swagger.js` |
| Patrón métricas Prometheus Python | `api-gateway/main.py` |
| Patrón Zipkin Python | `api-gateway/main.py` — función `_configurar_trazabilidad` |
| Patrón Dockerfile Python multi-stage | `empleados-service/Dockerfile` |
| Patrón Dockerfile Node.js | `notificaciones-service/Dockerfile` |
| Patrón docker-compose servicio | Cualquier servicio en `docker-compose.yml` |
| Patrón tests Python | `empleados-service/tests/test_empleados.py` |
| Patrón tests Node.js | `notificaciones-service/tests/notificaciones.test.js` |

---

## Variables de Entorno Comunes

```env
JWT_SECRET=changeme-super-secret-key-for-dev
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
RABBITMQ_EXCHANGE=rrhh_events
OTEL_EXPORTER_ZIPKIN_ENDPOINT=http://zipkin:9411/api/v2/spans
DATABASE_URL=postgresql://postgres:postgres@db-xxx:5432/xxxdb
```

---

## Comandos Útiles

```bash
# Levantar todo el sistema
docker-compose up --build

# Ver logs de un servicio
docker-compose logs -f vacaciones-service

# Ejecutar tests de un servicio Python
docker-compose run --rm vacaciones-service pytest tests/ -v

# Ver estado de RabbitMQ
# http://localhost:15672 — usuario: guest / contraseña: guest

# Ver métricas en Prometheus
# http://localhost:9090

# Ver dashboards en Grafana
# http://localhost:3001 — usuario: admin / contraseña: admin

# Acceder a Jenkins
# http://localhost:8090 — usuario: admin / contraseña: admin123

# Acceder a SonarQube
# http://localhost:9000 — usuario: admin / contraseña: admin

# Ver Zipkin (trazabilidad)
# http://localhost:9411
```

---

## Checklist Final de Entrega

### Funcionalidad (40%)
- [ ] Todos los microservicios funcionando (incluido vacaciones-service)
- [ ] Onboarding: crear empleado → credenciales en auth → email de bienvenida
- [ ] Gestión de perfil: actualizar datos personales, contacto y profesionales
- [ ] Vacaciones: programar → cuenta desactivada → email → cuenta reactivada al finalizar
- [ ] Offboarding: marcar RETIRADO → credenciales desactivadas permanentemente + auditoría
- [ ] API Gateway enruta correctamente todos los endpoints del PDF

### Calidad Técnica (30%)
- [ ] Swagger/OpenAPI en todos los microservicios
- [ ] Tests automatizados con cobertura ≥ 70% en todos
- [ ] `/health` responde `{"status": "UP"}` en todos
- [ ] Dockerfiles correctos (multi-stage recomendado)

### Observabilidad (15%)
- [ ] Logs centralizados en Loki (todos los servicios envían JSON)
- [ ] Prometheus scrapeando métricas de todos los servicios
- [ ] Grafana dashboards activos con métricas relevantes
- [ ] Alertas configuradas (ya están en `observability/grafana/provisioning/alerting/`)

### DevOps (10%)
- [ ] Jenkinsfiles en todos los microservicios propios
- [ ] `docker-compose up --build` levanta todo sin errores
- [ ] Jenkins ejecuta pipelines con etapas build/test/package

### Documentación (5%)
- [ ] README.md con instrucciones completas
- [ ] Credenciales por defecto de todas las herramientas
- [ ] Ejemplos de uso con curl
