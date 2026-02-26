from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from app.routes import empleados

# ─────────────────────────────────────────────────────────────────────────────
# Aplicación principal
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Servidor de Empleados",
    description=(
        "API REST para la gestión de empleados.\n\n"
        "## Características\n"
        "- Registro y consulta de empleados\n"
        "- Filtros por nombre, cargo, departamento y email\n"
        "- Paginación de resultados\n"
        "- Validación de duplicados"
    ),
    version="2.0.0",
)

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
