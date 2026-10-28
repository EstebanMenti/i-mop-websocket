"""Panel de control del servidor: puerto, iniciar/detener y estado."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from imop.constants import DEFAULT_PORT
from imop.core.models import ServerStatus

_STATUS_COLORS = {
    ServerStatus.STOPPED: "#757575",
    ServerStatus.STARTING: "#f9a825",
    ServerStatus.RUNNING: "#2e7d32",
    ServerStatus.ERROR: "#e53935",
}


class ServerPanel(QWidget):
    """Control del ciclo de vida del servidor WebSocket."""

    start_requested = Signal(int)
    stop_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Construye el panel con puerto, botones y estado inicial."""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QGroupBox("Servidor WebSocket"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Puerto:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(DEFAULT_PORT)
        row.addWidget(self.port_spin)
        row.addStretch(1)

        self.start_button = QPushButton("Iniciar servidor")
        self.stop_button = QPushButton("Detener")
        self.stop_button.setEnabled(False)
        row.addWidget(self.start_button)
        row.addWidget(self.stop_button)

        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Estado:"))
        self.status_label = QLabel(ServerStatus.STOPPED.value)
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        status_row.addWidget(QLabel("Clientes:"))
        self.clients_label = QLabel("0")
        status_row.addWidget(self.clients_label)

        outer = self.findChild(QGroupBox)
        assert outer is not None
        outer_layout = QVBoxLayout()
        outer_layout.addLayout(row)
        outer_layout.addLayout(status_row)
        outer.setLayout(outer_layout)
        layout.addWidget(outer)

        self.start_button.clicked.connect(self._emit_start)
        self.stop_button.clicked.connect(self.stop_requested.emit)

    def _emit_start(self) -> None:
        """Emite la solicitud de arranque con el puerto configurado."""
        self.start_requested.emit(self.port_spin.value())

    def set_status(self, status: ServerStatus) -> None:
        """Actualiza el estado mostrado y habilita/deshabilita controles.

        Args:
            status: Nuevo estado del servidor.
        """
        self.status_label.setText(status.value)
        color = _STATUS_COLORS[status]
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        running = status is ServerStatus.RUNNING
        self.start_button.setEnabled(status in (ServerStatus.STOPPED, ServerStatus.ERROR))
        self.stop_button.setEnabled(running)
        self.port_spin.setEnabled(not running)

    def set_clients(self, count: int) -> None:
        """Actualiza el contador de clientes conectados.

        Args:
            count: Cantidad actual de clientes.
        """
        self.clients_label.setText(str(count))
