import os
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional


class DepartamentoNoEncontradoError(Exception):
    """Excepción cuando no se encuentra un departamento."""
    def __init__(self, departamento_id: int):
        self.departamento_id = departamento_id
        self.message = f"El departamento con ID {departamento_id} no existe."
        super().__init__(self.message)


class DepartamentosServiceError(Exception):
    """Excepción cuando el servicio de departamentos no responde."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class DepartamentosClient:
    """
    Cliente HTTP para interactuar con el servicio de departamentos.
    Implementa retry logic con backoff exponencial.
    """

    def __init__(self):
        self.base_url = os.getenv(
            "DEPARTAMENTOS_SERVICE_URL",
            "http://departamentos-service:8080"
        )
        self.timeout = 5.0  # 5 segundos de timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True
    )
    async def validar_departamento_existe(self, departamento_id: int) -> bool:
        """
        Valida si un departamento existe en el servicio de departamentos.

        Args:
            departamento_id: ID del departamento a validar

        Returns:
            True si el departamento existe

        Raises:
            DepartamentoNoEncontradoError: Si el departamento no existe (404)
            DepartamentosServiceError: Si hay error de comunicación con el servicio
        """
        url = f"{self.base_url}/departamentos/{departamento_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    return True
                elif response.status_code == 404:
                    raise DepartamentoNoEncontradoError(departamento_id)
                else:
                    raise DepartamentosServiceError(
                        f"Error inesperado del servicio de departamentos: {response.status_code}"
                    )

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            # El retry de tenacity reintentará automáticamente
            raise DepartamentosServiceError(
                f"No se pudo conectar con el servicio de departamentos: {str(e)}"
            )
        except DepartamentoNoEncontradoError:
            # Re-lanzar sin modificar
            raise
        except Exception as e:
            raise DepartamentosServiceError(
                f"Error al validar departamento: {str(e)}"
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True
    )
    async def obtener_departamento(self, departamento_id: int) -> Optional[dict]:
        """
        Obtiene la información completa de un departamento.

        Args:
            departamento_id: ID del departamento

        Returns:
            Diccionario con los datos del departamento, o None si no existe

        Raises:
            DepartamentosServiceError: Si hay error de comunicación
        """
        url = f"{self.base_url}/departamentos/{departamento_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    raise DepartamentosServiceError(
                        f"Error del servicio de departamentos: {response.status_code}"
                    )

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            raise DepartamentosServiceError(
                f"No se pudo conectar con el servicio de departamentos: {str(e)}"
            )
        except Exception as e:
            raise DepartamentosServiceError(f"Error al obtener departamento: {str(e)}")


# Instancia global del cliente
departamentos_client = DepartamentosClient()
