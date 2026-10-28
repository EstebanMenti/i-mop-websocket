"""Servidor WebSocket asíncrono para recepción de mensajes JSON.

Pertenece a la capa de red: no importa nada de la capa GUI. Se ejecuta
dentro de un loop asyncio propio (hilo worker gestionado por ``gui.workers``).
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from websockets.asyncio.server import Server, ServerConnection, serve

from imop.network.client_registry import ClientRegistry

logger = logging.getLogger(__name__)


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

        Args:
            connection: Conexión WebSocket entrante.
        """
        peer = connection.remote_address
        logger.debug("Cliente conectado: %s", peer)
        async with self.registry.register(connection):
            async for raw in connection:
                if isinstance(raw, str):
                    self._dispatch(raw)
                else:
                    logger.debug("Frame binario ignorado de %s (%d bytes)", peer, len(raw))
        logger.debug("Cliente desconectado: %s", peer)

    def _dispatch(self, raw: str) -> None:
        """Entrega un frame de texto al callback, aislando sus errores.

        Args:
            raw: Contenido de texto del frame.
        """
        try:
            self._on_message(raw)
        except Exception:
            # El callback (pipeline) ya maneja JSON inválido; esto protege
            # contra errores inesperados sin tumbar la conexión.
            logger.exception("Error inesperado procesando mensaje de %d bytes", len(raw))
