import models
import schemas
from fastapi import FastAPI, Depends, HTTPException, status
from database import engine, SessionLocal, Base
from sqlalchemy.orm import Session
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging

# Configuración de logs para observar los reintentos
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Servicio de Empleados",
    description=(
        "## Microservicio de Gestión de Empleados\n\n"
        "Gestiona el registro, consulta y listado de empleados en el sistema.\n\n"
        "### Validación de Departamentos\n"
        "Antes de registrar un empleado, este servicio valida que el `departamentoId` "
        "exista en el **Servicio de Departamentos** mediante una llamada HTTP REST.\n\n"
        "### Resiliencia\n"
        "- **Reintentos automáticos** (hasta 3) con espera exponencial usando `tenacity`\n"
        "- **Timeout** de 5 segundos en llamadas externas via `httpx`\n"
        "- Manejo de errores de comunicación intercervicio"
    ),
    version="2.0.0",
    contact={
        "name": "Equipo de Microservicios",
        "email": "soporte@empresa.com"
    },
    license_info={
        "name": "MIT"
    }
)

DEPARTAMENTOS_SERVICE_URL = "http://departamentos-service:8080/departamentos"

# Patrón de Resiliencia: Configuración de timeout para peticiones externas
EXTERNAL_TIMEOUT = 5.0  # segundos

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Patrón de Resiliencia: Reintentos con Tenacity
# Reintenta hasta 3 veces con espera exponencial si hay errores de red o el servicio no está listo
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.ConnectError, httpx.TimeoutException)),
    before_sleep=lambda retry_state: logger.info(f"Reintentando consulta de departamento (intento {retry_state.attempt_number})...")
)
async def validar_departamento_externo(departamento_id: str):
    async with httpx.AsyncClient(timeout=EXTERNAL_TIMEOUT) as client:
        response = await client.get(f"{DEPARTAMENTOS_SERVICE_URL}/{departamento_id}")
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True


@app.get(
    "/",
    tags=["Diagnóstico"],
    summary="Health Check",
    description="Verifica que el servicio de empleados está activo y responde correctamente.",
    responses={
        200: {"description": "Servicio operativo"}
    }
)
def read_root():
    """Endpoint raíz para verificar que el servicio está en línea."""
    return {"status": "ok", "service": "empleados-service", "version": "2.0.0", "docs": "/docs"}


@app.post(
    "/empleados",
    response_model=schemas.EmpleadoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Empleados"],
    summary="Registrar un nuevo empleado",
    description=(
        "Registra un nuevo empleado en el sistema. Antes de persistir el registro, "
        "valida que el `departamentoId` proporcionado exista en el Servicio de Departamentos. "
        "Si el departamento no existe, se retorna un error 400. "
        "Si hay problemas de comunicación con el servicio de departamentos tras los reintentos, "
        "se retorna un error 500."
    ),
    responses={
        201: {"description": "Empleado registrado exitosamente"},
        400: {"description": "Datos inválidos o el departamento especificado no existe"},
        422: {"description": "Error de validación en los datos de entrada"},
        500: {"description": "Error interno o falla en la comunicación con el servicio de departamentos"}
    }
)
async def crear_empleado(empleado: schemas.EmpleadoCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo empleado en el sistema.

    - **id**: Identificador único del empleado (ej: 'E001')
    - **nombre**: Nombre completo del empleado
    - **email**: Correo electrónico institucional (debe ser válido)
    - **departamentoId**: ID del departamento al que pertenece (debe existir en departamentos-service)
    - **fechaIngreso**: Fecha de ingreso en formato YYYY-MM-DD
    """
    try:
        departamento_existe = await validar_departamento_externo(empleado.departamentoId)
        if not departamento_existe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El departamento con ID '{empleado.departamentoId}' no existe."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error de comunicación tras reintentos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo validar el departamento debido a problemas de comunicación persistentes."
        )

    # Verificar si el ID de empleado ya existe
    existente = db.query(models.Empleado).filter(models.Empleado.id == empleado.id).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un empleado con el ID '{empleado.id}'."
        )

    db_empleado = models.Empleado(**empleado.model_dump())
    db.add(db_empleado)
    db.commit()
    db.refresh(db_empleado)
    return db_empleado


@app.get(
    "/empleados",
    response_model=list[schemas.EmpleadoResponse],
    tags=["Empleados"],
    summary="Listar todos los empleados",
    description="Retorna la lista completa de todos los empleados registrados en el sistema.",
    responses={
        200: {"description": "Lista de empleados obtenida exitosamente"},
        500: {"description": "Error interno del servidor"}
    }
)
def listar_empleados(db: Session = Depends(get_db)):
    """Retorna todos los empleados registrados en la base de datos."""
    return db.query(models.Empleado).all()


@app.get(
    "/empleados/{empleado_id}",
    response_model=schemas.EmpleadoResponse,
    tags=["Empleados"],
    summary="Obtener un empleado por ID",
    description="Busca y retorna la información completa de un empleado específico mediante su ID.",
    responses={
        200: {"description": "Empleado encontrado y retornado exitosamente"},
        404: {"description": "No existe ningún empleado con el ID proporcionado"},
        500: {"description": "Error interno del servidor"}
    }
)
def obtener_empleado(empleado_id: str, db: Session = Depends(get_db)):
    """
    Busca un empleado por su identificador único.

    - **empleado_id**: El identificador único del empleado (ej: 'E001')
    """
    empleado = db.query(models.Empleado).filter(models.Empleado.id == empleado_id).first()
    if not empleado:
        raise HTTPException(status_code=404, detail=f"Empleado con ID '{empleado_id}' no encontrado")
    return empleado
