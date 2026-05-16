import os
import json
import logging
import asyncio
from aio_pika import connect_robust, Message, DeliveryMode
from app.database import SesionLocal, Usuario
from app.jwt_utils import crear_token_recuperacion

logger = logging.getLogger(__name__)

# URL del broker de mensajes (inyectada vía variable de entorno)
URL_RABBITMQ = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
NOMBRE_EXCHANGE = "rrhh_events"


class BrokerAuth:
    """
    Cliente RabbitMQ del servicio de autenticación.

    Consume:
        - empleado.creado        → crea usuario inhabilitado y publica usuario.creado
        - empleado.eliminado     → inhabilita el usuario asociado permanentemente
        - vacaciones.programadas → desactiva cuenta temporalmente (inicio de vacaciones)
        - vacaciones.finalizadas → reactiva cuenta (fin de vacaciones)

    Publica:
        - usuario.creado       → disparado al consumir empleado.creado
        - cuenta.desactivada   → disparado al inhabilitar por offboarding o vacaciones
        - cuenta.activada      → disparado al reactivar por fin de vacaciones
    """

    def __init__(self):
        self.conexion = None
        self.canal = None
        self.exchange = None

    async def _conectar(self):
        """Establece conexión con RabbitMQ con reintentos automáticos."""
        max_reintentos = 20
        for intento in range(max_reintentos):
            try:
                self.conexion = await connect_robust(URL_RABBITMQ)
                self.canal = await self.conexion.channel()
                self.exchange = await self.canal.declare_exchange(
                    NOMBRE_EXCHANGE, type="topic", durable=True
                )
                logger.info("Broker auth conectado a RabbitMQ")
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

    async def iniciar(self):
        """Inicia la conexión y el consumidor de eventos de empleados."""
        await self._conectar()
        cola = await self.canal.declare_queue("auth_queue", durable=True)
        await cola.bind(self.exchange, "empleado.creado")
        await cola.bind(self.exchange, "empleado.eliminado")
        await cola.bind(self.exchange, "vacaciones.programadas")
        await cola.bind(self.exchange, "vacaciones.finalizadas")
        await cola.consume(self._procesar_mensaje)
        logger.info("Broker auth: consumidor iniciado, esperando eventos...")

    async def _procesar_mensaje(self, mensaje):
        """Callback principal para todos los mensajes entrantes."""
        async with mensaje.process():
            clave_ruteo = mensaje.routing_key
            try:
                datos = json.loads(mensaje.body)
                logger.info(
                    f"Evento recibido: {clave_ruteo}",
                    extra={"evento": clave_ruteo, "datos": datos}
                )

                if clave_ruteo == "empleado.creado":
                    await self._manejar_empleado_creado(datos)
                elif clave_ruteo == "empleado.eliminado":
                    await self._manejar_empleado_eliminado(datos)
                elif clave_ruteo == "vacaciones.programadas":
                    await self._manejar_vacaciones_programadas(datos)
                elif clave_ruteo == "vacaciones.finalizadas":
                    await self._manejar_vacaciones_finalizadas(datos)

            except Exception as error:
                logger.error(f"Error procesando evento '{clave_ruteo}': {error}")

    async def _manejar_empleado_creado(self, datos: dict):
        """
        Al recibir empleado.creado:
        1. Crea un usuario inhabilitado (sin contraseña) con rol USER.
        2. Genera un token de recuperación/establecimiento de contraseña.
        3. Publica el evento usuario.creado con email y token.
        """
        email = datos.get("email")
        if not email:
            logger.warning("Evento empleado.creado recibido sin campo 'email', ignorando.")
            return

        empleado_id = datos.get("id")
        db = SesionLocal()
        try:
            # Verificar si el usuario ya existe (idempotencia)
            usuario_existente = db.query(Usuario).filter(Usuario.email == email).first()
            if not usuario_existente:
                nuevo_usuario = Usuario(
                    nombre_usuario=email,
                    email=email,
                    hash_contrasena=None,
                    rol="USER",
                    activo=False,  # Inhabilitado hasta que establezca su contraseña
                    empleado_id=empleado_id,
                )
                db.add(nuevo_usuario)
                db.commit()
                logger.info(f"Usuario creado automáticamente para el empleado: {email}")
            else:
                # Actualizar empleado_id si aún no estaba vinculado
                if empleado_id and not usuario_existente.empleado_id:
                    usuario_existente.empleado_id = empleado_id
                    db.commit()
                logger.info(f"Usuario ya existía para el empleado: {email}")

            # Generar token de establecimiento de contraseña (JWT stateless)
            token_recuperacion = crear_token_recuperacion(email)

            # Publicar evento para que notificaciones-service envíe el enlace
            await self.publicar("usuario.creado", {"email": email, "token": token_recuperacion})

        finally:
            db.close()

    async def _manejar_empleado_eliminado(self, datos: dict):
        """
        Al recibir empleado.eliminado:
        Inhabilita lógicamente al usuario, impidiendo futuros logins.
        Publica cuenta.desactivada para que notificaciones-service envíe email.
        """
        email = datos.get("email")
        if not email:
            return

        db = SesionLocal()
        try:
            usuario = db.query(Usuario).filter(Usuario.email == email).first()
            if usuario:
                usuario.activo = False
                db.commit()
                logger.info(f"Usuario inhabilitado por offboarding: {email}")
                await self.publicar(
                    "cuenta.desactivada",
                    {
                        "usuario_id": usuario.id,
                        "email": email,
                        "motivo": datos.get("motivo", "offboarding"),
                    }
                )
            else:
                logger.warning(f"No se encontró usuario para inhabilitar: {email}")
        finally:
            db.close()

    async def _manejar_vacaciones_programadas(self, datos: dict):
        """
        Al recibir vacaciones.programadas:
        Desactiva temporalmente la cuenta del empleado durante su periodo de vacaciones.
        Publica cuenta.desactivada para que notificaciones-service notifique al empleado.
        """
        empleado_id = datos.get("empleado_id")
        if not empleado_id:
            logger.warning("Evento vacaciones.programadas sin campo 'empleado_id', ignorando.")
            return

        db = SesionLocal()
        try:
            usuario = db.query(Usuario).filter(Usuario.empleado_id == empleado_id).first()
            if usuario:
                usuario.activo = False
                db.commit()
                logger.info(f"Cuenta desactivada por vacaciones para empleado_id: {empleado_id}")
                await self.publicar(
                    "cuenta.desactivada",
                    {
                        "usuario_id": usuario.id,
                        "email": usuario.email,
                        "motivo": "vacaciones",
                        "fecha_inicio": datos.get("fecha_inicio"),
                        "fecha_fin": datos.get("fecha_fin"),
                    }
                )
            else:
                logger.warning(
                    f"No se encontró usuario para empleado_id: {empleado_id} "
                    f"(vacaciones.programadas)"
                )
        finally:
            db.close()

    async def _manejar_vacaciones_finalizadas(self, datos: dict):
        """
        Al recibir vacaciones.finalizadas:
        Reactiva la cuenta del empleado al terminar sus vacaciones.
        Publica cuenta.activada para que notificaciones-service notifique al empleado.
        """
        empleado_id = datos.get("empleado_id")
        if not empleado_id:
            logger.warning("Evento vacaciones.finalizadas sin campo 'empleado_id', ignorando.")
            return

        db = SesionLocal()
        try:
            usuario = db.query(Usuario).filter(Usuario.empleado_id == empleado_id).first()
            if usuario:
                usuario.activo = True
                db.commit()
                logger.info(f"Cuenta reactivada por fin de vacaciones para empleado_id: {empleado_id}")
                await self.publicar(
                    "cuenta.activada",
                    {
                        "usuario_id": usuario.id,
                        "email": usuario.email,
                    }
                )
            else:
                logger.warning(
                    f"No se encontró usuario para empleado_id: {empleado_id} "
                    f"(vacaciones.finalizadas)"
                )
        finally:
            db.close()

    async def publicar(self, clave_ruteo: str, datos: dict):
        """Publica un evento en el exchange de RabbitMQ."""
        if not self.exchange:
            await self._conectar()
        cuerpo = json.dumps(datos).encode("utf-8")
        mensaje = Message(
            body=cuerpo,
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
        )
        await self.exchange.publish(mensaje, routing_key=clave_ruteo)
        logger.info(f"Evento publicado: {clave_ruteo}")

    async def detener(self):
        """Cierra la conexión con RabbitMQ al apagar el servicio."""
        if self.conexion and not self.conexion.is_closed:
            await self.conexion.close()
            logger.info("Conexión RabbitMQ cerrada.")


# Instancia global (Singleton)
broker = BrokerAuth()
