"""Tests de integración del servidor WebSocket (sin GUI)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import pytest
from websockets.asyncio.client import connect

from imop.network.server import WebSocketServer


@pytest.fixture
async def server_with_messages() -> AsyncIterator[tuple[WebSocketServer, list[str]]]:
    """Levanta un servidor efímero y expone los mensajes recibidos.

    Yields:
        Tupla (servidor, lista de frames recibidos).
    """
    received: list[str] = []
    server = WebSocketServer(host="127.0.0.1", port=0, on_message=received.append)
    await server.start()
    try:
        yield server, received
    finally:
        await server.stop()


async def received_wait(received: list[str]) -> None:
    """Espera (sondeando) hasta que llegue al menos un mensaje.

    Args:
        received: Lista compartida que llena el callback del servidor.
    """
    while not received:
        await asyncio.sleep(0.01)


async def test_recibe_json_de_cliente(
    server_with_messages: tuple[WebSocketServer, list[str]],
) -> None:
    server, received = server_with_messages
    uri = f"ws://127.0.0.1:{server.bound_port}"
    async with connect(uri) as client:
        await client.send(json.dumps({"sensor_temp": {"value": 23.4}}))
        await asyncio.wait_for(received_wait(received), timeout=2.0)
    assert received == [json.dumps({"sensor_temp": {"value": 23.4}})]


async def test_ack_confirma_seq_recibido(
    server_with_messages: tuple[WebSocketServer, list[str]],
) -> None:
    server, received = server_with_messages
    uri = f"ws://127.0.0.1:{server.bound_port}"
    async with connect(uri) as client:
        await client.send('{"seq": 7, "sensor_temp": {"value": 21.5}}')
        ack = await asyncio.wait_for(client.recv(), timeout=2.0)
    assert json.loads(ack) == {"ack_seq": 7, "status": "ok"}
    assert len(received) == 1


async def test_ack_error_cuando_callback_falla(
    server_with_messages: tuple[WebSocketServer, list[str]],
) -> None:
    """Si el callback lanza una excepción, el ACK informa status ``error``."""
    received: list[str] = []

    def callback_broken(raw: str) -> None:
        received.append(raw)
        msg = "fallo simulado"
        raise RuntimeError(msg)

    server = WebSocketServer(host="127.0.0.1", port=0, on_message=callback_broken)
    await server.start()
    try:
        uri = f"ws://127.0.0.1:{server.bound_port}"
        async with connect(uri) as client:
            await client.send('{"seq": 9, "x": 1}')
            ack = await asyncio.wait_for(client.recv(), timeout=2.0)
        assert json.loads(ack) == {"ack_seq": 9, "status": "error"}
    finally:
        await server.stop()


async def test_mensaje_sin_seq_no_genera_ack(
    server_with_messages: tuple[WebSocketServer, list[str]],
) -> None:
    server, received = server_with_messages
    uri = f"ws://127.0.0.1:{server.bound_port}"
    async with connect(uri) as client:
        await client.send(json.dumps({"sensor_temp": {"value": 21.5}}))
        await asyncio.wait_for(received_wait(received), timeout=2.0)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(client.recv(), timeout=0.5)


async def test_seq_no_entero_no_genera_ack(
    server_with_messages: tuple[WebSocketServer, list[str]],
) -> None:
    """``seq`` debe ser entero: strings o booleanos no generan ACK."""
    server, received = server_with_messages
    uri = f"ws://127.0.0.1:{server.bound_port}"
    async with connect(uri) as client:
        await client.send('{"seq": "abc", "sensor": 1}')
        await asyncio.wait_for(received_wait(received), timeout=2.0)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(client.recv(), timeout=0.5)


async def test_json_invalido_con_prefijo_de_seq_no_genera_ack(
    server_with_messages: tuple[WebSocketServer, list[str]],
) -> None:
    """Un frame que no parsea no puede extraer seq: no hay ACK."""
    server, received = server_with_messages
    uri = f"ws://127.0.0.1:{server.bound_port}"
    async with connect(uri) as client:
        await client.send("{esto no es json")
        await asyncio.wait_for(received_wait(received), timeout=2.0)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(client.recv(), timeout=0.5)


async def test_registro_de_clientes(
    server_with_messages: tuple[WebSocketServer, list[str]],
) -> None:
    server, _ = server_with_messages
    uri = f"ws://127.0.0.1:{server.bound_port}"
    async with connect(uri):
        for _ in range(100):
            if server.registry.count == 1:
                break
            await asyncio.sleep(0.01)
        assert server.registry.count == 1
    for _ in range(100):
        if server.registry.count == 0:
            break
        await asyncio.sleep(0.01)
    assert server.registry.count == 0


async def test_broadcast_a_clientes(
    server_with_messages: tuple[WebSocketServer, list[str]],
) -> None:
    server, _ = server_with_messages
    uri = f"ws://127.0.0.1:{server.bound_port}"
    async with connect(uri) as client:
        for _ in range(100):
            if server.registry.count == 1:
                break
            await asyncio.sleep(0.01)
        sent = await server.registry.broadcast('{"cmd": "ping"}')
        assert sent == 1
        reply = await asyncio.wait_for(client.recv(), timeout=2.0)
        assert reply == '{"cmd": "ping"}'
