import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from jose import jwt


CLAVE_SECRETA = "changeme-super-secret-key-for-dev"

# Motor SQLite compartido — StaticPool garantiza que todas las sesiones usen la misma BD
MOTOR_PRUEBA = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

with patch.dict("os.environ", {
    "DATABASE_URL": "sqlite:///:memory:",
    "JWT_SECRET": CLAVE_SECRETA,
    "RABBITMQ_URL": "amqp://guest:guest@localhost/",
}):
    with patch("app.broker.BrokerAuth.iniciar", new_callable=AsyncMock), \
         patch("app.broker.BrokerAuth.detener", new_callable=AsyncMock):
        from main import app
        from app.database import Base, obtener_db
        from app.routes.auth import obtener_usuario_actual
        import app.database as bd_modulo
        import main as main_modulo

# Redirigir las referencias del motor al motor de prueba
SesionPrueba = sessionmaker(autocommit=False, autoflush=False, bind=MOTOR_PRUEBA)
bd_modulo.motor = MOTOR_PRUEBA
bd_modulo.SesionLocal = SesionPrueba
main_modulo.motor = MOTOR_PRUEBA

# Crear tablas una sola vez
Base.metadata.create_all(bind=MOTOR_PRUEBA)

client = TestClient(app)


@pytest.fixture(autouse=True)
def limpiar_overrides():
    """Limpia los overrides de dependencias después de cada test."""
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def usuario_activo():
    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    usuario = MagicMock()
    usuario.nombre_usuario = "juan@empresa.com"
    usuario.email = "juan@empresa.com"
    usuario.hash_contrasena = ctx.hash("contrasena123")
    usuario.rol = "USER"
    usuario.activo = True
    usuario.id = 1
    return usuario


@pytest.fixture
def usuario_inactivo(usuario_activo):
    usuario_activo.activo = False
    return usuario_activo


class TestLogin:
    def test_login_credenciales_correctas_retorna_jwt(self, usuario_activo):
        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.first.return_value = usuario_activo
        app.dependency_overrides[obtener_db] = lambda: sesion

        respuesta = client.post("/auth/login", json={
            "nombre_usuario": "juan@empresa.com",
            "contrasena": "contrasena123",
        })
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert "access_token" in datos
        assert datos["token_type"] == "bearer"

    def test_token_contiene_sub_role_exp(self, usuario_activo):
        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.first.return_value = usuario_activo
        app.dependency_overrides[obtener_db] = lambda: sesion

        respuesta = client.post("/auth/login", json={
            "nombre_usuario": "juan@empresa.com",
            "contrasena": "contrasena123",
        })
        token = respuesta.json()["access_token"]
        payload = jwt.decode(token, CLAVE_SECRETA, algorithms=["HS256"])
        assert "sub" in payload
        assert "role" in payload
        assert "exp" in payload

    def test_login_contrasena_incorrecta_retorna_401(self, usuario_activo):
        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.first.return_value = usuario_activo
        app.dependency_overrides[obtener_db] = lambda: sesion

        respuesta = client.post("/auth/login", json={
            "nombre_usuario": "juan@empresa.com",
            "contrasena": "contrasena_incorrecta",
        })
        assert respuesta.status_code == 401

    def test_login_usuario_inexistente_retorna_401(self):
        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.first.return_value = None
        app.dependency_overrides[obtener_db] = lambda: sesion

        respuesta = client.post("/auth/login", json={
            "nombre_usuario": "noexiste@empresa.com",
            "contrasena": "cualquiera",
        })
        assert respuesta.status_code == 401

    def test_login_usuario_inactivo_retorna_401(self, usuario_inactivo):
        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.first.return_value = usuario_inactivo
        app.dependency_overrides[obtener_db] = lambda: sesion

        respuesta = client.post("/auth/login", json={
            "nombre_usuario": "juan@empresa.com",
            "contrasena": "contrasena123",
        })
        assert respuesta.status_code == 401


class TestHealth:
    def test_health_retorna_up(self):
        from app.broker import broker as _broker
        mock_conexion = MagicMock()
        mock_conexion.is_closed = False
        with patch.object(_broker, "conexion", mock_conexion):
            respuesta = client.get("/health")
        assert respuesta.status_code == 200
        assert respuesta.json()["status"] == "UP"


class TestRecuperacionContrasena:
    def test_recuperar_contrasena_siempre_retorna_200(self):
        sesion = MagicMock()
        sesion.query.return_value.filter.return_value.first.return_value = None
        app.dependency_overrides[obtener_db] = lambda: sesion

        respuesta = client.post("/auth/recover-password", json={
            "email": "noexiste@empresa.com",
        })
        assert respuesta.status_code == 200


class TestCambioContrasena:
    def _generar_token(self):
        from app.jwt_utils import crear_token_acceso
        return crear_token_acceso("juan@empresa.com", "USER")

    def test_cambiar_contrasena_exitoso(self, usuario_activo):
        token = self._generar_token()
        sesion = MagicMock()
        app.dependency_overrides[obtener_db] = lambda: sesion
        app.dependency_overrides[obtener_usuario_actual] = lambda: usuario_activo

        respuesta = client.post(
            "/auth/change-password",
            json={"contrasena_actual": "contrasena123", "nueva_contrasena": "nuevaClave456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert respuesta.status_code == 200
        assert "exitosamente" in respuesta.json()["mensaje"]

    def test_cambiar_contrasena_actual_incorrecta_retorna_401(self, usuario_activo):
        token = self._generar_token()
        sesion = MagicMock()
        app.dependency_overrides[obtener_db] = lambda: sesion
        app.dependency_overrides[obtener_usuario_actual] = lambda: usuario_activo

        respuesta = client.post(
            "/auth/change-password",
            json={"contrasena_actual": "incorrecta", "nueva_contrasena": "nuevaClave456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert respuesta.status_code == 401

    def test_cambiar_contrasena_sin_token_retorna_403(self):
        respuesta = client.post(
            "/auth/change-password",
            json={"contrasena_actual": "contrasena123", "nueva_contrasena": "nuevaClave456"},
        )
        assert respuesta.status_code == 403

    def test_cambiar_contrasena_token_invalido_retorna_401(self):
        respuesta = client.post(
            "/auth/change-password",
            json={"contrasena_actual": "contrasena123", "nueva_contrasena": "nuevaClave456"},
            headers={"Authorization": "Bearer token.invalido.aqui"},
        )
        assert respuesta.status_code == 401
