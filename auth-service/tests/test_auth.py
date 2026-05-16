import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from jose import jwt
import time


CLAVE_SECRETA = "changeme-super-secret-key-for-dev"


@pytest.fixture
def mock_db_sesion():
    """Sesión de BD simulada."""
    sesion = MagicMock()
    return sesion


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


with patch.dict("os.environ", {
    "DATABASE_URL": "sqlite:///:memory:",
    "JWT_SECRET": CLAVE_SECRETA,
    "RABBITMQ_URL": "amqp://guest:guest@localhost/",
}):
    with patch("app.database.motor"), \
         patch("app.database.SesionLocal"), \
         patch("app.database.Base.metadata.create_all"):
        from main import app

client = TestClient(app)


class TestLogin:
    def test_login_credenciales_correctas_retorna_jwt(self, mock_db_sesion, usuario_activo):
        mock_db_sesion.query.return_value.filter.return_value.first.return_value = usuario_activo
        with patch("app.routes.auth.obtener_db", return_value=iter([mock_db_sesion])):
            respuesta = client.post("/auth/login", json={
                "nombre_usuario": "juan@empresa.com",
                "contrasena": "contrasena123"
            })
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert "access_token" in datos
        assert datos["token_type"] == "bearer"

    def test_token_contiene_sub_role_exp(self, mock_db_sesion, usuario_activo):
        mock_db_sesion.query.return_value.filter.return_value.first.return_value = usuario_activo
        with patch("app.routes.auth.obtener_db", return_value=iter([mock_db_sesion])):
            respuesta = client.post("/auth/login", json={
                "nombre_usuario": "juan@empresa.com",
                "contrasena": "contrasena123"
            })
        token = respuesta.json()["access_token"]
        payload = jwt.decode(token, CLAVE_SECRETA, algorithms=["HS256"])
        assert "sub" in payload
        assert "role" in payload
        assert "exp" in payload

    def test_login_contrasena_incorrecta_retorna_401(self, mock_db_sesion, usuario_activo):
        mock_db_sesion.query.return_value.filter.return_value.first.return_value = usuario_activo
        with patch("app.routes.auth.obtener_db", return_value=iter([mock_db_sesion])):
            respuesta = client.post("/auth/login", json={
                "nombre_usuario": "juan@empresa.com",
                "contrasena": "contrasena_incorrecta"
            })
        assert respuesta.status_code == 401

    def test_login_usuario_inexistente_retorna_401(self, mock_db_sesion):
        mock_db_sesion.query.return_value.filter.return_value.first.return_value = None
        with patch("app.routes.auth.obtener_db", return_value=iter([mock_db_sesion])):
            respuesta = client.post("/auth/login", json={
                "nombre_usuario": "noexiste@empresa.com",
                "contrasena": "cualquiera"
            })
        assert respuesta.status_code == 401

    def test_login_usuario_inactivo_retorna_401(self, mock_db_sesion, usuario_inactivo):
        mock_db_sesion.query.return_value.filter.return_value.first.return_value = usuario_inactivo
        with patch("app.routes.auth.obtener_db", return_value=iter([mock_db_sesion])):
            respuesta = client.post("/auth/login", json={
                "nombre_usuario": "juan@empresa.com",
                "contrasena": "contrasena123"
            })
        assert respuesta.status_code == 401


class TestHealth:
    def test_health_retorna_up(self):
        respuesta = client.get("/health")
        assert respuesta.status_code == 200
        assert respuesta.json()["status"] == "UP"


class TestRecuperacionContrasena:
    def test_recuperar_contrasena_siempre_retorna_200(self, mock_db_sesion):
        mock_db_sesion.query.return_value.filter.return_value.first.return_value = None
        with patch("app.routes.auth.obtener_db", return_value=iter([mock_db_sesion])):
            respuesta = client.post("/auth/recover-password", json={
                "email": "noexiste@empresa.com"
            })
        assert respuesta.status_code == 200


class TestCambioContrasena:
    def _generar_token(self):
        from app.jwt_utils import crear_token_acceso
        return crear_token_acceso("juan@empresa.com", "USER")

    def test_cambiar_contrasena_exitoso(self, mock_db_sesion, usuario_activo):
        token = self._generar_token()
        mock_db_sesion.query.return_value.filter.return_value.first.return_value = usuario_activo
        with patch("app.routes.auth.obtener_db", return_value=iter([mock_db_sesion])):
            respuesta = client.post(
                "/auth/change-password",
                json={"contrasena_actual": "contrasena123", "nueva_contrasena": "nuevaClave456"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert respuesta.status_code == 200
        assert "exitosamente" in respuesta.json()["mensaje"]

    def test_cambiar_contrasena_actual_incorrecta_retorna_401(self, mock_db_sesion, usuario_activo):
        token = self._generar_token()
        mock_db_sesion.query.return_value.filter.return_value.first.return_value = usuario_activo
        with patch("app.routes.auth.obtener_db", return_value=iter([mock_db_sesion])):
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

    def test_cambiar_contrasena_token_invalido_retorna_403(self):
        respuesta = client.post(
            "/auth/change-password",
            json={"contrasena_actual": "contrasena123", "nueva_contrasena": "nuevaClave456"},
            headers={"Authorization": "Bearer token.invalido.aqui"},
        )
        assert respuesta.status_code == 401
