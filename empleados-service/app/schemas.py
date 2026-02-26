from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional

class EmpleadoBase(BaseModel):
    nombre: str = Field(..., description="Nombre completo del empleado", example="Juan Pérez")
    email: EmailStr = Field(..., description="Correo electrónico institucional", example="juan.perez@empresa.com")
    departamentoId: str = Field(..., description="Identificador único del departamento asociado", example="DEP-01")
    fechaIngreso: date = Field(..., description="Fecha de ingreso a la empresa (YYYY-MM-DD)", example="2024-01-15")

class EmpleadoCreate(EmpleadoBase):
    id: str = Field(..., description="Identificador único manual para el empleado", example="EMP-001")

class EmpleadoResponse(EmpleadoBase):
    id: str = Field(..., description="Identificador único del empleado")

    class Config:
        from_attributes = True

