from sqlalchemy import Column, String
from .database import Base

class Departamento(Base):
    __tablename__ = "departamentos"

    id = Column(String, primary_key=True, index=True)
    nombre = Column(String)
    descripcion = Column(String)