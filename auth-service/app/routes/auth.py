from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.database import obtener_db, Usuario
from app.jwt_utils import crear_token_acceso, crear_token_recuperacion, decodificar_token, JWTError
from app.broker import broker
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# Contexto para hashing de contraseñas con BCrypt
contexto_hash = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─────────────────────────────────────────────────────────────────
# Esquemas de entrada (Pydantic)
# ─────────────────────────────────────────────────────────────────

class SolicitudLogin(BaseModel):
    """Credenciales para iniciar sesión."""
    nombre_usuario: str
    contrasena: str


class SolicitudRecuperacion(BaseModel):
    """Email para iniciar el proceso de recuperación de contraseña."""
    email: EmailStr


class SolicitudRestablecimiento(BaseModel):
    """Token de recuperación y nueva contraseña."""
    token: str
    nueva_contrasena: str


# ─────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    summary="Autenticar usuario y obtener JWT de acceso",
    responses={
        200: {"description": "Login exitoso, retorna el token JWT"},
        401: {"description": "Credenciales inválidas o usuario inhabilitado"},
    },
)
async def iniciar_sesion(
    solicitud: SolicitudLogin,
    db: Session = Depends(obtener_db),
):
    """
    Verifica las credenciales del usuario y retorna un **JWT de acceso**.

    El token incluye:
    - `sub`: nombre de usuario
    - `role`: rol del usuario (`ADMIN` o `USER`)
    - `iat` / `exp`: tiempos de emisión y expiración
    """
    usuario = db.query(Usuario).filter(
        Usuario.nombre_usuario == solicitud.nombre_usuario
    ).first()

    # Verificar existencia, contraseña y estado activo
    if not usuario or not usuario.hash_contrasena:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )
    if not contexto_hash.verify(solicitud.contrasena, usuario.hash_contrasena):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inhabilitado. Contacte al administrador.",
        )

    token = crear_token_acceso(usuario.nombre_usuario, usuario.rol)
    logger.info(
        f"Login exitoso",
        extra={"evento": "login_exitoso", "usuario": usuario.nombre_usuario, "rol": usuario.rol}
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "rol": usuario.rol,
    }


@router.post(
    "/recover-password",
    summary="Solicitar recuperación de contraseña",
    responses={
        200: {"description": "Instrucciones enviadas (si el email existe)"},
    },
)
async def recuperar_contrasena(
    solicitud: SolicitudRecuperacion,
    db: Session = Depends(obtener_db),
):
    """
    Inicia el proceso de recuperación de contraseña.

    - Busca el usuario por email.
    - Genera un **token de recuperación JWT** (stateless, expira en 60 min).
    - Publica el evento `usuario.recuperacion` para que `notificaciones-service`
      simule el envío del correo con el token.

    *Por seguridad, siempre retorna el mismo mensaje independientemente de si
    el email existe o no.*
    """
    usuario = db.query(Usuario).filter(Usuario.email == solicitud.email).first()

    if usuario:
        token_recuperacion = crear_token_recuperacion(usuario.nombre_usuario)
        await broker.publicar(
            "usuario.recuperacion",
            {"email": solicitud.email, "token": token_recuperacion}
        )
        logger.info(
            f"Recuperación de contraseña solicitada",
            extra={"evento": "recuperacion_solicitada", "email": solicitud.email}
        )

    # Respuesta genérica para no revelar si el email existe
    return {"mensaje": "Si el email está registrado, recibirá instrucciones para restablecer su contraseña."}


@router.post(
    "/reset-password",
    summary="Establecer nueva contraseña con token de recuperación",
    responses={
        200: {"description": "Contraseña actualizada exitosamente"},
        400: {"description": "Token inválido, expirado o de tipo incorrecto"},
        404: {"description": "Usuario no encontrado"},
    },
)
async def restablecer_contrasena(
    solicitud: SolicitudRestablecimiento,
    db: Session = Depends(obtener_db),
):
    """
    Establece una nueva contraseña usando el **token de recuperación**.

    - Valida matemáticamente el JWT (firma y expiración).
    - Verifica que el claim `type` sea `RESET_PASSWORD`.
    - Actualiza el hash de la contraseña con BCrypt.
    - Activa la cuenta si estaba inhabilitada.
    """
    try:
        payload = decodificar_token(solicitud.token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado.",
        )

    if payload.get("type") != "RESET_PASSWORD":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El token proporcionado no es un token de recuperación.",
        )

    nombre_usuario = payload.get("sub")
    usuario = db.query(Usuario).filter(Usuario.nombre_usuario == nombre_usuario).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    # Hashear nueva contraseña y activar cuenta
    usuario.hash_contrasena = contexto_hash.hash(solicitud.nueva_contrasena)
    usuario.activo = True
    db.commit()

    logger.info(
        f"Contraseña restablecida",
        extra={"evento": "contrasena_restablecida", "usuario": nombre_usuario}
    )
    return {"mensaje": "Contraseña actualizada exitosamente. Ya puede iniciar sesión."}
