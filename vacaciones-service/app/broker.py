import os
import json
import logging
import asyncio
from aio_pika import connect_robust, Message, DeliveryMode

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
NOMBRE_EXCHANGE = os.environ.get("RABBITMQ_EXCHANGE", "rrhh_events")


class BrokerVacaciones:

    def __init__(self):
        self.conexion = None
        self.canal = None
        self.exchange = None

    async def _conectar(self):
        max_reintentos = 20
        for intento in range(max_reintentos):
            try:
                self.conexion = await connect_robust(RABBITMQ_URL)
                self.canal = await self.conexion.channel()
                self.exchange = await self.canal.declare_exchange(
                    NOMBRE_EXCHANGE, type="topic", durable=True
                )
                logger.info("Broker vacaciones conectado a RabbitMQ")
                return
            except Exception as error:
                if intento < max_reintentos - 1:
                    logger.warning(
                        f"Error conectando a RabbitMQ: {error}. "
                        f"Reintentando en 5s... ({intento + 1}/{max_reintentos})"
                    )
                    await asyncio.sleep(5)
                else:
                    logger.error("No se pudo conectar a RabbitMQ tras todos los reintentos.")
                    raise

    async def publicar(self, clave_ruteo: str, datos: dict):
        if not self.exchange:
            await self._conectar()
        cuerpo = json.dumps(datos, default=str).encode("utf-8")
        mensaje = Message(
            body=cuerpo,
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
        )
        await self.exchange.publish(mensaje, routing_key=clave_ruteo)
        logger.info(f"Evento publicado: {clave_ruteo}", extra={"evento": clave_ruteo})

    async def detener(self):
        if self.conexion and not self.conexion.is_closed:
            await self.conexion.close()
            logger.info("Conexión RabbitMQ cerrada.")


broker = BrokerVacaciones()
