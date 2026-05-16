# Observability

Este directorio concentra toda la infraestructura de observabilidad del sistema: métricas con Prometheus, logs con Loki y Promtail, visualización con Grafana y alertas automáticas desde Grafana Alerting.

## Objetivo general

La idea es que cada microservicio exponga métricas y logs de forma consistente, para después centralizar todo en un solo panel de control. El flujo queda así:

1. Los servicios publican métricas HTTP o Spring Boot Actuator.
2. Prometheus las recoge por scraping.
3. Promtail envía logs de contenedores a Loki.
4. Grafana consume Prometheus y Loki para mostrar dashboards.
5. Grafana Alerting dispara notificaciones cuando se detectan problemas.

## Estructura

```text
observability/
├── grafana/
│   └── provisioning/
│       ├── alerting/
│       │   ├── contact-points.yml
│       │   ├── policies.yml
│       │   └── rules.yml
│       ├── dashboards/
│       │   ├── dashboards.yml
│       │   └── microservices.json
│       └── datasources/
│           └── datasources.yml
├── loki/
│   └── loki-config.yml
├── prometheus/
│   └── prometheus.yml
└── promtail/
    └── promtail-config.yml
```

## Archivos

### Grafana

#### `grafana/provisioning/datasources/datasources.yml`

Define las fuentes de datos que Grafana carga automáticamente al iniciar.

- `Prometheus` apunta a `http://prometheus:9090` y queda como fuente por defecto.
- `Loki` apunta a `http://loki:3100` para explorar logs.
- Los `uid` `prometheus-ds` y `loki-ds` se usan después en el dashboard y en las reglas.
- `editable: false` evita que estas fuentes se cambien desde la UI por accidente.

En resumen, este archivo conecta Grafana con el resto del stack.

#### `grafana/provisioning/dashboards/dashboards.yml`

Registra la carpeta desde la que Grafana debe cargar dashboards en formato JSON.

- `folder: Microservicios` agrupa el dashboard dentro de esa carpeta en la interfaz.
- `type: file` indica que Grafana leerá los archivos desde disco.
- `allowUiUpdates: true` permite ajustes manuales desde la UI si se necesita probar cambios.
- `path: /etc/grafana/provisioning/dashboards` es la ruta esperada dentro del contenedor.

Este archivo no define paneles; solo indica dónde buscarlos.

#### `grafana/provisioning/dashboards/microservices.json`

Es el dashboard principal del sistema. Resume el estado de los servicios y muestra tendencias de tráfico, latencia y errores.

Paneles incluidos:

- `Estado de Servicios`: panel tipo `stat` que consulta `up{job="..."}` en Prometheus para cada microservicio.
- `Tasa de Peticiones por Servicio (req/s)`: serie temporal con el ritmo de solicitudes por servicio.
- `Latencia Promedio por Servicio (s)`: calcula latencia media a partir de la suma y el conteo de peticiones.
- `Errores HTTP 4xx y 5xx por Servicio`: muestra el volumen de errores agrupado por servicio y código.

Puntos importantes del JSON:

- El dashboard usa la fuente `prometheus-ds` definida en `datasources.yml`.
- Combina métricas de servicios Python/Node con métricas de Spring Boot.
- El panel de estado convierte `0` en `DOWN` y `1` en `UP` para que sea fácil de leer.
- El `refresh` está en `30s`, así que la vista se actualiza periódicamente.

Este archivo es la vista operacional del sistema.

#### `grafana/provisioning/alerting/contact-points.yml`

Define el canal de notificación de alertas.

- El único contact point declarado es `Discord`.
- Usa `GF_DISCORD_WEBHOOK_URL` como variable de entorno para el webhook real.
- El mensaje formatea el resumen y la descripción de la alerta con un texto legible para Discord.

Este archivo no dispara alertas por sí mismo; solo define a dónde se envían.

#### `grafana/provisioning/alerting/policies.yml`

Define la política de enrutamiento de alertas.

- Todas las alertas se envían al receiver `Discord`.
- `group_by` agrupa por carpeta y nombre de alerta para evitar ruido innecesario.
- `group_wait`, `group_interval` y `repeat_interval` controlan la frecuencia de notificaciones.

Sirve para que Grafana sepa cómo agrupar y repetir mensajes.

#### `grafana/provisioning/alerting/rules.yml`

Contiene las reglas que vigilan el estado del sistema.

