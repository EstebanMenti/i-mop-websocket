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
| 2026-10-29 | Protocolo de comandos: **JSON-RPC 2.0 (subconjunto)** + telemetría JSON existente | Estandarizado, bidireccional, correlacionado por `id`, retrocompatible con el ACK por `seq` | ✅ Aprobada por el usuario |
| 2026-10-29 | Transferencia de archivos: **frames binarios nativos** (control por JSON, datos crudos, CRC32, reanudable) | Sin overhead de codificación, RAM constante en el ESP32, convivencia con telemetría vía `transfer` id | ✅ Aprobada por el usuario |
| 2026-10-30 | Protocolo v2 (propuesta): **CBOR canónico** para comandos y telemetría nueva | Binario auto-descripto (RFC 8949), ~4-8× más chico que JSON, librerías probadas en ESP32; convive con v1 | 📝 Propuesta — [docs/user/protocol-cbor.md](../docs/user/protocol-cbor.md) |
| 2026-11-02 | Telemetría IMU: **JSON con un vector por sensor** (`fmt` 2, 25 muestras por mensaje) | Medido en placa con los 8 nodos BLE activos: ≥ 1000 muestras/s de capacidad (≥ 4× la producción) y 0 pérdidas a 100 Hz, con 2,5× menos bytes que el JSON de claves largas; la App lo confirma sin cambios. CBOR `imu_full_batch` queda como formato futuro | ✅ Aprobada por el usuario — [docs/user/protocol.md](../docs/user/protocol.md) §10 |
| 2026-11-05 | Consola remota estilo SSH sobre WebSocket: **comandos y respuestas en texto plano** (sin envoltorio JSON; el intérprete del ESP es CLI estilo `server`, `pass set <password>`, `pass get`) sobre la misma conexión y puerto existente, sin seguridad (TLS/auth) por ahora, pestaña "Consola" nueva en la GUI | El intérprete del ESP ya habla texto; JSON agregaría parseo innecesario. Enrutamiento simple: frame JSON → telemetría (pipeline actual), frame texto plano → consola. Plan detallado en [plans/consola-ssh-plan.md](consola-ssh-plan.md) | ✅ Aprobada e implementada — [docs/user/protocol.md](../docs/user/protocol.md) §15 |

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

### Fase 5b — Consola remota estilo SSH (pestaña "Consola") ← *COMPLETADA* — [plans/consola-ssh-plan.md](consola-ssh-plan.md)
- [x] Red: `ClientRegistry.send_to()/peers()/resolve()/peer_label()` + `WebSocketServer.send_console_line()` (agrega `\n` al comando) y tests de envío dirigido/broadcast/peer desconocido.
- [x] Worker: `ServerWorker.send_command()` thread-safe (`run_coroutine_threadsafe`), señal `console_output`, enrutamiento por tipo de frame: JSON → pipeline de telemetría, texto plano → consola (test E2E con worker real).
- [x] GUI: `QTabWidget` (Telemetría / Consola) + `ConsolePanel` (salida coloreada, historial ↑/↓, selector de destino, eco local, límite 5000 líneas).
- [x] Config: persistir `console_echo` y `last_tab`.
- [x] Firmware de referencia del ESP32 (CLI `server`/`pass set`/`pass get`) documentado en [docs/user/protocol.md](../docs/user/protocol.md) §15.
- [x] Docs: ARCHITECTURE §4.3 (flujo bidireccional), FAQ (uso y diagnóstico de la consola), README.
- [x] QA: ruff + mypy + pytest (57 passed) en verde; registro de la sesión de implementación aquí.

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

### 2026-10-29 — Sesión 5: Descubrimiento automático mDNS/Zeroconf
- **Objetivo (pedido del usuario):** revisar un texto sobre auto-descubrimiento mDNS/Zeroconf e implementar la función correspondiente.
- **Revisión del texto:** la idea era correcta pero con roles invertidos — aquí la **notebook es el servidor** (anuncia `_imop._tcp` con la librería Python `zeroconf`) y **el ESP32 es el cliente que descubre** (con `ESPmDNS`, no con `bonjour-service` de Node.js). `Test-NetConnection DESKTOP-XXX.local -Port 1001` queda como diagnóstico manual opcional. Correcciones documentadas en [docs/user/faq.md](../docs/user/faq.md).
- **Resultado:**
  - [`network/discovery.py`](../src/imop/network/discovery.py): `ServiceAnnouncer` (servicio `_imop._tcp.local.`, instancia `i-mop-<hostname>`, TXT `proto=ws,app=imop`); errores de mDNS solo se loguean (anuncio opcional, nunca bloquea el servidor).
  - [`gui/panels/server_panel.py`](../src/imop/gui/panels/server_panel.py): checkbox "Anunciar servicio en la red (mDNS/Zeroconf)".
  - [`gui/main_window.py`](../src/imop/gui/main_window.py): arranque/parada del anuncio junto al servidor; limpieza al cerrar; persistido como `announce_enabled` en [config.py](../src/imop/config.py).
  - [`pyproject.toml`](../pyproject.toml): dependencia `zeroconf>=0.131`.
  - 4 tests nuevos ([tests/network/test_discovery.py](../tests/network/test_discovery.py), incluye descubrimiento real con `ServiceBrowser`) → **40 passed**, ruff/mypy en verde.
  - Documentado en [docs/ARCHITECTURE.md §4.2](../docs/ARCHITECTURE.md).
