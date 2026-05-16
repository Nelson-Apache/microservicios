import os
import logging
from contextlib import asynccontextmanager
from pythonjsonlogger import jsonlogger

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.routes.vacaciones import router as router_vacaciones
from app.database import init_db
from app.broker import broker


class FormateadorJson(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["servicio"] = "vacaciones-service"
        log_record["nivel"] = record.levelname


manejador_log = logging.StreamHandler()
manejador_log.setFormatter(FormateadorJson("%(timestamp)s %(nivel)s %(name)s %(message)s"))
logging.getLogger().addHandler(manejador_log)
logging.getLogger().setLevel(logging.INFO)

logger = logging.getLogger(__name__)


def _configurar_trazabilidad(nombre_servicio: str) -> None:
    endpoint = os.environ.get("OTEL_EXPORTER_ZIPKIN_ENDPOINT", "http://zipkin:9411/api/v2/spans")
    recurso = Resource.create({"service.name": nombre_servicio})
    proveedor = TracerProvider(resource=recurso)
    proveedor.add_span_processor(BatchSpanProcessor(ZipkinExporter(endpoint=endpoint)))
    trace.set_tracer_provider(proveedor)


_configurar_trazabilidad(os.environ.get("OTEL_SERVICE_NAME", "vacaciones-service"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Base de datos inicializada")
    try:
        await broker._conectar()
        logger.info("Broker conectado al inicio")
    except Exception as e:
        logger.warning(f"Broker no disponible al inicio, se conectará al publicar: {e}")
    yield
    await broker.detener()


app = FastAPI(
    title="Vacaciones Service",
    description=(
        "Gestión de períodos de vacaciones de empleados.\n\n"
        "Publica eventos:\n"
        "- `vacaciones.programadas` al crear\n"
        "- `vacaciones.finalizadas` al cancelar o finalizar"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

FastAPIInstrumentor.instrument_app(app)
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.include_router(router_vacaciones)


@app.get("/health", tags=["Health"], summary="Health check del servicio")
async def verificar_salud():
    return {"status": "UP", "service": "vacaciones-service", "version": "1.0.0"}


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
        }
    }
    esquema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = esquema
    return esquema


app.openapi = esquema_openapi_personalizado
