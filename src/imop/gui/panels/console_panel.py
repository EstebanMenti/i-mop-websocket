"""Panel de consola remota: envío de comandos de texto al ESP32.

Consola estilo terminal dentro de una pestaña de la ventana principal:
la salida del ESP se imprime verbatim (texto plano), los comandos se
envían como frames de texto con ``\\n`` final (lo agrega la capa de red)
y el historial se navega con las flechas ↑/↓.

La respuesta del ESP llega por la señal ``console_output`` del worker y
este panel no espera nada: enviar nunca bloquea la GUI.
"""

from __future__ import annotations

import html
from datetime import datetime

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from imop.constants import COLOR_SYSTEM as SENT_COLOR
from imop.network.client_registry import BROADCAST_TARGET

#: Tope de bloques que retiene la salida (la propia QPlainTextEdit recorta).
MAX_CONSOLE_LINES = 5000

#: Colores de la salida.
STAMP_COLOR = "#9e9e9e"  # gris: timestamps tenues
TEXT_COLOR = "#212121"  # negro: respuestas del ESP

#: Prompt mostrado antes de cada comando enviado.
PROMPT = "esp32>"


class ConsolePanel(QWidget):
    """Consola de comandos: salida coloreada, historial y destino."""

    #: Comando aceptado para envío: (texto del comando, peer destino).
    send_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Construye la consola con su salida, prompt y controles."""
        super().__init__(parent)
        self._history: list[str] = []
        self._history_index = 0

        layout = QVBoxLayout(self)
        group = QGroupBox("Consola remota (texto plano)")
        inner = QVBoxLayout()

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(MAX_CONSOLE_LINES)
        self.output.setFont(QFont("Consolas", 10))
        self.output.setPlaceholderText(
            "Aquí aparece la respuesta del ESP32. Escribí un comando abajo y Enter para enviarlo."
        )
        inner.addWidget(self.output)

        # Fila de destino y controles.
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Destino:"))
        self.target_combo = QComboBox()
        self.target_combo.addItem(BROADCAST_TARGET)
        controls.addWidget(self.target_combo, stretch=1)
        self.echo_check = QCheckBox("Eco local")
        self.echo_check.setChecked(True)
        self.echo_check.setToolTip("Mostrar en la salida el comando enviado desde esta PC.")
        controls.addWidget(self.echo_check)
        self.clear_button = QPushButton("Limpiar")
        self.clear_button.clicked.connect(self.clear_output)
        controls.addWidget(self.clear_button)
        inner.addLayout(controls)

        # Fila de prompt + entrada + botón enviar.
        input_row = QHBoxLayout()
        self.prompt_label = QLabel(PROMPT)
        self.prompt_label.setStyleSheet(f"color: {SENT_COLOR}; font-weight: bold;")
        input_row.addWidget(self.prompt_label)
        self.input_edit = QLineEdit()
        self.input_edit.setFont(QFont("Consolas", 10))
        self.input_edit.setPlaceholderText("comando (ej.: server, pass set <password>, pass get)")
        self.input_edit.returnPressed.connect(self._submit)
        self.input_edit.installEventFilter(self)
        input_row.addWidget(self.input_edit, stretch=1)
        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self._submit)
        input_row.addWidget(self.send_button)
        inner.addLayout(input_row)

        group.setLayout(inner)
        layout.addWidget(group)

    # ------------------------------------------------------------- envío

    def _submit(self) -> None:
        """Valida la entrada, la emite como comando y la guarda en el historial."""
        cmd = self.input_edit.text().strip()
        if not cmd:
            return
        self.input_edit.clear()
        self._remember(cmd)
        if self._history:
            self._history_index = len(self._history)  # próximo ↑ vuelve al último
        peer = self.current_target()
        if self.echo_check.isChecked():
            self.append_sent(cmd)
        self.send_requested.emit(cmd, peer)

    def _remember(self, cmd: str) -> None:
        """Agrega el comando al historial evitando duplicados consecutivos.

        Args:
            cmd: Comando ingresado por el usuario.
        """
        if self._history and self._history[-1] == cmd:
            return
        self._history.append(cmd)
        if len(self._history) > 100:
            self._history.pop(0)

    def eventFilter(self, obj: object, event: object) -> bool:  # noqa: N802 (API Qt)
        """Intercepta ↑/↓ en el campo de entrada para navegar el historial.

        Args:
            obj: Objeto que generó el evento.
            event: Evento de teclado.

        Returns:
            ``True`` si el evento fue consumido (flechas del historial).
        """
        if obj is self.input_edit and event.type() == QEvent.Type.KeyPress:
            key_event: QKeyEvent = event  # type: ignore[assignment]
            if key_event.key() == Qt.Key.Key_Up:
                self._history_step(-1)
                return True
            if key_event.key() == Qt.Key.Key_Down:
                self._history_step(1)
                return True
        return super().eventFilter(obj, event)  # type: ignore[arg-type]

    def _history_step(self, delta: int) -> None:
        """Navega el historial con ↑/↓ sin salirse de los extremos.

        Args:
            delta: ``-1`` para el comando anterior, ``+1`` para el siguiente.
        """
        if not self._history:
            return
        self._history_index = max(0, min(len(self._history), self._history_index + delta))
        if self._history_index == len(self._history):
            self.input_edit.clear()
        else:
            self.input_edit.setText(self._history[self._history_index])

    # ------------------------------------------------------------ salida

    def append_output(self, text: str) -> None:
        """Muestra un frame de texto recibido del ESP (respuesta de consola).

        Args:
            text: Texto crudo recibido (se imprime tal cual, verbatim).
        """
        stamp = datetime.now().strftime("%H:%M:%S")
        body = html.escape(text.rstrip("\n"))
        self.output.appendHtml(
            f'<span style="color:{STAMP_COLOR}">[{stamp}]</span> '
            f'<span style="color:{TEXT_COLOR}">{body}</span>'
        )

    def append_sent(self, cmd: str) -> None:
        """Muestra el comando enviado (eco local, en color verde).

        Args:
            cmd: Comando enviado.
        """
        stamp = datetime.now().strftime("%H:%M:%S")
        body = html.escape(cmd)
        self.output.appendHtml(
            f'<span style="color:{STAMP_COLOR}">[{stamp}]</span> '
            f'<span style="color:{SENT_COLOR}; font-weight:bold">{PROMPT} {body}</span>'
        )

    def clear_output(self) -> None:
        """Borra la salida de la consola (el historial se conserva)."""
        self.output.clear()

    # ------------------------------------------------------------ destino

    def current_target(self) -> str:
        """Devuelve la etiqueta del destino seleccionado en el combo.

        Returns:
            Etiqueta ``host:puerto`` o :data:`BROADCAST_TARGET`.
        """
        return self.target_combo.currentText()

    def set_peers(self, peers: list[str]) -> None:
        """Actualiza el selector de destino con los clientes conectados.

        Conserva la selección si el peer sigue conectado; si no, elige el
        primer cliente disponible (o broadcast si no hay ninguno).

        Args:
            peers: Lista de etiquetas ``host:puerto`` conectadas.
        """
        previous = self.current_target()
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItem(BROADCAST_TARGET)
        self.target_combo.addItems(peers)
        # La selección persiste solo si el peer elegido sigue conectado;
        # si no, default = primer cliente (o broadcast si no hay ninguno).
        if previous not in peers:
            previous = peers[0] if peers else BROADCAST_TARGET
        index = self.target_combo.findText(previous)
        self.target_combo.setCurrentIndex(max(0, index))
        self.target_combo.blockSignals(False)

    # --------------------------------------------------------- eco/config

    def is_echo_enabled(self) -> bool:
        """Indica si el eco local está activado.

        Returns:
            Estado del checkbox de eco.
        """
        return self.echo_check.isChecked()

    def set_echo_enabled(self, enabled: bool) -> None:
        """Establece el eco local (carga de configuración).

        Args:
            enabled: Nuevo estado del checkbox.
        """
        self.echo_check.setChecked(enabled)
