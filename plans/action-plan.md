# Plan de Acción Maestro — i-mop-websocket

> **Propósito:** Este documento es el registro vivo de todo el trabajo de planificación y desarrollo del proyecto. Toda decisión tomada (por el usuario o por la IA) debe quedar registrada aquí, con fecha, para garantizar trazabilidad completa del proyecto.

---

## 1. Visión del producto

Aplicación de escritorio en Python que:

- Ejecuta un **servidor WebSocket** en un **puerto configurable**.
- Recibe mensajes **JSON** desde dispositivos externos (principalmente un **ESP32**).
- Muestra los mensajes en un **visualizador claro, con colores y timestamps**.
- Aplica **5 filtros configurables por prefijo** sobre los mensajes entrantes:
  - Si el JSON (o su `type`/clave raíz) **comienza** con un filtro habilitado → se escribe a un **archivo de log dedicado** (si el guardado de logs está habilitado).
  - Los filtros también se aplican al **panel inferior de mensajes en vivo**: si no hay filtros activos, se muestran **todos** los datos.
- En el futuro: **teclas / botones para enviar datos** al ESP32 (comunicación bidireccional).

## 2. Decisiones registradas

| Fecha | Decisión | Motivo | Estado |
|-------|----------|--------|--------|
| 2026-10-28 | Framework GUI: **PySide6 (Qt)** | GUI profesional, colores, tablas, multiplataforma, empaqueta bien a .exe con PyInstaller | ✅ Aprobada por el usuario |
| 2026-10-28 | Python mínimo: **3.10+** | Tipado moderno (`X | Y`), match, soporte activo | 📝 Propuesta |
| 2026-10-28 | Servidor WebSocket: **`websockets`** (asyncio) | Estándar de facto en Python, integración natural con asyncio, madurez | 📝 Propuesta |
| 2026-10-28 | Gestión de proyecto: **pyproject.toml + uv/pip** | Estándar moderno (PEP 621) | 📝 Propuesta |
| 2026-10-28 | Flujo Git: **GitFlow simplificado** | Ver [docs/GIT_WORKFLOW.md](../docs/GIT_WORKFLOW.md) | 📝 Propuesta |
| 2026-10-28 | Empaquetado Windows: **PyInstaller (onefile/onedir)** | Estándar para apps Qt | 📝 Propuesta |

## 3. Roadmap por fases

