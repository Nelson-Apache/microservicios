# PRD – Reto 7: Observabilidad y Monitoreo del Ecosistema de Microservicios

## 1. Resumen Ejecutivo

Este documento define los requisitos de producto para la implementación de un stack de observabilidad completo sobre el ecosistema de microservicios de onboarding/offboarding de empleados. El sistema actualmente opera como una "caja negra": cuando algo falla en producción, no es posible determinar con rapidez qué servicio falló, por qué, ni qué petición lo provocó.

El objetivo de este reto es instrumentar el ecosistema para que responda a las cuatro preguntas fundamentales de cualquier sistema distribuido en producción:

| Pregunta | Solución |
|---|---|
| ¿Está vivo el sistema? | Health Checks (`/health`) |
| ¿Cómo se está comportando? | Métricas con Prometheus + Grafana |
| ¿Qué hizo exactamente? | Trazabilidad distribuida con OpenTelemetry + Zipkin/Jaeger |
| ¿Alguien me avisa si algo falla? | Alertas proactivas con Grafana |

---

## 2. Contexto y Antecedentes

El sistema de microservicios fue construido progresivamente en retos anteriores:

- **Reto 1 y 2:** Despliegue con Docker y Docker Compose.
- **Reto 3:** Comunicación sincrónica y asincrónica.
- **Reto 4:** Seguridad con JWT.
- **Reto 5:** Automatización de pruebas.
- **Reto 6:** Integración Continua (CI).

A pesar de contar con seguridad, pruebas y CI, el sistema carece de visibilidad operativa. No es posible saber si una latencia elevada en el Servicio de Empleados es responsabilidad suya, de la base de datos, del broker de mensajes o del servicio de departamentos al que llama.

---

## 3. Objetivos del Producto

- Integrar un stack de observabilidad (Prometheus, Grafana, Loki, Promtail, Zipkin/Jaeger) al ecosistema existente vía Docker Compose.
- Instrumentar todos los microservicios con endpoints de métricas, health checks y trazabilidad distribuida.
- Construir un dashboard en Grafana con métricas consolidadas de múltiples servicios.
- Configurar reglas de alerta proactiva con notificación a un canal externo.
- Documentar toda la arquitectura de observabilidad en el README del repositorio.

---

## 4. Requisitos Funcionales

### 4.1 Health Checks

Cada microservicio debe exponer un endpoint `GET /health` que retorne JSON indicando su estado operativo.

**Respuesta cuando el servicio está saludable (HTTP 200):**

```json
{
  "status": "UP",
  "service": "empleados-service",
  "checks": {
    "database": "UP",
    "messageBroker": "UP"
  }
}
```

**Respuesta cuando el servicio está degradado (HTTP 503):**

```json
{
  "status": "DOWN",
  "service": "empleados-service",
  "checks": {
    "database": "DOWN",
    "messageBroker": "UP"
  }
}
```

> **Nota:** En Spring Boot, esta funcionalidad está integrada en `/actuator/health`. Para otros lenguajes, debe implementarse manualmente verificando conectividad con base de datos y broker.

---

### 4.2 Métricas en Formato Prometheus

Cada microservicio debe exponer un endpoint de métricas en texto plano compatible con Prometheus. Las métricas mínimas requeridas son:

- Uso de CPU y memoria del proceso.
- Número de peticiones HTTP recibidas, separadas por código de respuesta.
- Latencia de las peticiones HTTP (tiempo de respuesta).

**Librerías de referencia por lenguaje:**

| Lenguaje / Framework | Librería | Endpoint típico |
|---|---|---|
| Java / Spring Boot | `micrometer-registry-prometheus` | `/actuator/prometheus` |
| Node.js / Express | `prom-client` | `/metrics` |
| Python / FastAPI | `prometheus-fastapi-instrumentator` | `/metrics` |
| Python / Flask | `prometheus-flask-exporter` | `/metrics` |
| Go | `prometheus/client_golang` | `/metrics` |
| .NET / ASP.NET Core | `prometheus-net.AspNetCore` | `/metrics` |

---

### 4.3 Trazabilidad Distribuida con OpenTelemetry

