"""Panel inferior: visualizador de mensajes en tiempo real con colores.

Incluye el contador de paquetes recibidos; el botón "Limpiar" borra la
lista y restablece el contador a cero.

Rendimiento: los mensajes entrantes se **acumulan en un buffer** y se
pintan en lote (~10 Hz). A tasas altas (cientos de msg/s) pintar de a uno
satura el event loop de Qt y congela la GUI; el batching limita los
repaints y los recortes de lista a un flush periódico.
"""

from __future__ import annotations

from collections import deque

from PySide6.QtCore import QTimer
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

# Frecuencia de volcado del buffer de render y tope de ítems por volcado.
FLUSH_INTERVAL_MS = 100
MAX_ITEMS_PER_FLUSH = 500

# Cota de memoria del buffer pendiente (no afecta al contador de paquetes).
_MAX_PENDING = MAX_DISPLAY_MESSAGES * 2


class MessagePanel(QWidget):
    """Lista de mensajes recibidos, con color por origen y límite de filas.

    Los mensajes se acumulan en un buffer y se renderizan en lote mediante
    un :class:`QTimer`; usar :meth:`flush_now` para volcarlos de inmediato
    (útil en tests o antes de consultar la lista).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Construye el panel con la lista, el contador y el botón de limpieza."""
        super().__init__(parent)
        self._packet_count = 0
        self._pending: deque[DisplayMessage] = deque(maxlen=_MAX_PENDING)

        layout = QVBoxLayout(self)
        group = QGroupBox("Mensajes en vivo")
        inner = QVBoxLayout()

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setUniformItemSizes(True)
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

        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(FLUSH_INTERVAL_MS)
        self._flush_timer.timeout.connect(self._flush_pending)

    @property
    def packet_count(self) -> int:
        """Cantidad de paquetes recibidos desde el último "Limpiar"."""
        return self._packet_count

    @property
    def pending_count(self) -> int:
        """Mensajes en el buffer aún no pintados en la lista."""
        return len(self._pending)

    def append_message(self, message: DisplayMessage) -> None:
        """Encola un mensaje para el próximo volcado e incrementa el contador.

        Args:
            message: Mensaje procesado por el pipeline.
        """
        self._pending.append(message)
        self._packet_count += 1
        self.counter_label.setText(self._counter_text())
        if not self._flush_timer.isActive():
            self._flush_timer.start()

    def flush_now(self) -> None:
        """Pinta de inmediato todos los mensajes pendientes en el buffer."""
        self._flush_timer.stop()
        while self._pending:
            self._flush_pending()
        self._flush_timer.stop()

    def clear_all(self) -> None:
        """Borra la lista, el buffer pendiente y restablece el contador."""
        self._flush_timer.stop()
        self._pending.clear()
        self.list_widget.clear()
        self._packet_count = 0
        self.counter_label.setText(self._counter_text())

    def _flush_pending(self) -> None:
        """Pinta en un solo pase los mensajes acumulados (máx. por lote)."""
        if not self._pending:
            self._flush_timer.stop()
            return

        batch: list[DisplayMessage] = []
        while self._pending and len(batch) < MAX_ITEMS_PER_FLUSH:
            batch.append(self._pending.popleft())

        self.list_widget.setUpdatesEnabled(False)
        try:
            for message in batch:
                stamp = message.timestamp.strftime("%H:%M:%S.%f")[:-3]
                color = _CATEGORY_COLORS.get(message.category, message.color)
                item = QListWidgetItem(f"[{stamp}]  {message.text}")
                item.setForeground(QColor(color))
                self.list_widget.addItem(item)
            while self.list_widget.count() > MAX_DISPLAY_MESSAGES:
                self.list_widget.takeItem(0)
            self.list_widget.scrollToBottom()
        finally:
            self.list_widget.setUpdatesEnabled(True)
            self.counter_label.setText(self._counter_text())

        if self._pending:
            # Quedaron mensajes: reprogramar el próximo volcado.
            self._flush_timer.start()

    def _counter_text(self) -> str:
        """Devuelve el texto del contador según el estado actual.

        Returns:
            Texto "Paquetes: N".
        """
        return f"Paquetes: {self._packet_count}"
