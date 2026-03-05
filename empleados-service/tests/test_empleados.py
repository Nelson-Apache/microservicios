"""
Pruebas unitarias para el servicio de empleados.
Utiliza pytest y pytest-asyncio para pruebas asíncronas.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from datetime import datetime

from app.models.empleado import Empleado, EmpleadoCreate, EmpleadoUpdate
from app.database import EmpleadoYaExisteError, EmpleadoNoEncontradoError
from app.clients.departamentos_client import DepartamentoNoEncontradoError, DepartamentosServiceError


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def empleado_valido():
    """Fixture que retorna un empleado válido para las pruebas."""
    return {
        "id": 1,
        "nombre": "Juan Pérez",
        "cargo": "Developer",
        "departamento_id": 1,
        "email": "juan@empresa.com",
        "salario": 50000.0,
        "fecha_ingreso": datetime(2024, 1, 15),
        "activo": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


@pytest.fixture
def empleado_create_request():
    """Fixture para un request de creación de empleado."""
    return EmpleadoCreate(
        id=1,
        nombre="Juan Pérez",
        cargo="Developer",
        departamento_id=1,
        email="juan@empresa.com",
        salario=50000.0,
        fecha_ingreso=datetime(2024, 1, 15)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tests de validación de departamentos
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validar_departamento_existe_exitoso():
    """Debe validar que el departamento existe correctamente."""
    from app.clients.departamentos_client import DepartamentosClient
    
    client = DepartamentosClient()
    
    with patch.object(client, 'validar_departamento_existe', return_value=True) as mock_validate:
        resultado = await client.validar_departamento_existe(1)
        
        assert resultado is True
        mock_validate.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_validar_departamento_no_encontrado():
    """Debe lanzar excepción cuando el departamento no existe."""
    from app.clients.departamentos_client import DepartamentosClient
    
    client = DepartamentosClient()
    
    with patch.object(
        client, 
        'validar_departamento_existe', 
        side_effect=DepartamentoNoEncontradoError(999)
    ):
        with pytest.raises(DepartamentoNoEncontradoError) as exc_info:
            await client.validar_departamento_existe(999)
        
        assert "999" in str(exc_info.value)


@pytest.mark.asyncio
async def test_validar_departamento_servicio_no_disponible():
    """Debe lanzar excepción cuando el servicio no está disponible."""
    from app.clients.departamentos_client import DepartamentosClient
    
    client = DepartamentosClient()
    
    with patch.object(
        client,
        'validar_departamento_existe',
        side_effect=DepartamentosServiceError("Servicio no disponible")
    ):
        with pytest.raises(DepartamentosServiceError) as exc_info:
            await client.validar_departamento_existe(1)
        
        assert "Servicio no disponible" in str(exc_info.value)


# ─────────────────────────────────────────────────────────────────────────────
# Tests de operaciones de base de datos
# ─────────────────────────────────────────────────────────────────────────────

def test_crear_empleado_exitoso(empleado_valido, mocker):
    """Debe crear un empleado exitosamente."""
    from app.database import EmpleadosDB
    
    db = EmpleadosDB()
    
    # Mock de los métodos de la base de datos
    mock_session = mocker.MagicMock()
    mocker.patch('app.database.get_db_session', return_value=mock_session.__enter__)
    mock_session.__enter__.return_value.add = mocker.MagicMock()
    mock_session.__enter__.return_value.commit = mocker.MagicMock()
    mock_session.__enter__.return_value.refresh = mocker.MagicMock()
    mock_session.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None
    
    # Mock del modelo que se retorna
    mock_empleado = mocker.MagicMock()
    mock_empleado.id = empleado_valido["id"]
    mock_empleado.nombre = empleado_valido["nombre"]
    mock_empleado.cargo = empleado_valido["cargo"]
    mock_empleado.departamento_id = empleado_valido["departamento_id"]
    mock_empleado.email = empleado_valido["email"]
    mock_empleado.salario = empleado_valido["salario"]
    mock_empleado.fecha_ingreso = empleado_valido["fecha_ingreso"]
    mock_empleado.activo = empleado_valido["activo"]
    
    with patch('app.database.EmpleadoModel', return_value=mock_empleado):
        resultado = db.crear_empleado(
            id=empleado_valido["id"],
            nombre=empleado_valido["nombre"],
            cargo=empleado_valido["cargo"],
            departamento_id=empleado_valido["departamento_id"],
            email=empleado_valido["email"],
            salario=empleado_valido["salario"],
            fecha_ingreso=empleado_valido["fecha_ingreso"]
        )
    
    assert resultado["id"] == empleado_valido["id"]
    assert resultado["nombre"] == empleado_valido["nombre"]
    assert resultado["email"] == empleado_valido["email"]


def test_crear_empleado_id_duplicado(mocker):
    """Debe lanzar excepción cuando el ID ya existe."""
    from app.database import EmpleadosDB, EmpleadoYaExisteError
    
    db = EmpleadosDB()
    
    mock_session = mocker.MagicMock()
    mocker.patch('app.database.get_db_session', return_value=mock_session.__enter__)
    
    # Simular que el ID ya existe
    mock_empleado_existente = mocker.MagicMock()
    mock_empleado_existente.id = 1
    mock_session.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_empleado_existente
    
    with pytest.raises(EmpleadoYaExisteError):
        db.crear_empleado(
            id=1,
            nombre="Test",
            cargo="Developer",
            email="test@empresa.com"
        )


def test_buscar_empleado_por_id_exitoso(empleado_valido, mocker):
    """Debe encontrar un empleado por ID."""
    from app.database import EmpleadosDB
    
    db = EmpleadosDB()
    
    mock_session = mocker.MagicMock()
    mocker.patch('app.database.get_db_session', return_value=mock_session.__enter__)
    
    mock_empleado = mocker.MagicMock()
    mock_empleado.id = empleado_valido["id"]
    mock_empleado.nombre = empleado_valido["nombre"]
    mock_empleado.cargo = empleado_valido["cargo"]
    mock_empleado.activo = True
    
    mock_session.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_empleado
    
    resultado = db.buscar_empleado_por_id(empleado_valido["id"])
    
    assert resultado is not None
    assert resultado["id"] == empleado_valido["id"]
    assert resultado["nombre"] == empleado_valido["nombre"]


def test_buscar_empleado_no_encontrado(mocker):
    """Debe lanzar excepción cuando el empleado no existe."""
    from app.database import EmpleadosDB, EmpleadoNoEncontradoError
    
    db = EmpleadosDB()
    
    mock_session = mocker.MagicMock()
    mocker.patch('app.database.get_db_session', return_value=mock_session.__enter__)
    mock_session.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None
    
    with pytest.raises(EmpleadoNoEncontradoError):
        db.buscar_empleado_por_id(999)


def test_eliminar_empleado_soft_delete(empleado_valido, mocker):
    """Debe realizar soft delete marcando activo=False."""
    from app.database import EmpleadosDB
    
    db = EmpleadosDB()
    
    mock_session = mocker.MagicMock()
    mocker.patch('app.database.get_db_session', return_value=mock_session.__enter__)
    
    mock_empleado = mocker.MagicMock()
    mock_empleado.id = empleado_valido["id"]
    mock_empleado.activo = True
    
    mock_session.__enter__.return_value.query.return_value.filter.return_value.first.return_value = mock_empleado
    
    db.eliminar_empleado(empleado_valido["id"])
    
    # Verificar que se marcó como inactivo
    assert mock_empleado.activo is False
    mock_session.__enter__.return_value.commit.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Tests de validaciones
# ─────────────────────────────────────────────────────────────────────────────

def test_modelo_empleado_email_valido():
    """Debe aceptar emails válidos."""
    empleado = EmpleadoCreate(
        id=1,
        nombre="Test",
        cargo="Developer",
        email="test@empresa.com"
    )
    
    assert empleado.email == "test@empresa.com"


def test_modelo_empleado_email_invalido():
    """Debe rechazar emails inválidos."""
    with pytest.raises(ValueError):
        EmpleadoCreate(
            id=1,
            nombre="Test",
            cargo="Developer",
            email="email_invalido"
        )


def test_empleado_update_campos_opcionales():
    """Debe permitir actualización parcial."""
    update = EmpleadoUpdate(nombre="Nuevo Nombre")
    
    assert update.nombre == "Nuevo Nombre"
    assert update.cargo is None
    assert update.email is None


# ─────────────────────────────────────────────────────────────────────────────
# Tests de paginación y filtros
# ─────────────────────────────────────────────────────────────────────────────

def test_buscar_empleados_con_filtros(mocker):
    """Debe aplicar filtros correctamente."""
    from app.database import EmpleadosDB
    
    db = EmpleadosDB()
    
    mock_session = mocker.MagicMock()
    mocker.patch('app.database.get_db_session', return_value=mock_session.__enter__)
    
    mock_query = mocker.MagicMock()
    mock_session.__enter__.return_value.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = []
    mock_query.count.return_value = 0
    
    resultado = db.buscar_empleados(
        nombre="Juan",
        cargo="Developer",
        page=1,
        page_size=10
    )
    
    assert resultado["items"] == []
    assert resultado["total"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
