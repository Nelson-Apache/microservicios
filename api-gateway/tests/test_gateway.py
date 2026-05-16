import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from jose import jwt
import time

CLAVE_SECRETA = "changeme-super-secret-key-for-dev"
ALGORITMO = "HS256"


def crear_token(rol: str, sub: str = "usuario_test", exp_offset: int = 3600) -> str:
    payload = {
        "sub": sub,
        "role": rol,
        "exp": int(time.time()) + exp_offset,
    }
    return jwt.encode(payload, CLAVE_SECRETA, algorithm=ALGORITMO)


def crear_token_expirado() -> str:
    payload = {
        "sub": "usuario_test",
        "role": "USER",
        "exp": int(time.time()) - 100,
    }
    return jwt.encode(payload, CLAVE_SECRETA, algorithm=ALGORITMO)


with patch.dict("os.environ", {"JWT_SECRET": CLAVE_SECRETA}):
    from main import app

client = TestClient(app, raise_server_exceptions=False)


class TestHealthCheck:
    def test_health_es_publico(self):
        respuesta = client.get("/health")
        assert respuesta.status_code == 200
        assert respuesta.json()["status"] == "UP"

    def test_health_no_requiere_jwt(self):
        # Sin cabecera Authorization
        respuesta = client.get("/health")
        assert respuesta.status_code == 200


class TestAutenticacion:
    def test_ruta_protegida_sin_token_retorna_401(self):
        respuesta = client.get("/empleados")
        assert respuesta.status_code == 401

    def test_token_invalido_retorna_401(self):
        respuesta = client.get(
            "/empleados",
            headers={"Authorization": "Bearer token_invalido_xxx"}
        )
        assert respuesta.status_code == 401

    def test_token_expirado_retorna_401(self):
        token = crear_token_expirado()
        respuesta = client.get(
            "/empleados",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert respuesta.status_code == 401

    def test_cabecera_sin_bearer_retorna_401(self):
        token = crear_token("USER")
        respuesta = client.get(
            "/empleados",
            headers={"Authorization": token}
        )
        assert respuesta.status_code == 401


class TestRBAC:
    def test_rol_user_en_get_es_permitido(self):
        token = crear_token("USER")
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b'[]'
            mock_resp.headers = {"content-type": "application/json"}
            mock_req.return_value = mock_resp
            respuesta = client.get(
                "/empleados",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert respuesta.status_code != 403

    def test_rol_user_en_post_retorna_403(self):
        token = crear_token("USER")
        respuesta = client.post(
            "/empleados",
            json={"id": 99, "nombre": "Test", "cargo": "Dev"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert respuesta.status_code == 403

    def test_rol_admin_en_post_no_retorna_403(self):
        token = crear_token("ADMIN")
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 201
            mock_resp.content = b'{}'
            mock_resp.headers = {"content-type": "application/json"}
            mock_req.return_value = mock_resp
            respuesta = client.post(
                "/empleados",
                json={"id": 99, "nombre": "Test", "cargo": "Dev"},
                headers={"Authorization": f"Bearer {token}"}
            )
        assert respuesta.status_code != 403

    def test_rol_user_en_delete_retorna_403(self):
        token = crear_token("USER")
        respuesta = client.delete(
            "/empleados/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert respuesta.status_code == 403


class TestEnrutamiento:
    def test_servicio_no_mapeado_retorna_404(self):
        token = crear_token("ADMIN")
        respuesta = client.get(
            "/servicio_inexistente/recurso",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert respuesta.status_code == 404

    def test_ruta_auth_es_publica(self):
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b'{"access_token": "tok"}'
            mock_resp.headers = {"content-type": "application/json"}
            mock_req.return_value = mock_resp
            respuesta = client.post("/auth/login", json={"nombre_usuario": "u", "contrasena": "p"})
        assert respuesta.status_code != 401
