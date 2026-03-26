from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.openapi.utils import get_openapi
import httpx
from jose import jwt, JWTError
import os
import logging
from pythonjsonlogger import jsonlogger


# ─────────────────────────────────────────────────────────────────────────────
# Configuración de logging estructurado en JSON
# ─────────────────────────────────────────────────────────────────────────────

class FormateadorJsonGateway(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["servicio"] = "api-gateway"
        log_record["nivel"] = record.levelname


manejador_log = logging.StreamHandler()
manejador_log.setFormatter(FormateadorJsonGateway("%(timestamp)s %(nivel)s %(name)s %(message)s"))
logger_raiz = logging.getLogger()
logger_raiz.addHandler(manejador_log)
logger_raiz.setLevel(logging.INFO)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Configuración de seguridad JWT
# ─────────────────────────────────────────────────────────────────────────────

# La misma clave secreta usada por auth-service (inyectada vía variable de entorno)
CLAVE_SECRETA = os.environ.get("JWT_SECRET", "changeme-super-secret-key-for-dev")
ALGORITMO = "HS256"

# Métodos que solo puede ejecutar el rol ADMIN
METODOS_SOLO_ADMIN = {"POST", "PUT", "DELETE", "PATCH"}

# Rutas que no requieren token JWT (acceso público)
PREFIJOS_PUBLICOS = ["/auth/", "/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"]


# ─────────────────────────────────────────────────────────────────────────────
# Mapa de servicios internos (nombre_prefijo → URL interna del contenedor)
# ─────────────────────────────────────────────────────────────────────────────

SERVICIOS = {
    "auth":           os.environ.get("AUTH_SERVICE_URL",           "http://auth-service:8085"),
    "empleados":      os.environ.get("EMPLEADOS_SERVICE_URL",      "http://empleados-service:8080"),
    "departamentos":  os.environ.get("DEPARTAMENTOS_SERVICE_URL",  "http://departamentos-service:8080"),
    "notificaciones": os.environ.get("NOTIFICACIONES_SERVICE_URL", "http://notificaciones-service:3000"),
    "perfiles":       os.environ.get("PERFILES_SERVICE_URL",       "http://perfiles-service:3000"),
    "reportes":       os.environ.get("REPORTES_SERVICE_URL",       "http://reportes-service:3000"),
}


# ─────────────────────────────────────────────────────────────────────────────
# Aplicación FastAPI
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="API Gateway",
    description=(
        "Punto de entrada centralizado para el ecosistema de microservicios.\n\n"
        "## Autenticación\n"
        "1. Obtener token → `POST /auth/login`\n"
        "2. Incluir el token en todas las peticiones protegidas:\n"
        "   ```\n"
        "   Authorization: Bearer <token_jwt>\n"
        "   ```\n\n"
        "## Roles y permisos (RBAC)\n"
        "| Rol   | Métodos permitidos |\n"
        "|-------|--------------------|\n"
        "| ADMIN | GET, POST, PUT, DELETE, PATCH |\n"
        "| USER  | Solo GET |\n\n"
        "## Enrutamiento\n"
        "| Prefijo de ruta      | Servicio destino         |\n"
        "|----------------------|--------------------------|\n"
        "| `/auth/*`            | auth-service :8085       |\n"
        "| `/empleados/*`       | empleados-service :8080  |\n"
        "| `/departamentos/*`   | departamentos-service :8081 |\n"
        "| `/notificaciones/*`  | notificaciones-service :8082 |\n"
        "| `/perfiles/*`        | perfiles-service :8084   |\n"
        "| `/reportes/*`        | reportes-service :8083   |"
    ),
    version="1.0.0",
)


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
    # Aplicar BearerAuth globalmente a todas las rutas (excepto las públicas)
    esquema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = esquema
    return esquema


app.openapi = esquema_openapi_personalizado


# ─────────────────────────────────────────────────────────────────────────────
# Funciones auxiliares
# ─────────────────────────────────────────────────────────────────────────────

def es_ruta_publica(ruta: str) -> bool:
    """Retorna True si la ruta no requiere autenticación JWT."""
    return any(ruta.startswith(prefijo) for prefijo in PREFIJOS_PUBLICOS)


def validar_y_obtener_payload(cabecera_autorizacion: str | None) -> dict:
    """
    Extrae y valida el JWT del header Authorization.
    Lanza JSONResponse con 401 si el token falta o es inválido.
    """
    if not cabecera_autorizacion or not cabecera_autorizacion.startswith("Bearer "):
        raise _error_401("Token JWT requerido. Incluya 'Authorization: Bearer <token>'.")
    token = cabecera_autorizacion.split(" ", 1)[1]
    try:
        return jwt.decode(token, CLAVE_SECRETA, algorithms=[ALGORITMO])
    except JWTError:
        raise _error_401("Token inválido o expirado.")


