"""Arranque de la aplicación: QApplication + ventana principal."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from imop import __version__
from imop.cli import parse_args
from imop.config import load_config
from imop.constants import APP_NAME, ORG_NAME
from imop.gui.main_window import MainWindow

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Configura el logging raíz de la aplicación."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada de la aplicación.

    Args:
        argv: Argumentos de línea de comandos (None usa ``sys.argv``).

    Returns:
        Código de salida del proceso.
    """
    _configure_logging()
    args = parse_args(argv if argv is not None else sys.argv[1:])
    logger.info("i-mop-websocket %s", __version__)

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)

    config = load_config()
    if args.port != config.port:
        config.port = args.port  # el CLI tiene prioridad sobre la config guardada

    window = MainWindow(config)
    window.show()
    return app.exec()
