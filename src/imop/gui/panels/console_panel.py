"""Panel de consola remota: terminal integrado para comandos al ESP32.

Aspecto de terminal (fondo negro, texto claro): la salida del ESP se
imprime verbatim y la última línea de la misma consola es el campo de
escritura con cursor, estilo consola de comandos de Windows (sin etiqueta
de prompt separada). Los comandos se envían como frames de texto con
``\\n`` final (lo agrega la capa de red) dirigidos al ESP seleccionado en
"Destino" (fila superior); el historial se navega con las flechas ↑/↓.
"""

from __future__ import annotations

import html
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from imop.constants import COLOR_SYSTEM as SENT_COLOR

#: Tope de bloques que retiene la terminal (la propia QPlainTextEdit recorta).
MAX_CONSOLE_LINES = 5000

#: Colores de la terminal (fondo negro).
STAMP_COLOR = "#8a8a8a"  # gris: timestamps tenues
TEXT_COLOR = "#e0e0e0"  # claro: respuestas del ESP
TERMINAL_STYLESHEET = (
    "QPlainTextEdit {"
    " background-color: #000000;"
    " color: #e0e0e0;"
    " border: 1px solid #333333;"
    " font-family: Consolas, monospace;"
    " font-size: 10pt;"
    " selection-background-color: #264f78;"
    "}"
)

#: Prefijo de la línea de escritura (estilo consola de comandos).
PROMPT = "> "


