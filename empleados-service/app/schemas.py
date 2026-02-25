from pydantic import BaseModel

class EmpleadoBase(BaseModel):
    nombre: str
    cargo: str

class EmpleadoCreate(EmpleadoBase):
    pass

class EmpleadoResponse(EmpleadoBase):
    id: int

    class Config:
        from_attributes = True