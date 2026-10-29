"""Servidor WebSocket asíncrono para recepción de mensajes JSON.

Pertenece a la capa de red: no importa nada de la capa GUI. Se ejecuta
dentro de un loop asyncio propio (hilo worker gestionado por ``gui.workers``).

Protocolo de confirmación (ACK): si el mensaje del cliente incluye un campo
``"seq"`` entero, el servidor responde con ``{"ack_seq": <seq>, "status": "ok|error"}``
después de procesarlo. Mensajes sin ``seq`` no generan respuesta (retrocompatible).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from imop.network.client_registry import ClientRegistry

logger = logging.getLogger(__name__)

SEQ_KEY = "seq"


class WebSocketServer:
    """Servidor WebSocket de texto; cada frame JSON se pasa al callback."""

    def __init__(
        self,
        host: str,
        port: int,
        on_message: Callable[[str], None],
        on_clients_changed: Callable[[int], None] | None = None,
    ) -> None:
        """Inicializa el servidor (no escucha hasta :meth:`start`).

        Args:
            host: Interfaz de escucha (``"0.0.0.0"`` para todas).
            port: Puerto TCP; ``0`` para elegir uno efímero (tests).
            on_message: Callback por cada frame de texto recibido.
                Se ejecuta en el loop del servidor; no debe bloquear.
            on_clients_changed: Callback opcional con el conteo de clientes.
        """
        self._host = host
        self._port = port
        self._on_message = on_message
        self.registry = ClientRegistry(on_change=on_clients_changed)
        self._httpd: Server | None = None
        self._bound_port: int | None = None

    @property
    def bound_port(self) -> int:
        """Puerto realmente en escucha tras :meth:`start` (útil con puerto 0).

        Raises:
            RuntimeError: Si el servidor aún no arrancó.
        """
        if self._bound_port is None:
            raise RuntimeError("El servidor no está iniciado; no hay puerto asignado")
        return self._bound_port

    async def start(self) -> None:
        """Pone el servidor en escucha.

        Raises:
            OSError: Si el puerto está ocupado o no se puede bindear.
        """
        self._httpd = await serve(self._handler, self._host, self._port)
        sockets = self._httpd.sockets or ()
        self._bound_port = sockets[0].getsockname()[1] if sockets else self._port
        logger.info("Servidor WebSocket escuchando en %s:%s", self._host, self._bound_port)

    async def stop(self) -> None:
        """Detiene la escucha y cierra todas las conexiones activas."""
        if self._httpd is not None:
            self._httpd.close()
            await self._httpd.wait_closed()
            self._httpd = None
        await self.registry.close_all()
        logger.info("Servidor WebSocket detenido")

    async def _handler(self, connection: ServerConnection) -> None:
        """Atiende una conexión de cliente hasta que se desconecta.

        Las caídas abruptas de red (ESP32 que se apaga, Wi-Fi que se corta)
        se registran en INFO sin propagar errores al framework.

        Args:
            connection: Conexión WebSocket entrante.
        """
        peer = connection.remote_address
        logger.debug("Cliente conectado: %s", peer)
        async with self.registry.register(connection):
            try:
                async for raw in connection:
                    if isinstance(raw, str):
                        await self._dispatch(connection, raw)
                    else:
                        logger.debug("Frame binario ignorado de %s (%d bytes)", peer, len(raw))
            except ConnectionClosed as exc:
                logger.info("Cliente %s cerró la conexión sin frame de cierre: %s", peer, exc)
            except (ConnectionResetError, OSError) as exc:
                logger.info("Cliente %s perdió la conexión de red: %s", peer, exc)
        logger.debug("Cliente desconectado: %s", peer)

    async def _dispatch(self, connection: ServerConnection, raw: str) -> None:
        """Procesa un frame de texto y confirma con ACK si corresponde.

        Args:
            connection: Conexión del cliente emisor.
            raw: Contenido de texto del frame.
        """
        seq = self._extract_seq(raw)
        try:
            self._on_message(raw)
        except Exception:
            # El callback (pipeline) ya maneja JSON inválido; esto protege
            # contra errores inesperados sin tumbar la conexión.
            logger.exception("Error inesperado procesando mensaje de %d bytes", len(raw))
            await self._send_ack(connection, seq, status="error")
            return
        await self._send_ack(connection, seq, status="ok")

    @staticmethod
    def _extract_seq(raw: str) -> int | None:
        """Extrae el campo ``seq`` del mensaje si es un entero válido.

        Args:
            raw: Frame de texto crudo.

        Returns:
            El valor de ``seq``, o ``None`` si no existe o no es entero.
        """
        try:
            payload: Any = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        seq = payload.get(SEQ_KEY)
        if isinstance(seq, int) and not isinstance(seq, bool):
            return seq
        return None

    @staticmethod
    async def _send_ack(
        connection: ServerConnection,
        seq: int | None,
        status: str,
    ) -> None:
        """Envía el ACK con el seq recibido (solo si el cliente envió seq).

        Args:
            connection: Conexión destino.
            seq: Valor de seq a confirmar; ``None`` no envía nada.
            status: ``"ok"`` o ``"error"`` según el resultado del procesamiento.
        """
        if seq is None:
            return
        ack = json.dumps({"ack_seq": seq, "status": status})
        try:
            await connection.send(ack)
            logger.debug("ACK enviado: %s", ack)
        except ConnectionClosed:
            logger.debug("No se pudo enviar ACK %d: conexión cerrada", seq)
