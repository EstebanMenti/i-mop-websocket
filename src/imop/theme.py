"""Asignación estable de colores por clave raíz del mensaje.

Módulo puro (sin Qt): puede usarse desde dominio y tests.
"""

from __future__ import annotations

import zlib

from imop.constants import COLOR_ERROR, COLOR_SYSTEM, MESSAGE_PALETTE


def color_for_root_key(key: str) -> str:
    """Devuelve un color estable para una clave raíz dada.

    Usa CRC32 (no ``hash()``, que es salado por ejecución) para que el
    mismo identificador tenga siempre el mismo color entre sesiones.

    Args:
        key: Clave raíz del JSON (p. ej. ``"sensor_temp"``).

    Returns:
        Color hexadecimal; color de sistema si la clave está vacía.
    """
    if not key:
        return COLOR_SYSTEM
    index = zlib.crc32(key.encode("utf-8")) % len(MESSAGE_PALETTE)
    return MESSAGE_PALETTE[index]


def error_color() -> str:
    """Color reservado para mensajes con error de parseo/operación."""
    return COLOR_ERROR
