# Dockerfile para ejecutar pruebas E2E BDD
# Permite ejecutar las pruebas sin instalar Java/Maven localmente

FROM maven:3.9-eclipse-temurin-17-alpine

# Metadata
LABEL maintainer="equipo-microservicios"
LABEL description="Pruebas E2E BDD con Cucumber + Rest Assured"

# Directorio de trabajo
WORKDIR /app

# Copiar archivos de configuración de Maven primero (para aprovechar cache de Docker)
COPY pom.xml .

# Descargar dependencias (se cachea si pom.xml no cambia)
RUN mvn dependency:go-offline -B

# Copiar el código fuente
COPY src ./src

# Variables de entorno por defecto (pueden ser sobrescritas en docker-compose)
ENV BASE_URL=http://api-gateway:8000
ENV ADMIN_USER=admin
ENV ADMIN_PASSWORD=admin123
ENV USER_USER=usuario
ENV USER_PASSWORD=usuario123
ENV JWT_SECRET=changeme-super-secret-key-for-dev

# Comando por defecto: ejecutar las pruebas
CMD ["mvn", "test"]
