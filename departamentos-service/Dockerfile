# syntax=docker/dockerfile:1
# =====================================================
# STAGE 1: Builder — compila con Maven
# =====================================================
FROM maven:3.9-eclipse-temurin-17 AS builder

WORKDIR /app

# Copiar solo el POM primero para cachear dependencias.
# --mount=type=cache evita que los "absent markers" de Maven queden
# atrapados en una capa Docker tras un fallo de red previo.
COPY pom.xml .
RUN --mount=type=cache,target=/root/.m2 \
    find /root/.m2 -name "*.lastUpdated" -delete 2>/dev/null || true && \
    mvn dependency:go-offline -B

# Copiar código fuente y compilar
COPY src ./src
RUN --mount=type=cache,target=/root/.m2 \
    mvn clean package -DskipTests -B

# =====================================================
# STAGE 2: Runtime — JRE mínimo sin Maven
# =====================================================
FROM eclipse-temurin:17-jre-alpine AS runtime

LABEL maintainer="equipo-microservicios"
LABEL service="departamentos-service"
LABEL version="1.1.0"

WORKDIR /app

# Copiar solo el JAR compilado
COPY --from=builder /app/target/*.jar app.jar

# Usuario no-root para seguridad
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup && \
    chown -R appuser:appgroup /app
USER appuser

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
