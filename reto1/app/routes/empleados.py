from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional
from math import ceil
from app.models.empleado import Empleado, PaginatedEmpleados
from app.database import db, EmpleadoYaExisteError

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
        409: {"description": "El empleado ya existe (ID o nombre+cargo duplicado)"},
        422: {"description": "Datos de entrada inválidos"},
    },
)
async def registrar_empleado(empleado: Empleado):
    """
    Registra un nuevo empleado en el sistema.

    - Valida que el **ID** no esté duplicado.
    - Valida que no exista otro empleado con el mismo **nombre** y **cargo**.
    """
    try:
        return db.crear_empleado(empleado)
    except EmpleadoYaExisteError as e:
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
    departamento: Optional[str] = Query(None, description="Filtrar por departamento (búsqueda parcial)"),
    email: Optional[str] = Query(None, description="Filtrar por email (búsqueda parcial)"),
    pagina: int = Query(1, ge=1, description="Número de página (inicia en 1)"),
    por_pagina: int = Query(10, ge=1, le=100, description="Registros por página (máx. 100)"),
):
    """
    Devuelve la lista de empleados de forma paginada con filtros opcionales.

    **Filtros disponibles** (todos opcionales, búsqueda parcial insensible a mayúsculas):
    - `nombre`
    - `cargo`
    - `departamento`
    - `email`

    **Paginación**: use `pagina` y `por_pagina` para navegar por los resultados.
    """
    empleados_pagina, total = db.buscar_empleados(
        nombre=nombre,
        cargo=cargo,
        departamento=departamento,
        email=email,
        pagina=pagina,
        por_pagina=por_pagina,
    )

    total_paginas = ceil(total / por_pagina) if total > 0 else 1

    return PaginatedEmpleados(
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=total_paginas,
        empleados=empleados_pagina,
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

    empleado = db.obtener_empleado(id)

    if empleado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró ningún empleado con el id {id}.",
        )

    return empleado