Todos los microservicios deben estar instrumentados con OpenTelemetry (OTel) para propagar un `traceId` a través de toda la cadena de llamadas, independientemente del lenguaje.

**Resultado esperado:** Desde la UI de Zipkin/Jaeger, debe ser posible buscar un `traceId` y visualizar la cascada completa de spans mostrando:
1. Qué servicio recibió la petición original.
2. A qué otros servicios llamó y cuánto tardó cada llamada.
3. Si algún servicio retornó un error.

**Librerías de referencia por lenguaje:**

| Lenguaje | SDK / Librería |
|---|---|
| Java / Spring Boot | `opentelemetry-spring-boot-starter` + exportador OTLP/Zipkin |
| Node.js | `@opentelemetry/sdk-node` + `@opentelemetry/exporter-zipkin` |
| Python | `opentelemetry-sdk` + `opentelemetry-exporter-zipkin` |
| Go | `go.opentelemetry.io/otel` + exportador Zipkin |
| .NET | `OpenTelemetry.Exporter.Zipkin` |

**Variables de entorno de configuración mínima:**

```env
OTEL_SERVICE_NAME=empleados-service
OTEL_EXPORTER_ZIPKIN_ENDPOINT=http://zipkin:9411/api/v2/spans
OTEL_PROPAGATORS=tracecontext,baggage
```

> **Importante:** La URL del exportador debe usar el nombre de red de Docker (`zipkin`), no `localhost`.

**Configuración mínima por servicio:**

- `service.name`: Nombre descriptivo del servicio (ej. `empleados-service`).
- Exportador: Apuntando a la URL del servidor Zipkin/Jaeger en Docker Compose.
- Propagación: W3C Trace Context para compatibilidad entre lenguajes.

---

### 4.4 Logs Estructurados (Loki + Promtail)

Cada microservicio debe emitir logs en formato JSON. Esto permite filtrar, agregar y correlacionar logs con trazas distribuidas.

**Campos mínimos requeridos en cada log:**

```json
{
  "timestamp": "2026-04-30T15:00:00Z",
  "level": "INFO",
  "service": "empleados-service",
  "traceId": "abc123def456",
  "message": "Empleado creado exitosamente",
  "employeeId": "E010"
}
```

> **Nota:** El campo `traceId` permite correlacionar logs con trazas en Zipkin/Jaeger. Los SDKs de OTel lo inyectan automáticamente en el contexto de logging.

**Librerías de referencia por lenguaje:**

| Lenguaje | Librería | Configuración clave |
|---|---|---|
| Java / Spring Boot | Logback + `logstash-logback-encoder` | Appender JSON en `logback-spring.xml` |
| Node.js | `winston` + `winston-json-formatter` | `format: winston.format.json()` |
| Python | `structlog` o `python-json-logger` | `JSONRenderer` como procesador final |
| Go | `zap` o `zerolog` | Ambas emiten JSON por defecto |
| .NET | `Serilog` + `Serilog.Sinks.Console` | `outputTemplate` en formato JSON |

---

### 4.5 Dashboard en Grafana

Debe construirse al menos un dashboard con los siguientes paneles obligatorios:

| Panel | Métrica a visualizar | Tipo de gráfica |
|---|---|---|
| Estado de cada servicio | `up{job="nombre-servicio"}` | Stat (verde/rojo) |
| Tasa de peticiones por servicio | `rate(http_requests_total[1m])` | Time Series |
| Latencia promedio | `rate(http_request_duration_seconds_sum[1m]) / rate(http_request_duration_seconds_count[1m])` | Time Series |
| Errores HTTP (4xx y 5xx) | `sum by (status) (rate(http_requests_total{status=~"[45].."}[1m]))` | Time Series |

**Organización mínima del dashboard (2 filas):**

1. **Resumen del Sistema:** Estado de salud de todos los servicios (paneles tipo Stat).
2. **Comportamiento del Tráfico:** Métricas de peticiones y latencia (gráficas de serie temporal).

> **Nota:** Los nombres exactos de las métricas pueden variar según la librería utilizada. El equipo debe adaptar las consultas PromQL según las métricas reales expuestas por cada servicio.

---

### 4.6 Alertas Proactivas

Deben configurarse al menos **dos** de las siguientes reglas de alerta en Grafana:

