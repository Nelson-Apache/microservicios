import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import date, datetime
from fastapi.testclient import TestClient

# Parchear la base de datos y el broker antes de importar la app
with patch("app.database.init_db"), \
     patch("app.database.engine"), \
     patch("app.broker.broker"):
    from main import app

client = TestClient(app)

VACACION_BASE = {
    "id": 1,
    "empleado_id": 10,
    "fecha_inicio": date(2026, 7, 1),
    "fecha_fin": date(2026, 7, 15),
    "motivo": "Vacaciones de verano",
    "estado": "PROGRAMADA",
    "created_at": datetime(2026, 5, 15),
}


@pytest.fixture
def mock_db():
    with patch("app.routes.vacaciones.db") as m:
        yield m


@pytest.fixture
def mock_broker():
    with patch("app.routes.vacaciones.broker") as m:
        m.publicar = AsyncMock()
        yield m


class TestHealthCheck:
    def test_health_retorna_up(self):
        respuesta = client.get("/health")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert datos["status"] == "UP"
        assert datos["service"] == "vacaciones-service"


class TestProgramarVacaciones:
    def test_crear_vacacion_exitoso(self, mock_db, mock_broker):
        mock_db.crear_vacacion.return_value = VACACION_BASE.copy()
        payload = {
            "id": 1,
            "empleado_id": 10,
            "fecha_inicio": "2026-07-01",
            "fecha_fin": "2026-07-15",
            "motivo": "Vacaciones de verano",
        }
        respuesta = client.post("/vacaciones", json=payload)
        assert respuesta.status_code == 201
        datos = respuesta.json()
        assert datos["id"] == 1
        assert datos["empleado_id"] == 10
        assert datos["estado"] == "PROGRAMADA"

    def test_crear_vacacion_solapamiento_retorna_409(self, mock_db, mock_broker):
        from app.database import SolapamientoError
        mock_db.crear_vacacion.side_effect = SolapamientoError("Solapamiento detectado.")
        payload = {
            "id": 2,
            "empleado_id": 10,
            "fecha_inicio": "2026-07-05",
            "fecha_fin": "2026-07-20",
        }
        respuesta = client.post("/vacaciones", json=payload)
        assert respuesta.status_code == 409

    def test_crear_vacacion_id_duplicado_retorna_409(self, mock_db, mock_broker):
        from app.database import VacacionYaExisteError
        mock_db.crear_vacacion.side_effect = VacacionYaExisteError("ID duplicado.")
        payload = {
            "id": 1,
            "empleado_id": 10,
            "fecha_inicio": "2026-08-01",
            "fecha_fin": "2026-08-15",
        }
        respuesta = client.post("/vacaciones", json=payload)
        assert respuesta.status_code == 409


class TestListarVacaciones:
    def test_listar_todas(self, mock_db):
        mock_db.buscar_vacaciones.return_value = ([VACACION_BASE.copy()], 1)
        respuesta = client.get("/vacaciones")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert datos["total"] == 1
        assert len(datos["vacaciones"]) == 1

    def test_filtrar_por_empleado(self, mock_db):
        mock_db.buscar_vacaciones.return_value = ([VACACION_BASE.copy()], 1)
        respuesta = client.get("/vacaciones?empleado_id=10")
        assert respuesta.status_code == 200
        mock_db.buscar_vacaciones.assert_called_once_with(empleado_id=10, pagina=1, por_pagina=10)

    def test_lista_vacia(self, mock_db):
        mock_db.buscar_vacaciones.return_value = ([], 0)
        respuesta = client.get("/vacaciones")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert datos["total"] == 0
        assert datos["vacaciones"] == []


class TestConsultarVacacion:
    def test_consultar_existente(self, mock_db):
        mock_db.obtener_vacacion.return_value = VACACION_BASE.copy()
        respuesta = client.get("/vacaciones/1")
        assert respuesta.status_code == 200
        assert respuesta.json()["id"] == 1

    def test_consultar_no_encontrada_retorna_404(self, mock_db):
        mock_db.obtener_vacacion.return_value = None
        respuesta = client.get("/vacaciones/999")
        assert respuesta.status_code == 404


class TestCancelarVacacion:
    def test_cancelar_exitoso(self, mock_db, mock_broker):
        cancelada = {**VACACION_BASE, "estado": "CANCELADA"}
        mock_db.cancelar_vacacion.return_value = cancelada
        respuesta = client.delete("/vacaciones/1")
        assert respuesta.status_code == 200

    def test_cancelar_no_encontrada_retorna_404(self, mock_db, mock_broker):
        from app.database import VacacionNoEncontradaError
        mock_db.cancelar_vacacion.side_effect = VacacionNoEncontradaError("No encontrada.")
        respuesta = client.delete("/vacaciones/999")
        assert respuesta.status_code == 404


class TestActualizarVacacion:
    def test_actualizar_exitoso(self, mock_db, mock_broker):
        actualizada = {**VACACION_BASE, "motivo": "Cambio de fechas"}
        mock_db.actualizar_vacacion.return_value = actualizada
        respuesta = client.put("/vacaciones/1", json={"motivo": "Cambio de fechas"})
        assert respuesta.status_code == 200

    def test_actualizar_no_encontrada_retorna_404(self, mock_db, mock_broker):
        from app.database import VacacionNoEncontradaError
        mock_db.actualizar_vacacion.side_effect = VacacionNoEncontradaError("No encontrada.")
        respuesta = client.put("/vacaciones/999", json={"motivo": "x"})
        assert respuesta.status_code == 404

    def test_finalizar_publica_evento(self, mock_db, mock_broker):
        finalizada = {**VACACION_BASE, "estado": "FINALIZADA", "empleado_id": 10}
        mock_db.actualizar_vacacion.return_value = finalizada
        respuesta = client.put("/vacaciones/1", json={"estado": "FINALIZADA"})
        assert respuesta.status_code == 200
        mock_broker.publicar.assert_called_once()
        args = mock_broker.publicar.call_args[0]
        assert args[0] == "vacaciones.finalizadas"
