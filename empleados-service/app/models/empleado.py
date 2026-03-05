from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class Empleado(BaseModel):
    """
    Modelo Pydantic para representar un empleado.

    Attributes:
        id: Identificador único del empleado
        nombre: Nombre completo del empleado
        cargo: Cargo o posición del empleado en la empresa
        departamento_id: ID del departamento al que pertenece
        email: Correo electrónico del empleado
        salario: Salario del empleado
        fecha_ingreso: Fecha de ingreso a la empresa
        activo: Indica si el empleado está activo
    """
    id: int = Field(..., description="Identificador único del empleado", gt=0)
    nombre: str = Field(..., description="Nombre completo del empleado", min_length=1, max_length=100)
    cargo: str = Field(..., description="Cargo del empleado", min_length=1, max_length=100)
    departamento_id: Optional[int] = Field(None, description="ID del departamento", gt=0)
    email: Optional[EmailStr] = Field(None, description="Correo electrónico del empleado", max_length=150)
    salario: Optional[float] = Field(None, description="Salario del empleado", ge=0)
    fecha_ingreso: Optional[str] = Field(None, description="Fecha de ingreso (ISO format)")
    activo: Optional[bool] = Field(True, description="Indica si el empleado está activo")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "nombre": "Juan Pérez",
                "cargo": "Desarrollador",
                "departamento_id": 1,
                "email": "juan.perez@empresa.com",
                "salario": 50000.0,
                "fecha_ingreso": "2024-01-15T00:00:00",
                "activo": True
            }
        }


class EmpleadoCreate(BaseModel):
    """
    Modelo para crear un nuevo empleado.
    """
    id: int = Field(..., description="Identificador único del empleado", gt=0)
    nombre: str = Field(..., description="Nombre completo del empleado", min_length=1, max_length=100)
    cargo: str = Field(..., description="Cargo del empleado", min_length=1, max_length=100)
    departamento_id: Optional[int] = Field(None, description="ID del departamento", gt=0)
    email: Optional[EmailStr] = Field(None, description="Correo electrónico del empleado")
    salario: Optional[float] = Field(None, description="Salario del empleado", ge=0)
    fecha_ingreso: Optional[datetime] = Field(None, description="Fecha de ingreso")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "nombre": "Juan Pérez",
                "cargo": "Desarrollador",
                "departamento_id": 1,
                "email": "juan.perez@empresa.com",
                "salario": 50000.0
            }
        }


class EmpleadoUpdate(BaseModel):
    """
    Modelo para actualizar un empleado existente.
    Todos los campos son opcionales.
    """
    nombre: Optional[str] = Field(None, description="Nombre completo del empleado", min_length=1, max_length=100)
    cargo: Optional[str] = Field(None, description="Cargo del empleado", min_length=1, max_length=100)
    departamento_id: Optional[int] = Field(None, description="ID del departamento", gt=0)
    email: Optional[EmailStr] = Field(None, description="Correo electrónico del empleado")
    salario: Optional[float] = Field(None, description="Salario del empleado", ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "cargo": "Senior Developer",
                "salario": 60000.0
            }
        }


class PaginatedEmpleados(BaseModel):
    """
    Respuesta paginada de empleados.

    Attributes:
        total: Total de empleados que coinciden con los filtros
        pagina: Página actual
        por_pagina: Cantidad de empleados por página
        total_paginas: Total de páginas disponibles
        empleados: Lista de empleados en la página actual
    """
    total: int = Field(..., description="Total de registros que coinciden con los filtros")
    pagina: int = Field(..., description="Página actual")
    por_pagina: int = Field(..., description="Registros por página")
    total_paginas: int = Field(..., description="Total de páginas")
    empleados: List[Empleado] = Field(..., description="Lista de empleados en esta página")
