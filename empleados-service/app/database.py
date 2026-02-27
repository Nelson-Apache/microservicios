import os
from typing import Optional, List, Tuple
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

# Base de SQLAlchemy
Base = declarative_base()


# ─────────────────────────────────────────
# Modelo SQLAlchemy
# ─────────────────────────────────────────

class EmpleadoModel(Base):
    """
    Modelo de base de datos para empleados usando SQLAlchemy.
    """
    __tablename__ = "empleados"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, index=True)
    cargo = Column(String(100), nullable=False, index=True)
    departamento_id = Column(Integer, nullable=True, index=True)
    email = Column(String(150), nullable=True, unique=True)
    salario = Column(Float, nullable=True)
    fecha_ingreso = Column(DateTime, nullable=False, default=datetime.utcnow)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─────────────────────────────────────────
# Excepciones personalizadas
# ─────────────────────────────────────────

class EmpleadoYaExisteError(Exception):
    """Error lanzado cuando se intenta crear un empleado con un ID o email duplicado."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class EmpleadoNoEncontradoError(Exception):
    """Error lanzado cuando no se encuentra un empleado."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


# ─────────────────────────────────────────
# Configuración de base de datos
# ─────────────────────────────────────────

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/empleadosdb"
)

# Crear engine con pool de conexiones
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,  # Verifica conexiones antes de usar
    echo=False  # Cambiar a True para debug SQL
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ─────────────────────────────────────────
# Context manager para sesiones
# ─────────────────────────────────────────

