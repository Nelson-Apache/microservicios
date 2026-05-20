import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import date, datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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


# ─────────────────────────────────────────────────────────────────────────────
# Tests de rutas (usando mocks del módulo)
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Tests unitarios de VacacionesDB (con SQLite en memoria)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def motor_prueba():
    """Motor SQLite compartido para todos los tests de VacacionesDB."""
    from app.database import Base
    motor = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=motor)
    yield motor
    Base.metadata.drop_all(bind=motor)


@pytest.fixture(autouse=False)
def sesion_prueba(motor_prueba):
    """Redirige SessionLocal al motor de prueba y limpia la tabla después de cada test."""
    import app.database as bd
    from app.database import VacacionModel
    SesionTest = sessionmaker(bind=motor_prueba)
    bd.SessionLocal = SesionTest
    yield
    sesion = SesionTest()
    sesion.query(VacacionModel).delete()
    sesion.commit()
    sesion.close()


class TestVacacionesDB:
    """Tests unitarios de VacacionesDB usando SQLite en memoria."""

    def test_crear_vacacion_basico(self, sesion_prueba):
        from app.database import VacacionesDB
        db_test = VacacionesDB()
        resultado = db_test.crear_vacacion(
            id=1,
            empleado_id=10,
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 15),
            motivo="Test",
        )
        assert resultado["id"] == 1
        assert resultado["empleado_id"] == 10
        assert resultado["estado"] == "PROGRAMADA"
        assert resultado["motivo"] == "Test"

    def test_crear_vacacion_fecha_fin_anterior_lanza_error(self, sesion_prueba):
        from app.database import VacacionesDB
        db_test = VacacionesDB()
        with pytest.raises(ValueError):
            db_test.crear_vacacion(
                id=1,
                empleado_id=10,
                fecha_inicio=date(2026, 7, 15),
                fecha_fin=date(2026, 7, 1),
            )

    def test_crear_vacacion_id_duplicado_lanza_error(self, sesion_prueba):
        from app.database import VacacionesDB, VacacionYaExisteError
        db_test = VacacionesDB()
        db_test.crear_vacacion(1, 10, date(2026, 7, 1), date(2026, 7, 15))
        with pytest.raises(VacacionYaExisteError):
            db_test.crear_vacacion(1, 10, date(2026, 8, 1), date(2026, 8, 15))

    def test_crear_vacacion_solapamiento_lanza_error(self, sesion_prueba):
        from app.database import VacacionesDB, SolapamientoError
        db_test = VacacionesDB()
        db_test.crear_vacacion(1, 10, date(2026, 7, 1), date(2026, 7, 15))
        with pytest.raises(SolapamientoError):
            db_test.crear_vacacion(2, 10, date(2026, 7, 10), date(2026, 7, 20))

    def test_cancelada_no_bloquea_nuevo_solapamiento(self, sesion_prueba):
        from app.database import VacacionesDB
        db_test = VacacionesDB()
        db_test.crear_vacacion(1, 10, date(2026, 7, 1), date(2026, 7, 15))
        db_test.cancelar_vacacion(1)
        # Mismo período debe ser válido después de cancelar
        resultado = db_test.crear_vacacion(2, 10, date(2026, 7, 1), date(2026, 7, 15))
        assert resultado["id"] == 2

    def test_obtener_vacacion_existente(self, sesion_prueba):
        from app.database import VacacionesDB
        db_test = VacacionesDB()
        db_test.crear_vacacion(1, 10, date(2026, 7, 1), date(2026, 7, 15))
        resultado = db_test.obtener_vacacion(1)
        assert resultado is not None
        assert resultado["id"] == 1

    def test_obtener_vacacion_no_existente_retorna_none(self, sesion_prueba):
        from app.database import VacacionesDB
        db_test = VacacionesDB()
        resultado = db_test.obtener_vacacion(999)
        assert resultado is None

    def test_buscar_vacaciones_sin_filtro(self, sesion_prueba):
        from app.database import VacacionesDB
        db_test = VacacionesDB()
        db_test.crear_vacacion(1, 10, date(2026, 7, 1), date(2026, 7, 15))
        db_test.crear_vacacion(2, 20, date(2026, 8, 1), date(2026, 8, 15))
        vacaciones, total = db_test.buscar_vacaciones()
        assert total == 2
        assert len(vacaciones) == 2

    def test_buscar_vacaciones_filtro_empleado(self, sesion_prueba):
        from app.database import VacacionesDB
        db_test = VacacionesDB()
        db_test.crear_vacacion(1, 10, date(2026, 7, 1), date(2026, 7, 15))
        db_test.crear_vacacion(2, 20, date(2026, 8, 1), date(2026, 8, 15))
        vacaciones, total = db_test.buscar_vacaciones(empleado_id=10)
        assert total == 1
        assert vacaciones[0]["empleado_id"] == 10

    def test_actualizar_motivo(self, sesion_prueba):
        from app.database import VacacionesDB
        db_test = VacacionesDB()
        db_test.crear_vacacion(1, 10, date(2026, 7, 1), date(2026, 7, 15), motivo="Original")
        resultado = db_test.actualizar_vacacion(1, motivo="Actualizado")
        assert resultado["motivo"] == "Actualizado"

    def test_actualizar_estado_a_finalizada(self, sesion_prueba):
        from app.database import VacacionesDB
        db_test = VacacionesDB()
        db_test.crear_vacacion(1, 10, date(2026, 7, 1), date(2026, 7, 15))
        resultado = db_test.actualizar_vacacion(1, estado="FINALIZADA")
        assert resultado["estado"] == "FINALIZADA"

    def test_actualizar_fechas_con_verificacion_solapamiento(self, sesion_prueba):
        from app.database import VacacionesDB, SolapamientoError
        db_test = VacacionesDB()
        db_test.crear_vacacion(1, 10, date(2026, 7, 1), date(2026, 7, 10))
        db_test.crear_vacacion(2, 10, date(2026, 7, 20), date(2026, 7, 31))
        with pytest.raises(SolapamientoError):
            db_test.actualizar_vacacion(1, fecha_fin=date(2026, 7, 25))

    def test_actualizar_fecha_fin_invalida_lanza_error(self, sesion_prueba):
        from app.database import VacacionesDB
        db_test = VacacionesDB()
        db_test.crear_vacacion(1, 10, date(2026, 7, 10), date(2026, 7, 20))
        with pytest.raises(ValueError):
            db_test.actualizar_vacacion(1, fecha_fin=date(2026, 7, 1))

    def test_actualizar_no_encontrada_lanza_error(self, sesion_prueba):
        from app.database import VacacionesDB, VacacionNoEncontradaError
        db_test = VacacionesDB()
        with pytest.raises(VacacionNoEncontradaError):
            db_test.actualizar_vacacion(999, motivo="x")

    def test_cancelar_vacacion(self, sesion_prueba):
        from app.database import VacacionesDB
        db_test = VacacionesDB()
        db_test.crear_vacacion(1, 10, date(2026, 7, 1), date(2026, 7, 15))
        resultado = db_test.cancelar_vacacion(1)
        assert resultado["estado"] == "CANCELADA"

    def test_cancelar_no_encontrada_lanza_error(self, sesion_prueba):
        from app.database import VacacionesDB, VacacionNoEncontradaError
        db_test = VacacionesDB()
        with pytest.raises(VacacionNoEncontradaError):
            db_test.cancelar_vacacion(999)


