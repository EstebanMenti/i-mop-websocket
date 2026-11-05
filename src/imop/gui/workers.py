"""Worker que ejecuta el servidor WebSocket en un hilo propio.

Puente asyncio ↔ Qt: el loop corre en este QThread y los mensajes se
entregan a la GUI mediante señales (thread-safe, queued connections).

Enrutamiento bidireccional:
- Frame JSON válido → pipeline de telemetría (filtros, logs, panel).
- Cualquier otro texto → consola remota (señal ``console_output``).
- La GUI envía líneas de comando con :meth:`send_command` (thread-safe).
"""

from __future__ import annotations

import asyncio
import logging

from PySide6.QtCore import QThread, Signal

from imop.core.models import DisplayMessage, ServerStatus
from imop.core.parser import MessageParseError, parse_message
from imop.core.pipeline import MessagePipeline
from imop.network.server import WebSocketServer

logger = logging.getLogger(__name__)


class ServerWorker(QThread):
    """Ciclo de vida completo del servidor en un hilo dedicado."""

    message_received = Signal(object)
    console_output = Signal(str)
    state_changed = Signal(object)
    clients_changed = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, host: str, port: int, pipeline: MessagePipeline) -> None:
        """Inicializa el worker (el servidor arranca con :meth:`start`).

        Args:
            host: Interfaz de escucha.
            port: Puerto TCP.
            pipeline: Pipeline de dominio que procesa cada mensaje.
        """
        super().__init__()
        self._host = host
        self._port = port
        self._pipeline = pipeline
        self._stop_event = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: WebSocketServer | None = None

    @property
    def bound_port(self) -> int | None:
        """Puerto realmente en escucha, o ``None`` si no arrancó."""
        if self._server is not None and self._server._bound_port is not None:
            return self._server._bound_port
        return None

    def run(self) -> None:
        """Punto de entrada del hilo: corre el loop asyncio hasta parar."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._stop_event = asyncio.Event()
        self._server = WebSocketServer(
            host=self._host,
            port=self._port,
            on_message=self._handle_raw,
            on_clients_changed=self.clients_changed.emit,
        )

        async def _main() -> None:
            await self._server.start()  # type: ignore[union-attr]
            self.state_changed.emit(ServerStatus.RUNNING)
            await self._stop_event.wait()
            await self._server.stop()  # type: ignore[union-attr]

        try:
            loop.run_until_complete(_main())
        except OSError as exc:
            logger.error("No se pudo iniciar/sostener el servidor: %s", exc)
            self.error_occurred.emit(str(exc))
            self.state_changed.emit(ServerStatus.ERROR)
        finally:
            try:
                loop.close()
            except RuntimeError:
                logger.warning("Loop asyncio ya cerrado", exc_info=True)
            self.state_changed.emit(ServerStatus.STOPPED)

    def stop(self) -> None:
        """Solicita la detención ordenada (thread-safe)."""
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._stop_event.set)

    def send_command(self, cmd: str, peer: str | None = None) -> None:
        """Envía una línea de comando de la consola a un cliente (thread-safe).

        No espera la respuesta del ESP: el frame se publica en el loop del
        worker y la respuesta llega después por ``console_output``.

        Args:
            cmd: Comando tal como lo escribió el usuario.
            peer: Etiqueta ``host:puerto`` del destino; ``None`` difunde a
                todos los clientes conectados.
        """
        if self._loop is None or not self._loop.is_running() or self._server is None:
            logger.warning("Servidor no activo; comando de consola descartado")
            return
        asyncio.run_coroutine_threadsafe(self._server.send_console_line(cmd, peer), self._loop)

    def _handle_raw(self, raw: str) -> None:
        """Callback del servidor: enruta el frame según su tipo.

        JSON válido va al pipeline de telemetría; cualquier otro texto es
        salida de la consola remota.

        Args:
            raw: Frame de texto recibido.
        """
        try:
            parse_message(raw)
        except MessageParseError:
            self.console_output.emit(raw)
            return
        try:
            message: DisplayMessage | None = self._pipeline.process(raw)
        except Exception:
            logger.exception("Error en el pipeline; frame descartado")
            return
        if message is not None:
            self.message_received.emit(message)