- **Rama:** `feature/zeroconf-discovery` (desde `develop`).
- **Pendiente:** Verificar descubrimiento con un ESP32 real en la misma red (firewall UDP 5353).

### 2026-10-29 — Sesión 6: Definición del protocolo de comandos y archivos
- **Objetivo (pedido del usuario):** investigar formatos para el envío de comandos al ESP32 (botones con y sin parámetros, `set/get` UWB, listado de la SD) y la recepción de archivos; luego unificar: **comandos por JSON, archivos por frames binarios**, en un documento que fije las reglas para que todo comando nuevo sea coherente.
- **Investigación (resumen):**
  - Comparados: texto tipo AT, JSON a medida, **JSON-RPC 2.0**, MessagePack/CBOR, Protobuf. Veredicto: JSON-RPC 2.0 en subconjunto — estandarizado, bidireccional, correlacionado por `id`, retrocompatible con el ACK por `seq`; lo binario queda como escalamiento solo si aparece streaming de alta frecuencia.
  - Recepción de archivos: WebSocket soporta frames binarios nativos. Propuesta: control JSON-RPC (`file_pull`/`file_push`/`file_cancel`/`file_ack`) + datos crudos por frames binarios (chunks de 4 KiB, CRC32, reanudable por `offset`, una transferencia a la vez, RAM constante en el ESP32).
- **Resultado:**
  - Creado [docs/user/protocol.md](../docs/user/protocol.md) **v1.0**: principios, tipos de mensaje, envelope JSON-RPC, política de IDs (`id` incremental App ≥ 1 / ESP32 ≥ 1000000, `seq` de telemetría, `transfer` de archivo), nomenclatura de métodos (`verbo_objeto`, vocabulario cerrado get/set/do/list), convención de parámetros (epoch UTC + tz, MAC hex, rutas POSIX), tabla de errores (estándar `-326xx` + aplicación `-320xx`), handshake `hello`, transferencia de archivos, **catálogo v1** (`get_info`, `ping`, `set/get_hora`, `set/get_uwb`, `sd_list`, `file_pull/push/ack/cancel`), checklist obligatorio para agregar comandos y reglas de compatibilidad.
  - Decisiones aprobadas registradas en §2 de este documento.
- **Rama:** `feature/protocolo-v1` (desde `develop`).
- **Pendiente:** Implementación (Fase 5): registro de comandos en GUI + botones, `file_pull` con canal binario, soporte `bytes` en el handler del servidor.

### 2026-10-29 — Sesión 7: Corrección de congelamiento con alta tasa de mensajes
- **Objetivo (reporte del usuario):** con ~6000 muestras en 60 s (100 msg/s), la GUI se congelaba.
- **Causa raíz:** cada mensaje disparaba, uno por uno, la señal Qt → creación de `QListWidgetItem` + `addItem` + actualización del contador + recorte de lista + `scrollToBottom` → un repaint completo por mensaje. A 100 msg/s el event loop de Qt quedaba saturado solo pintando.
- **Resultado:**
  - [`gui/panels/message_panel.py`](../src/imop/gui/panels/message_panel.py): **render por lotes** — los mensajes entrantes se acumulan en un buffer (deque acotado) y se pintan cada 100 ms en un solo pase (`setUpdatesEnabled(False)` → inserción → recorte único → `scrollToBottom` → repintado). Tope de 500 ítems por volcado; `setUniformItemSizes(True)`; el contador de paquetes sigue contando en tiempo real.
  - API nueva: `flush_now()` (volcado inmediato del buffer), `pending_count` (mensajes aún no pintados). `clear_all()` descarta también el buffer.
  - Test nuevo de alta tasa (1500 mensajes de una vez: lista acotada a 1000, contador exacto, buffer vacío tras `flush_now`) → **41 passed**, ruff/mypy en verde.
- **Rama:** `feature/perf-render-lote` (desde `develop`).
- **Pendiente:** Validación del usuario con el flujo real del ESP32 (~100 msg/s sostenidos).

