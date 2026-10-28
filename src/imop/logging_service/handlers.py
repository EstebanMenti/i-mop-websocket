"""Escritura de logs en archivos rotativos, uno por filtro habilitado.

Formato: una línea JSON por mensaje::

    {"timestamp": "...", "filter": "sensor_", "message": {...}}
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from imop.constants import LOG_BACKUP_COUNT, LOG_MAX_BYTES
from imop.core.models import JsonPayload

logger = logging.getLogger(__name__)


class FilterLogManager:
    """Administra un ``RotatingFileHandler`` por nombre de filtro.

    Los handlers se crean de forma perezosa (al primer mensaje coincidente)
    y se reinician si cambia la carpeta destino.
    """

    def __init__(self, log_dir: Path, max_bytes: int = LOG_MAX_BYTES) -> None:
        """Inicializa el gestor.

        Args:
            log_dir: Carpeta donde se crean los archivos ``<filtro>.log``.
            max_bytes: Tamaño máximo por archivo antes de rotar.
        """
        self._log_dir = log_dir
        self._max_bytes = max_bytes
        self._backup_count = LOG_BACKUP_COUNT
        self._handlers: dict[str, RotatingFileHandler] = {}
        self.enabled: bool = False

    @property
    def log_dir(self) -> Path:
        """Carpeta destino actual de los logs."""
        return self._log_dir

    def set_log_dir(self, log_dir: Path) -> None:
        """Cambia la carpeta destino y cierra los handlers abiertos.

        Args:
            log_dir: Nueva carpeta destino.
        """
        if log_dir == self._log_dir:
            return
        self.close_all()
        self._log_dir = log_dir
        logger.info("Carpeta de logs cambiada a %s", log_dir)

    def write(
        self,
        filter_name: str,
        payload: JsonPayload,
        timestamp: datetime,
    ) -> None:
        """Escribe un mensaje en el log del filtro indicado.

        No hace nada si el guardado está deshabilitado. Los errores de
        escritura se loguean sin propagarse (el servicio de logs no debe
        tumbar la recepción de mensajes).

        Args:
            filter_name: Nombre del filtro (prefijo) coincidente.
            payload: JSON parseado del mensaje.
            timestamp: Momento de recepción.
        """
        if not self.enabled:
            return
        handler = self._get_handler(filter_name)
        record = {
            "timestamp": timestamp.isoformat(),
            "filter": filter_name,
            "message": payload,
        }
        try:
            handler.handle(
                logging.LogRecord(
                    name=f"imop.filter.{filter_name}",
                    level=logging.INFO,
                    pathname=__file__,
                    lineno=0,
                    msg=json.dumps(record, ensure_ascii=False),
                    args=(),
                    exc_info=None,
                )
            )
        except OSError:
            logger.exception("No se pudo escribir el log del filtro %r", filter_name)

    def close_all(self) -> None:
        """Cierra y libera todos los handlers abiertos (llamar al salir)."""
        for handler in self._handlers.values():
            try:
                handler.close()
            except OSError:
                logger.warning("Fallo al cerrar un handler de log", exc_info=True)
        self._handlers.clear()

    def _get_handler(self, filter_name: str) -> RotatingFileHandler:
        """Devuelve el handler del filtro, creándolo si es necesario."""
        handler = self._handlers.get(filter_name)
        if handler is None:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            safe_name = filter_name.strip("/\\") or "filtro"
            handler = RotatingFileHandler(
                self._log_dir / f"{safe_name}.log",
                maxBytes=self._max_bytes,
                backupCount=self._backup_count,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._handlers[filter_name] = handler
        return handler
