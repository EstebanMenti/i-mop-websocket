"""Tests de la consola remota: enrutamiento del worker y terminal integrada.

El worker se prueba sin arrancar el hilo (``_handle_raw`` se invoca
directo); el panel se prueba offscreen con QApplication. El test E2E
arranca el worker completo con un cliente real de ``websockets``.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from websockets.asyncio.client import connect

from imop.gui.workers import ServerWorker

pytest.importorskip("PySide6.QtWidgets")

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

pytestmark = pytest.mark.gui


@pytest.fixture
def qapp() -> QApplication:
    """Crea (o reutiliza) la QApplication offscreen."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app  # type: ignore[misc]


@pytest.fixture
def worker(tmp_path: Path) -> ServerWorker:
    """Worker con pipeline real (sin iniciar el hilo del servidor).

    Yields:
        ServerWorker listo para recibir frames en ``_handle_raw``.
    """
    from imop.core.pipeline import MessagePipeline
    from imop.logging_service.handlers import FilterLogManager

    pipeline = MessagePipeline(
        rules=[],
        log_manager=FilterLogManager(log_dir=tmp_path),  # type: ignore[arg-type]
    )
    return ServerWorker(host="127.0.0.1", port=0, pipeline=pipeline)


def collect(worker: ServerWorker, signal_name: str) -> list[object]:
    """Conecta una señal del worker a una lista y devuelve la lista.

    Args:
        worker: ServerWorker bajo prueba.
        signal_name: Nombre de la señal (``console_output`` o ``message_received``).

    Returns:
        Lista que se llena con cada emisión.
    """
    received: list[object] = []
    getattr(worker, signal_name).connect(received.append)
    return received


def test_frame_texto_plano_va_a_la_consola(worker: ServerWorker) -> None:
    console = collect(worker, "console_output")
    telemetry = collect(worker, "message_received")
    worker._handle_raw("modo: STA, ip: 192.168.0.42")
    assert console == ["modo: STA, ip: 192.168.0.42"]
    assert telemetry == []


def test_frame_json_va_a_telemetria(worker: ServerWorker, tmp_path: Path) -> None:
    console = collect(worker, "console_output")
    telemetry = collect(worker, "message_received")
    raw = json.dumps({"sensor_temp": {"value": 23.4}})
    worker._handle_raw(raw)
    assert console == []
    assert len(telemetry) == 1


def test_frame_json_invalido_va_a_la_consola(worker: ServerWorker) -> None:
    console = collect(worker, "console_output")
    telemetry = collect(worker, "message_received")
    worker._handle_raw("{esto no es json")
    assert console == ["{esto no es json"]
    assert telemetry == []


def test_send_command_sin_servidor_no_falla(worker: ServerWorker) -> None:
    """Sin loop activo, ``send_command`` descarta el comando sin lanzar."""
    worker.send_command("server")  # no debe lanzar excepciones


def _press(term: object, key: object) -> None:
    """Envía un QKeyEvent de teclado a la terminal.

    Args:
        term: ConsoleTerminal bajo prueba.
        key: Tecla Qt a simular.
    """
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent

    event = QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
    term.keyPressEvent(event)  # type: ignore[attr-defined]


def test_terminal_historial_y_envio(qapp: QApplication) -> None:
    """Escribir + Enter emite el comando; ↑/↓ recorren el historial."""
    from PySide6.QtCore import Qt

    from imop.gui.panels.console_panel import ConsolePanel

    panel = ConsolePanel()
    sent: list[tuple[str, str]] = []
    panel.send_requested.connect(lambda cmd, peer: sent.append((cmd, peer)))

    # Sin clientes conectados el destino queda vacío (sin broadcast).
    assert panel.current_target() == ""

    # Escribir en la terminal y enviar con Enter.
    panel.terminal.set_input("pass set abc123")
    _press(panel.terminal, Qt.Key.Key_Return)
    assert sent == [("pass set abc123", "")]
    assert panel.terminal._input_text() == ""

    # ↑ recupera el último comando; ↓ de nuevo vacía la línea.
    _press(panel.terminal, Qt.Key.Key_Up)
    assert panel.terminal._input_text() == "pass set abc123"
    _press(panel.terminal, Qt.Key.Key_Down)
    assert panel.terminal._input_text() == ""

    # Línea vacía + Enter no envía nada.
    _press(panel.terminal, Qt.Key.Key_Return)
    assert len(sent) == 1

    # El eco local quedó en la salida (comando en verde).
    assert "pass set abc123" in panel.terminal.toPlainText()