| # | Regla | Condición | Descripción |
|---|---|---|---|
| 1 | Servicio Caído | `up{job="<nombre-servicio>"} == 0` durante 1 minuto | Un microservicio dejó de responder al scraping de Prometheus. |
| 2 | Alta Tasa de Errores | Porcentaje de respuestas HTTP 5xx > 10% durante 2 minutos | El servicio retorna errores de servidor de forma sostenida. |
| 3 | Alta Latencia | Latencia promedio > 2 segundos durante 2 minutos | Posible sobrecarga o dependencia lenta. |
| 4 | Contenedor Reiniciado | Métrica de reinicios del contenedor aumenta | Un servicio colapsó y fue reiniciado por Docker. |

**Canal de notificación (Contact Point):** Debe configurarse al menos uno:

| Canal | Complejidad | Observación |
|---|---|---|
| Webhook de Discord | Baja | Crear servidor Discord y generar Webhook. Soportado nativamente en Grafana. |
| Bot de Telegram | Baja | Crear bot con @BotFather y configurar `chat_id`. Soportado nativamente en Grafana. |
| Slack | Media | Requiere app de Slack con Incoming Webhook. |
| Email | Media | Requiere configurar SMTP en Grafana (puede usarse Mailhog en Docker para pruebas). |

---

## 5. Requisitos de Infraestructura

### 5.1 Stack de Observabilidad en Docker Compose

Los siguientes servicios deben agregarse al `docker-compose.yml` existente:

| Servicio | Imagen de referencia | Puerto | Rol |
|---|---|---|---|
| Prometheus | `prom/prometheus:latest` | 9090 | Recolector de métricas (modelo Pull) |
| Grafana | `grafana/grafana:latest` | 3000 | Visualización de métricas, logs y gestión de alertas |
| Loki | `grafana/loki:latest` | 3100 | Agregación y almacenamiento de logs |
| Promtail | `grafana/promtail:latest` | — | Agente recolector de logs (envía a Loki) |
| Zipkin o Jaeger | `openzipkin/zipkin:latest` | 9411 / 16686 | Servidor de trazabilidad distribuida |

**Estructura de referencia en `docker-compose.yml`:**

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./observability/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - microservices-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./observability/grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    networks:
      - microservices-network

  zipkin:
    image: openzipkin/zipkin:latest
    ports:
      - "9411:9411"
    networks:
      - microservices-network

volumes:
  grafana-data:
```

**Restricciones de red:**
- Prometheus, Grafana y el servidor de trazas deben estar en la misma red Docker que los microservicios.
- Las URLs internas deben usar nombres de servicio Docker, no `localhost` ni IPs fijas.

**Persistencia:**
- Los datos de Grafana (dashboards, configuraciones) deben persistir en un volumen Docker.
- Grafana debe tener Prometheus configurado como datasource de forma automatizada (archivos de aprovisionamiento en volúmenes).

---

### 5.2 Configuración de Prometheus (`prometheus.yml`)

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'api-gateway'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['api-gateway:8080']

  - job_name: 'empleados-service'
    metrics_path: '/actuator/prometheus'  # Ajustar según lenguaje/framework
    static_configs:
      - targets: ['empleados-service:8081']

  - job_name: 'departamentos-service'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['departamentos-service:8082']

  # Repetir para cada microservicio del ecosistema...
```

> **Importante:** El API Gateway debe ser el primer `scrape_job`. Sus métricas de latencia y tasa de error ofrecen la visión más valiosa del sistema desde la perspectiva del cliente.

**Rutas del endpoint de métricas por lenguaje:**

| Lenguaje / Framework | `metrics_path` |
|---|---|
| Spring Boot (Java) | `/actuator/prometheus` |
| Express (Node.js) | `/metrics` |
| FastAPI / Flask (Python) | `/metrics` |
| Go | `/metrics` |

---

### 5.3 Configuración de Promtail

```yaml
# observability/promtail/promtail-config.yml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker-containers
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        target_label: 'container'
      - source_labels: ['__meta_docker_container_label_com_docker_compose_service']
        target_label: 'service'
```

> **Importante:** El contenedor de Promtail necesita acceso al socket de Docker (`/var/run/docker.sock`) como volumen para descubrir contenedores automáticamente.

