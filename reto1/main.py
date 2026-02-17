from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.routes import empleados

# Crear la aplicación FastAPI
app = FastAPI(
    title="Servidor de Empleados",
    description="API REST para la gestión de empleados",
    version="1.0.0"
)

# Incluir los routers
app.include_router(empleados.router)


@app.get("/")
async def root():
    """
    Endpoint raíz para verificar que el servidor está funcionando.
    """
    return {"mensaje": "Servidor de empleados activo"}


@app.exception_handler(404)
async def custom_404_handler(request, exc):
    """
    Manejador personalizado para errores 404.
    """
    return JSONResponse(
        status_code=404,
        content={"detail": "Recurso no encontrado"}
    )
