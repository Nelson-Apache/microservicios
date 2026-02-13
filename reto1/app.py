from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict

# Crear la aplicación FastAPI
app = FastAPI(title="Servidor de Empleados")

# Modelo Pydantic para validación de datos
class Empleado(BaseModel):
    id: int
    nombre: str
    cargo: str

# Almacenamiento en memoria
empleados_db: Dict[int, Empleado] = {}

@app.post("/empleados", status_code=200)
async def registrar_empleado(empleado: Empleado):
    """
    Registra un nuevo empleado en el sistema.
    """
    empleados_db[empleado.id] = empleado
    return empleado

@app.get("/empleados/{id}", status_code=200)
async def consultar_empleado(id: int):
    """
    Consulta la información de un empleado por su ID.
    """
    if id not in empleados_db:
        raise HTTPException(
            status_code=404,
            detail=f"El empleado con id {id} no existe"
        )
    return empleados_db[id]

# Manejador personalizado para rutas no encontradas
@app.exception_handler(404)
async def custom_404_handler(request, exc):
    return {"detail": "Recurso no encontrado"}

# Endpoint raíz para verificar que el servidor está funcionando
@app.get("/")
async def root():
    return {"mensaje": "Servidor de empleados activo"}
