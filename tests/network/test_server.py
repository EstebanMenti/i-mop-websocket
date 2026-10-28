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


async def test_recibe_json_de_cliente(
    server_with_messages: tuple[WebSocketServer, list[str]],
) -> None:
    server, received = server_with_messages
    uri = f"ws://127.0.0.1:{server.bound_port}"
    async with connect(uri) as client:
        await client.send(json.dumps({"sensor_temp": {"value": 23.4}}))
        await asyncio.wait_for(received_wait(received), timeout=2.0)
    assert received == [json.dumps({"sensor_temp": {"value": 23.4}})]


async def received_wait(received: list[str]) -> None:
    """Espera (sondeando) hasta que llegue al menos un mensaje.

    Args:
        received: Lista compartida que llena el callback del servidor.
    """
    while not received:
        await asyncio.sleep(0.01)


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
