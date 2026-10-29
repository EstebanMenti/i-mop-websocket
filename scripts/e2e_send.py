"""Verificación E2E manual: envía JSON de prueba al servidor WebSocket.

Uso (con la aplicación iniciada en el puerto elegido)::

    .venv\\Scripts\\python scripts\\e2e_send.py --port 8765

Envía una secuencia de mensajes de ejemplo (sensor_, motor_, gps_, JSON
inválido y un mensaje sin filtro) e imprime el ACK del servidor cuando el
mensaje incluye ``"seq"``. Verificar en la GUI los colores, el panel y los
archivos de log si están activos.
"""

from __future__ import annotations

import argparse
import asyncio
import json

SAMPLE_MESSAGES: list[tuple[int | None, str]] = [
    (1, json.dumps({"seq": 1, "sensor_temp": {"value": 23.4, "unit": "C"}})),
    (2, json.dumps({"seq": 2, "sensor_hum": {"value": 61.0, "unit": "%"}})),
    (3, json.dumps({"seq": 3, "motor_rpm": {"value": 1450}})),
    (4, json.dumps({"seq": 4, "gps_pos": {"lat": -34.6, "lon": -58.4}})),
    (5, json.dumps({"seq": 5, "heartbeat": {"uptime_s": 120}})),
    (None, json.dumps({"sin_seq": {"value": 1}})),  # sin seq → sin ACK
    (None, "{esto no es json válido"),  # inválido → sin ACK, ERROR en la GUI
]

ACK_TIMEOUT_S = 2.0


async def run(port: int, host: str) -> None:
    """Conecta y envía los mensajes de ejemplo, mostrando los ACK.

    Args:
        port: Puerto del servidor.
        host: Host del servidor.
    """
    from websockets.asyncio.client import connect

    uri = f"ws://{host}:{port}"
    async with connect(uri) as client:
        print(f"Conectado a {uri}")
        for seq, raw in SAMPLE_MESSAGES:
            await client.send(raw)
            print(f"-> enviado: {raw}")
            if seq is not None:
                try:
                    ack = await asyncio.wait_for(client.recv(), timeout=ACK_TIMEOUT_S)
                    print(f"<- ACK:     {ack}")
                except TimeoutError:
                    print(f"<- ACK:     ¡NO RECIBIDO! (timeout de {ACK_TIMEOUT_S}s)")
            await asyncio.sleep(0.3)
        print("Listo. Verificar el panel de la GUI y los archivos de log.")


def main() -> None:
    """Punto de entrada del script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    asyncio.run(run(args.port, args.host))


if __name__ == "__main__":
    main()
