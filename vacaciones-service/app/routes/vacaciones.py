from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional
from math import ceil
from app.models.vacacion import Vacacion, VacacionCreate, VacacionUpdate, PaginatedVacaciones
from app.database import db, SolapamientoError, VacacionYaExisteError, VacacionNoEncontradaError
from app.broker import broker
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vacaciones", tags=["vacaciones"])


@router.post(
    "",
    response_model=Vacacion,
    status_code=status.HTTP_201_CREATED,
    summary="Programar vacaciones para un empleado",
    responses={
        409: {"description": "ID duplicado o solapamiento de períodos"},
        422: {"description": "Datos inválidos (fecha_fin < fecha_inicio)"},
    },
)
async def programar_vacaciones(vacacion: VacacionCreate):
    logger.info(
        "Solicitud de programación de vacaciones",
        extra={"empleado_id": vacacion.empleado_id, "vacacion_id": vacacion.id}
    )
    try:
        vacacion_dict = db.crear_vacacion(
            id=vacacion.id,
            empleado_id=vacacion.empleado_id,
            fecha_inicio=vacacion.fecha_inicio,
            fecha_fin=vacacion.fecha_fin,
            motivo=vacacion.motivo,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except VacacionYaExisteError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
    except SolapamientoError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)

    try:
        await broker.publicar(
            "vacaciones.programadas",
            {
                "empleado_id": vacacion.empleado_id,
                "vacacion_id": vacacion.id,
                "fecha_inicio": str(vacacion.fecha_inicio),
                "fecha_fin": str(vacacion.fecha_fin),
            }
        )
    except Exception as e:
        logger.error(
            "Error publicando evento vacaciones.programadas",
            extra={"error": str(e), "vacacion_id": vacacion.id}
        )

    return Vacacion(**vacacion_dict)


@router.get(
    "",
    response_model=PaginatedVacaciones,
    status_code=status.HTTP_200_OK,
    summary="Listar vacaciones con filtro opcional por empleado",
)
async def listar_vacaciones(
    empleado_id: Optional[int] = Query(None, description="Filtrar por ID de empleado"),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(10, ge=1, le=100),
):
    vacaciones_pagina, total = db.buscar_vacaciones(
        empleado_id=empleado_id,
        pagina=pagina,
        por_pagina=por_pagina,
    )
    total_paginas = ceil(total / por_pagina) if total > 0 else 1
    return PaginatedVacaciones(
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=total_paginas,
        vacaciones=[Vacacion(**v) for v in vacaciones_pagina],
    )


@router.get(
    "/{id}",
    response_model=Vacacion,
    status_code=status.HTTP_200_OK,
    summary="Consultar una vacación por ID",
    responses={404: {"description": "Vacación no encontrada"}},
)
async def consultar_vacacion(id: int):
    vacacion_dict = db.obtener_vacacion(id)
    if vacacion_dict is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la vacación con id {id}.",
        )
    return Vacacion(**vacacion_dict)


@router.put(
    "/{id}",
    response_model=Vacacion,
    status_code=status.HTTP_200_OK,
    summary="Actualizar una vacación",
    responses={
        404: {"description": "Vacación no encontrada"},
        409: {"description": "Solapamiento de períodos"},
        422: {"description": "Datos inválidos"},
    },
)
async def actualizar_vacacion(id: int, datos: VacacionUpdate):
    try:
        vacacion_dict = db.actualizar_vacacion(
            vacacion_id=id,
            fecha_inicio=datos.fecha_inicio,
            fecha_fin=datos.fecha_fin,
            motivo=datos.motivo,
            estado=datos.estado.value if datos.estado else None,
        )
    except VacacionNoEncontradaError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except SolapamientoError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Publicar finalización si el estado cambia a FINALIZADA
    if datos.estado and datos.estado.value == "FINALIZADA":
        try:
            await broker.publicar(
                "vacaciones.finalizadas",
                {
                    "empleado_id": vacacion_dict["empleado_id"],
                    "vacacion_id": id,
                }
            )
        except Exception as e:
            logger.error(
                "Error publicando evento vacaciones.finalizadas",
                extra={"error": str(e), "vacacion_id": id}
            )

    return Vacacion(**vacacion_dict)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Cancelar una vacación",
    responses={404: {"description": "Vacación no encontrada"}},
)
async def cancelar_vacacion(id: int):
    try:
        vacacion_dict = db.cancelar_vacacion(id)
    except VacacionNoEncontradaError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)

    try:
        await broker.publicar(
            "vacaciones.finalizadas",
            {
                "empleado_id": vacacion_dict["empleado_id"],
                "vacacion_id": id,
                "motivo": "cancelacion",
            }
        )
    except Exception as e:
        logger.error(
            "Error publicando evento vacaciones.finalizadas por cancelación",
            extra={"error": str(e), "vacacion_id": id}
        )

    return {"mensaje": f"Vacación {id} cancelada exitosamente.", "vacacion": vacacion_dict}