### 2026-10-30 — Sesión 8: Propuesta de protocolo binario CBOR (v2)
- **Objetivo (pedido del usuario):** proponer un protocolo con formato CBOR, definir el formato de la IMU y ejemplos de otros comandos (los del chat) con calidad de guía de implementación.
- **Análisis previo:** comparados binario propio a medida vs CBOR vs MessagePack vs Protobuf vs FlatBuffers. Elegido **CBOR**: binario auto-descripto (RFC 8949), 4-8× más chico que JSON, librerías probadas (cbor2 en Python; TinyCBOR/QCBOR en ESP32), sin codegen. El ahorro real principal es CPU/RAM en el ESP32 (sin parseo JSON), más que ancho de banda en LAN.
- **Resultado:** creado [docs/user/protocol-cbor.md](../docs/user/protocol-cbor.md) **v2.0-draft**:
  - Perfil CBOR canónico (longitudes definidas, ints mínimos, claves ordenadas, sin tags) — ejemplos **hex normativos** byte a byte para tests golden.
  - Envelope `[tipo, cid, cmd, payload]` (4 tipos), registro de códigos por dominio, convención de claves enteras y unidades.
  - Especificaciones completas con hex: `get_info`, `ping`, `set/get_hora`, `set/get_uwb`, `sd_list`, `file_pull/push/cancel/ack`, ejemplo de error.
  - **Telemetría IMU** definida en detalle: `imu` (muestra individual: t_ms + accel en milig i16 ×3 + gyro en 0.1 dps i16 ×3 = 24 bytes/frame), `imu_batch` (ráfagas de N muestras con t0 + período, 1 frame/s a 100 Hz); más ejemplos `uwb_range`, `bat`, `temp`.
  - Coexistencia con v1: texto JSON = telemetría existente; binario CBOR = comandos/telemetría nueva; chunks de archivo crudos sin cambio.
  - Checklist de 8 pasos para agregar comandos CBOR nuevos.
- **Rama:** `feature/protocolo-cbor` (desde `develop`).
- **Pendiente:** Aprobación del usuario; luego implementación Fase 5 (codec CBOR en la App + botones de comandos).

### 2026-11-02 — Sesión 9: Formato de la telemetría IMU (JSON vector)
- **Objetivo (pedido del usuario):** dejar especificado en el protocolo el formato de la telemetría IMU elegido después de las mediciones en placa
  (firmware `i-mop-esp32`, `docs/TELEMETRIA_EFICIENCIA.md`).
- **Contexto:** con los 8 nodos BLE activos el JSON de claves largas (~424 B por muestra) tenía un margen de envío justo (2,9× la producción). Se
  midieron tres formatos: JSON de claves largas, JSON con un vector por sensor (~172 B) y CBOR `imu_full_batch` (~34 B, especificado en la rama
  `feature/protocolo-cbor-imu-completo`, sin integrar). El usuario eligió el **JSON vector**.
- **Resultado:** [docs/user/protocol.md](../docs/user/protocol.md) **v1.1**:
  - §10 nuevo: mensaje con ejemplo verificado, campos de la muestra y del sobre, reglas de valores, ritmo y tamaño, confirmación acumulativa,
    reenvío tras reconexión y descarte de repetidos por `sid` + `s`, código de lectura y los otros formatos de la placa.
  - §3.4: la confirmación de un mensaje con varias muestras usa el `seq` de la última y es acumulativa.
  - §4 corregido: el `seq` de telemetría es por sesión de la placa (`sid`) y **no** se reinicia al reconectar (así funciona el firmware).
  - Secciones 10 a 13 renumeradas a 11 a 14.
- **Rama:** `feature/protocolo-telemetria-imu` (desde `develop`).
- **Pendiente:** descartar en el servidor las muestras repetidas tras una reconexión (§10.5, punto 4); probar el formato con la placa contra la App;
  implementar `0x8006` cuando se adopte CBOR (el ejemplo `set_hora` de `protocol-cbor.md` codifica −180 como `18 B5`; lo correcto es `38 B3`).

### 2026-11-05 — Sesión 10: Plan de la consola remota estilo SSH
- **Objetivo (pedido del usuario):** simular una consola SSH por WebSocket (sin seguridad por ahora): el ESP se conecta al servidor como ya lo hace (puerto seleccionable), y desde la PC se envían comandos que el ESP responde, con una pestaña nueva de consola en la GUI.
- **Corrección del usuario:** los comandos **no son JSON**: son texto plano tipo CLI (`server`, `pass set <password>`, `pass get`). El plan se ajustó: sin envelope, sin `id`/`eof`; respuestas también en texto plano impreso verbatim.
- **Resultado:** creado [plans/consola-ssh-plan.md](consola-ssh-plan.md) con:
  - Protocolo de texto plano: la App envía el comando tal cual + `\n` final; el ESP responde con frames de texto que se imprimen verbatim; prompt `esp32> ` re-mostrado tras cada respuesta (consola sin bloqueo).
  - Decisiones D1-D7: texto plano sin envoltorio, `\n` agregado por la App, sin ACK por `seq` para la consola, enrutamiento por tipo de frame en el worker (JSON válido → pipeline de telemetría intacto; texto plano → consola), selector de destino por peer + broadcast, envío thread-safe con `run_coroutine_threadsafe`.
  - Cambios por capa: `ClientRegistry.send_to()/peers()/resolve()`, `WebSocketServer.send_console_line()`, `ServerWorker.send_command()` + señal `console_output`, `QTabWidget` con pestañas Telemetría/Consola y nuevo `ConsolePanel` (historial ↑/↓, eco local, límite de líneas), config `echo_local`.
  - Plan de 8 pasos (Paso 0 rama → Paso 7 QA), riesgos con mitigaciones (respuesta JSON que cae en Telemetría → convención CLI texto plano) y escalamientos futuros (TLS/auth, marcador de fin, CBOR, autocompletado).
  - Fase **5b** agregada al roadmap y decisión registrada en §2 (estado: propuesta).
