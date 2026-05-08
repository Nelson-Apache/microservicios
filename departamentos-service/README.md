# 🏢 Departamentos Service

Microservicio para la gestión de departamentos organizacionales. Implementado en **Java 17** con **Spring Boot 3** y persistencia en **PostgreSQL**.

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Java 17 |
| Framework | Spring Boot 3.2 |
| Base de datos | PostgreSQL 15 |
| ORM | Spring Data JPA / Hibernate |
| Documentación | SpringDoc OpenAPI 2.3 (Swagger UI) |
| Build Tool | Maven 3.9 |
| Dockerfile | Multi-stage (Maven builder + JRE Alpine runtime) |
| Métricas | Micrometer + `micrometer-registry-prometheus` |
| Trazabilidad | `micrometer-tracing-bridge-otel` + `opentelemetry-exporter-zipkin` |
| Logs estructurados | Logback + `logstash-logback-encoder` 7.4 |

## 📁 Estructura

```
departamentos-service/
├── src/main/java/com/empresa/departamentos/
│   ├── DepartamentosServiceApplication.java   # Clase principal
│   ├── model/
│   │   └── Departamento.java                  # Entidad JPA
│   ├── dto/
│   │   ├── DepartamentoRequest.java           # DTO de entrada
│   │   └── DepartamentoResponse.java          # DTO de salida
│   ├── repository/
│   │   └── DepartamentoRepository.java        # Repositorio JPA
│   ├── service/
│   │   ├── DepartamentoService.java           # Interface del servicio
│   │   └── DepartamentoServiceImpl.java       # Implementación con @Transactional
│   ├── controller/
│   │   └── DepartamentoController.java        # Endpoints REST
│   ├── config/
│   │   └── OpenApiConfig.java                 # Configuración Swagger
│   └── exception/
│       └── GlobalExceptionHandler.java        # Manejo global de errores
├── src/main/resources/
│   ├── application.properties                 # Configuración DB + Swagger
│   └── logback-spring.xml                     # Configuración JSON logging
├── src/test/java/com/empresa/departamentos/
│   └── service/
│       └── DepartamentoServiceImplTest.java   # Tests unitarios con Mockito
├── pom.xml
├── Dockerfile                                 # Multi-stage: Maven → JRE Alpine
└── README.md
```

## 🏗️ Arquitectura en Capas

Este servicio implementa el patrón **Service Layer**:

1. **Controller Layer** (`DepartamentoController`): Maneja peticiones HTTP, validación de entrada
2. **Service Layer** (`DepartamentoService`): Lógica de negocio, transacciones con `@Transactional`
3. **Repository Layer** (`DepartamentoRepository`): Acceso a datos con Spring Data JPA
4. **Exception Layer** (`GlobalExceptionHandler`): Manejo centralizado de errores

### Beneficios
- Separación de responsabilidades
- Facilita testing con mocks
- Transacciones gestionadas por Spring
- Código más mantenible y testeable

## 🚀 Endpoints

### API de Negocio

| Método | Ruta | Descripción | Códigos |
|--------|------|-------------|---------|
| POST | `/departamentos` | Crear departamento | 201, 400, 422, 500 |
| GET | `/departamentos` | Listar departamentos | 200, 500 |
| GET | `/departamentos/{id}` | Obtener por ID | 200, 404, 500 |
| PUT | `/departamentos/{id}` | Actualizar departamento | 200, 400, 404, 422, 500 |
| DELETE | `/departamentos/{id}` | Eliminar departamento | 204, 404, 500 |

### Endpoints de Observabilidad (Spring Boot Actuator)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/actuator/health` | Health check detallado (DB status, disk space) |
| GET | `/actuator/prometheus` | Métricas en formato Prometheus (scraping) |
| GET | `/actuator/metrics` | Métricas del sistema (JVM, HTTP requests, etc.) |
| GET | `/actuator/info` | Información del servicio |

**Ejemplo de health check**:
```bash
curl http://localhost:8080/actuator/health
```

**Respuesta**:
```json
{
  "status": "UP",
  "components": {
    "db": {
      "status": "UP",
      "details": {
        "database": "PostgreSQL",
        "validationQuery": "isValid()"
      }
    },
    "diskSpace": {
      "status": "UP"
    }
  }
}
```

## 📖 Documentación OpenAPI

- **Swagger UI**: `http://localhost:8081/docs`
- **OpenAPI JSON**: `http://localhost:8081/api-docs`

## 🐳 Docker (multi-stage)

```bash
# Construir imagen (Stage 1: Maven compila, Stage 2: JRE ejecuta)
docker build -t departamentos-service .

# Ejecutar contenedor individual
docker run -p 8081:8080 \
  -e DATABASE_URL=jdbc:postgresql://host:5432/departamentosdb \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  departamentos-service
```

## 🔌 Variables de Entorno

| Variable | Default | Descripción | Requerido |
|----------|---------|-------------|-----------|
| `DATABASE_URL` | `jdbc:postgresql://localhost:5432/departamentosdb` | JDBC URL de PostgreSQL | ✅ Sí |
| `DB_USER` | `postgres` | Usuario de la BD | ✅ Sí |
| `DB_PASSWORD` | `postgres` | Contraseña de la BD | ✅ Sí |
| `PORT` | `8080` | Puerto interno del servidor | ❌ No |
| `SPRING_PROFILES_ACTIVE` | - | Perfil de Spring (dev, prod) | ❌ No |
| `MANAGEMENT_ZIPKIN_TRACING_ENDPOINT` | `http://zipkin:9411/api/v2/spans` | Endpoint Zipkin para exportar trazas OTel | ❌ No |