class ConsoleTerminal(QPlainTextEdit):
    """Terminal de una sola pieza: salida y línea de escritura integradas.

    El texto se edita solo después del último prompt ``"> "``; el historial
    se recorre con ↑/↓ y Enter envía la línea actual (señal
    ``submit_requested``). El contenido por encima del prompt es de solo
    lectura: el cursor siempre se reubica al final si se intenta editar.
    """

    #: Línea aceptada con Enter (texto ya recortado).
    submit_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Construye la terminal vacía con su primera línea de prompt."""
        super().__init__(parent)
        self.setReadOnly(False)
        self.setMaximumBlockCount(MAX_CONSOLE_LINES)
        self.setStyleSheet(TERMINAL_STYLESHEET)
        self.setPlaceholderText(
            "Esperando un ESP32 conectado... los comandos se escriben acá abajo "
            "y se envían con Enter."
        )
        self._prompt_pos = 0
        self._history: list[str] = []
        self._history_index = 0
        self.show_echo = True
        self.cursorPositionChanged.connect(self._clamp_cursor)
        self._append_prompt("")

    # ----------------------------------------------------------- entrada

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (API Qt)
        """Enter envía, ↑/↓ navegan el historial, Home/Backspace respetan el prompt."""
        key = event.key()
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self._submit()
            return
        if key == Qt.Key.Key_Up:
            self._history_step(-1)
            return
        if key == Qt.Key.Key_Down:
            self._history_step(1)
            return
        if key == Qt.Key.Key_Home:
            cursor = self.textCursor()
            cursor.setPosition(self._prompt_pos)
            self.setTextCursor(cursor)
            return
        if key == Qt.Key.Key_Backspace and self.textCursor().position() <= self._prompt_pos:
            return
        super().keyPressEvent(event)
        self._clamp_cursor()

    def _clamp_cursor(self) -> None:
        """Mantiene el cursor en la zona editable (después del prompt)."""
        cursor = self.textCursor()
        if cursor.position() < self._prompt_pos:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)

    def _input_text(self) -> str:
        """Texto de la línea actual (después del último prompt)."""
        cursor = self.textCursor()
        cursor.setPosition(self._prompt_pos)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        return cursor.selectedText()

    def set_input(self, text: str) -> None:
        """Reemplaza el contenido de la línea de escritura.

        Args:
            text: Texto a colocar después del prompt.
        """
        cursor = self.textCursor()
        cursor.setPosition(self._prompt_pos)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        if text:
            cursor.insertHtml(html.escape(text))
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def _submit(self) -> None:
        """Valida la línea, la imprime (eco) y emite el comando."""
        cmd = self._input_text().strip()
        if not cmd:
            self._append_prompt("")
            return
        self._remember(cmd)
        cursor = self.textCursor()
        cursor.setPosition(self._prompt_pos)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        if self.show_echo:
            cursor.insertHtml(
                f'<span style="color:{SENT_COLOR}; font-weight:bold">{html.escape(cmd)}</span>'
            )
        else:
            cursor.removeSelectedText()
        self._append_prompt("")
        self.submit_requested.emit(cmd)

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

    def _history_step(self, delta: int) -> None:
        """Navega el historial con ↑/↓ sin salirse de los extremos.

        Args:
            delta: ``-1`` para el comando anterior, ``+1`` para el siguiente.
        """
        if not self._history:
            return
        self._history_index = max(0, min(len(self._history), self._history_index + delta))
        if self._history_index == len(self._history):
            self.set_input("")
        else:
            self.set_input(self._history[self._history_index])

    # ------------------------------------------------------------ salida

    def append_output(self, text: str) -> None:
        """Muestra un frame de texto recibido del ESP, sobre la línea actual.

        Args:
            text: Texto crudo recibido (se imprime tal cual, verbatim).
        """
        stamp = datetime.now().strftime("%H:%M:%S")
        saved = self._input_text()
        cursor = self.textCursor()
        cursor.setPosition(self._prompt_pos)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        body = html.escape(text.rstrip("\n"))
        self.appendHtml(
            f'<span style="color:{STAMP_COLOR}">[{stamp}]</span> '
            f'<span style="color:{TEXT_COLOR}">{body}</span>'
        )
        self._append_prompt(saved)

    def _append_prompt(self, input_text: str) -> None:
        """Agrega una línea de prompt (con el texto de entrada indicado).

        El prompt siempre inicia en una línea nueva (salvo al inicio del
        documento), para que la salida del ESP quede separada del próximo
        comando.

        Args:
            input_text: Texto del usuario a restaurar después del prompt.
        """
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if cursor.position() > 0:
            cursor.insertBlock()
        cursor.insertHtml(f'<span style="color:{SENT_COLOR}; font-weight:bold">{PROMPT}</span>')
        if input_text:
            cursor.insertHtml(html.escape(input_text))
        self._prompt_pos = cursor.position()
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_output(self) -> None:
        """Borra la terminal y deja una línea de prompt nueva."""
        self.clear()
        self._prompt_pos = 0
        self._append_prompt("")


class ConsolePanel(QWidget):
    """Consola de comandos: destino arriba y terminal integrada abajo."""

    #: Comando aceptado para envío: (texto del comando, peer destino).
    send_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Construye la consola con su selector de destino y la terminal."""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        group = QGroupBox("Consola remota (texto plano)")
        inner = QVBoxLayout()

        # Fila superior: destino + controles.
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Destino:"))
        self.target_combo = QComboBox()
        self.target_combo.setToolTip("ESP32 conectado que recibirá los comandos.")
        self.target_combo.setEnabled(False)
        controls.addWidget(self.target_combo, stretch=1)
        self.echo_check = QCheckBox("Eco local")
        self.echo_check.setChecked(True)
        self.echo_check.setToolTip(
            "Dejar el comando tipeado en la terminal (en verde) al enviarlo."
        )
        self.echo_check.toggled.connect(self._sync_echo)
        controls.addWidget(self.echo_check)
        self.clear_button = QPushButton("Limpiar")
        self.clear_button.clicked.connect(self.clear_output)
        controls.addWidget(self.clear_button)
        inner.addLayout(controls)

        # Terminal integrada (salida + línea de escritura con cursor).
        self.terminal = ConsoleTerminal()
        inner.addWidget(self.terminal, stretch=1)
        self.terminal.submit_requested.connect(self._on_submit)

        group.setLayout(inner)
        layout.addWidget(group)

    # ------------------------------------------------------------- envío

    def _on_submit(self, cmd: str) -> None:
        """Reenvía el comando aceptado en la terminal al destino elegido.

        Args:
            cmd: Comando en texto plano.
        """
        self.send_requested.emit(cmd, self.current_target())

    def current_target(self) -> str:
        """Etiqueta ``host:puerto`` del ESP seleccionado (o ``""`` si no hay).

        Returns:
            Etiqueta del destino; vacía si no hay clientes conectados.
        """
        if not self.target_combo.isEnabled() or self.target_combo.currentText() == "":
            return ""
        return self.target_combo.currentText()

    def set_peers(self, peers: list[str]) -> None:
        """Actualiza el selector de destino con los clientes conectados.

        Conserva la selección si el peer sigue conectado; si no, elige el
        primero. Sin clientes el selector queda deshabilitado.

        Args:
            peers: Lista de etiquetas ``host:puerto`` conectadas.
        """
        previous = self.current_target()
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItems(peers)
        self.target_combo.setEnabled(bool(peers))
        if peers:
            index = self.target_combo.findText(previous)
            self.target_combo.setCurrentIndex(index if index >= 0 else 0)
        self.target_combo.blockSignals(False)

    # ------------------------------------------------------------ salida

    def append_output(self, text: str) -> None:
        """Muestra un frame de texto recibido del ESP (respuesta de consola).

        Args:
            text: Texto crudo recibido (se imprime tal cual, verbatim).
        """
        self.terminal.append_output(text)

    def clear_output(self) -> None:
        """Borra la terminal (el historial se conserva)."""
        self.terminal.clear_output()

    # --------------------------------------------------------- eco/config

    def _sync_echo(self, enabled: bool) -> None:
        """Sincroniza el eco local de la terminal con el checkbox.

        Args:
            enabled: Nuevo estado del checkbox.
        """
        self.terminal.show_echo = enabled

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
