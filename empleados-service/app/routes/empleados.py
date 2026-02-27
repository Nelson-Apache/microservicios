from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional
from math import ceil
from app.models.empleado import Empleado, EmpleadoCreate, EmpleadoUpdate, PaginatedEmpleados
from app.database import db, EmpleadoYaExisteError, EmpleadoNoEncontradoError
from app.clients.departamentos_client import (
    departamentos_client,
    DepartamentoNoEncontradoError,
    DepartamentosServiceError
)
import logging

logger = logging.getLogger(__name__)

# Router de empleados
router = APIRouter(
    prefix="/empleados",
    tags=["empleados"]
)


# ─────────────────────────────────────────────────────────────────────────────
# POST /empleados  — Registrar empleado
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=Empleado,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo empleado",
    responses={
        400: {"description": "Departamento no existe"},
        409: {"description": "El empleado ya existe (ID o email duplicado)"},
        422: {"description": "Datos de entrada inválidos"},
        503: {"description": "Servicio de departamentos no disponible"},
    },
)
async def registrar_empleado(empleado: EmpleadoCreate):
    """
    Registra un nuevo empleado en el sistema.

    - Valida que el **ID** no esté duplicado.
    - Valida que el **email** no esté duplicado (si se proporciona).
    - Valida que el **departamento_id** exista (si se proporciona).
    """
    logger.info(
        "Solicitud de registro de empleado",
        extra={
            "event": "empleado_create_request",
            "empleado_id": empleado.id,
            "departamento_id": empleado.departamento_id
        }
    )
    
    # Validar departamento si se proporciona
    if empleado.departamento_id is not None:
        try:
            await departamentos_client.validar_departamento_existe(empleado.departamento_id)
            logger.info(
                "Departamento validado exitosamente",
                extra={"event": "departamento_validated", "departamento_id": empleado.departamento_id}
            )
        except DepartamentoNoEncontradoError as e:
            logger.warning(
                "Departamento no encontrado",
                extra={"event": "departamento_not_found", "departamento_id": empleado.departamento_id}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=e.message,
            )
        except DepartamentosServiceError as e:
            logger.error(
                "Error al validar departamento",
                extra={"event": "departamento_validation_error", "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No se pudo validar el departamento: {e.message}",
            )

    # Crear empleado
    try:
        empleado_dict = db.crear_empleado(
            id=empleado.id,
            nombre=empleado.nombre,
            cargo=empleado.cargo,
            departamento_id=empleado.departamento_id,
            email=empleado.email,
            salario=empleado.salario,
            fecha_ingreso=empleado.fecha_ingreso
        )
        logger.info(
            "Empleado creado exitosamente",
            extra={"event": "empleado_created", "empleado_id": empleado.id}
        )
        return Empleado(**empleado_dict)
    except EmpleadoYaExisteError as e:
        logger.warning(
            "Intento de crear empleado duplicado",
            extra={"event": "empleado_duplicate", "empleado_id": empleado.id}
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )


# ─────────────────────────────────────────────────────────────────────────────
# GET /empleados  — Listar con filtros y paginación
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=PaginatedEmpleados,
    status_code=status.HTTP_200_OK,
    summary="Listar empleados con filtros y paginación",
    responses={
        400: {"description": "Parámetros de paginación inválidos"},
    },
)
async def obtener_todos_empleados(
    nombre: Optional[str] = Query(None, description="Filtrar por nombre (búsqueda parcial)"),
    cargo: Optional[str] = Query(None, description="Filtrar por cargo (búsqueda parcial)"),
    departamento_id: Optional[int] = Query(None, description="Filtrar por ID de departamento"),
    email: Optional[str] = Query(None, description="Filtrar por email (búsqueda parcial)"),
    pagina: int = Query(1, ge=1, description="Número de página (inicia en 1)"),
    por_pagina: int = Query(10, ge=1, le=100, description="Registros por página (máx. 100)"),
):
    """
    Devuelve la lista de empleados de forma paginada con filtros opcionales.

    **Filtros disponibles** (todos opcionales, búsqueda parcial insensible a mayúsculas):
    - `nombre`
    - `cargo`
    - `departamento_id`
    - `email`

    **Paginación**: use `pagina` y `por_pagina` para navegar por los resultados.
    """
    empleados_pagina, total = db.buscar_empleados(
        nombre=nombre,
        cargo=cargo,
        departamento_id=departamento_id,
        email=email,
        pagina=pagina,
        por_pagina=por_pagina,
    )

    total_paginas = ceil(total / por_pagina) if total > 0 else 1

    empleados_models = [Empleado(**emp) for emp in empleados_pagina]

    return PaginatedEmpleados(
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=total_paginas,
        empleados=empleados_models,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /empleados/{id}  — Consultar empleado por ID
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{id}",
    response_model=Empleado,
    status_code=status.HTTP_200_OK,
    summary="Consultar un empleado por ID",
    responses={
        400: {"description": "ID inválido (debe ser un entero positivo)"},
        404: {"description": "Empleado no encontrado"},
    },
)
async def consultar_empleado(id: int):
    """
    Consulta la información de un empleado por su **ID**.

    Retorna 404 si el empleado no existe.
    """
    if id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ID debe ser un número entero mayor que 0.",
        )

    empleado_dict = db.obtener_empleado(id)

    if empleado_dict is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún empleado con el id {id}.",
        )

    return Empleado(**empleado_dict)


# ─────────────────────────────────────────────────────────────────────────────
# PUT /empleados/{id}  — Actualizar empleado
# ─────────────────────────────────────────────────────────────────────────────

@router.put(
    "/{id}",
    response_model=Empleado,
    status_code=status.HTTP_200_OK,
    summary="Actualizar un empleado existente",
    responses={
        400: {"description": "Departamento no existe"},
        404: {"description": "Empleado no encontrado"},
        409: {"description": "Email duplicado con otro empleado"},
        422: {"description": "Datos de entrada inválidos"},
        503: {"description": "Servicio de departamentos no disponible"},
    },
)
async def actualizar_empleado(id: int, empleado: EmpleadoUpdate):
    """
    Actualiza la información de un empleado existente.

    - Todos los campos son opcionales.
    - Solo se actualizan los campos proporcionados.
    - Valida que el **email** no esté duplicado con otro empleado (si se cambia).
    - Valida que el **departamento_id** exista (si se cambia).
    """
    if id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ID debe ser un número entero mayor que 0.",
        )

    # Validar departamento si se proporciona
    if empleado.departamento_id is not None:
        try:
            await departamentos_client.validar_departamento_existe(empleado.departamento_id)
        except DepartamentoNoEncontradoError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=e.message,
            )
        except DepartamentosServiceError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No se pudo validar el departamento: {e.message}",
            )

    try:
        empleado_dict = db.actualizar_empleado(
            empleado_id=id,
            nombre=empleado.nombre,
            cargo=empleado.cargo,
            departamento_id=empleado.departamento_id,
            email=empleado.email,
            salario=empleado.salario,
        )
        return Empleado(**empleado_dict)
    except EmpleadoNoEncontradoError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except EmpleadoYaExisteError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /empleados/{id}  — Eliminar empleado (soft delete)
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un empleado (soft delete)",
    responses={
        404: {"description": "Empleado no encontrado"},
    },
)
async def eliminar_empleado(id: int):
    """
    Elimina un empleado del sistema (soft delete).

    El empleado no se borra físicamente, solo se marca como inactivo.
    """
    if id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ID debe ser un número entero mayor que 0.",
        )

    eliminado = db.eliminar_empleado(id)

    if not eliminado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún empleado con el id {id}.",
        )