---

## 6. Estructura de Archivos del Repositorio

```
repositorio/
├── docker-compose.yml          # Actualizado con servicios de observabilidad
├── observability/
│   ├── prometheus/
│   │   └── prometheus.yml
│   ├── grafana/
│   │   └── provisioning/
│   │       ├── datasources/    # Configuración automática de Prometheus y Loki
│   │       └── dashboards/     # Dashboard exportado en JSON
│   ├── loki/
│   │   └── loki-config.yml
│   └── promtail/
│       └── promtail-config.yml
└── README.md                   # Actualizado con documentación de observabilidad
```

---

## 7. Pruebas del Sistema – Simulación de Caos

### 7.1 Verificación Inicial

1. Levantar el ecosistema completo:
   ```bash
   docker-compose up --build
   ```
2. Verificar que el stack está activo:
   - **Prometheus UI:** `http://localhost:9090` → sección Targets debe mostrar todos los microservicios en estado `UP`.
   - **Grafana:** `http://localhost:3000` → dashboard con métricas en tiempo real.
   - **Zipkin:** `http://localhost:9411` (o Jaeger en `http://localhost:16686`).

### 7.2 Generación de Tráfico

```bash
# Crear un empleado (genera trazas y métricas)
curl -X POST http://localhost:<puerto>/empleados \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"id": "E010", "nombre": "Ana Gómez", "email": "ana@empresa.com", "departamentoId": "IT", "fechaIngreso": "2026-04-30"}'

# Múltiples consultas para generar métricas de tráfico
for i in {1..10}; do curl http://localhost:<puerto>/empleados -H "Authorization: Bearer <token>"; done
```

### 7.3 Verificación de Trazabilidad

Abrir Zipkin/Jaeger, buscar las trazas recientes y localizar la correspondiente a la creación del empleado. La cascada debe mostrar:

```
gateway → empleados-service → departamentos-service → message broker → auth-service → notificaciones-service → perfiles-service
```

### 7.4 Simulación de Caos – Servicio Caído

```bash
docker-compose stop departamentos-service
```

Esperar ~2 minutos y verificar:
- **Prometheus:** El target `departamentos-service` pasa a estado `DOWN`.
- **Grafana:** El panel de estado cambia a rojo.
- **Canal de alertas:** Debe llegar la notificación "Servicio Caído".

### 7.5 Simulación de Caos – Latencia Artificial

Introducir temporalmente un retardo en el código de un servicio:

```python
# Ejemplo en Python
import time, random
if random.random() < 0.5:
    time.sleep(5)  # Latencia artificial
```

Reconstruir el contenedor y verificar en Grafana que el panel de latencia refleja el incremento. Si la regla de "Alta Latencia" está configurada, debe dispararse la alerta.

---

## 8. Conceptos a Investigar y Documentar en el README

El equipo debe investigar y documentar los siguientes conceptos en el README antes de implementar:

| Concepto | Descripción a investigar |
|---|---|
| Los tres pilares de la Observabilidad | Métricas, Logs y Trazas: ¿cuál es el rol de cada una? |
| Modelo Pull vs. Push | ¿Cómo funciona el scraping de Prometheus (Pull)? ¿Cómo funciona el envío de trazas a Zipkin/Jaeger (Push)? |
| OpenTelemetry | ¿Qué es la CNCF? ¿Por qué es relevante OTel como estándar agnóstico? |
| W3C Trace Context | ¿Cómo viaja el `traceId` a través de cabeceras HTTP entre servicios de distintos lenguajes? |

---

## 9. Diagrama de Arquitectura (Entregable)

El diagrama debe mostrar:
1. Los componentes del stack de observabilidad levantados.
2. Cómo se conecta Prometheus a cada microservicio (red de Docker).
3. Cómo fluyen las trazas desde un microservicio hasta Zipkin/Jaeger.
4. Cómo Grafana consume datos de Prometheus y Loki.

**Flujo general de referencia:**