@contextmanager
def get_db_session():
    """
    Context manager para gestionar sesiones de base de datos.
    Asegura que las sesiones se cierren correctamente.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ─────────────────────────────────────────
# Inicialización de base de datos
# ─────────────────────────────────────────

def init_db():
    """
    Inicializa la base de datos creando todas las tablas.
    """
    Base.metadata.create_all(bind=engine)


# ─────────────────────────────────────────
# Clase de repositorio
# ─────────────────────────────────────────

class EmpleadosDB:
    """
    Repositorio para gestionar operaciones CRUD de empleados con PostgreSQL.
    """

    # ─────────────────────────────────────────
    # Conversión entre modelos
    # ─────────────────────────────────────────

    @staticmethod
    def _modelo_a_dict(empleado_model: EmpleadoModel) -> dict:
        """Convierte un EmpleadoModel de SQLAlchemy a diccionario."""
        return {
            "id": empleado_model.id,
            "nombre": empleado_model.nombre,
            "cargo": empleado_model.cargo,
            "departamento_id": empleado_model.departamento_id,
            "email": empleado_model.email,
            "salario": empleado_model.salario,
            "fecha_ingreso": empleado_model.fecha_ingreso.isoformat() if empleado_model.fecha_ingreso else None,
            "activo": empleado_model.activo,
        }

    # ─────────────────────────────────────────
    # Escritura
    # ─────────────────────────────────────────

    def crear_empleado(
        self,
        id: int,
        nombre: str,
        cargo: str,
        departamento_id: Optional[int] = None,
        email: Optional[str] = None,
        salario: Optional[float] = None,
        fecha_ingreso: Optional[datetime] = None
    ) -> dict:
        """
        Registra un nuevo empleado en la base de datos.

        Raises:
            EmpleadoYaExisteError: Si el ID ya está registrado o el email está duplicado.
        """
        with get_db_session() as session:
            # Validar ID duplicado
            existe = session.query(EmpleadoModel).filter(EmpleadoModel.id == id).first()
            if existe:
                raise EmpleadoYaExisteError(f"Ya existe un empleado con el id {id}.")

            # Validar email duplicado (si se proporciona)
            if email:
                existe_email = session.query(EmpleadoModel).filter(
                    EmpleadoModel.email == email
                ).first()
                if existe_email:
                    raise EmpleadoYaExisteError(f"Ya existe un empleado con el email {email}.")

            # Crear nuevo empleado
            nuevo_empleado = EmpleadoModel(
                id=id,
                nombre=nombre,
                cargo=cargo,
                departamento_id=departamento_id,
                email=email,
                salario=salario,
                fecha_ingreso=fecha_ingreso or datetime.utcnow(),
                activo=True
            )

            session.add(nuevo_empleado)
            session.commit()
            session.refresh(nuevo_empleado)

            return self._modelo_a_dict(nuevo_empleado)

    def actualizar_empleado(
        self,
        empleado_id: int,
        nombre: Optional[str] = None,
        cargo: Optional[str] = None,
        departamento_id: Optional[int] = None,
        email: Optional[str] = None,
        salario: Optional[float] = None,
    ) -> dict:
        """
        Actualiza un empleado existente.

        Raises:
            EmpleadoNoEncontradoError: Si el empleado no existe.
            EmpleadoYaExisteError: Si el email ya está en uso por otro empleado.
        """
        with get_db_session() as session:
            empleado = session.query(EmpleadoModel).filter(
                EmpleadoModel.id == empleado_id,
                EmpleadoModel.activo == True
            ).first()

            if not empleado:
                raise EmpleadoNoEncontradoError(f"No se encontró el empleado con id {empleado_id}.")

            # Validar email duplicado (si se cambia)
            if email and email != empleado.email:
                existe_email = session.query(EmpleadoModel).filter(
                    EmpleadoModel.email == email,
                    EmpleadoModel.id != empleado_id
                ).first()
                if existe_email:
                    raise EmpleadoYaExisteError(f"Ya existe un empleado con el email {email}.")

            # Actualizar campos
            if nombre is not None:
                empleado.nombre = nombre
            if cargo is not None:
                empleado.cargo = cargo
            if departamento_id is not None:
                empleado.departamento_id = departamento_id
            if email is not None:
                empleado.email = email
            if salario is not None:
                empleado.salario = salario

            empleado.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(empleado)

            return self._modelo_a_dict(empleado)

    def eliminar_empleado(self, empleado_id: int) -> bool:
        """
        Elimina (soft delete) un empleado.

        Returns:
            True si se eliminó, False si no existía.
        """
        with get_db_session() as session:
            empleado = session.query(EmpleadoModel).filter(
                EmpleadoModel.id == empleado_id,
                EmpleadoModel.activo == True
            ).first()

            if not empleado:
                return False

            empleado.activo = False
            empleado.updated_at = datetime.utcnow()
            session.commit()

            return True

    # ─────────────────────────────────────────
    # Lectura individual
    # ─────────────────────────────────────────

    def obtener_empleado(self, empleado_id: int) -> Optional[dict]:
        """
        Obtiene un empleado por su ID.

        Returns:
            Diccionario con datos del empleado si existe, None en caso contrario.
        """
        with get_db_session() as session:
            empleado = session.query(EmpleadoModel).filter(
                EmpleadoModel.id == empleado_id,
                EmpleadoModel.activo == True
            ).first()

            if empleado:
                return self._modelo_a_dict(empleado)
            return None

    def existe_empleado(self, empleado_id: int) -> bool:
        """Verifica si un empleado existe por su ID."""
        with get_db_session() as session:
            existe = session.query(EmpleadoModel).filter(
                EmpleadoModel.id == empleado_id,
                EmpleadoModel.activo == True
            ).first()
            return existe is not None

    # ─────────────────────────────────────────
    # Lectura con filtros y paginación
    # ─────────────────────────────────────────

    def obtener_todos_empleados(self) -> List[dict]:
        """Obtiene todos los empleados activos sin filtros ni paginación."""
        with get_db_session() as session:
            empleados = session.query(EmpleadoModel).filter(
                EmpleadoModel.activo == True
            ).all()
            return [self._modelo_a_dict(emp) for emp in empleados]

    def buscar_empleados(
        self,
        nombre: Optional[str] = None,
        cargo: Optional[str] = None,
        departamento_id: Optional[int] = None,
        email: Optional[str] = None,
        pagina: int = 1,
        por_pagina: int = 10,
    ) -> Tuple[List[dict], int]:
        """
        Busca empleados aplicando filtros opcionales y paginación.

        Args:
            nombre: Filtro parcial (case-insensitive) por nombre.
            cargo: Filtro parcial (case-insensitive) por cargo.
            departamento_id: Filtro por ID de departamento.
            email: Filtro parcial (case-insensitive) por email.
            pagina: Número de página (1-indexed).
            por_pagina: Cantidad de registros por página.

        Returns:
            Tupla (lista_de_empleados_en_pagina, total_de_coincidencias).
        """
        with get_db_session() as session:
            query = session.query(EmpleadoModel).filter(EmpleadoModel.activo == True)

            # Aplicar filtros
            if nombre:
                query = query.filter(EmpleadoModel.nombre.ilike(f"%{nombre}%"))

            if cargo:
                query = query.filter(EmpleadoModel.cargo.ilike(f"%{cargo}%"))

            if departamento_id is not None:
                query = query.filter(EmpleadoModel.departamento_id == departamento_id)

            if email:
                query = query.filter(EmpleadoModel.email.ilike(f"%{email}%"))

            # Contar total
            total = query.count()

            # Aplicar paginación
            empleados = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()

            return [self._modelo_a_dict(emp) for emp in empleados], total


# Instancia global de la base de datos
db = EmpleadosDB()