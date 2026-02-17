from fastapi import APIRouter, HTTPException, status
from typing import List
from app.models.empleado import Empleado
from app.database import db

# Crear el router para los endpoints de empleados
router = APIRouter(
    prefix="/empleados",
    tags=["empleados"]
)


@router.post("", response_model=Empleado, status_code=status.HTTP_200_OK)
async def registrar_empleado(empleado: Empleado):
    """
    Registra un nuevo empleado en el sistema.
    
    Args:
        empleado: Datos del empleado a registrar
        
    Returns:
        El empleado registrado
    """
    return db.crear_empleado(empleado)


@router.get("", response_model=List[Empleado], status_code=status.HTTP_200_OK)
async def obtener_todos_empleados():
    """
    Obtiene la lista de todos los empleados registrados.
    
    Returns:
        Lista de empleados (puede estar vacía)
    """
    return db.obtener_todos_empleados()


@router.get("/{id}", response_model=Empleado, status_code=status.HTTP_200_OK)
async def consultar_empleado(id: int):
    """
    Consulta la información de un empleado por su ID.
    
    Args:
        id: ID del empleado a consultar
        
    Returns:
        Los datos del empleado
        
    Raises:
        HTTPException: 404 si el empleado no existe
    """
    empleado = db.obtener_empleado(id)
    
    if empleado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El empleado con id {id} no existe"
        )
    
    return empleado
