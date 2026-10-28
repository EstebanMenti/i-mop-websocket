"""Panel de configuración del guardado de logs por filtro."""

from __future__ import annotations

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LogSettingsPanel(QWidget):
    """Controla el flag "guardar logs" y la carpeta destino."""

    save_enabled_changed = Signal(bool)
    log_dir_changed = Signal(str)

    def __init__(self, initial_dir: str, parent: QWidget | None = None) -> None:
        """Construye el panel con la carpeta inicial.

        Args:
            initial_dir: Carpeta de logs inicial (de la configuración).
        """
        super().__init__(parent)
        layout = QVBoxLayout(self)
        group = QGroupBox("Guardado de logs")
        inner = QVBoxLayout()

        self.enabled_check = QCheckBox("Guardar logs de los filtros coincidentes")
        self.enabled_check.toggled.connect(self.save_enabled_changed.emit)
        inner.addWidget(self.enabled_check)

        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("Carpeta:"))
        self.dir_edit = QLineEdit(initial_dir)
        self.dir_edit.editingFinished.connect(
            lambda: self.log_dir_changed.emit(self.dir_edit.text())
        )
        browse_button = QPushButton("Examinar…")
        browse_button.clicked.connect(self._browse)
        open_button = QPushButton("Abrir carpeta")
        open_button.clicked.connect(self._open_folder)
        dir_row.addWidget(self.dir_edit, stretch=1)
        dir_row.addWidget(browse_button)
        dir_row.addWidget(open_button)
        inner.addLayout(dir_row)

        group.setLayout(inner)
        layout.addWidget(group)

    def is_enabled(self) -> bool:
        """Indica si el guardado de logs está activado.

        Returns:
            Estado del checkbox principal.
        """
        return self.enabled_check.isChecked()

    def set_enabled_checked(self, checked: bool) -> None:
        """Establece el estado del checkbox (carga de configuración).

        Args:
            checked: Nuevo estado.
        """
        self.enabled_check.setChecked(checked)

    def log_dir(self) -> str:
        """Devuelve la carpeta destino actual.

        Returns:
            Ruta de la carpeta como texto.
        """
        return self.dir_edit.text()

    def set_log_dir(self, path: str) -> None:
        """Establece la carpeta destino (carga de configuración).

        Args:
            path: Ruta de la carpeta.
        """
        self.dir_edit.setText(path)

    def _browse(self) -> None:
        """Abre el diálogo de selección de carpeta."""
        chosen = QFileDialog.getExistingDirectory(self, "Carpeta de logs", self.dir_edit.text())
        if chosen:
            self.dir_edit.setText(chosen)
            self.log_dir_changed.emit(chosen)

    def _open_folder(self) -> None:
        """Abre la carpeta de logs en el explorador del sistema."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.dir_edit.text()))
