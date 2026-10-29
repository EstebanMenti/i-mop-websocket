"""Ventana principal: integra paneles, pipeline y worker del servidor."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from imop.config import AppConfig, save_config
from imop.constants import DEFAULT_HOST
from imop.core.models import DisplayMessage, ServerStatus
from imop.core.pipeline import MessagePipeline
from imop.gui.panels.filter_panel import FilterPanel
from imop.gui.panels.log_settings_panel import LogSettingsPanel
from imop.gui.panels.message_panel import MessagePanel
from imop.gui.panels.server_panel import ServerPanel
from imop.gui.workers import ServerWorker
from imop.logging_service.handlers import FilterLogManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Ventana principal de i-mop-websocket."""

    def __init__(self, config: AppConfig) -> None:
        """Construye la ventana y aplica la configuración inicial.

        Args:
            config: Configuración cargada del disco.
        """
        super().__init__()
        self.setWindowTitle("i-mop-websocket — Monitor JSON para ESP32")
        self._config = config
        self._pipeline: MessagePipeline | None = None
        self._worker: ServerWorker | None = None

        self._build_ui()
        self._apply_config()
        self._connect_internal()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        """Crea todos los paneles y el layout principal."""
        central = QWidget()
        main_layout = QVBoxLayout(central)

        self.server_panel = ServerPanel()
        self.filter_panel = FilterPanel()
        self.log_panel = LogSettingsPanel(initial_dir=str(self._config.log_dir))
        self.message_panel = MessagePanel()

        top_row = QHBoxLayout()
        top_row.addWidget(self.server_panel, stretch=2)
        top_row.addWidget(self.log_panel, stretch=3)

        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left.setLayout(top_row)
        top_splitter.addWidget(left)
        top_splitter.addWidget(self.filter_panel)

        vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        vertical_splitter.addWidget(top_splitter)
        vertical_splitter.addWidget(self.message_panel)
        vertical_splitter.setStretchFactor(0, 0)
        vertical_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(vertical_splitter)
        self.setCentralWidget(central)
        self._build_clock()
        self.statusBar().showMessage("Listo.")

    def _build_clock(self) -> None:
        """Crea el reloj permanente en la esquina inferior derecha."""
        self._clock_label = QLabel()
        self.statusBar().addPermanentWidget(self._clock_label)
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._update_clock)
        self._update_clock()
        self._clock_timer.start()

    def _update_clock(self) -> None:
        """Refresca la hora mostrada en la barra de estado."""
        self._clock_label.setText(datetime.now().strftime("%H:%M:%S"))

    def _apply_config(self) -> None:
        """Vuelca la configuración cargada en los controles."""
        self.server_panel.port_spin.setValue(self._config.port)
        self.filter_panel.set_rules(self._config.filters)
        self.log_panel.set_enabled_checked(self._config.log_enabled)

    def _connect_internal(self) -> None:
        """Conecta las señales internas de la ventana."""
        self.server_panel.start_requested.connect(self._on_start)
        self.server_panel.stop_requested.connect(self._on_stop)
        self.log_panel.save_enabled_changed.connect(self._on_log_enabled_changed)
        self.log_panel.log_dir_changed.connect(self._on_log_dir_changed)

    # ------------------------------------------------------------- servidor

    def _on_start(self, port: int) -> None:
        """Arranca el worker del servidor con el pipeline configurado.

        Args:
            port: Puerto elegido en el panel del servidor.
        """
        if self._worker is not None:
            return
        log_dir = Path(self.log_panel.log_dir())
        log_manager = FilterLogManager(log_dir=log_dir)
        log_manager.enabled = self.log_panel.is_enabled()
        self._pipeline = MessagePipeline(
            rules=self.filter_panel.rules(),
            log_manager=log_manager,
        )
        # Filtros y logs en caliente mientras el servidor corre.
        self.filter_panel.connect_to_manager(self._pipeline.filters)
        self.log_panel.save_enabled_changed.connect(self._pipeline.set_log_enabled)
        self.log_panel.log_dir_changed.connect(self._pipeline.set_log_dir)

        self._worker = ServerWorker(host=DEFAULT_HOST, port=port, pipeline=self._pipeline)
        self._worker.message_received.connect(self._on_message)
        self._worker.state_changed.connect(self._on_state_changed)
        self._worker.clients_changed.connect(self.server_panel.set_clients)
        self._worker.error_occurred.connect(self._on_server_error)
        self.server_panel.set_status(ServerStatus.STARTING)
        self._worker.start()

    def _on_stop(self) -> None:
        """Detiene el servidor de forma ordenada."""
        if self._worker is None:
            return
        self._worker.stop()
        if not self._worker.wait(5000):
            logger.warning("El servidor no terminó en 5 s; se abandona el hilo")
        self._worker = None
        self._pipeline = None

    def _on_message(self, message: DisplayMessage) -> None:
        """Muestra un mensaje procesado en el panel inferior.

        Args:
            message: Mensaje emitido por el worker.
        """
        self.message_panel.append_message(message)

    def _on_state_changed(self, status: ServerStatus) -> None:
        """Refleja el estado del servidor en el panel y la barra.

        Args:
            status: Nuevo estado del servidor.
        """
        self.server_panel.set_status(status)
        self.statusBar().showMessage(f"Servidor: {status.value}")

    def _on_server_error(self, detail: str) -> None:
        """Muestra el error operativo del servidor.

        Args:
            detail: Descripción del error (p. ej. puerto ocupado).
        """
        self.statusBar().showMessage(f"Error del servidor: {detail}")
        QMessageBox.critical(self, "Error del servidor", detail)

    # ------------------------------------------------------------ logs/config

    def _on_log_enabled_changed(self, enabled: bool) -> None:
        """Propaga el flag de guardado de logs al pipeline activo.

        Args:
            enabled: Nuevo estado del flag.
        """
        if self._pipeline is not None:
            self._pipeline.set_log_enabled(enabled)

    def _on_log_dir_changed(self, path: str) -> None:
        """Propaga el cambio de carpeta de logs al pipeline activo.

        Args:
            path: Nueva carpeta destino.
        """
        if self._pipeline is not None:
            self._pipeline.set_log_dir(path)

    # ----------------------------------------------------------------- ciclo

    def closeEvent(self, event: object) -> None:  # noqa: N802 (API Qt)
        """Detiene el servidor y persiste la configuración al salir.

        Args:
            event: Evento de cierre de Qt.
        """
        self._on_stop()
        self._config.port = self.server_panel.port_spin.value()
        self._config.filters = self.filter_panel.rules()
        self._config.log_enabled = self.log_panel.is_enabled()
        self._config.log_dir = Path(self.log_panel.log_dir())
        save_config(self._config)
        super().closeEvent(event)  # type: ignore[arg-type]
