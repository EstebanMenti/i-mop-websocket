"""Tests del parser JSON."""

from __future__ import annotations

import pytest

from imop.core.parser import MessageParseError, parse_message, root_key


def test_parse_message_json_valido_devuelve_dict() -> None:
    payload = parse_message('{"sensor_temp": {"value": 23.4}}')
    assert payload == {"sensor_temp": {"value": 23.4}}


@pytest.mark.parametrize(
    ("raw", "motivo"),
    [
        ("no es json", "texto inválido"),
        ("[1, 2, 3]", "array no aceptado"),
        ('"hola"', "string no aceptado"),
        ("42", "número no aceptado"),
        ("", "vacío"),
    ],
)
def test_parse_message_invalido_lanza_error(raw: str, motivo: str) -> None:
    with pytest.raises(MessageParseError):
        parse_message(raw)


def test_root_key_devuelve_primera_clave() -> None:
    assert root_key({"sensor_temp": 1, "otra": 2}) == "sensor_temp"


def test_root_key_diccionario_vacio_devuelve_cadena_vacia() -> None:
    assert root_key({}) == ""
