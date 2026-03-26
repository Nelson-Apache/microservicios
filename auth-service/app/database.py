import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# URL de conexión a la base de datos del servicio de autenticación
URL_BASE_DATOS = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db-auth:5432/authdb"
)

motor = create_engine(URL_BASE_DATOS)
SesionLocal = sessionmaker(autocommit=False, autoflush=False, bind=motor)
Base = declarative_base()


class Usuario(Base):
    """Modelo de usuario del sistema de autenticación."""
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    # El nombre de usuario es el email del empleado
    nombre_usuario = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    # Nulo para cuentas creadas automáticamente (esperan que el usuario establezca contraseña)
    hash_contrasena = Column(String(255), nullable=True)
    # Rol: ADMIN o USER
    rol = Column(String(10), nullable=False, default="USER")
    # False hasta que el usuario establezca su contraseña vía reset-password
    activo = Column(Boolean, nullable=False, default=False)


def inicializar_db():
    """Crea todas las tablas en la base de datos si no existen."""
    Base.metadata.create_all(bind=motor)


def obtener_db():
    """Dependencia de FastAPI para obtener una sesión de base de datos."""
    db = SesionLocal()
    try:
        yield db
    finally:
        db.close()
