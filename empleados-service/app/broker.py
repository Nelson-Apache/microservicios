import os
import json
import logging
import asyncio
from aio_pika import connect_robust, Message, DeliveryMode

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")


class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.exchange_name = "rrhh_events"

    async def connect(self):
        logger.info(f"Conectando a RabbitMQ en {RABBITMQ_URL}")
        max_retries = 20
        for i in range(max_retries):
            try:
                self.connection = await connect_robust(RABBITMQ_URL)
                self.channel = await self.connection.channel()
                self.exchange = await self.channel.declare_exchange(
                    self.exchange_name,
                    type="topic",
                    durable=True
                )
                logger.info("Conexión a RabbitMQ establecida exitosamente")
                return
            except Exception as e:
                if i < max_retries - 1:
                    logger.warning(f"Error al conectar a RabbitMQ: {e}. Reintentando en 5 segundos... ({i+1}/{max_retries})")
                    await asyncio.sleep(5)
                else:
                    logger.error("No se pudo conectar a RabbitMQ después de varios reintentos.")
                    raise

    async def iniciar_consumidor(self):
        """
        Suscribe empleados-service a eventos de vacaciones para mantener
        el campo estado sincronizado con el ciclo de vida del empleado.
        """
        from app.database import db
        cola = await self.channel.declare_queue("empleados_vacaciones_queue", durable=True)
        await cola.bind(self.exchange, "vacaciones.programadas")
        await cola.bind(self.exchange, "vacaciones.finalizadas")

        async def _procesar(mensaje):
            async with mensaje.process():
                clave = mensaje.routing_key
                try:
                    datos = json.loads(mensaje.body)
                    empleado_id = datos.get("empleado_id")
                    if not empleado_id:
                        return

                    if clave == "vacaciones.programadas":
                        actualizado = db.actualizar_estado_empleado(empleado_id, "EN_VACACIONES")
                        if actualizado:
                            logger.info(
                                "Estado empleado actualizado a EN_VACACIONES",
                                extra={"empleado_id": empleado_id}
                            )
                    elif clave == "vacaciones.finalizadas":
                        actualizado = db.actualizar_estado_empleado(empleado_id, "ACTIVO")
                        if actualizado:
                            logger.info(
                                "Estado empleado restaurado a ACTIVO",
                                extra={"empleado_id": empleado_id}
                            )
                except Exception as error:
                    logger.error(
                        f"Error procesando evento '{clave}': {error}",
                        extra={"evento": clave}
                    )

        await cola.consume(_procesar)
        logger.info("Consumidor de vacaciones iniciado en empleados-service")

    async def close(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()

    async def publish_event(self, routing_key: str, event_data: dict):
        if not self.exchange:
            await self.connect()

        message_body = json.dumps(event_data).encode("utf-8")
        message = Message(
            body=message_body,
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json"
        )

        await self.exchange.publish(message, routing_key=routing_key)
        logger.info(f"Evento publicado: {routing_key}")


# Instancia global (Singleton)
rabbitmq_client = RabbitMQClient()
