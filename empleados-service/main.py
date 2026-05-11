from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from pydantic import ValidationError
from app.routes import empleados
from app.database import init_db, engine, EmpleadoModel
from sqlalchemy import text
import sys
import logging
from pythonjsonlogger import jsonlogger
import os

# ── Observabilidad — Reto 7 ──
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Gauge
import asyncio

SERVICIO_SALUDABLE = Gauge(
    'servicio_saludable',
    'Servicio y dependencias operativas: 1=sí, 0=no',
    ['service']
)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# ─────────────────────────────────────────────────────────────────────────────
# Configuración de logging estructurado en JSON
# ─────────────────────────────────────────────────────────────────────────────

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Formateador JSON personalizado que añade campos estándar a cada log.
    """
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['service'] = 'empleados-service'
        log_record['level'] = record.levelname
        log_record['logger'] = record.name

# Configurar el handler con formato JSON
logHandler = logging.StreamHandler()
formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
logHandler.setFormatter(formatter)

# Configurar el logger raíz
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Aplicar también a uvicorn
logging.getLogger("uvicorn.access").handlers = [logHandler]
logging.getLogger("uvicorn.error").handlers = [logHandler]


def _configurar_trazabilidad(nombre_servicio: str) -> None:
    """Inicializa OpenTelemetry con exportador Zipkin."""
    endpoint = os.environ.get("OTEL_EXPORTER_ZIPKIN_ENDPOINT", "http://zipkin:9411/api/v2/spans")
    recurso = Resource.create({"service.name": nombre_servicio})
    proveedor = TracerProvider(resource=recurso)
    proveedor.add_span_processor(BatchSpanProcessor(ZipkinExporter(endpoint=endpoint)))
    trace.set_tracer_provider(proveedor)


_configurar_trazabilidad(os.environ.get("OTEL_SERVICE_NAME", "empleados-service"))


# ─────────────────────────────────────────────────────────────────────────────
# Aplicación principal
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Servidor de Empleados",
    description=(
        "API REST para la gestión de empleados.\n\n"
        "## Características\n"
        "- Registro, consulta, actualización y eliminación de empleados\n"
        "- Filtros por nombre, cargo, departamento y email\n"
        "- Paginación de resultados\n"
        "- Validación de duplicados\n"
        "- Persistencia en PostgreSQL"
    ),
    version="2.0.0",
)


# ─────────────────────────────────────────────────────────────────────────────
# Eventos de ciclo de vida
# ─────────────────────────────────────────────────────────────────────────────
from app.broker import rabbitmq_client

async def _monitorear_bd():
    """Verifica la BD cada 30 s y actualiza la métrica servicio_saludable."""
    while True:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False
        broker_ok = bool(rabbitmq_client.connection and not rabbitmq_client.connection.is_closed)
        SERVICIO_SALUDABLE.labels(service='empleados-service').set(1 if (db_ok and broker_ok) else 0)
        await asyncio.sleep(30)


@app.on_event("startup")
async def startup_event():
    """
    Inicializa la base de datos al arrancar la aplicación.
    """
    try:
        logger.info("Conectando a la base de datos", extra={"event": "db_connection_start"})
        init_db()
        logger.info("Base de datos inicializada correctamente", extra={"event": "db_initialized"})
    except Exception as e:
        logger.error("Error al inicializar la base de datos", extra={"event": "db_init_error", "error": str(e)})
        sys.exit(1)

    # Conectar a RabbitMQ de forma no bloqueante: si falla, el servicio sigue
    # activo y reconectará automáticamente al intentar publicar un evento.
    try:
        await rabbitmq_client.connect()
    except Exception as e:
        logger.warning("No se pudo conectar a RabbitMQ al arrancar. Se reintentará al publicar.", extra={"event": "rabbitmq_init_warning", "error": str(e)})

    asyncio.create_task(_monitorear_bd())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Cerrando conexiones...")
    await rabbitmq_client.close()


# Incluir routers
app.include_router(empleados.router)

FastAPIInstrumentor.instrument_app(app)
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


def esquema_openapi_personalizado():
    if app.openapi_schema:
        return app.openapi_schema
    esquema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    esquema.setdefault("components", {})["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Token JWT obtenido desde POST /auth/login",
        }
    }
    esquema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = esquema
    return esquema


app.openapi = esquema_openapi_personalizado


# ─────────────────────────────────────────────────────────────────────────────
# Manejadores globales de errores
# ─────────────────────────────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Maneja errores de validación de Pydantic (422).
    Devuelve un mensaje legible con el detalle de cada campo inválido.
    """
    errores = []
    for error in exc.errors():
        campo = " → ".join(str(loc) for loc in error["loc"])
        errores.append({
            "campo": campo,
            "mensaje": error["msg"],
            "tipo": error["type"],
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Error de validación en los datos enviados.",
            "detalles": errores,
        },
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Maneja rutas no encontradas (404)."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "Recurso no encontrado.",
            "ruta": str(request.url),
        },
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc):
    """Maneja métodos HTTP no permitidos (405)."""
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content={
            "error": "Método HTTP no permitido para esta ruta.",
            "metodo": request.method,
            "ruta": str(request.url.path),
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Maneja errores internos del servidor (500)."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Error interno del servidor. Por favor intente más tarde.",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Raíz
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["general"], summary="Estado del servidor")
async def root():
    """Verifica que el servidor está en línea."""
    return {
        "mensaje": "Servidor de empleados activo",
        "version": "2.0.0",
        "documentacion": "/docs",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["general"], summary="Health check del servicio")
async def health_check():
    """
    Verifica el estado del servicio y sus dependencias.

    Retorna:
        - 200 si el servicio y todas las dependencias están operativas
        - 503 si hay problemas con alguna dependencia
    """
    health_status = {
        "status": "UP",
        "service": "empleados-service",
        "version": "2.0.0",
        "checks": {}
    }
    degradado = False

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "UP"
    except Exception as e:
        health_status["checks"]["database"] = "DOWN"
        degradado = True

    health_status["checks"]["messageBroker"] = (
        "UP" if (rabbitmq_client.connection and not rabbitmq_client.connection.is_closed) else "DOWN"
    )
    if health_status["checks"]["messageBroker"] == "DOWN":
        degradado = True

    if degradado:
        health_status["status"] = "DOWN"
        SERVICIO_SALUDABLE.labels(service='empleados-service').set(0)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_status
        )
    SERVICIO_SALUDABLE.labels(service='empleados-service').set(1)
    return health_status
