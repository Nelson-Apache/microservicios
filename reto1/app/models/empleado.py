from pydantic import BaseModel, Field


class Empleado(BaseModel):
    """
    Modelo Pydantic para representar un empleado.
    
    Attributes:
        id: Identificador único del empleado
        nombre: Nombre completo del empleado
        cargo: Cargo o posición del empleado en la empresa
    """
    id: int = Field(..., description="Identificador único del empleado", gt=0)
    nombre: str = Field(..., description="Nombre completo del empleado", min_length=1)
    cargo: str = Field(..., description="Cargo del empleado", min_length=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "nombre": "Juan Pérez",
                "cargo": "Desarrollador"
            }
        }
