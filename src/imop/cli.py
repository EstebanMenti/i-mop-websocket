"""Argumentos de línea de comandos de la aplicación.

Uso::

    imop [--port 8765] [--version]
"""

from __future__ import annotations

import argparse

from imop import __version__
from imop.constants import DEFAULT_PORT


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos CLI.

    Returns:
        Parser configurado con las opciones soportadas.
    """
    parser = argparse.ArgumentParser(
        prog="imop",
        description="Monitor WebSocket con visualizador JSON para ESP32.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Puerto inicial del servidor WebSocket (por defecto: {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parsea los argumentos de línea de comandos.

    Args:
        argv: Lista de argumentos (None usa ``sys.argv``).

    Returns:
        Namespace con los valores parseados.
    """
    return build_parser().parse_args(argv)
