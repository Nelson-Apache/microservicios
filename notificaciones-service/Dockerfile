# =====================================================
# STAGE 1: Builder — instala dependencias Node.js
# =====================================================
FROM node:18-alpine AS builder

WORKDIR /app

# Copiar manifiestos de depend encias
COPY package*.json ./

# Instalar SOLO dependencias de producción
RUN npm install --omit=dev

# =====================================================
# STAGE 2: Runtime — imagen limpia
# =====================================================
FROM node:18-alpine AS runtime

LABEL maintainer="equipo-microservicios"
LABEL service="notificaciones-service"
LABEL version="1.0.0"

WORKDIR /app

# Copiar dependencias desde builder
COPY --from=builder /app/node_modules ./node_modules

# Copiar código fuente
COPY src/ ./src/
COPY package.json ./

# Usuario no-root para seguridad
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup && \
    chown -R appuser:appgroup /app
USER appuser

EXPOSE 3000

CMD ["node", "src/index.js"]
