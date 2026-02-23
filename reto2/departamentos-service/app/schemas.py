from pydantic import BaseModel

class DepartamentoBase(BaseModel):
    id: str
    nombre: str
    descripcion: str

class DepartamentoCreate(DepartamentoBase):
    pass

class DepartamentoResponse(DepartamentoBase):
    class Config:
        from_attributes = True