def verificar_rbac(metodo: str, rol: str) -> None:
    """
    Verifica que el rol tenga permisos para el método HTTP solicitado.
    Lanza JSONResponse con 403 si el rol no tiene acceso.
    """
    if metodo in METODOS_SOLO_ADMIN and rol != "ADMIN":
        raise _error_403(f"El rol '{rol}' no tiene permiso para ejecutar {metodo}. Se requiere rol ADMIN.")


def _error_401(detalle: str):
    return _ErrorHTTP(
        JSONResponse(
            status_code=401,
            content={"error": "No autorizado", "detalle": detalle},
            headers={"WWW-Authenticate": "Bearer"},
        )
    )


def _error_403(detalle: str):
    return _ErrorHTTP(
        JSONResponse(status_code=403, content={"error": "Acceso prohibido", "detalle": detalle})
    )


class _ErrorHTTP(Exception):
    """Excepción interna para propagar respuestas de error HTTP."""
    def __init__(self, respuesta: JSONResponse):
        self.respuesta = respuesta


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints propios del gateway
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Gateway"], summary="Health check del gateway")
async def verificar_salud():
    """Verifica que el API Gateway está operativo."""
    return {"status": "healthy", "servicio": "api-gateway", "version": "1.0.0"}


# ─────────────────────────────────────────────────────────────────────────────
# Proxy inverso — catch-all
# ─────────────────────────────────────────────────────────────────────────────

@app.api_route(
    "/{ruta:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    tags=["Proxy"],
    summary="Enruta la petición al microservicio correspondiente",
    include_in_schema=False,  # No listar en Swagger (ruta dinámica)
)
async def proxy(request: Request, ruta: str):
    """
    Intercepta todas las peticiones, valida el JWT (si la ruta lo requiere),
    verifica el RBAC y reenvía la petición al microservicio destino.
    """
    ruta_completa = f"/{ruta}"

    # 1. Validar JWT y RBAC (si la ruta no es pública)
    if not es_ruta_publica(ruta_completa):
        try:
            payload = validar_y_obtener_payload(request.headers.get("Authorization"))
            rol = payload.get("role", "USER")
            verificar_rbac(request.method, rol)
        except _ErrorHTTP as error_http:
            return error_http.respuesta

    # 2. Determinar el servicio destino según el primer segmento de la ruta
    primer_segmento = ruta.split("/")[0]
    url_servicio = SERVICIOS.get(primer_segmento)

    if not url_servicio:
        logger.warning(f"Ruta sin servicio destino: {ruta_completa}")
        return JSONResponse(
            status_code=404,
            content={"error": "Ruta no encontrada en el gateway.", "ruta": ruta_completa},
        )

    # 3. Construir URL de destino (incluyendo query string)
    url_destino = f"{url_servicio}/{ruta}"
    if request.url.query:
        url_destino += f"?{request.url.query}"

    # 4. Reenviar la petición al servicio destino
    cabeceras = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding")
    }
    cuerpo = await request.body()

    try:
        async with httpx.AsyncClient(timeout=30.0) as cliente:
            respuesta = await cliente.request(
                method=request.method,
                url=url_destino,
                headers=cabeceras,
                content=cuerpo,
                follow_redirects=True,
            )
            logger.info(
                f"Petición proxy exitosa",
                extra={
                    "metodo": request.method,
                    "ruta": ruta_completa,
                    "destino": url_destino,
                    "codigo_estado": respuesta.status_code,
                }
            )
            # Filtrar cabeceras que no deben reenviarse al cliente
            cabeceras_respuesta = {
                k: v for k, v in respuesta.headers.items()
                if k.lower() not in ("transfer-encoding", "content-encoding")
            }
            return Response(
                content=respuesta.content,
                status_code=respuesta.status_code,
                headers=cabeceras_respuesta,
                media_type=respuesta.headers.get("content-type"),
            )
    except httpx.ConnectError:
        logger.error(f"Servicio no disponible: {url_servicio}")
        return JSONResponse(
            status_code=503,
            content={
                "error": "Servicio no disponible.",
                "servicio": primer_segmento,
                "detalle": f"No se pudo conectar con {url_servicio}",
            },
        )
    except httpx.TimeoutException:
        logger.error(f"Timeout al contactar: {url_servicio}")
        return JSONResponse(
            status_code=504,
            content={"error": "Timeout del servicio destino.", "servicio": primer_segmento},
        )
