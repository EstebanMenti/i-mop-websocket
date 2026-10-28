"""Pipeline de procesamiento de mensajes entrantes.

Conecta: parseo JSON → filtros → logs por filtro → mensaje de visualización.
Es código de dominio puro (sin Qt ni red) y corre en el hilo del servidor.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from imop.core.filters import FilterManager
from imop.core.models import DisplayMessage, FilterRule, JsonPayload, MessageCategory
from imop.core.parser import MessageParseError, parse_message, root_key
from imop.logging_service.handlers import FilterLogManager
from imop.theme import color_for_root_key

logger = logging.getLogger(__name__)

_RAW_PREVIEW_LIMIT = 200


class MessagePipeline:
    """Procesa cada frame de texto recibido y produce un mensaje visualizable."""

    def __init__(
        self,
        rules: list[FilterRule] | None = None,
        log_manager: FilterLogManager | None = None,
    ) -> None:
        """Inicializa el pipeline.

        Args:
            rules: Reglas de filtro iniciales (vacías = mostrar todo).
            log_manager: Gestor de logs por filtro; si es ``None`` no se
                escribe ningún archivo.
        """
        self.filters = FilterManager(rules or [])
        self.log_manager = log_manager

    def set_log_enabled(self, enabled: bool) -> None:
        """Activa/desactiva el guardado de logs en caliente.

        Args:
            enabled: Nuevo estado del flag "guardar logs".
        """
        if self.log_manager is not None:
            self.log_manager.enabled = enabled

    def set_log_dir(self, log_dir: str) -> None:
        """Cambia la carpeta de logs en caliente.

        Args:
            log_dir: Nueva carpeta destino.
        """
        if self.log_manager is not None:
            self.log_manager.set_log_dir(Path(log_dir))

    def process(self, raw: str, received_at: datetime | None = None) -> DisplayMessage | None:
        """Procesa un frame crudo y devuelve el mensaje a mostrar.

        Escribe en los logs de los filtros coincidentes (si están activos).
        Los mensajes que no pasan los filtros visuales devuelven ``None``
        (ya fueron logueados si correspondía).

        Args:
            raw: Frame WebSocket de texto recibido.
            received_at: Timestamp de recepción (por defecto, ahora UTC).

        Returns:
            Mensaje para el panel inferior, o ``None`` si fue filtrado.
        """
        timestamp = received_at or datetime.now(timezone.utc)
        try:
            payload = parse_message(raw)
        except MessageParseError as exc:
            return self._error_message(str(exc), raw, timestamp)

        matched = self.filters.match(payload)
        if self.log_manager is not None:
            for rule in matched:
                self.log_manager.write(rule.name, payload, timestamp)

        if not self.filters.passes_display(payload):
            return None
        return self._data_message(payload, raw, timestamp, matched)

    def _error_message(self, reason: str, raw: str, timestamp: datetime) -> DisplayMessage:
        """Construye el mensaje de error para JSON inválido."""
        preview = raw if len(raw) <= _RAW_PREVIEW_LIMIT else raw[:_RAW_PREVIEW_LIMIT] + "…"
        return DisplayMessage(
            text=f"{reason} | crudo: {preview!r}",
            category=MessageCategory.ERROR,
            color="",  # el panel usa el color de ERROR
            timestamp=timestamp,
        )

    def _data_message(
        self,
        payload: JsonPayload,
        raw: str,
        timestamp: datetime,
        matched: tuple[FilterRule, ...],
    ) -> DisplayMessage:
        """Construye el mensaje de datos para el panel inferior."""
        key = root_key(payload)
        suffix = f"  [{', '.join(rule.name for rule in matched)}]" if matched else ""
        return DisplayMessage(
            text=f"{key} | {raw}{suffix}",
            category=MessageCategory.DATA,
            color=color_for_root_key(key),
            timestamp=timestamp,
            payload=payload,
            matched_filters=tuple(rule.name for rule in matched),
        )
