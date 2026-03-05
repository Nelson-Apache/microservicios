# =====================================================
# STAGE 1: Builder — compila con Maven
# =====================================================
FROM maven:3.9-eclipse-temurin-17-alpine AS builder

WORKDIR /app

# Copiar solo el POM primero para cachear dependencias
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Copiar código fuente y compilar
COPY src ./src
RUN mvn clean package -DskipTests -B

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