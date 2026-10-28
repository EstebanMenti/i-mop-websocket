"""Panel de los 5 filtros por prefijo (nombre + habilitado)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from imop.constants import MAX_FILTERS
from imop.core.filters import FilterManager
from imop.core.models import FilterRule


class FilterPanel(QWidget):
    """Edita las ``MAX_FILTERS`` reglas de filtro y notifica cambios."""

    filters_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Construye el panel con filas de filtro vacías."""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        group = QGroupBox(f"Filtros ({MAX_FILTERS}) — prefijo sobre la clave raíz del JSON")
        rows = QVBoxLayout()
        self._checks: list[QCheckBox] = []
        self._edits: list[QLineEdit] = []

        for index in range(MAX_FILTERS):
            row = QHBoxLayout()
            check = QCheckBox(f"F{index + 1}")
            edit = QLineEdit()
            edit.setPlaceholderText("prefijo, ej.: sensor_")
            check.toggled.connect(lambda _checked: self.filters_changed.emit())
            edit.textChanged.connect(lambda _text: self.filters_changed.emit())
            row.addWidget(check)
            row.addWidget(edit, stretch=1)
            rows.addLayout(row)
            self._checks.append(check)
            self._edits.append(edit)

        group.setLayout(rows)
        layout.addWidget(group)

    def rules(self) -> list[FilterRule]:
        """Devuelve las reglas configuradas actualmente.

        Returns:
            Lista de ``MAX_FILTERS`` reglas en orden (F1..F5).
        """
        return [
            FilterRule(name=edit.text().strip(), enabled=check.isChecked())
            for check, edit in zip(self._checks, self._edits, strict=True)
        ]

    def set_rules(self, rules: list[FilterRule]) -> None:
        """Carga reglas en el panel (al iniciar la aplicación).

        Args:
            rules: Reglas guardadas en la configuración.
        """
        for index in range(MAX_FILTERS):
            rule = rules[index] if index < len(rules) else FilterRule(name="")
            self._checks[index].setChecked(rule.enabled)
            self._edits[index].setText(rule.name)

    def connect_to_manager(self, manager: FilterManager) -> None:
        """Sincroniza cambios del panel con un ``FilterManager`` en vivo.

        Args:
            manager: Gestor de filtros del pipeline activo.
        """
        self.filters_changed.connect(lambda: manager.set_rules(self.rules()))