```
Cliente HTTP
    │
    ▼
🚪 API Gateway
    │
    ├──► 👥 empleados-service ──► 🗄 Base de datos
    ├──► 🏢 departamentos-service
    ├──► 🔐 auth-service
    ├──► 📋 perfiles-service
    └──► 📧 notificaciones-service
              │
         📨 Message Broker

Stack de Observabilidad (misma red Docker):
    📊 Prometheus ──scraping pull /metrics──► todos los servicios
    📂 Loki ◄──push logs── 📋 Promtail ──docker socket──► contenedores
    🔍 Zipkin/Jaeger ◄──push trazas (OTel)──► todos los servicios
    📈 Grafana ──PromQL──► Prometheus
               ──LogQL──► Loki
               ──alertas──► 🔔 Canal (Discord/Telegram/Slack)
```

> El diagrama puede construirse con draw.io, Mermaid, Excalidraw u otra herramienta e incluirse en el README o como imagen en el repositorio.

---

## 10. Criterios de Evaluación

El reto se evalúa sobre **6 puntos** distribuidos así:

| # | Elemento | Valor | Aspectos a evaluar |
|---|---|---|---|
| 1 | Infraestructura de Observabilidad | 1.0 | Prometheus, Grafana, Loki/Promtail y Zipkin/Jaeger correctamente configurados en `docker-compose.yml`. Redes Docker correctas. `prometheus.yml` con todos los servicios como targets. |
| 2 | Instrumentación de Microservicios | 1.0 | Todos los microservicios (incluido API Gateway) exponen métricas Prometheus y `/health`. OpenTelemetry configurado con nombre de servicio, exportador y propagación W3C. |
| 3 | Logs Centralizados | 1.0 | Logs en formato JSON en todos los servicios. Loki y Promtail configurados. Grafana con Loki como datasource. Al menos una consulta LogQL evidenciada en el README. |
| 4 | Dashboard en Grafana | 1.0 | Dashboard con los 4 paneles requeridos. Aprovisionado automáticamente (JSON exportado y versionado en Git). |
| 5 | Alertas Proactivas | 1.0 | Mínimo dos reglas de alerta configuradas. Canal externo funcional y documentado. Evidencia (captura de pantalla) de alerta recibida. |
| 6 | Pruebas de Caos y Documentación | 1.0 | Simulación de caos documentada con capturas de pantalla (dashboard, traza distribuida y alerta). Diagrama de arquitectura en README. Respuesta fundamentada a la pregunta de análisis. |

> **Nota transversal:** La documentación en `README.md` y el versionamiento adecuado en GitHub afectan la evaluación de todos los elementos.

---

## 11. Entregables

- [ ] Código versionado en GitHub.
- [ ] Carpeta `observability/` con:
  - `observability/prometheus/prometheus.yml`
  - `observability/grafana/provisioning/` (datasources y dashboards en JSON)
  - `observability/loki/loki-config.yml`
  - `observability/promtail/promtail-config.yml`
- [ ] `docker-compose.yml` actualizado con todos los servicios de observabilidad.
- [ ] `README.md` actualizado con:
  - Diagrama de arquitectura de observabilidad.
  - Investigación de conceptos (Pull vs. Push, OTel, W3C Trace Context).
  - Librerías utilizadas en cada microservicio para métricas y trazabilidad.
  - Justificación de elección entre Zipkin y Jaeger.
  - Canal de alertas elegido y guía de configuración.
  - Capturas de pantalla de las pruebas de caos (dashboard, trazas y alerta recibida).
  - Respuesta a: *"¿Qué servicio del ecosistema tardó más en responder y cómo lo identificaron?"*

---

## 12. Consideraciones Técnicas

- Todos los servicios del ecosistema deben estar instrumentados, no solo los nuevos.
- Las URLs de los servicios de observabilidad dentro de Docker Compose deben usar **nombres de red de Docker**, nunca `localhost`.
- Los archivos de configuración de Grafana (datasources, dashboards) deben estar **versionados en Git** para que estén disponibles automáticamente al ejecutar `docker-compose up`, sin configuración manual.
- La simulación del caos es **obligatoria** y debe estar evidenciada con capturas de pantalla en el README.
- El equipo puede proponer alternativas al stack de referencia (Datadog, New Relic, ELK Stack, etc.) siempre que cubran los mismos requisitos funcionales y lo justifiquen en el README.
