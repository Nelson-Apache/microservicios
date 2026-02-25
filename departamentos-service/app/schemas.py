from pydantic import BaseModel
from typing import Optional

class DepartamentoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class DepartamentoCreate(DepartamentoBase):
    pass

class DepartamentoResponse(DepartamentoBase):
    id: str

    class Config:
        from_attributes = True