### Fase 0 — Fundaciones (documentación y estándares) ← *ESTA ENTREGA*
- [x] Definir visión del producto.
- [x] Elegir framework GUI (PySide6).
- [x] Estándares de codificación Python → [docs/CODING_STANDARDS.md](../docs/CODING_STANDARDS.md)
- [x] Reglas de documentación (código, usuario, IA) → [docs/DOCUMENTATION_RULES.md](../docs/DOCUMENTATION_RULES.md)
- [x] Flujo Git profesional / GitFlow → [docs/GIT_WORKFLOW.md](../docs/GIT_WORKFLOW.md)
- [x] Arquitectura y estructura del proyecto → [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- [x] Guía de compilación .exe y multiplataforma → [docs/BUILD_AND_DEPLOYMENT.md](../docs/BUILD_AND_DEPLOYMENT.md)
- [x] README del proyecto → [README.md](../README.md)

### Fase 1 — Scaffolding del proyecto
- [ ] Inicializar repositorio Git + ramas GitFlow (`main`, `develop`).
- [ ] Crear `pyproject.toml` con dependencias y tooling (ruff, mypy, pytest).
- [ ] Crear estructura de paquetes según [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).
- [ ] Configurar entornos virtuales por plataforma (instrucciones venv/uv).
- [ ] Pre-commit hooks (ruff format + ruff check + mypy).

### Fase 2 — Núcleo WebSocket
- [ ] `WebSocketServer`: servidor asyncio en puerto configurable (CLI `--port` y GUI).
- [ ] Parser/validador de JSON con manejo de errores robusto.
- [ ] Pruebas unitarias con pytest (parser, servidor mock).

### Fase 3 — GUI con PySide6
- [ ] Ventana principal: estado del servidor, puerto, botones iniciar/detener.
- [ ] Panel inferior: lista/tabla de mensajes en vivo con colores por tipo, timestamps, límite de filas.
- [ ] Configuración de los **5 filtros** (prefijo + habilitado on/off).
- [ ] Checkbox "guardar logs" + selector de carpeta de destino.
- [ ] Persistencia de configuración (QSettings o JSON local).

### Fase 4 — Logging por filtros
- [ ] `FilterManager`: comparación de prefijos sobre la clave raíz del JSON.
- [ ] Rotación de archivos de log (RotatingFileHandler).
- [ ] Un archivo por filtro habilitado + log general opcional.

### Fase 5 — Envío de datos al ESP32 (futuro)
- [ ] Registro de clientes conectados.
- [ ] Teclas/botones configurables que envían JSON predefinidos.
- [ ] Documentar protocolo de mensajes bidireccional.

### Fase 6 — Empaquetado y distribución
- [ ] Script de build PyInstaller (`.spec`) para Windows (.exe).
- [ ] Instrucciones/build para Linux (AppImage o binario) y macOS (.app).
- [ ] Publicar release en GitHub (tags semánticos vX.Y.Z).

## 4. Registro de sesiones de trabajo (obligatorio)

Cada sesión de trabajo con IA debe agregar una entrada al final de esta sección:

### 2026-10-28 — Sesión 1: Diseño y reglas del proyecto
- **Objetivo:** Generar todas las reglas de diseño (Python, documentación, Git, README, estructura, compilación, multiplataforma).
- **Resultado:** Creados `README.md`, `plans/action-plan.md` y 5 documentos en `docs/`.
- **Pendiente:** Aprobación del usuario y comienzo de Fase 1.

### 2026-10-28 — Sesión 2: Implementación completa (Fases 1-4)
- **Objetivo:** Implementar la aplicación end-to-end siguiendo las reglas aprobadas.
- **Resultado:**
  - Scaffolding completo: `pyproject.toml` (ruff, mypy, pytest, extras dev/build), `.gitignore`, `.pre-commit-config.yaml`.
  - Dominio puro (`src/imop/core/`): `models` (JsonPayload, FilterRule, DisplayMessage, ServerStatus), `parser` (MessageParseError), `filters` (FilterManager: prefijos sobre clave raíz, case-insensitive; sin filtros → mostrar todo), `pipeline` (parseo → filtros → logs → display).
  - Red (`src/imop/network/`): `WebSocketServer` asyncio (websockets 13+ API), `ClientRegistry` con broadcast (base del envío futuro al ESP32).
  - Logs (`src/imop/logging_service/`): `FilterLogManager` con RotatingFileHandler por filtro (5 MiB × 3 backups), activable en caliente.
  - GUI PySide6 (`src/imop/gui/`): `MainWindow`, `ServerPanel` (puerto/start/stop/estado/clientes), `FilterPanel` (5 filtros en vivo), `MessagePanel` (colores por clave raíz, timestamps, límite 1000 filas), `LogSettingsPanel`, `ServerWorker` (QThread + asyncio loop, señales thread-safe).
  - Config persistente atómica en `~/.imop/config.json`; CLI `--port/--version`; entrada `python -m imop` y `imop`.
  - Tests: **30 passed** (unit: parser/filters/pipeline/config; network: servidor real con cliente websockets; GUI: smoke offscreen).
  - Calidad: `ruff check` ✓, `ruff format` ✓, `mypy` ✓ (0 errores).
  - Script E2E manual: `scripts/e2e_send.py` (envía JSON de ejemplo a la GUI).
- **Decisiones técnicas registradas:**
  - Paquete `logging_service` (no `logging`) para evitar ambigüedad con el stdlib — ARCHITECTURE.md actualizado.
  - `theme.py` movido a nivel de paquete (módulo puro, importable desde dominio) — ARCHITECTURE.md actualizado.
  - `websockets` >= 13 con API moderna `websockets.asyncio.server`.
  - Git: `main` (docs) → `develop` → `feature/scaffolding-e-implementacion` según GIT_WORKFLOW.md.
- **Pendiente:** Verificación manual E2E con GUI por parte del usuario; empaquetado PyInstaller (Fase 6); manual de usuario (Fase 3-docs).

### 2026-10-29 — Sesión 3: ACK por seq + robustez de conexión
- **Objetivo:** El servidor debe confirmar cada mensaje con el `seq` recibido del cliente; además, los tracebacks por desconexiones abruptas del ESP32 ensuciaban el log.
- **Resultado:**
  - [`network/server.py`](../src/imop/network/server.py): si el JSON incluye `"seq"` entero → responde `{"ack_seq": <seq>, "status": "ok|error"}`; sin `seq` no responde (retrocompatible).
  - Manejo limpio de `ConnectionClosed` / `ConnectionResetError` / `OSError` en el handler (INFO, sin tracebacks).
  - [`scripts/e2e_send.py`](../scripts/e2e_send.py): ahora envía mensajes con `seq` e imprime el ACK recibido.
  - 5 tests nuevos del ACK (ok, error de callback, sin seq, seq no entero, JSON inválido) → **35 passed**, ruff/mypy en verde.
  - Documentado el protocolo en [docs/ARCHITECTURE.md §4.1](ARCHITECTURE.md).
- **Rama:** `feature/ack-seq` (desde `develop`).
- **Pendiente:** Verificar con el ESP32 real que recibe y usa el ACK para retransmisiones.

### 2026-10-29 — Sesión 4: Reloj en barra de estado + contador de paquetes
- **Objetivo (pedido del usuario):** hora en la esquina inferior derecha; contador de paquetes recibidos que se restablezca con "Limpiar".
- **Resultado:**
  - [`gui/main_window.py`](../src/imop/gui/main_window.py): reloj `HH:MM:SS` como widget permanente de la barra de estado (esquina inferior derecha), actualizado por `QTimer` cada 1 s.
  - [`gui/panels/message_panel.py`](../src/imop/gui/panels/message_panel.py): etiqueta "Paquetes: N" junto al botón Limpiar; se incrementa con cada mensaje y `clear_all()` (botón o programático) la restablece a 0.
  - Smoke tests ampliados: contador, reset con botón y formato del reloj → **36 passed**, ruff/mypy en verde.
- **Rama:** `feature/reloj-y-contador` (desde `develop`).
- **Pendiente:** Verificación visual del usuario en la GUI.

---

## 5. Convenciones transversales

- **Protocolo de mensajes ESP32 → App:** JSON con clave raíz identificadora, p. ej.
  `{"sensor_temp": {"value": 23.4, "unit": "C"}}` → el filtro `sensor_` lo captura.
- **Idioma del código:** identificadores en inglés, comentarios/DOCs en español.
- **Toda nueva fase debe registrarse aquí antes de implementarse.**
