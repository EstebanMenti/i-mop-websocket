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


async def test_texto_plano_no_genera_ack(
    server_with_messages: tuple[WebSocketServer, list[str]],
) -> None:
    """Un comando de consola (texto sin ``seq``) no dispara ACK."""
    server, received = server_with_messages
    uri = f"ws://127.0.0.1:{server.bound_port}"
    async with connect(uri) as client:
        await client.send("pass get")
        await asyncio.wait_for(received_wait(received), timeout=2.0)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(client.recv(), timeout=0.5)


async def test_peers_y_resolve(
    server_with_messages: tuple[WebSocketServer, list[str]],
) -> None:
    """``peers()`` lista los clientes y ``resolve()`` recupera la conexión."""
    from imop.network.client_registry import BROADCAST_TARGET

    server, _ = server_with_messages
    uri = f"ws://127.0.0.1:{server.bound_port}"
    async with connect(uri) as client:
        for _ in range(100):
            if server.registry.count == 1:
                break
            await asyncio.sleep(0.01)
        peers = server.registry.peers()
        assert len(peers) == 1
        assert peers[0].startswith("127.0.0.1:")
        assert server.registry.resolve(peers[0]) is not None
        assert server.registry.resolve(BROADCAST_TARGET) is None
        assert server.registry.resolve("1.2.3.4:9999") is None
        assert client.remote_address is not None


async def test_send_console_line_broadcast_agrega_salto(
    server_with_messages: tuple[WebSocketServer, list[str]],
) -> None:
    """``send_console_line`` envía el comando con un único ``\\n`` final."""
    server, _ = server_with_messages
    uri = f"ws://127.0.0.1:{server.bound_port}"
    async with connect(uri) as client:
        for _ in range(100):
            if server.registry.count == 1:
                break
            await asyncio.sleep(0.01)
        sent = await server.send_console_line("pass set abc123  ", peer=None)
        assert sent == 1
        reply = await asyncio.wait_for(client.recv(), timeout=2.0)
        assert reply == "pass set abc123\n"


async def test_send_console_line_dirigido_a_un_peer(
    server_with_messages: tuple[WebSocketServer, list[str]],
) -> None:
    """Con destino puntual, solo el cliente elegido recibe el comando."""
    server, _ = server_with_messages
    uri = f"ws://127.0.0.1:{server.bound_port}"
    async with connect(uri) as client:
        for _ in range(100):
            if server.registry.count == 1:
                break
            await asyncio.sleep(0.01)
        peer = server.registry.peers()[0]
        sent = await server.send_console_line("server", peer=peer)
        assert sent == 1
        assert await asyncio.wait_for(client.recv(), timeout=2.0) == "server\n"


async def test_send_console_line_peer_desconocido_no_envia(
    server_with_messages: tuple[WebSocketServer, list[str]],
) -> None:
    """Un peer inexistente no envía nada ni lanza errores."""
    server, _ = server_with_messages
    uri = f"ws://127.0.0.1:{server.bound_port}"
    async with connect(uri) as client:
        for _ in range(100):
            if server.registry.count == 1:
                break
            await asyncio.sleep(0.01)
        sent = await server.send_console_line("server", peer="1.2.3.4:9999")
        assert sent == 0
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(client.recv(), timeout=0.5)


async def test_on_clients_changed_reporta_lista_de_peers() -> None:
    """El callback de cambios recibe la lista de peers, no un conteo."""
    snapshots: list[list[str]] = []
    server = WebSocketServer(
        host="127.0.0.1", port=0, on_message=lambda raw: None, on_clients_changed=snapshots.append
    )
    await server.start()
    try:
        uri = f"ws://127.0.0.1:{server.bound_port}"
        async with connect(uri):
            for _ in range(100):
                if server.registry.count == 1:
                    break
                await asyncio.sleep(0.01)
        assert snapshots and snapshots[-1] == server.registry.peers()
    finally:
        await server.stop()
    assert snapshots[-1] == []
