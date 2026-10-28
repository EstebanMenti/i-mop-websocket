"""Constantes globales de la aplicación.

Valores por defecto del servidor, límites de filtros/logs y paleta de colores.
Toda configuración modificable por el usuario vive en :mod:`imop.config`;
estos valores son solo puntos de partida.
"""

from __future__ import annotations

from pathlib import Path

APP_NAME = "i-mop-websocket"
ORG_NAME = "imop"

# Servidor WebSocket
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8765

# Filtros
MAX_FILTERS = 5

# Visualizador
MAX_DISPLAY_MESSAGES = 1000

# Logs por filtro
DEFAULT_LOG_DIR = Path.home() / ".imop" / "logs"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MiB por archivo
LOG_BACKUP_COUNT = 3

# Paleta de colores (hex RGB) asignada de forma estable por clave raíz del JSON.
MESSAGE_PALETTE: tuple[str, ...] = (
    "#1e88e5",  # azul
    "#8e24aa",  # violeta
    "#f4511e",  # naranja
    "#00897b",  # verde azulado
    "#c0ca33",  # lima
    "#5e35b1",  # índigo
    "#d81b60",  # rosa
    "#43a047",  # verde
    "#fb8c00",  # ámbar
    "#3949ab",  # azul índigo
)

COLOR_ERROR = "#e53935"  # rojo: JSON inválido o error operativo
COLOR_SYSTEM = "#2e7d32"  # verde: eventos del sistema (conexión, arranque)
