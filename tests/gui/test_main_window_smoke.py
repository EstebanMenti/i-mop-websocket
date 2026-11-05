"""Smoke test de la GUI: la ventana se construye sin errores.

Requiere PySide6; se ejecuta offscreen (sin mostrar la ventana).
Cubre el contador de paquetes y el reloj de la barra de estado.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

pytest.importorskip("PySide6.QtWidgets")

pytestmark = pytest.mark.gui


@pytest.fixture
def qapp() -> object:
    """Crea (o reutiliza) la QApplication offscreen."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _sample_message(text: str) -> object:
    """Construye un DisplayMessage de prueba.

    Args:
        text: Contenido del mensaje.

    Returns:
        DisplayMessage con timestamp actual.
    """
    from imop.core.models import DisplayMessage, MessageCategory

    return DisplayMessage(
        text=text,
        category=MessageCategory.DATA,
        color="#1e88e5",
        timestamp=datetime.now(timezone.utc),
    )


def test_ventana_principal_se_construye(qapp: object, tmp_path: object) -> None:
    from imop.config import AppConfig
    from imop.gui.main_window import MainWindow

    config = AppConfig(log_dir=tmp_path)  # type: ignore[arg-type]
    window = MainWindow(config)
    assert window.windowTitle().startswith("i-mop-websocket")
    assert window.statusBar() is not None

    # Simular mensajes entrantes y verificar el contador de paquetes.
    # (el render es por lotes: volcar el buffer antes de consultar la lista)
    window._on_message(_sample_message('sensor_temp | {"sensor_temp": 1}'))
    window._on_message(_sample_message('sensor_temp | {"sensor_temp": 2}'))
    window.message_panel.flush_now()
    assert window.message_panel.list_widget.count() == 2
    assert window.message_panel.packet_count == 2

    # "Limpiar" borra la lista y restablece el contador.
    window.message_panel.clear_all()
    assert window.message_panel.list_widget.count() == 0
    assert window.message_panel.packet_count == 0
    assert window.message_panel.counter_label.text() == "Paquetes: 0"

    # El reloj existe y muestra una hora con formato HH:MM:SS.
    clock_text = window._clock_label.text()
    assert len(clock_text) == 8
    assert clock_text[2] == ":" and clock_text[5] == ":"
    window.close()


def test_limpiar_button_restablece_contador(qapp: object, tmp_path: object) -> None:
    from PySide6.QtWidgets import QApplication

    from imop.config import AppConfig
    from imop.gui.main_window import MainWindow

    _ = QApplication.instance() or QApplication([])
    config = AppConfig(log_dir=tmp_path)  # type: ignore[arg-type]
    window = MainWindow(config)
    window._on_message(_sample_message("x | {}"))
    window.message_panel.flush_now()
    assert window.message_panel.packet_count == 1

    window.message_panel.clear_button.click()
    assert window.message_panel.packet_count == 0
    window.close()


def test_ventana_tiene_pestana_consola(qapp: object, tmp_path: object) -> None:
    """La ventana principal expone las pestañas Telemetría y Consola."""
    from imop.config import AppConfig
    from imop.gui.main_window import MainWindow

    config = AppConfig(log_dir=tmp_path)  # type: ignore[arg-type]
    window = MainWindow(config)
    assert window.tabs.count() == 2
    assert window.tabs.tabText(0) == "Telemetría"
    assert window.tabs.tabText(1) == "Consola"

    # El contador de clientes del ServerPanel responde a la lista de peers.
    window._on_clients_changed(["192.168.0.42:4511"])
    assert window.server_panel.clients_label.text() == "1"
    assert window.console_panel.current_target() == "192.168.0.42:4511"

    # La salida de consola del worker llega a la terminal integrada.
    window._on_console_output("OK")
    assert "OK" in window.console_panel.terminal.toPlainText()

    # Enviar con el servidor detenido no lanza errores (solo avisa en la barra).
    window._on_console_send("server", "192.168.0.42:4511")
    window.close()


def test_alta_tasa_de_mensajes_lote(qapp: object, tmp_path: object) -> None:
    """A alta tasa, el render por lotes mantiene la lista acotada y el buffer vacío."""
    from imop.config import AppConfig
    from imop.constants import MAX_DISPLAY_MESSAGES
    from imop.gui.main_window import MainWindow

    config = AppConfig(log_dir=tmp_path)  # type: ignore[arg-type]
    window = MainWindow(config)

    total = 1500  # ~15 s a 100 msg/s, el escenario que congelaba la GUI
    for i in range(total):
        window._on_message(_sample_message(f'sensor_temp | {{"n": {i}}}'))

    assert window.message_panel.packet_count == total
    assert window.message_panel.pending_count > 0  # todavía no se pintó todo

    window.message_panel.flush_now()
    assert window.message_panel.pending_count == 0
    assert window.message_panel.list_widget.count() == MAX_DISPLAY_MESSAGES

    # "Limpiar" también descarta el buffer pendiente.
    window._on_message(_sample_message('sensor_temp | {"n": 9999}'))
    window.message_panel.clear_all()
    window.message_panel.flush_now()
    assert window.message_panel.list_widget.count() == 0
    assert window.message_panel.packet_count == 0
    window.close()
