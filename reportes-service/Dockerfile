# =====================================================
# STAGE 1: Builder — descarga deps y compila binario
# =====================================================
FROM golang:1.21-alpine AS builder

# Instalar herramientas necesarias
RUN apk add --no-cache git && \
    go install github.com/swaggo/swag/cmd/swag@v1.16.3

WORKDIR /app

# Copiar módulo
COPY go.mod ./

# Descargar dependencias y generar go.sum automáticamente
RUN go mod download || true

# Copiar el resto del código fuente
COPY . .

# Actualizar dependencias
RUN go mod tidy

# Generar documentación Swagger
RUN swag init --parseDependency --parseInternal || true

# Compilar binario estático
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o reportes-service .

# =====================================================
# STAGE 2: Runtime — imagen mínima sin Go
# =====================================================
FROM alpine:3.18 AS runtime

LABEL maintainer="equipo-microservicios"
LABEL service="reportes-service"
LABEL version="1.0.0"

# Instalar certificados SSL para llamadas HTTPS
RUN apk --no-cache add ca-certificates

WORKDIR /app

# Copiar solo el binario compilado
COPY --from=builder /app/reportes-service .

# Usuario no-root para seguridad
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup && \
    chown -R appuser:appgroup /app
USER appuser

EXPOSE 3000

CMD ["./reportes-service"]
