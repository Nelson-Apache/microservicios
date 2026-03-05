import os
import json
import logging
from aio_pika import connect_robust, Message, DeliveryMode

logger = logging.getLogger(__name__)

# Se obtiene la URL del entorno, por defecto apunta al de docker-compose
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

class RabbitMQClient:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.exchange_name = "rrhh_events" # Nombre del exchange

    async def connect(self):
        logger.info(f"Conectando a RabbitMQ en {RABBITMQ_URL}")
        self.connection = await connect_robust(RABBITMQ_URL)
        self.channel = await self.connection.channel()
        
        # Declarar un exchange de tipo topic para que múltiples consumidores escuchen
        self.exchange = await self.channel.declare_exchange(
            self.exchange_name, 
            type="topic", 
            durable=True
        )
        logger.info("Conexión a RabbitMQ establecida exitosamente")

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
