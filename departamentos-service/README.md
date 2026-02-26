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
│   ├── controller/
│   │   └── DepartamentoController.java        # Endpoints REST
│   ├── config/
│   │   └── OpenApiConfig.java                 # Configuración Swagger
│   └── exception/
│       └── GlobalExceptionHandler.java        # Manejo global de errores
├── src/main/resources/
│   └── application.properties                 # Configuración DB + Swagger
├── pom.xml
├── Dockerfile                                 # Multi-stage: Maven → JRE Alpine
└── README.md
```

## 🚀 Endpoints

| Método | Ruta | Descripción | Códigos |
|--------|------|-------------|---------|
| GET | `/` | Health check | 200 |
| POST | `/departamentos` | Crear departamento | 201, 400, 422, 500 |
| GET | `/departamentos` | Listar departamentos | 200, 500 |
| GET | `/departamentos/{id}` | Obtener por ID | 200, 404, 500 |

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

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_URL` | `jdbc:postgresql://localhost:5432/departamentosdb` | JDBC URL de PostgreSQL |
| `DB_USER` | `postgres` | Usuario de la BD |
| `DB_PASSWORD` | `postgres` | Contraseña de la BD |
| `PORT` | `8080` | Puerto interno del servidor |

## 🧪 Pruebas rápidas

```bash
# Crear departamento
curl -X POST http://localhost:8081/departamentos \
  -H "Content-Type: application/json" \
  -d '{"id": "IT", "nombre": "Tecnología", "descripcion": "Departamento de TI"}'

# Listar todos
curl http://localhost:8081/departamentos

# Obtener por ID
curl http://localhost:8081/departamentos/IT
```
