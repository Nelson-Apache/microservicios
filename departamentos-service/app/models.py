from sqlalchemy import Column, Integer, String
from database import Base
import uuid

class Departamento(Base):
    __tablename__ = "departamentos"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)