"""Verificación E2E manual: envía JSON de prueba al servidor WebSocket.

Uso (con la aplicación iniciada en el puerto elegido)::

    .venv\\Scripts\\python scripts\\e2e_send.py --port 8765

Envía una secuencia de mensajes de ejemplo (sensor_, motor_, gps_, JSON
inválido y un mensaje sin filtro) e imprime el resultado de cada envío.
Verificar en la GUI que aparecen con colores y en los logs si están activos.
"""

from __future__ import annotations

import argparse
import asyncio
import json

SAMPLE_MESSAGES: list[str] = [
    json.dumps({"sensor_temp": {"value": 23.4, "unit": "C"}}),
    json.dumps({"sensor_hum": {"value": 61.0, "unit": "%"}}),
    json.dumps({"motor_rpm": {"value": 1450}}),
    json.dumps({"gps_pos": {"lat": -34.6, "lon": -58.4}}),
    json.dumps({"heartbeat": {"uptime_s": 120}}),
    "{esto no es json válido",  # debe verse como ERROR en la GUI, sin caer
]


async def run(port: int, host: str) -> None:
    """Conecta y envía los mensajes de ejemplo.

    Args:
        port: Puerto del servidor.
        host: Host del servidor.
    """
    from websockets.asyncio.client import connect

    uri = f"ws://{host}:{port}"
    async with connect(uri) as client:
        print(f"Conectado a {uri}")
        for raw in SAMPLE_MESSAGES:
            await client.send(raw)
            print(f"-> enviado: {raw}")
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
