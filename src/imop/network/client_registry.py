"""Registro de clientes WebSocket conectados.

Base para la comunicación bidireccional futura (envío de teclas/datos
al ESP32 desde la GUI).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from typing import Any

from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


class ClientRegistry:
    """Trackea las conexiones activas y permite difundir mensajes."""

    def __init__(self, on_change: Callable[[int], None] | None = None) -> None:
        """Inicializa el registro.

        Args:
            on_change: Callback (opcional) invocado con la cantidad de
                clientes cada vez que cambia.
        """
        self._clients: set[Any] = set()
        self._lock = asyncio.Lock()
        self._on_change = on_change

    @property
    def count(self) -> int:
        """Cantidad de clientes conectados actualmente."""
        return len(self._clients)

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
        """Notifica el cambio en la cantidad de clientes."""
        if self._on_change is not None:
            self._on_change(len(self._clients))
