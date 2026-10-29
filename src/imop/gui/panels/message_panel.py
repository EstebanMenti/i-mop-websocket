"""Panel inferior: visualizador de mensajes en tiempo real con colores.

Incluye el contador de paquetes recibidos; el botón "Limpiar" borra la
lista y restablece el contador a cero.
"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from imop.constants import COLOR_ERROR as ERROR_COLOR
from imop.constants import COLOR_SYSTEM as SYSTEM_COLOR
from imop.constants import MAX_DISPLAY_MESSAGES
from imop.core.models import DisplayMessage, MessageCategory

_CATEGORY_COLORS = {
    MessageCategory.ERROR: ERROR_COLOR,
    MessageCategory.SYSTEM: SYSTEM_COLOR,
}


class MessagePanel(QWidget):
    """Lista de mensajes recibidos, con color por origen y límite de filas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Construye el panel con la lista, el contador y el botón de limpieza."""
        super().__init__(parent)
        self._packet_count = 0

        layout = QVBoxLayout(self)
        group = QGroupBox("Mensajes en vivo")
        inner = QVBoxLayout()

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        inner.addWidget(self.list_widget)

        controls = QHBoxLayout()
        self.counter_label = QLabel(self._counter_text())
        self.clear_button = QPushButton("Limpiar")
        self.clear_button.clicked.connect(self.clear_all)
        controls.addWidget(self.counter_label)
        controls.addStretch(1)
        controls.addWidget(self.clear_button)
        inner.addLayout(controls)

        group.setLayout(inner)
        layout.addWidget(group)

    @property
    def packet_count(self) -> int:
        """Cantidad de paquetes recibidos desde el último "Limpiar"."""
        return self._packet_count

    def append_message(self, message: DisplayMessage) -> None:
        """Agrega un mensaje coloreado, incrementa el contador y recorta la lista.

        Args:
            message: Mensaje procesado por el pipeline.
        """
        stamp = message.timestamp.strftime("%H:%M:%S.%f")[:-3]
        color = _CATEGORY_COLORS.get(message.category, message.color)
        item = QListWidgetItem(f"[{stamp}]  {message.text}")
        item.setForeground(QColor(color))
        self.list_widget.addItem(item)
        self._packet_count += 1
        self.counter_label.setText(self._counter_text())
        while self.list_widget.count() > MAX_DISPLAY_MESSAGES:
            self.list_widget.takeItem(0)
        self.list_widget.scrollToBottom()

    def clear_all(self) -> None:
        """Borra la lista de mensajes y restablece el contador de paquetes."""
        self.list_widget.clear()
        self._packet_count = 0
        self.counter_label.setText(self._counter_text())

    def _counter_text(self) -> str:
        """Devuelve el texto del contador según el estado actual.

        Returns:
            Texto "Paquetes: N".
        """
        return f"Paquetes: {self._packet_count}"
