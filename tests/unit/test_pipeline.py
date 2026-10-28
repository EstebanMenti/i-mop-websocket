"""Tests del pipeline de mensajes (parseo + filtros + logs)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from imop.core.models import FilterRule, MessageCategory
from imop.core.pipeline import MessagePipeline
from imop.logging_service.handlers import FilterLogManager

TS = datetime(2026, 10, 28, 12, 0, 0, tzinfo=timezone.utc)


def test_json_invalido_genera_mensaje_de_error() -> None:
    pipeline = MessagePipeline()
    message = pipeline.process("{invalido", TS)
    assert message is not None
    assert message.category is MessageCategory.ERROR
    assert message.payload is None


def test_sin_filtros_devuelve_todos_los_mensajes() -> None:
    pipeline = MessagePipeline()
    message = pipeline.process('{"gps_pos": {"lat": -34.6}}', TS)
    assert message is not None
    assert message.category is MessageCategory.DATA
    assert message.text.startswith("gps_pos |")


def test_filtro_activo_oculta_no_coincidentes() -> None:
    pipeline = MessagePipeline(rules=[FilterRule(name="sensor_", enabled=True)])
    assert pipeline.process('{"gps_pos": 1}', TS) is None
    message = pipeline.process('{"sensor_temp": 1}', TS)
    assert message is not None
    assert message.matched_filters == ("sensor_",)


def test_log_se_escribe_cuando_habilitado(tmp_path: Path) -> None:
    log_manager = FilterLogManager(log_dir=tmp_path)
    log_manager.enabled = True
    pipeline = MessagePipeline(
        rules=[FilterRule(name="sensor_", enabled=True)], log_manager=log_manager
    )
    pipeline.process('{"sensor_temp": 21.5}', TS)
    log_file = tmp_path / "sensor_.log"
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert '"filter": "sensor_"' in content
    assert '"sensor_temp"' in content


def test_log_no_coincidente_no_se_escribe(tmp_path: Path) -> None:
    log_manager = FilterLogManager(log_dir=tmp_path)
    log_manager.enabled = True
    pipeline = MessagePipeline(
        rules=[FilterRule(name="motor_", enabled=True)], log_manager=log_manager
    )
    pipeline.process('{"sensor_temp": 21.5}', TS)
    assert not (tmp_path / "motor_.log").exists()


def test_log_deshabilitado_no_escribe(tmp_path: Path) -> None:
    log_manager = FilterLogManager(log_dir=tmp_path)
    pipeline = MessagePipeline(
        rules=[FilterRule(name="sensor_", enabled=True)], log_manager=log_manager
    )
    pipeline.process('{"sensor_temp": 21.5}', TS)
    assert not (tmp_path / "sensor_.log").exists()


def test_color_estable_por_clave_raiz() -> None:
    pipeline = MessagePipeline()
    first = pipeline.process('{"sensor_temp": 1}', TS)
    second = pipeline.process('{"sensor_temp": 2}', TS)
    assert first is not None and second is not None
    assert first.color == second.color
    assert first.color.startswith("#")
