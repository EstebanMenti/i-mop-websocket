"""Registro de clientes WebSocket conectados.

Base para la comunicación bidireccional (consola de comandos hacia el
ESP32 desde la GUI): envío dirigido, difusión y listado de peers.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from typing import Any

from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)

#: Etiqueta que representa "todos los clientes" en el selector de destino.
BROADCAST_TARGET = "Todos (broadcast)"


class ClientRegistry:
    """Trackea las conexiones activas y permite enviarles mensajes."""

    def __init__(self, on_change: Callable[[list[str]], None] | None = None) -> None:
        """Inicializa el registro.

        Args:
            on_change: Callback (opcional) invocado con la lista de peers
                conectados cada vez que cambia.
        """
        self._clients: set[Any] = set()
        self._lock = asyncio.Lock()
        self._on_change = on_change

    @property
    def count(self) -> int:
        """Cantidad de clientes conectados actualmente."""
        return len(self._clients)

    @staticmethod
    def peer_label(connection: Any) -> str:
        """Etiqueta legible de un cliente (``host:puerto`` remoto).

        Args:
            connection: Conexión WebSocket registrada.

        Returns:
            Etiqueta ``host:puerto``; ``"desconocido"`` si no hay dirección.
        """
        address = getattr(connection, "remote_address", None)
        if address is None:
            return "desconocido"
        host, port = address[0], address[1]
        return f"{host}:{port}"

    def peers(self) -> list[str]:
        """Lista de etiquetas ``host:puerto`` de los clientes conectados.

        Returns:
            Etiquetas ordenadas para mostrar en la GUI.
        """
        return sorted(self.peer_label(c) for c in self._clients)

    def resolve(self, peer: str) -> Any | None:
        """Resuelve la etiqueta de un peer a su conexión.

        Args:
            peer: Etiqueta ``host:puerto``; cualquier otro valor
                (incluido :data:`BROADCAST_TARGET`) devuelve ``None``.

        Returns:
            La conexión correspondiente, o ``None`` si no existe.
        """
        if peer == BROADCAST_TARGET:
            return None
        for connection in self._clients:
            if self.peer_label(connection) == peer:
                return connection
        return None

    async def send_to(self, connection: Any, text: str) -> bool:
        """Envía un texto a un cliente específico.

        Args:
            connection: Conexión destino.
            text: Contenido a enviar.

        Returns:
            ``True`` si el envío salió bien; ``False`` si el cliente estaba
            muerto (se descarta del registro).
        """
        try:
            await connection.send(text)
            return True
        except ConnectionClosed:
            self._clients.discard(connection)
            self._notify()
        except OSError:
            logger.exception("Fallo de red al enviar a un cliente")
        return False

    @asynccontextmanager
    async def register(self, connection: Any) -> AsyncIterator[None]:
        """Contexto de vida de una conexión: la registra y da de baja al salir.

        Args:
            connection: Conexión WebSocket del cliente.

        Yields:
            ``None`` mientras la conexión está registrada.
        """
        self._clients.add(connection)
        self._notify()
        try:
            yield
        finally:
            self._clients.discard(connection)
            self._notify()

    async def broadcast(self, text: str) -> int:
        """Envía un texto a todos los clientes conectados.

        Los clientes muertos se descartan silenciosamente.

        Args:
            text: Contenido a enviar.

        Returns:
            Cantidad de clientes a los que se envió con éxito.
        """
        sent = 0
        for connection in list(self._clients):
            try:
                await connection.send(text)
                sent += 1
            except ConnectionClosed:
                self._clients.discard(connection)
                self._notify()
            except OSError:
                logger.exception("Fallo de red al difundir a un cliente")
        return sent

    async def close_all(self) -> None:
        """Cierra todas las conexiones activas (usado al detener el servidor)."""
        for connection in list(self._clients):
            with suppress(ConnectionClosed, OSError):
                await connection.close()
        self._clients.clear()
        self._notify()

    def _notify(self) -> None:
        """Notifica el cambio en la lista de clientes conectados."""
        if self._on_change is not None:
            self._on_change(self.peers())