## 📊 JSON Logging

El servicio utiliza **logstash-logback-encoder** para generar logs en formato JSON estructurado. Configuración en [src/main/resources/logback-spring.xml](src/main/resources/logback-spring.xml).

Los campos `traceId` y `spanId` son inyectados automáticamente por **Micrometer Tracing** vía MDC, lo que permite correlacionar cada línea de log con su traza en Zipkin:

```json
{
  "timestamp": "2026-04-30T15:00:00.123Z",
  "level": "INFO",
  "logger_name": "c.e.d.service.DepartamentoServiceImpl",
  "message": "Departamento creado exitosamente",
  "service": "departamentos-service",
  "traceId": "65d3c4b2a1f0e8c7d6b5a4f3",
  "spanId": "a1b2c3d4e5f6",
  "thread_name": "http-nio-8080-exec-1"
}
```

## 📡 Observabilidad (Reto 7)

### Métricas con Prometheus

La dependencia `micrometer-registry-prometheus` expone automáticamente métricas en formato Prometheus en `/actuator/prometheus`. Prometheus raspa este endpoint cada 15 segundos desde la red Docker interna.

Métricas disponibles (selección):

| Métrica | Descripción |
| ------- | ----------- |
| `http_server_requests_seconds_count` | Total de peticiones HTTP recibidas |
| `http_server_requests_seconds_sum` | Suma de duraciones (para calcular latencia promedio) |
| `jvm_memory_used_bytes` | Memoria JVM utilizada |
| `jvm_threads_live_threads` | Hilos activos de la JVM |

Configuración en `application.properties`:

```properties
management.endpoints.web.exposure.include=health,info,metrics,prometheus
management.prometheus.metrics.export.enabled=true
management.tracing.sampling.probability=1.0
```

### Trazabilidad Distribuida (OpenTelemetry + Zipkin)

El servicio utiliza la cadena **Micrometer Tracing → OpenTelemetry → Zipkin**:

- `micrometer-tracing-bridge-otel`: Puente entre Micrometer Tracing (API de Spring Boot) y el SDK de OpenTelemetry.
- `opentelemetry-exporter-zipkin`: Exporta las trazas al servidor Zipkin en formato compatible.

El `traceId` se propaga automáticamente a través de cabeceras HTTP estándar **W3C Trace Context** (`traceparent`), lo que garantiza compatibilidad con los demás microservicios del ecosistema (Python, Node.js, Go).

```text
API Gateway → departamentos-service
                    ↳ Span: "GET /departamentos/{id}"  (traceId propagado desde el gateway)
```

Visualización en Zipkin: `http://localhost:9411`

### Consulta LogQL en Loki (ejemplo)

Para filtrar logs de este servicio en Grafana → Explore:

```logql
{service="departamentos-service"} | json | level="ERROR"
```

Para correlacionar un log con su traza:

```logql
{service="departamentos-service"} | json | traceId="<traceId-de-zipkin>"
```

## 🧪 Testing

### Ejecutar tests

```bash
# Ejecutar todos los tests
mvn test

# Ejecutar con reporte de coverage
mvn test jacoco:report

# Ejecutar tests específicos
mvn test -Dtest=DepartamentoServiceImplTest

# Ver reporte de coverage
open target/site/jacoco/index.html
```

### Tests implementados

El servicio incluye **tests unitarios con JUnit 5 + Mockito + AssertJ**:

- ✅ **DepartamentoServiceImplTest** (15 test cases)
  - Creación de departamentos (success + duplicate ID)
  - Listado completo
  - Obtención por ID (found + not found)
  - Actualización (success + not found)
  - Eliminación (success + not found)
  - Verificación de existencia

**Ejemplo de test**:
```java
@Test
@DisplayName("Debe crear un departamento exitosamente")
void testCrearDepartamento_Success() {
    when(repository.existsById(anyString())).thenReturn(false);
    when(repository.save(any(Departamento.class))).thenReturn(departamento);
    
    DepartamentoResponse response = service.crear(validRequest);
    
    assertThat(response.getId()).isEqualTo("IT");
    verify(repository, times(1)).save(any(Departamento.class));
}
```

## 🔧 Pruebas rápidas con curl

```bash
# Health check con Actuator
curl http://localhost:8080/actuator/health

# Crear departamento
curl -X POST http://localhost:8080/departamentos \
  -H "Content-Type: application/json" \
  -d '{"id": "IT", "nombre": "Tecnología", "descripcion": "Departamento de TI"}'

# Listar todos
curl http://localhost:8080/departamentos

# Obtener por ID
curl http://localhost:8080/departamentos/IT

# Actualizar departamento
curl -X PUT http://localhost:8080/departamentos/IT \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Tecnología e Innovación", "descripcion": "Desarrollo de software y soporte"}'

# Eliminar departamento
curl -X DELETE http://localhost:8080/departamentos/IT

# Verificar existencia (antes de crear empleado)
curl http://localhost:8080/departamentos/IT
# Responde 200 si existe, 404 si no existe

# Error esperado: ID duplicado (HTTP 400)
curl -X POST http://localhost:8080/departamentos \
  -H "Content-Type: application/json" \
  -d '{"id": "IT", "nombre": "Duplicado", "descripcion": "Error"}'

# Ver métricas del sistema
curl http://localhost:8080/actuator/metrics
```
