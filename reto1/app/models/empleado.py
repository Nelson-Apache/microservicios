from pydantic import BaseModel, Field
from typing import Optional, List


class Empleado(BaseModel):
    """
    Modelo Pydantic para representar un empleado.

    Attributes:
        id: Identificador único del empleado
        nombre: Nombre completo del empleado
        cargo: Cargo o posición del empleado en la empresa
        departamento: Departamento al que pertenece el empleado
        email: Correo electrónico del empleado
    """
    id: int = Field(..., description="Identificador único del empleado", gt=0)
    nombre: str = Field(..., description="Nombre completo del empleado", min_length=1, max_length=100)
    cargo: str = Field(..., description="Cargo del empleado", min_length=1, max_length=100)
    departamento: Optional[str] = Field(None, description="Departamento del empleado", max_length=100)
    email: Optional[str] = Field(None, description="Correo electrónico del empleado", max_length=150)

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "nombre": "Juan Pérez",
                "cargo": "Desarrollador",
                "departamento": "Tecnología",
                "email": "juan.perez@empresa.com"
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