Reglas incluidas:

- `Servicio Caído`: alerta si `up` baja por debajo de `1` durante 1 minuto.
- `Alta Tasa de Errores 5xx`: alerta si el porcentaje de respuestas 5xx supera el 10% durante 2 minutos.

Detalles relevantes:

- Las reglas usan `prometheus-ds` como fuente de datos principal.
- `noDataState` y `execErrState` definen cómo tratar ausencia de datos o errores de ejecución.
- Las anotaciones `summary` y `description` se reutilizan en el mensaje de Discord.
- `severity` distingue entre alerta crítica y advertencia.

Este archivo es la lógica automática de supervisión.

### Loki

#### `loki/loki-config.yml`

Configura el backend de logs centralizado.

- `auth_enabled: false` simplifica el entorno local o de laboratorio.
- `http_listen_port: 3100` expone la API de Loki.
- `path_prefix: /loki` define dónde se almacenan chunks y reglas en el filesystem.
- `schema_config` usa `tsdb` con almacenamiento en filesystem y esquema `v13`.
- `ruler.alertmanager_url` apunta a `http://localhost:9093`, preparado para integración con Alertmanager.
- `limits_config` evita aceptar muestras muy antiguas y habilita metadatos estructurados.

Este archivo define cómo Loki guarda y consulta los logs.

### Prometheus

#### `prometheus/prometheus.yml`

Define qué servicios se deben scrapear y con qué frecuencia.

- `scrape_interval: 15s` actualiza métricas cada 15 segundos.
- `evaluation_interval: 15s` mantiene el mismo ritmo para reglas calculadas.
- Cada `job_name` identifica un microservicio concreto.
- `metrics_path` cambia según el stack: algunos servicios exponen `/metrics` y `departamentos-service` usa `/actuator/prometheus`.

Servicios monitorizados:

- `api-gateway` en `api-gateway:8000`
- `auth-service` en `auth-service:8085`
- `empleados-service` en `empleados-service:8080`
- `departamentos-service` en `departamentos-service:8080`
- `notificaciones-service` en `notificaciones-service:3000`
- `perfiles-service` en `perfiles-service:3000`
- `reportes-service` en `reportes-service:3000`

Este archivo es el inventario de métricas del sistema.

### Promtail

#### `promtail/promtail-config.yml`

Configura el envío de logs de contenedores hacia Loki.

- `server.http_listen_port: 9080` expone el servidor interno de Promtail.
- `positions.filename` guarda el progreso de lectura para no reenviar logs ya procesados.
- `clients.url` apunta a `http://loki:3100/loki/api/v1/push`.
- `docker_sd_configs` descubre contenedores Docker automáticamente.
- `relabel_configs` añade etiquetas útiles como `container`, `service` y `stream`.
- `pipeline_stages` intenta extraer campos JSON como `level`, `service` y `traceId`.

Este archivo conecta el mundo de contenedores con la centralización de logs.

## Relación entre archivos

- `prometheus.yml` alimenta el dashboard `microservices.json`.
- `datasources.yml` permite que Grafana llegue tanto a Prometheus como a Loki.
- `rules.yml`, `contact-points.yml` y `policies.yml` trabajan juntos para alertar por Discord.
- `promtail-config.yml` envía los logs que luego pueden consultarse desde Grafana.
- `loki-config.yml` define cómo se almacenan y sirven esos logs.

## Notas operativas

- El webhook de Discord debe definirse en `GF_DISCORD_WEBHOOK_URL` antes de levantar Grafana.
- Si se agrega un microservicio nuevo, hay que actualizar `prometheus.yml` y, si corresponde, el dashboard.
- Si el servicio emite logs en un formato diferente, puede requerir ajustes en `promtail-config.yml`.
- Si se añaden nuevas alertas, conviene revisar también `rules.yml` y `policies.yml`.

## Resumen corto por archivo

- `datasources.yml`: conecta Grafana con Prometheus y Loki.
- `dashboards.yml`: registra la carpeta de dashboards.
- `microservices.json`: panel visual principal del sistema.
- `contact-points.yml`: define la salida de alertas hacia Discord.
- `policies.yml`: agrupa y enruta alertas.
- `rules.yml`: define qué condiciones disparan alertas.
- `loki-config.yml`: configura el backend de logs.
- `prometheus.yml`: define el scraping de métricas.
- `promtail-config.yml`: envía logs de Docker a Loki.
