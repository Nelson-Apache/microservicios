from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from app.routes import empleados
from app.database import init_db, engine, EmpleadoModel
from sqlalchemy import text
import sys
import logging
from pythonjsonlogger import jsonlogger

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


# Incluir routers
app.include_router(empleados.router)


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
        - 200 si el servicio y la BD están operativos
        - 503 si hay problemas con la BD
    """
    health_status = {
        "status": "healthy",
        "service": "empleados-service",
        "version": "2.0.0",
        "checks": {}
    }
    
    # Verificar conexión a base de datos
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"error: {str(e)}"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_status
        )
    
    return health_status
