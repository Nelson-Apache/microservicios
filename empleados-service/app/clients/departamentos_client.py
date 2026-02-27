import os
import logging
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pybreaker import CircuitBreaker, CircuitBreakerError
from cachetools import TTLCache
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configurar logger
logger = logging.getLogger(__name__)


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
    
    Implementa patrones de resiliencia:
    - Retry logic con backoff exponencial (tenacity)
    - Circuit Breaker (pybreaker)
    - Cache con TTL para fallback cuando el servicio está caído
    
    El Circuit Breaker se abre después de 5 fallos consecutivos
    y permanece abierto por 60 segundos antes de intentar recovery.
    """

    def __init__(self):
        self.base_url = os.getenv(
            "DEPARTAMENTOS_SERVICE_URL",
            "http://departamentos-service:8080"
        )
        self.timeout = 5.0  # 5 segundos de timeout
        
        # Cache con TTL de 5 minutos para 100 departamentos
        self._cache: TTLCache = TTLCache(maxsize=100, ttl=300)
        
        # Circuit Breaker: se abre tras 5 fallos, se cierra tras 60s
        self._circuit_breaker = CircuitBreaker(
            fail_max=5,           # Máximo de fallos antes de abrir
            timeout_duration=60,  # Tiempo en estado abierto (segundos)
            name="departamentos-service"
        )
        
        logger.info(
            "DepartamentosClient inicializado",
            extra={
                "base_url": self.base_url,
                "circuit_breaker_fail_max": 5,
                "circuit_breaker_timeout": 60,
                "cache_ttl_seconds": 300
            }
        )

    def _get_from_cache(self, departamento_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene un departamento del cache si existe."""
        cache_key = f"dept_{departamento_id}"
        cached_value = self._cache.get(cache_key)
        
        if cached_value:
            logger.info(
                "Cache HIT para departamento",
                extra={"departamento_id": departamento_id, "source": "cache"}
            )
        
        return cached_value

    def _save_to_cache(self, departamento_id: int, data: Dict[str, Any]):
        """Guarda un departamento en el cache."""
        cache_key = f"dept_{departamento_id}"
        self._cache[cache_key] = data
        logger.debug(
            "Departamento guardado en cache",
            extra={"departamento_id": departamento_id}
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True
    )
    async def _fetch_departamento(self, departamento_id: int) -> Optional[Dict[str, Any]]:
        """
        Realiza la petición HTTP real al servicio de departamentos.
        Este método es llamado por el Circuit Breaker.
        """
        url = f"{self.base_url}/departamentos/{departamento_id}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                # Guardar en cache cuando la respuesta es exitosa
                self._save_to_cache(departamento_id, data)
                return data
            elif response.status_code == 404:
                return None
            else:
                raise DepartamentosServiceError(
                    f"Error del servicio de departamentos: {response.status_code}"
                )

    async def validar_departamento_existe(self, departamento_id: int) -> bool:
        """
        Valida si un departamento existe en el servicio de departamentos.
        
        Flujo de resiliencia:
        1. Verifica el Circuit Breaker
        2. Si está cerrado: intenta llamar al servicio (con retry)
        3. Si está abierto o falla: usa cache como fallback
        4. Si no hay cache: lanza excepción

        Args:
            departamento_id: ID del departamento a validar

        Returns:
            True si el departamento existe (en servicio o en cache)

        Raises:
            DepartamentoNoEncontradoError: Si el departamento no existe (404)
            DepartamentosServiceError: Si hay error y no hay cache disponible
        """
        try:
            # Intentar obtener del servicio con Circuit Breaker
            resultado = await self._circuit_breaker.call_async(
                self._fetch_departamento,
                departamento_id
            )
            
            if resultado is None:
                raise DepartamentoNoEncontradoError(departamento_id)
            
            logger.info(
                "Departamento validado exitosamente",
                extra={
                    "departamento_id": departamento_id,
                    "source": "service",
                    "circuit_state": self._circuit_breaker.current_state
                }
            )
            return True
            
        except CircuitBreakerError:
            # Circuit Breaker está abierto, usar cache como fallback
            logger.warning(
                "Circuit Breaker ABIERTO - usando cache como fallback",
                extra={
                    "departamento_id": departamento_id,
                    "circuit_state": "open",
                    "fail_counter": self._circuit_breaker.fail_counter
                }
            )
            
            cached_data = self._get_from_cache(departamento_id)
            if cached_data:
                return True
            else:
                raise DepartamentosServiceError(
                    f"Servicio de departamentos no disponible y no hay datos en cache para ID {departamento_id}"
                )
                
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            # Error de red, intentar fallback a cache
            logger.error(
                "Error de conexión con servicio de departamentos",
                extra={
                    "departamento_id": departamento_id,
                    "error": str(e),
                    "attempting_cache_fallback": True
                }
            )
            
            cached_data = self._get_from_cache(departamento_id)
            if cached_data:
                logger.info(
                    "Usando cache como fallback tras error de conexión",
                    extra={"departamento_id": departamento_id}
                )
                return True
            else:
                raise DepartamentosServiceError(
                    f"No se pudo conectar con el servicio de departamentos y no hay cache disponible: {str(e)}"
                )
                
        except DepartamentoNoEncontradoError:
            # Re-lanzar sin modificar
            raise
            
        except Exception as e:
            logger.error(
                "Error inesperado al validar departamento",
                extra={"departamento_id": departamento_id, "error": str(e)}
            )
            raise DepartamentosServiceError(f"Error al validar departamento: {str(e)}")

    async def obtener_departamento(self, departamento_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene la información completa de un departamento.
        
        Con fallback a cache si el servicio falla.

        Args:
            departamento_id: ID del departamento

        Returns:
            Diccionario con los datos del departamento, o None si no existe

        Raises:
            DepartamentosServiceError: Si hay error de comunicación y no hay cache
        """
        try:
            # Intentar obtener del servicio con Circuit Breaker
            resultado = await self._circuit_breaker.call_async(
                self._fetch_departamento,
                departamento_id
            )
            
            return resultado
            
        except CircuitBreakerError:
            # Circuit Breaker abierto, usar cache
            logger.warning(
                "Circuit Breaker ABIERTO - retornando datos de cache",
                extra={"departamento_id": departamento_id}
            )
            return self._get_from_cache(departamento_id)
            
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            # Fallback a cache
            cached_data = self._get_from_cache(departamento_id)
            if cached_data:
                logger.info(
                    "Usando cache tras error de conexión",
                    extra={"departamento_id": departamento_id}
                )
                return cached_data
            
            raise DepartamentosServiceError(
                f"No se pudo conectar con el servicio de departamentos: {str(e)}"
            )
            
        except Exception as e:
            raise DepartamentosServiceError(f"Error al obtener departamento: {str(e)}")

    def get_circuit_breaker_state(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del Circuit Breaker para monitoreo.
        
        Returns:
            Diccionario con el estado del circuit breaker
        """
        return {
            "state": self._circuit_breaker.current_state,
            "fail_counter": self._circuit_breaker.fail_counter,
            "fail_max": self._circuit_breaker.fail_max,
            "timeout_duration": self._circuit_breaker.timeout_duration,
            "cache_size": len(self._cache),
            "cache_maxsize": self._cache.maxsize
        }


# Instancia global del cliente
departamentos_client = DepartamentosClient()
