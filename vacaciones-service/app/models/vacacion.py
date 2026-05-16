import enum
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class EstadoVacacion(str, enum.Enum):
    PROGRAMADA = "PROGRAMADA"
    ACTIVA = "ACTIVA"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"


class Vacacion(BaseModel):
    id: int = Field(..., gt=0)
    empleado_id: int = Field(..., gt=0)
    fecha_inicio: date
    fecha_fin: date
    motivo: Optional[str] = None
    estado: EstadoVacacion = EstadoVacacion.PROGRAMADA
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "empleado_id": 10,
                "fecha_inicio": "2026-07-01",
                "fecha_fin": "2026-07-15",
                "motivo": "Vacaciones de verano",
                "estado": "PROGRAMADA",
                "created_at": "2026-05-15T00:00:00"
            }
        }


class VacacionCreate(BaseModel):
    id: int = Field(..., gt=0)
    empleado_id: int = Field(..., gt=0)
    fecha_inicio: date
    fecha_fin: date
    motivo: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "empleado_id": 10,
                "fecha_inicio": "2026-07-01",
                "fecha_fin": "2026-07-15",
                "motivo": "Vacaciones de verano"
            }
        }


class VacacionUpdate(BaseModel):
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    motivo: Optional[str] = None
    estado: Optional[EstadoVacacion] = None


class PaginatedVacaciones(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int
    vacaciones: List[Vacacion]
