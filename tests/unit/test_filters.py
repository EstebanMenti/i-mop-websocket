"""Tests del FilterManager."""

from __future__ import annotations

from imop.core.filters import FilterManager
from imop.core.models import FilterRule


def _payload(key: str) -> dict[str, object]:
    return {key: {"value": 1}}


def test_sin_filtros_activos_muestra_todo() -> None:
    manager = FilterManager([])
    assert manager.passes_display(_payload("cualquiera")) is True


def test_filtros_vacios_o_deshabilitados_se_ignoran() -> None:
    manager = FilterManager(
        [FilterRule(name="", enabled=True), FilterRule(name="sensor_", enabled=False)]
    )
    assert manager.active_rules == ()
    assert manager.passes_display(_payload("cualquiera")) is True


def test_coincidencia_por_prefijo() -> None:
    manager = FilterManager(
        [FilterRule(name="sensor_", enabled=True), FilterRule(name="motor_", enabled=True)]
    )
    matched = manager.match(_payload("sensor_temp"))
    assert [rule.name for rule in matched] == ["sensor_"]
    assert manager.passes_display(_payload("sensor_temp")) is True


def test_sin_coincidencia_oculta_el_mensaje() -> None:
    manager = FilterManager([FilterRule(name="sensor_", enabled=True)])
    assert manager.passes_display(_payload("gps_pos")) is False
    assert manager.match(_payload("gps_pos")) == ()


def test_matching_insensible_a_mayusculas() -> None:
    manager = FilterManager([FilterRule(name="Sensor_", enabled=True)])
    matched = manager.match(_payload("SENSOR_TEMP"))
    assert [rule.name for rule in matched] == ["Sensor_"]


def test_clave_raiz_vacia_no_coincide() -> None:
    manager = FilterManager([FilterRule(name="s", enabled=True)])
    assert manager.match({}) == ()


def test_set_rules_reemplaza_reglas() -> None:
    manager = FilterManager([FilterRule(name="viejo")])
    manager.set_rules([FilterRule(name="nuevo", enabled=True)])
    assert [rule.name for rule in manager.rules] == ["nuevo"]
