"""Gestión de los filtros por prefijo (máximo ``MAX_FILTERS``).

Semántica acordada (docs/ARCHITECTURE.md §4):

- Un filtro coincide cuando la **clave raíz** del JSON comienza con el
  prefijo configurado (comparación insensible a mayúsculas).
- Prefijos vacíos o reglas deshabilitadas se ignoran en el matching.
- Si no hay filtros habilitados con prefijo, se muestran **todos** los
  mensajes en el panel inferior.
"""

from __future__ import annotations

from collections.abc import Sequence

from imop.core.models import FilterRule, JsonPayload
from imop.core.parser import root_key


class FilterManager:
    """Evalúa las reglas de filtro sobre los mensajes entrantes."""

    def __init__(self, rules: Sequence[FilterRule] = ()) -> None:
        """Inicializa el gestor con una lista de reglas.

        Args:
            rules: Reglas iniciales (se copian; el orden se preserva).
        """
        self._rules: list[FilterRule] = list(rules)

    @property
    def rules(self) -> tuple[FilterRule, ...]:
        """Reglas actuales, en orden de configuración."""
        return tuple(self._rules)

    def set_rules(self, rules: Sequence[FilterRule]) -> None:
        """Reemplaza todas las reglas (invocado desde la GUI en vivo).

        Args:
            rules: Nuevas reglas.
        """
        self._rules = list(rules)

    @property
    def active_rules(self) -> tuple[FilterRule, ...]:
        """Reglas habilitadas con prefijo no vacío."""
        return tuple(rule for rule in self._rules if rule.enabled and rule.name)

    def match(self, payload: JsonPayload) -> tuple[FilterRule, ...]:
        """Devuelve las reglas activas cuyo prefijo coincide con la clave raíz.

        Args:
            payload: JSON ya parseado.

        Returns:
            Reglas coincidentes en orden de configuración (puede ser vacío).
        """
        key = root_key(payload).lower()
        if not key:
            return ()
        return tuple(rule for rule in self.active_rules if key.startswith(rule.name.lower()))

    def passes_display(self, payload: JsonPayload) -> bool:
        """Indica si el mensaje debe mostrarse en el panel inferior.

        Sin filtros activos se muestran todos; con filtros activos, solo
        los mensajes que coinciden con al menos uno.

        Args:
            payload: JSON ya parseado.

        Returns:
            ``True`` si el mensaje pasa los filtros visuales.
        """
        if not self.active_rules:
            return True
        return bool(self.match(payload))
