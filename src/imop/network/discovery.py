"""Publicación del servidor vía mDNS/Zeroconf (Bonjour).

Permite que clientes (ESP32, otros equipos) descubran automáticamente la
IP y el puerto del servidor WebSocket escaneando el servicio
``_imop._tcp.local.`` en la red local, sin configurar IPs a mano.

Nota: mDNS solo funciona dentro del mismo segmento de red (multicast);
no atraviesa routers ni VPN.
"""

from __future__ import annotations

import logging
import socket

from zeroconf import ServiceInfo, Zeroconf

logger = logging.getLogger(__name__)

SERVICE_TYPE = "_imop._tcp.local."


def default_instance_name() -> str:
    """Nombre de instancia por defecto basado en el hostname.

    Returns:
        Cadena ``i-mop-<HOSTNAME>``.
    """
    return f"i-mop-{socket.gethostname()}"


class ServiceAnnouncer:
    """Registra el servidor como servicio mDNS y lo da de baja al detenerse."""

    def __init__(self, instance_name: str, port: int) -> None:
        """Inicializa el anunciador (no publica hasta :meth:`start`).

        Args:
            instance_name: Nombre visible en la red (p. ej. ``i-mop-DESKTOP``).
            port: Puerto TCP del servidor WebSocket.
        """
        self._instance_name = instance_name
        self._port = port
        self._zc: Zeroconf | None = None
        self._info: ServiceInfo | None = None

    @property
    def instance_name(self) -> str:
        """Nombre de instancia publicado en la red."""
        return self._instance_name

    @property
    def service_name(self) -> str:
        """Nombre completo del servicio (instancia + tipo)."""
        return f"{self._instance_name}.{SERVICE_TYPE}"

    @property
    def running(self) -> bool:
        """Indica si el servicio está publicado actualmente."""
        return self._zc is not None and self._info is not None

    def start(self) -> None:
        """Publica el servicio en la red local.

        Los errores de red (firewall sobre UDP 5353, interfaces virtuales)
        se registran y no propagan: el servidor sigue funcionando sin
        descubrimiento automático.
        """
        if self.running:
            return
        try:
            zc = Zeroconf()
            info = ServiceInfo(
                SERVICE_TYPE,
                self.service_name,
                port=self._port,
                properties={"proto": "ws", "app": "imop"},
                server=f"{self._instance_name.lower()}.local.",
            )
            zc.register_service(info)
            self._zc = zc
            self._info = info
            logger.info("Servicio mDNS publicado: %s (puerto %d)", self.service_name, self._port)
        except OSError:
            logger.exception(
                "No se pudo publicar el servicio mDNS %s; el servidor seguirá "
                "funcionando sin descubrimiento automático",
                self.service_name,
            )
            self._cleanup()

    def stop(self) -> None:
        """Retira el servicio de la red y libera recursos."""
        if not self.running:
            return
        assert self._zc is not None and self._info is not None
        try:
            self._zc.unregister_service(self._info)
            logger.info("Servicio mDNS retirado: %s", self.service_name)
        except OSError:
            logger.warning("Fallo al retirar el servicio mDNS", exc_info=True)
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        """Cierra el stack Zeroconf y limpia el estado interno."""
        if self._zc is not None:
            try:
                self._zc.close()
            except OSError:
                logger.debug("Zeroconf ya cerrado", exc_info=True)
        self._zc = None
        self._info = None
