"""Parseo y validación de mensajes JSON entrantes."""

from __future__ import annotations

import json
import logging
from typing import Any

from imop.core.models import JsonPayload

logger = logging.getLogger(__name__)


class MessageParseError(ValueError):
    """Se lanza cuando un mensaje entrante no es un objeto JSON válido."""


def parse_message(raw: str) -> JsonPayload:
    """Parsea un texto crudo a un objeto JSON (diccionario).

    Args:
        raw: Contenido del frame WebSocket de texto.

    Returns:
        Diccionario JSON ya validado.

    Raises:
        MessageParseError: Si el texto no es JSON válido o no es un objeto
            (array, string, número, etc.).
    """
    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MessageParseError(f"JSON inválido: {exc.msg} (línea {exc.lineno})") from exc
    if not isinstance(data, dict):
        raise MessageParseError(
            f"Se esperaba un objeto JSON ({{...}}), recibido: {type(data).__name__}"
        )
    return data


def root_key(payload: JsonPayload) -> str:
    """Devuelve la primera clave raíz del payload (identificador del mensaje).

    Args:
        payload: JSON parseado.

    Returns:
        Primera clave del diccionario; cadena vacía si no tiene claves.
    """
    return next(iter(payload), "")
