"""Tests de configuración persistente."""

from __future__ import annotations

from pathlib import Path

from imop.config import AppConfig, load_config, save_config
from imop.core.models import FilterRule


def test_roundtrip_config(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    config = AppConfig(
        port=9000,
        filters=[FilterRule(name=f"f{i}_", enabled=i % 2 == 0) for i in range(5)],
        log_enabled=True,
        log_dir=tmp_path / "mislogs",
        console_echo=False,
        last_tab=1,
    )
    save_config(config, path)
    loaded = load_config(path)
    assert loaded.port == 9000
    assert loaded.log_enabled is True
    assert loaded.log_dir == tmp_path / "mislogs"
    assert loaded.console_echo is False
    assert loaded.last_tab == 1
    assert [rule.name for rule in loaded.filters] == [f"f{i}_" for i in range(5)]
    assert [rule.enabled for rule in loaded.filters] == [i % 2 == 0 for i in range(5)]


def test_archivo_inexistente_devuelve_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path / "no_existe.json")
    assert config.log_enabled is False
    assert len(config.filters) == 5


def test_archivo_corrupto_devuelve_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{esto no es json", encoding="utf-8")
    config = load_config(path)
    assert config.log_enabled is False
    assert len(config.filters) == 5


def test_config_parcial_se_completa(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"port": 1234}', encoding="utf-8")
    config = load_config(path)
    assert config.port == 1234
    assert len(config.filters) == 5


def test_defaults_de_consola(tmp_path: Path) -> None:
    """Sin configuración previa: eco local activo y pestaña Telemetría."""
    config = load_config(tmp_path / "no_existe.json")
    assert config.console_echo is True
    assert config.last_tab == 0
