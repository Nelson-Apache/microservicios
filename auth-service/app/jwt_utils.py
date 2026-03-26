import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError  # noqa: F401 — JWTError se re-exporta para uso externo

# Clave secreta compartida entre todos los servicios (inyectada vía variable de entorno)
CLAVE_SECRETA = os.environ.get("JWT_SECRET", "changeme-super-secret-key-for-dev")
ALGORITMO = "HS256"
MINUTOS_EXPIRACION_ACCESO = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
MINUTOS_EXPIRACION_RESET = int(os.environ.get("RESET_TOKEN_EXPIRE_MINUTES", "60"))


def crear_token_acceso(nombre_usuario: str, rol: str) -> str:
    """
    Genera un JWT de acceso con el nombre de usuario y el rol.
    Expira según MINUTOS_EXPIRACION_ACCESO (por defecto 60 min).
    """
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": nombre_usuario,
        "role": rol,
        "iat": int(ahora.timestamp()),
        "exp": int((ahora + timedelta(minutes=MINUTOS_EXPIRACION_ACCESO)).timestamp()),
    }
    return jwt.encode(payload, CLAVE_SECRETA, algorithm=ALGORITMO)


def crear_token_recuperacion(nombre_usuario: str) -> str:
    """
    Genera un JWT de recuperación/establecimiento de contraseña (Opción A - Stateless).
    Incluye el claim 'type: RESET_PASSWORD' para distinguirlo del token de acceso.
    Expira según MINUTOS_EXPIRACION_RESET (por defecto 60 min).
    """
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": nombre_usuario,
        "type": "RESET_PASSWORD",
        "iat": int(ahora.timestamp()),
        "exp": int((ahora + timedelta(minutes=MINUTOS_EXPIRACION_RESET)).timestamp()),
    }
    return jwt.encode(payload, CLAVE_SECRETA, algorithm=ALGORITMO)


def decodificar_token(token: str) -> dict:
    """
    Decodifica y verifica un JWT.
    Lanza JWTError si el token es inválido o ha expirado.
    """
    return jwt.decode(token, CLAVE_SECRETA, algorithms=[ALGORITMO])
