"""Smoke test de la GUI: la ventana se construye sin errores.

Requiere PySide6; se ejecuta offscreen (sin mostrar la ventana).
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

pytestmark = pytest.mark.gui


@pytest.fixture
def qapp() -> object:
    """Crea (o reutiliza) la QApplication offscreen."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_ventana_principal_se_construye(qapp: object, tmp_path: object) -> None:
    from imop.config import AppConfig
    from imop.gui.main_window import MainWindow

    config = AppConfig(log_dir=tmp_path)  # type: ignore[arg-type]
    window = MainWindow(config)
    assert window.windowTitle().startswith("i-mop-websocket")

    # Simular un mensaje entrante y verificar que aparece en el panel.
    from datetime import datetime, timezone

    from imop.core.models import DisplayMessage, MessageCategory

    window._on_message(
        DisplayMessage(
            text='sensor_temp | {"sensor_temp": 1}',
            category=MessageCategory.DATA,
            color="#1e88e5",
            timestamp=datetime.now(timezone.utc),
        )
    )
    assert window.message_panel.list_widget.count() == 1
    window.close()
