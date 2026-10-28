# Estándares de Codificación Python — i-mop-websocket

> **Regla:** Todo código nuevo debe cumplir este documento. Las desviaciones deben justificarse en el Pull Request y registrarse en [plans/action-plan.md](../plans/action-plan.md).

## 1. Referencias normativas

| Estándar | Alcance |
|----------|---------|
| [PEP 8](https://peps.python.org/pep-0008/) | Estilo de código |
| [PEP 257](https://peps.python.org/pep-0257/) | Docstrings |
| [PEP 484 / 585 / 604](https://peps.python.org/pep-0484/) | Type hints |
| [PEP 621](https://peps.python.org/pep-0621/) | Metadatos en `pyproject.toml` |
| [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) | Referencia complementaria |

## 2. Versiones y compatibilidad

- Python mínimo: **3.10** (usar sintaxis moderna: `list[dict]`, `str | None`, `match`).
- Prohibido código solo-Windows en el paquete `imop` central: toda dependencia de plataforma va aislada en módulos con guardas (`sys.platform`).

## 3. Formato y linting (automatizado, no negociable)

Herramientas: **ruff** (lint + format), **mypy** (tipado estático).

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "C4", "SIM", "T20", "PTH", "RUF"]

[tool.mypy]
python_version = "3.10"
strict = true
```

Reglas destacadas:

- **`T20`**: prohibido `print()` — usar `logging`. La GUI nunca imprime a stdout.
- **`I`**: imports ordenados alfabéticamente, agrupados (stdlib / terceros / locales).
- **`UP`**: sintaxis moderna obligatoria.
- Línea máxima: **100 caracteres**.
- Indentación: **4 espacios**, sin tabs.
- Comillas dobles `"` por defecto.

## 4. Nomenclatura

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Módulos/paquetes | `snake_case`, cortos, minúsculas | `filter_manager.py` |
| Clases | `PascalCase` | `WebSocketServer` |
| Funciones/variables | `snake_case` | `parse_message()` |
| Constantes | `UPPER_SNAKE_CASE` | `DEFAULT_PORT = 8765` |
| Privado | prefijo `_` | `_on_client_connected()` |
| Señales Qt | sufijo descriptivo de evento | `message_received = Signal(dict)` |

## 5. Tipado

- **Obligatorio** en todas las funciones, métodos y atributos públicos.
- `from __future__ import annotations` en todos los módulos.
- Preferir tipos específicos: `dict[str, Any]` sobre `dict`, `pathlib.Path` sobre `str` de rutas.
- Evitar `Any`; cuando sea inevitable, comentar el motivo.
- `mypy --strict` debe pasar sin errores en CI.

## 6. Docstrings (resumen — detalle en [DOCUMENTATION_RULES.md](DOCUMENTATION_RULES.md))

- Estilo **Google**.
- Obligatorio en: módulos, clases, métodos públicos, funciones públicas.
- Incluir `Args`, `Returns`, `Raises` cuando aplique.

```python
def apply_filters(self, payload: dict[str, Any]) -> list[str]:
    """Devuelve los filtros cuyo prefijo coincide con la clave raíz del JSON.

    Args:
        payload: Mensaje JSON ya parseado.

    Returns:
        Lista de nombres de filtros coincidentes (puede estar vacía).

    Raises:
        TypeError: Si `payload` no es un diccionario.
    """
```

## 7. Arquitectura de código

- **Separación estricta de capas**: red (`server/`), dominio (`filters/`, `logging/`), GUI (`gui/`). La GUI **nunca** implementa lógica de red ni de filtros.
- **Comunicación por señales Qt** entre el hilo de red (asyncio) y la GUI (hilo Qt). Prohibido tocar widgets desde otro hilo.
- Funciones puras y clases pequeñas (< 50 líneas por función como meta; máx. ~80).
- Un módulo = una responsabilidad (SRP). Si un archivo supera ~400 líneas, dividir.
- Manejo de errores: capturar excepciones **específicas**; nunca `except:` desnudo. Loguear con `logger.exception()` antes de recuperar o propagar.
- Sin estado global mutable; usar inyección de dependencias (constructor).

## 8. Concurrencia

- Red: **asyncio** + librería `websockets`, ejecutado en un hilo dedicado (o `qasync` si se integra al loop de Qt — decisión en Fase 3).
- Todo recurso compartido entre hilos debe protegerse (`queue.Queue`, `threading.Lock`).
- Cancelación limpia de tareas asyncio al detener el servidor.

## 9. Logging

- Logger por módulo: `logger = logging.getLogger(__name__)`.
- Niveles: `DEBUG` (detalle de red), `INFO` (eventos normales), `WARNING` (recuperable), `ERROR` (fallo operativa), `CRITICAL` (app inservible).
- Nunca loguear contenido completo de mensajes sensibles en INFO+ (recortar a 200 chars).

## 10. Pruebas

- Framework: **pytest** (+ `pytest-qt` para GUI, `pytest-asyncio` para red).
- Cobertura mínima objetivo: **80 %** en dominio (`filters`, `parsing`); la GUI se prueba por humo.
- Nombre de tests: `test_<unidad>_<escenario>_<resultado_esperado>.py`.
- Cada corrección de bug incluye primero un test que lo reproduce (regresión).

## 11. Commits y revisiones

- Ver [GIT_WORKFLOW.md](GIT_WORKFLOW.md) para convencionales commits (`feat:`, `fix:`, `docs:`, ...).
- Un PR = una funcionalidad coherente; máximo recomendado ~400 líneas cambiadas.

## 12. Sugerencias / mejores prácticas adicionales

1. **Configuración externa**: puerto y filtros en archivo de config (`~/.imop/config.json` o QSettings), nunca hardcodeados salvo `DEFAULT_*`.
2. **Constantes de protocolo** centralizadas en `imop/core/constants.py`.
3. **Type aliases** para dominio: `JsonPayload = dict[str, Any]`, `FilterName = str`.
4. **`pathlib.Path`** siempre para rutas; nunca concatenar strings de rutas.
5. **Sin sorpresas de encoding**: abrir archivos siempre con `encoding="utf-8"` explícito (crítico en Windows).
6. **Cierre ordenado**: el servidor detiene tareas asyncio, cierra handlers de log y persiste configuración al salir (`aboutToQuit` de Qt).
7. **Versión única**: `imop/__version__` como fuente de verdad, leída por `pyproject.toml` (dynamic).
