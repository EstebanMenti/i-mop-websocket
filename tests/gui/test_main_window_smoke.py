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
    window._on_message(_sample_message('sensor_temp | {"sensor_temp": 1}'))
    window._on_message(_sample_message('sensor_temp | {"sensor_temp": 2}'))
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
    assert window.message_panel.packet_count == 1

    window.message_panel.clear_button.click()
    assert window.message_panel.packet_count == 0
    window.close()
