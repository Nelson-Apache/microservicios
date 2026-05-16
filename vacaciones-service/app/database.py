import os
import enum
from typing import Optional, List, Tuple
from contextlib import contextmanager
from datetime import date, datetime

from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Enum as SAEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class EstadoVacacionDB(str, enum.Enum):
    PROGRAMADA = "PROGRAMADA"
    ACTIVA = "ACTIVA"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"


class VacacionModel(Base):
    __tablename__ = "vacaciones"

    id = Column(Integer, primary_key=True, index=True)
    empleado_id = Column(Integer, nullable=False, index=True)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    motivo = Column(String(500), nullable=True)
    estado = Column(SAEnum(EstadoVacacionDB), nullable=False, default=EstadoVacacionDB.PROGRAMADA)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SolapamientoError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class VacacionYaExisteError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class VacacionNoEncontradaError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/vacacionesdb"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    Base.metadata.create_all(bind=engine)


class VacacionesDB:

    @staticmethod
    def _modelo_a_dict(v: VacacionModel) -> dict:
        return {
            "id": v.id,
            "empleado_id": v.empleado_id,
            "fecha_inicio": v.fecha_inicio,
            "fecha_fin": v.fecha_fin,
            "motivo": v.motivo,
            "estado": v.estado.value if v.estado else "PROGRAMADA",
            "created_at": v.created_at,
        }

    def _verificar_solapamiento(self, session, empleado_id: int, fecha_inicio: date, fecha_fin: date, excluir_id: Optional[int] = None):
        query = session.query(VacacionModel).filter(
            VacacionModel.empleado_id == empleado_id,
            VacacionModel.estado.notin_([EstadoVacacionDB.CANCELADA, EstadoVacacionDB.FINALIZADA]),
            VacacionModel.fecha_inicio <= fecha_fin,
            VacacionModel.fecha_fin >= fecha_inicio,
        )
        if excluir_id is not None:
            query = query.filter(VacacionModel.id != excluir_id)
        if query.first():
            raise SolapamientoError(
                f"El empleado {empleado_id} ya tiene vacaciones programadas en ese período."
            )

    def crear_vacacion(
        self,
        id: int,
        empleado_id: int,
        fecha_inicio: date,
        fecha_fin: date,
        motivo: Optional[str] = None,
    ) -> dict:
        if fecha_fin < fecha_inicio:
            raise ValueError("fecha_fin debe ser mayor o igual a fecha_inicio.")

        with get_db_session() as session:
            existe = session.query(VacacionModel).filter(VacacionModel.id == id).first()
            if existe:
                raise VacacionYaExisteError(f"Ya existe una vacación con el id {id}.")

            self._verificar_solapamiento(session, empleado_id, fecha_inicio, fecha_fin)

            nueva = VacacionModel(
                id=id,
                empleado_id=empleado_id,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                motivo=motivo,
                estado=EstadoVacacionDB.PROGRAMADA,
            )
            session.add(nueva)
            session.commit()
            session.refresh(nueva)
            return self._modelo_a_dict(nueva)

    def actualizar_vacacion(
        self,
        vacacion_id: int,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        motivo: Optional[str] = None,
        estado: Optional[str] = None,
    ) -> dict:
        with get_db_session() as session:
            vacacion = session.query(VacacionModel).filter(VacacionModel.id == vacacion_id).first()
            if not vacacion:
                raise VacacionNoEncontradaError(f"No se encontró la vacación con id {vacacion_id}.")

            nueva_inicio = fecha_inicio or vacacion.fecha_inicio
            nueva_fin = fecha_fin or vacacion.fecha_fin

            if nueva_fin < nueva_inicio:
                raise ValueError("fecha_fin debe ser mayor o igual a fecha_inicio.")

            if fecha_inicio is not None or fecha_fin is not None:
                self._verificar_solapamiento(session, vacacion.empleado_id, nueva_inicio, nueva_fin, excluir_id=vacacion_id)

            if fecha_inicio is not None:
                vacacion.fecha_inicio = fecha_inicio
            if fecha_fin is not None:
                vacacion.fecha_fin = fecha_fin
            if motivo is not None:
                vacacion.motivo = motivo
            if estado is not None:
                vacacion.estado = EstadoVacacionDB(estado)

            vacacion.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(vacacion)
            return self._modelo_a_dict(vacacion)

    def cancelar_vacacion(self, vacacion_id: int) -> dict:
        with get_db_session() as session:
            vacacion = session.query(VacacionModel).filter(VacacionModel.id == vacacion_id).first()
            if not vacacion:
                raise VacacionNoEncontradaError(f"No se encontró la vacación con id {vacacion_id}.")

            vacacion.estado = EstadoVacacionDB.CANCELADA
            vacacion.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(vacacion)
            return self._modelo_a_dict(vacacion)

    def obtener_vacacion(self, vacacion_id: int) -> Optional[dict]:
        with get_db_session() as session:
            vacacion = session.query(VacacionModel).filter(VacacionModel.id == vacacion_id).first()
            return self._modelo_a_dict(vacacion) if vacacion else None

    def buscar_vacaciones(
        self,
        empleado_id: Optional[int] = None,
        pagina: int = 1,
        por_pagina: int = 10,
    ) -> Tuple[List[dict], int]:
        with get_db_session() as session:
            query = session.query(VacacionModel)
            if empleado_id is not None:
                query = query.filter(VacacionModel.empleado_id == empleado_id)

            total = query.count()
            vacaciones = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()
            return [self._modelo_a_dict(v) for v in vacaciones], total


db = VacacionesDB()
