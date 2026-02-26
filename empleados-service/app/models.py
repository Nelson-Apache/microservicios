from sqlalchemy import Column, String, Date
from database import Base

class Empleado(Base):
    __tablename__ = "empleados"

    id = Column(String, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    email = Column(String, nullable=False)
    departamentoId = Column(String, nullable=False)
    fechaIngreso = Column(Date, nullable=False)
