"""Modelos de dominio compartidos entre capas."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeAlias

JsonPayload: TypeAlias = dict[str, Any]


class MessageCategory(enum.Enum):
    """Categoría visual de un mensaje en el panel inferior."""

    DATA = "data"
    ERROR = "error"
    SYSTEM = "system"


class ServerStatus(enum.Enum):
    """Estado del servidor WebSocket para la GUI."""

    STOPPED = "Detenido"
    STARTING = "Iniciando…"
    RUNNING = "En ejecución"
    ERROR = "Error"


@dataclass(frozen=True)
class FilterRule:
    """Regla de filtro por prefijo sobre la clave raíz del JSON.

    Attributes:
        name: Prefijo a comparar (vacío = regla inactiva).
        enabled: Si ``False`` la regla no se evalúa.
    """

    name: str
    enabled: bool = True


@dataclass(frozen=True)
class DisplayMessage:
    """Mensaje listo para mostrar en la GUI o escribir en logs.

    Attributes:
        text: Texto legible de una línea para el panel inferior.
        category: Categoría visual (dato, error o sistema).
        color: Color hexadecimal para el renderizado.
        timestamp: Momento de recepción del mensaje.
        payload: JSON parseado (``None`` en errores/sistema).
        matched_filters: Nombres de filtros que coincidieron.
    """

    text: str
    category: MessageCategory
    color: str
    timestamp: datetime
    payload: JsonPayload | None = None
    matched_filters: tuple[str, ...] = field(default_factory=tuple)
