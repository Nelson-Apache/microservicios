from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.database import inicializar_db, SesionLocal, Usuario, motor
from app.broker import broker
from app.routes.auth import router as router_auth, contexto_hash
import os
import sys
import logging
from pythonjsonlogger import jsonlogger


# ─────────────────────────────────────────────────────────────────────────────
# Configuración de logging estructurado en JSON
# ─────────────────────────────────────────────────────────────────────────────

class FormateadorJsonPersonalizado(jsonlogger.JsonFormatter):
    """Añade metadatos del servicio a cada línea de log."""
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["servicio"] = "auth-service"
        log_record["nivel"] = record.levelname
        log_record["logger"] = record.name


manejador_log = logging.StreamHandler()
manejador_log.setFormatter(FormateadorJsonPersonalizado("%(timestamp)s %(nivel)s %(name)s %(message)s"))
logger_raiz = logging.getLogger()
logger_raiz.addHandler(manejador_log)
logger_raiz.setLevel(logging.INFO)
logging.getLogger("uvicorn.access").handlers = [manejador_log]
logging.getLogger("uvicorn.error").handlers = [manejador_log]

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Usuario administrador semilla (seed)
# ─────────────────────────────────────────────────────────────────────────────

def crear_usuario_admin_semilla():
    """
    Crea el usuario ADMIN inicial si no existe.
    Las credenciales se inyectan vía variables de entorno:
      - ADMIN_USERNAME  (por defecto: admin)
      - ADMIN_PASSWORD  (por defecto: admin123)
      - ADMIN_EMAIL     (por defecto: admin@empresa.com)
    """
    nombre_admin = os.environ.get("ADMIN_USERNAME", "admin")
    contrasena_admin = os.environ.get("ADMIN_PASSWORD", "admin123")
    email_admin = os.environ.get("ADMIN_EMAIL", "admin@empresa.com")

    db = SesionLocal()
    try:
        existente = db.query(Usuario).filter(Usuario.nombre_usuario == nombre_admin).first()
        if not existente:
            admin = Usuario(
                nombre_usuario=nombre_admin,
                email=email_admin,
                hash_contrasena=contexto_hash.hash(contrasena_admin),
                rol="ADMIN",
                activo=True,
            )
            db.add(admin)
            db.commit()
            logger.info(f"Usuario ADMIN semilla creado: {nombre_admin}")
        else:
            logger.info(f"Usuario ADMIN semilla ya existe: {nombre_admin}")
        
        # Crear usuario USER de prueba si no existe
        nombre_user = os.environ.get("USER_USERNAME", "usuario")
        contrasena_user = os.environ.get("USER_PASSWORD", "usuario123")
        email_user = os.environ.get("USER_EMAIL", "usuario@empresa.com")
        
        existente_user = db.query(Usuario).filter(Usuario.nombre_usuario == nombre_user).first()
        if not existente_user:
            user = Usuario(
                nombre_usuario=nombre_user,
                email=email_user,
                hash_contrasena=contexto_hash.hash(contrasena_user),
                rol="USER",
                activo=True,
            )
            db.add(user)
            db.commit()
            logger.info(f"Usuario USER semilla creado: {nombre_user}")
        else:
            logger.info(f"Usuario USER semilla ya existe: {nombre_user}")
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Ciclo de vida de la aplicación
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Inicialización y apagado del servicio."""
    try:
        logger.info("Inicializando base de datos...")
        inicializar_db()
        crear_usuario_admin_semilla()
        logger.info("Conectando al broker de mensajes...")
        await broker.iniciar()
    except Exception as error:
        logger.error(f"Error al inicializar auth-service: {error}")
        sys.exit(1)
    yield
    await broker.detener()


# ─────────────────────────────────────────────────────────────────────────────
# Aplicación principal
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Auth Service",
    description=(
        "Servicio de autenticación y gestión de identidad.\n\n"
        "## Flujo de autenticación\n"
        "1. El empleado es creado → se genera cuenta inhabilitada automáticamente\n"
        "2. `notificaciones-service` envía el token de establecimiento por 'correo'\n"
        "3. El usuario llama `POST /auth/reset-password` para activar su cuenta\n"
        "4. El usuario llama `POST /auth/login` para obtener su JWT de acceso\n"
        "5. El JWT se envía en el header `Authorization: Bearer <token>` a la API Gateway\n\n"
        "## Seguridad\n"
        "- Contraseñas almacenadas con **BCrypt**\n"
        "- Tokens firmados con **HMAC SHA-256**\n"
        "- Token de recuperación es un JWT stateless con claim `type: RESET_PASSWORD`"
    ),
    version="1.0.0",
    lifespan=ciclo_de_vida,
)

app.include_router(router_auth)


# ─────────────────────────────────────────────────────────────────────────────
# Swagger con esquema BearerAuth
# ─────────────────────────────────────────────────────────────────────────────

def esquema_openapi_personalizado():
    """Agrega el esquema de seguridad BearerAuth a la documentación OpenAPI."""
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
    app.openapi_schema = esquema
    return esquema


app.openapi = esquema_openapi_personalizado


# ─────────────────────────────────────────────────────────────────────────────
# Manejadores de errores globales
# ─────────────────────────────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def manejador_validacion(request: Request, exc: RequestValidationError):
    errores = [
        {"campo": " → ".join(str(loc) for loc in e["loc"]), "mensaje": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Error de validación en los datos enviados.", "detalles": errores},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints generales
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["General"], summary="Estado del servicio")
async def raiz():
    """Verifica que el servicio de autenticación está en línea."""
    return {"mensaje": "Auth service activo", "version": "1.0.0", "documentacion": "/docs"}


@app.get("/health", tags=["General"], summary="Health check del servicio")
async def verificar_salud():
    """Verifica el estado del servicio y la conexión a la base de datos."""
    estado = {"status": "healthy", "servicio": "auth-service", "version": "1.0.0", "checks": {}}
    try:
        with motor.connect() as conn:
            conn.execute(text("SELECT 1"))
        estado["checks"]["base_de_datos"] = "ok"
    except Exception as error:
        estado["status"] = "unhealthy"
        estado["checks"]["base_de_datos"] = f"error: {str(error)}"
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=estado)
    return estado
