"""Tests del anunciador de servicio mDNS/Zeroconf."""

from __future__ import annotations

import socket
import threading

from zeroconf import ServiceBrowser, Zeroconf

from imop.network.discovery import SERVICE_TYPE, ServiceAnnouncer


def _free_port() -> int:
    """Reserva un puerto efímero y lo libera.

    Returns:
        Número de puerto disponible.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_start_y_stop_del_announcer() -> None:
    announcer = ServiceAnnouncer("i-mop-test", _free_port())
    assert announcer.running is False
    announcer.start()
    assert announcer.running is True
    assert announcer.service_name == f"i-mop-test.{SERVICE_TYPE}"
    announcer.stop()
    assert announcer.running is False


def test_stop_sin_start_no_falla() -> None:
    announcer = ServiceAnnouncer("i-mop-test", _free_port())
    announcer.stop()  # no debe lanzar excepciones
    assert announcer.running is False


def test_start_doble_es_inofensivo() -> None:
    announcer = ServiceAnnouncer("i-mop-test", _free_port())
    announcer.start()
    announcer.start()  # segunda llamada ignorada
    assert announcer.running is True
    announcer.stop()


def test_servicio_descubierto_por_browser() -> None:
    """Un ServiceBrowser debe encontrar el servicio anunciado (multicast real)."""
    port = _free_port()
    announcer = ServiceAnnouncer("i-mop-discovery-test", port)
    announcer.start()
    try:
        found = threading.Event()
        zeroconf = Zeroconf()

        class _Listener:
            """Listener mínimo que marca el evento al descubrir el servicio."""

            def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                if name.startswith("i-mop-discovery-test"):
                    found.set()

            def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                pass

            def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                pass

        browser = ServiceBrowser(zeroconf, SERVICE_TYPE, _Listener())
        try:
            assert found.wait(timeout=8.0), "El servicio no fue descubierto en 8 s"
        finally:
            browser.cancel()
            zeroconf.close()
    finally:
        announcer.stop()