- **Rama prevista:** `feature/consola-ssh` (desde `develop`).
- **Pendiente:** aprobación del usuario del plan; luego implementar según los pasos 0-7.

### 2026-11-05 — Sesión 11: Implementación de la consola remota (Fase 5b)
- **Objetivo:** implementar el plan aprobado de la sesión 10: consola estilo SSH (texto plano) en una pestaña nueva, sin tocar la telemetría ni el puerto configurable.
- **Resultado (rama `feature/consola-ssh`):**
  - [`network/client_registry.py`](../src/imop/network/client_registry.py): `peer_label()`, `peers()`, `resolve()`, `send_to()`; `on_change` ahora entrega la **lista de peers** (`BROADCAST_TARGET` como etiqueta de difusión).
  - [`network/server.py`](../src/imop/network/server.py): `send_console_line(text, peer)` normaliza el comando (recorta espacios finales, agrega un `\n`), envía dirigido o en broadcast y avisa si el peer no está conectado.
  - [`gui/workers.py`](../src/imop/gui/workers.py): `send_command()` thread-safe con `run_coroutine_threadsafe`, señal `console_output` y enrutamiento en `_handle_raw` (pre-parseo: JSON → pipeline intacto, texto plano → consola).
  - [`gui/panels/console_panel.py`](../src/imop/gui/panels/console_panel.py) (nuevo): salida `QPlainTextEdit` (tope 5000 bloques), prompt `esp32>`, historial ↑/↓, selector de destino (persiste selección; default = primer cliente), eco local, "Limpiar".
  - [`gui/main_window.py`](../src/imop/gui/main_window.py): `QTabWidget` con pestañas **Telemetría** (todo lo previo, sin cambios) y **Consola**; wiring `send_requested` ↔ `send_command` y `console_output` ↔ panel; persiste `console_echo` y `last_tab` ([config.py](../src/imop/config.py)).
  - Tests nuevos: 6 de red (texto sin ACK, peers/resolve, broadcast con `\n`, dirigido, peer desconocido, lista de peers en `on_clients_changed`), 3 de config y 7 de GUI (enrutamiento del worker, panel con historial/destino/salida, **E2E** con worker real: comando → cliente eco → respuesta → señal de consola). **Total: 57 passed**, ruff ✓, ruff format ✓, mypy ✓.
  - Docs: [docs/user/protocol.md](../docs/user/protocol.md) **v1.2** (§15 consola remota + sketch Arduino de referencia), [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) §4.3 (diagrama de secuencia del flujo bidireccional), [docs/user/faq.md](../docs/user/faq.md) (paso a paso y diagnóstico) y README.
- **Correcciones durante la implementación:**
  - Bug detectado por el test de peer desconocido: `send_console_line` caía en broadcast cuando el peer no existía → ahora devuelve 0 con log WARNING.
  - El enrutamiento no podía depender de que el pipeline lance `MessageParseError` (el pipeline convierte JSON inválido en mensaje de ERROR): se pre-parsea en el worker.
  - Las señales Qt entre hilos requieren `processEvents()` en el test E2E (encoladas al hilo principal).
- **Commits:** `feat(network)`, `feat(gui)` + `docs` de la sesión, sobre `feature/consola-ssh`.
- **Pendiente:** prueba manual del usuario con un ESP32 real (CLI `server` / `pass set` / `pass get`); capturas de la pestaña Consola para el manual; TLS/autenticación como escalamiento futuro.

---

## 5. Convenciones transversales

- **Protocolo de mensajes ESP32 → App:** JSON con clave raíz identificadora, p. ej.
  `{"sensor_temp": {"value": 23.4, "unit": "C"}}` → el filtro `sensor_` lo captura.
- **Idioma del código:** identificadores en inglés, comentarios/DOCs en español.
- **Toda nueva fase debe registrarse aquí antes de implementarse.**
