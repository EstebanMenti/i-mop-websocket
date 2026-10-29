"""Configuración persistente de la aplicación.

Se guarda en ``~/.imop/config.json`` con escritura atómica. Tolerante a
archivos corruptos o incompletos: siempre devuelve una configuración válida.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from imop.constants import DEFAULT_LOG_DIR, DEFAULT_PORT, MAX_FILTERS
from imop.core.filters import FilterRule

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".imop"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class AppConfig:
    """Estado completo de configuración de la aplicación.

    Attributes:
        port: Puerto de escucha del servidor WebSocket.
        filters: Reglas de filtro por prefijo (máx. ``MAX_FILTERS``).
        log_enabled: Si ``True`` se guardan logs de los filtros coincidentes.
        log_dir: Carpeta destino de los archivos de log.
    """

    port: int = DEFAULT_PORT
    filters: list[FilterRule] = field(
        default_factory=lambda: [FilterRule(name="") for _ in range(MAX_FILTERS)]
    )
    log_enabled: bool = False
    log_dir: Path = DEFAULT_LOG_DIR
    announce_enabled: bool = True


def load_config(path: Path = CONFIG_FILE) -> AppConfig:
    """Carga la configuración desde disco.

    Args:
        path: Ruta del archivo de configuración.

    Returns:
        Configuración cargada; valores por defecto si el archivo no existe
        o es inválido (se registra la advertencia y se continúa).
    """
    config = AppConfig()
    if not path.exists():
        return config
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Configuración ilegible en %s; usando valores por defecto", path)
        return config

    config.port = int(data.get("port", config.port))
    config.log_enabled = bool(data.get("log_enabled", config.log_enabled))
    config.log_dir = Path(data.get("log_dir", str(config.log_dir)))
    config.announce_enabled = bool(data.get("announce_enabled", config.announce_enabled))

    raw_filters = data.get("filters", [])
    filters: list[FilterRule] = []
    for raw in raw_filters[:MAX_FILTERS]:
        if isinstance(raw, dict):
            filters.append(
                FilterRule(name=str(raw.get("name", "")), enabled=bool(raw.get("enabled", True)))
            )
    while len(filters) < MAX_FILTERS:
        filters.append(FilterRule(name=""))
    config.filters = filters
    return config


def save_config(config: AppConfig, path: Path = CONFIG_FILE) -> None:
    """Guarda la configuración con escritura atómica (temporal + rename).

    Args:
        config: Configuración a persistir.
        path: Ruta destino del archivo.
    """
    payload = {
        "port": config.port,
        "log_enabled": config.log_enabled,
        "log_dir": str(config.log_dir),
        "announce_enabled": config.announce_enabled,
        "filters": [{"name": rule.name, "enabled": rule.enabled} for rule in config.filters],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        Path(tmp_name).replace(path)
    except OSError:
        logger.exception("No se pudo guardar la configuración en %s", path)
        with_context = Path(tmp_name)
        if with_context.exists():
            with_context.unlink(missing_ok=True)
