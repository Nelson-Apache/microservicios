from sqlalchemy import Column, Integer, String
from database import Base
class Empleado(Base):
    __tablename__ = "empleados"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    cargo = Column(String, nullable=False)