# ─────────────────────────────────────────────────────────────────────────────
# Tests unitarios de BrokerVacaciones
# ─────────────────────────────────────────────────────────────────────────────

class TestBrokerVacaciones:

    @pytest.mark.asyncio
    async def test_conectar_establece_exchange(self):
        from app.broker import BrokerVacaciones
        broker_test = BrokerVacaciones()
        mock_exchange = AsyncMock()
        mock_canal = AsyncMock()
        mock_canal.declare_exchange = AsyncMock(return_value=mock_exchange)
        mock_conexion = AsyncMock()
        mock_conexion.channel = AsyncMock(return_value=mock_canal)

        with patch("app.broker.connect_robust", return_value=mock_conexion):
            await broker_test._conectar()

        assert broker_test.conexion == mock_conexion
        assert broker_test.exchange == mock_exchange

    @pytest.mark.asyncio
    async def test_conectar_reintenta_tras_error(self):
        from app.broker import BrokerVacaciones
        broker_test = BrokerVacaciones()
        mock_exchange = AsyncMock()
        mock_canal = AsyncMock()
        mock_canal.declare_exchange = AsyncMock(return_value=mock_exchange)
        mock_conexion = AsyncMock()
        mock_conexion.channel = AsyncMock(return_value=mock_canal)

        intentos = {"n": 0}

        async def mock_connect(url):
            intentos["n"] += 1
            if intentos["n"] < 3:
                raise Exception("Connection refused")
            return mock_conexion

        with patch("app.broker.connect_robust", side_effect=mock_connect), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            await broker_test._conectar()

        assert intentos["n"] == 3
        assert broker_test.exchange == mock_exchange

    @pytest.mark.asyncio
    async def test_publicar_llama_conectar_sin_exchange(self):
        from app.broker import BrokerVacaciones
        broker_test = BrokerVacaciones()
        mock_exchange = AsyncMock()

        async def _mock_conectar():
            broker_test.exchange = mock_exchange

        with patch.object(broker_test, "_conectar", side_effect=_mock_conectar) as mock_conectar:
            await broker_test.publicar("vacaciones.programadas", {"empleado_id": 1})

        mock_conectar.assert_called_once()
        mock_exchange.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publicar_no_llama_conectar_si_exchange_existe(self):
        from app.broker import BrokerVacaciones
        broker_test = BrokerVacaciones()
        mock_exchange = AsyncMock()
        broker_test.exchange = mock_exchange

        with patch.object(broker_test, "_conectar", new_callable=AsyncMock) as mock_conectar:
            await broker_test.publicar("vacaciones.finalizadas", {"empleado_id": 2})

        mock_conectar.assert_not_called()
        mock_exchange.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_detener_cierra_conexion_abierta(self):
        from app.broker import BrokerVacaciones
        broker_test = BrokerVacaciones()
        mock_conexion = AsyncMock()
        mock_conexion.is_closed = False
        broker_test.conexion = mock_conexion

        await broker_test.detener()
        mock_conexion.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_detener_sin_conexion_no_falla(self):
        from app.broker import BrokerVacaciones
        broker_test = BrokerVacaciones()
        await broker_test.detener()  # no debe lanzar excepción

    @pytest.mark.asyncio
    async def test_detener_conexion_ya_cerrada_no_llama_close(self):
        from app.broker import BrokerVacaciones
        broker_test = BrokerVacaciones()
        mock_conexion = AsyncMock()
        mock_conexion.is_closed = True
        broker_test.conexion = mock_conexion

        await broker_test.detener()
        mock_conexion.close.assert_not_called()