def test_terminal_sin_eco_borra_la_linea(qapp: QApplication) -> None:
    """Con eco desactivado, el comando no queda en la salida."""
    from PySide6.QtCore import Qt

    from imop.gui.panels.console_panel import ConsolePanel

    panel = ConsolePanel()
    panel.echo_check.setChecked(False)
    sent: list[tuple[str, str]] = []
    panel.send_requested.connect(lambda cmd, peer: sent.append((cmd, peer)))

    panel.terminal.set_input("server")
    _press(panel.terminal, Qt.Key.Key_Return)
    assert sent == [("server", "")]
    assert "server" not in panel.terminal.toPlainText()


def test_panel_selector_de_destino_sin_broadcast(qapp: QApplication) -> None:
    """El combo solo lista peers; sin clientes queda deshabilitado."""
    from imop.gui.panels.console_panel import ConsolePanel

    panel = ConsolePanel()
    assert panel.current_target() == ""
    assert not panel.target_combo.isEnabled()

    # Con un peer conectado, el combo lo selecciona por defecto.
    panel.set_peers(["192.168.0.42:4511"])
    assert panel.target_combo.isEnabled()
    assert panel.current_target() == "192.168.0.42:4511"

    # Si ese peer se desconecta, queda el primero disponible.
    panel.set_peers(["192.168.0.42:4511", "192.168.0.42:4512"])
    assert panel.current_target() == "192.168.0.42:4511"
    panel.set_peers([])
    assert panel.current_target() == ""
    assert not panel.target_combo.isEnabled()
    # Nunca aparece la opción de broadcast.
    for i in range(panel.target_combo.count()):
        assert "broadcast" not in panel.target_combo.itemText(i).lower()


def test_panel_salida_y_limpiar(qapp: QApplication) -> None:
    from imop.gui.panels.console_panel import ConsolePanel

    panel = ConsolePanel()
    panel.append_output("OK")
    panel.append_output("ERROR: pass vacío\n")
    assert "OK" in panel.terminal.toPlainText()
    assert "ERROR: pass vacío" in panel.terminal.toPlainText()
    panel.clear_output()
    assert "OK" not in panel.terminal.toPlainText()
    # Tras limpiar queda una línea de prompt lista para escribir.
    assert panel.terminal._prompt_pos > 0


def test_terminal_fondo_negro(qapp: QApplication) -> None:
    """La terminal usa fondo negro (requisito visual de la consola)."""
    from imop.gui.panels.console_panel import TERMINAL_STYLESHEET, ConsoleTerminal

    term = ConsoleTerminal()
    assert "#000000" in TERMINAL_STYLESHEET
    assert "#000000" in term.styleSheet()


async def test_e2e_worker_comando_y_respuesta(qapp: QApplication, tmp_path: Path) -> None:
    """Envía un comando desde el hilo Qt y recibe la respuesta del "ESP".

    Flujo completo: worker (QThread + asyncio) con servidor real → cliente
    eco que actúa como ESP32 → el comando llega con ``\\n`` y la respuesta
    de texto plano sale por ``console_output``.
    """
    from PySide6.QtWidgets import QApplication

    from imop.core.pipeline import MessagePipeline
    from imop.logging_service.handlers import FilterLogManager

    pipeline = MessagePipeline(
        rules=[],
        log_manager=FilterLogManager(log_dir=tmp_path),  # type: ignore[arg-type]
    )
    worker = ServerWorker(host="127.0.0.1", port=0, pipeline=pipeline)
    console: list[str] = []
    worker.console_output.connect(console.append)
    worker.start()
    app = QApplication.instance()
    try:
        # Las señales Qt entre hilos son encoladas: hay que procesar eventos
        # en el hilo principal para recibirlas. Esperamos el puerto en escucha.
        for _ in range(500):
            if worker.bound_port is not None:
                break
            if app is not None:
                app.processEvents()
            await asyncio.sleep(0.01)
        assert worker.bound_port is not None
        uri = f"ws://127.0.0.1:{worker.bound_port}"
        async with connect(uri) as esp:
            # El comando sale del hilo Qt (thread-safe) y llega con \n final.
            worker.send_command("pass get", peer=None)  # difusión (capa de red)
            assert await asyncio.wait_for(esp.recv(), timeout=2.0) == "pass get\n"
            # El "ESP" responde texto plano → consola.
            await esp.send("OK miclave123")
            for _ in range(500):
                if console:
                    break
                if app is not None:
                    app.processEvents()
                await asyncio.sleep(0.01)
            assert console == ["OK miclave123"]
    finally:
        worker.stop()
        assert worker.wait(5000)
