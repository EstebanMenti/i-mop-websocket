# Plan — Consola remota estilo SSH sobre WebSocket

> **Regla:** este documento planifica la funcionalidad "consola SSH simulada" para i-mop-websocket: enviar comandos de **texto plano** desde la PC al ESP32 por la conexión WebSocket existente y ver sus respuestas en una pestaña nueva de la GUI. Sin seguridad (sin TLS ni autenticación) por ahora; quedará registrado como escalamiento futuro.

---

## 1. Objetivo y alcance

- **Objetivo:** desde la PC (servidor), escribir comandos de texto que viajan por el WebSocket al ESP32 conectado; el ESP los ejecuta con su intérprete propio (p. ej. `server`, `pass set <password>`, `pass get`) y responde; las respuestas se muestran en una consola estilo terminal dentro de la GUI.
- **Se mantiene tal cual:** el puerto configurable del servidor, la conexión del ESP como cliente, la telemetría JSON existente, los filtros, los logs y el mDNS. La consola convive en **la misma conexión y el mismo puerto** (no se abre ningún socket extra).
- **Fuera de alcance (esta entrega):** TLS/WSS, autenticación, múltiples sesiones por cliente, redirección de archivos, soporte CBOR para la consola (queda para el protocolo v2).

## 2. Decisiones de diseño

| # | Decisión | Motivo |
|---|----------|--------|
| D1 | **Comandos como frames de texto plano** (no JSON): lo que escribe el usuario viaja tal cual, sin envoltorio | El intérprete del ESP ya espera líneas de texto (estilo CLI: `server`, `pass set <pass>`, `pass get`); JSON agregaría parseo del lado del ESP para nada |
| D2 | **Respuestas como texto plano**: cada respuesta del ESP es un frame de texto que se imprime verbatim en la consola | Simétrico al comando; el ESP imprime su salida como lo haría por Serial. Sin marcador de fin: la App re-muestra el prompt después de cada frame de respuesta |
| D3 | **La App agrega `\n` al final de cada comando** (comportamiento por defecto) | Los intérpretes línea-a-línea del ESP esperan un salto de línea; el usuario nunca lo escribe |
| D4 | **Sin ACK del servidor para frames de consola**: texto plano no lleva `seq`, así que el mecanismo `ack_seq` existente no se dispara | El ACK por `seq` sigue funcionando solo para telemetría JSON, sin cambios |
| D5 | **Enrutamiento por tipo de frame en el worker**: frame con **JSON válido** → pipeline actual (telemetría, filtros, logs); **cualquier otro frame de texto** → consola | Un solo punto de decisión ([`workers.py`](../src/imop/gui/workers.py)); la telemetría no ensucia la consola y la salida de la consola no dispara filtros/logs. Convención: el intérprete del ESP imprime texto plano (no JSON) en sus respuestas |
| D6 | **Selector de destino**: combo con los clientes conectados (por `host:puerto` remoto) + opción "Todos (broadcast)" | Ya existe `ClientRegistry.broadcast()`; se agrega `send_to()` para apuntar a un cliente puntual |
| D7 | **Envío thread-safe**: método `send_command()` en [`ServerWorker`](../src/imop/gui/workers.py) que hace `asyncio.run_coroutine_threadsafe()` contra el loop del hilo worker | La GUI (hilo Qt) nunca toca el loop asyncio directamente |

## 3. Protocolo de la consola

### 3.1 Comando (PC → ESP): texto plano

```
pass set miclave123
```

- El frame WebSocket de texto contiene **exactamente el texto del comando**, sin envoltorio JSON ni secuencias de escape.
- La App agrega `\n` al final (D3) antes de enviar.
- Comandos de ejemplo del intérprete del ESP: `server`, `pass set <password>`, `pass get`.

### 3.2 Respuesta (ESP → PC): texto plano, uno o varios frames

```
OK
```

- Cada frame de texto recibido se imprime tal cual en la salida de la consola (con timestamp local tenue).
- Los `\n` que envíe el ESP se respetan; la salida puede llegar partida en varios frames.
- Después de cada frame de respuesta la App re-muestra el prompt `esp32> ` (no hay marcador de fin de respuesta; la consola nunca bloquea).

### 3.3 Convivencia con la telemetría (misma conexión)

| Frame entrante | Destino en la App |
|----------------|-------------------|
| Texto plano (no-JSON) | **Consola** (pestaña nueva) |
| JSON válido (telemetría, p. ej. `{"sensor_temp": ...}` o IMU) | Pipeline actual: filtros, logs y panel de mensajes (sin cambio) |

- Regla para el firmware: el intérprete de la consola responde **solo texto plano**; la telemetría sigue siendo JSON. Así el enrutamiento (D5) es inequívoco.
- El ACK `{"ack_seq": ...}` del servidor a telemetría no cambia; los frames de consola (sin `seq`) no generan ACK.

### 3.4 Ejemplo mínimo de firmware (referencia para el ESP32)

```cpp
// Pseudocódigo Arduino: el handler de texto ya existente solo debe
// tratar el frame como línea de comando del intérprete CLI.
void onTextFrame(WebSocket ws, String line) {   // line ya sin "\n"
  String out = cliExec(line);                   // intérprete propio: server, pass set/get...
  ws.send(out);                                 // respuesta en texto plano
}
```

El ejemplo completo (con el CLI de ejemplo `server` / `pass set` / `pass get`) se documentará en [docs/user/protocol.md](../docs/user/protocol.md) al implementar.

## 4. Cambios por capa

### 4.1 Red — [`network/client_registry.py`](../src/imop/network/client_registry.py) y [`network/server.py`](../src/imop/network/server.py)

1. `ClientRegistry.send_to(connection, text) -> bool`: envío dirigido a una conexión; descarta clientes muertos (misma política que `broadcast()`).
2. `ClientRegistry.peers() -> list[str]`: lista legible de `host:puerto` remotos (para el combo de destino de la GUI).
3. `ClientRegistry.resolve(peer: str) -> connection | None`: traduce la etiqueta del combo a la conexión (o `None` = broadcast).
4. `WebSocketServer.send_console_line(text: str, peer: str | None) -> int`: agrega `\n` si falta y envía el texto al destino; devuelve cuántos clientes recibieron el frame. Sin validación de contenido (es texto libre).
5. `on_clients_changed` pasa de `count: int` a la **lista de peers** (señal Qt `clients_changed(list)`); la cantidad es `len(lista)` donde se necesite.

### 4.2 Worker — [`gui/workers.py`](../src/imop/gui/workers.py)

1. `ServerWorker.send_command(cmd: str, peer: str | None)`: thread-safe; publica en el loop con `run_coroutine_threadsafe` llamando a `send_console_line` (el `\n` lo agrega la capa de red, D3).
2. Señal nueva `console_output = Signal(str)` con el texto crudo recibido.
3. En `_handle_raw`: **si el frame es JSON válido** → pipeline actual (flujo intacto); **si no** → emitir `console_output`. El ACK por `seq` se decide antes, como hoy (solo aplica a JSON con `seq`).
4. Señal `clients_changed` pasa a emitir la lista de peers.

### 4.3 GUI — [`gui/main_window.py`](../src/imop/gui/main_window.py) y nuevo [`gui/panels/console_panel.py`](../src/imop/gui/panels/console_panel.py)

1. `MainWindow._build_ui()`: envolver el contenido actual en un `QTabWidget`:
   - **Pestaña 1 — "Telemetría"**: paneles actuales (servidor, filtros, logs, mensajes).
   - **Pestaña 2 — "Consola"**: el nuevo `ConsolePanel`.
2. `ConsolePanel` (nuevo panel):
   - Salida: `QPlainTextEdit` read-only con timestamps tenues; texto del comando enviado en color distintivo (verde), respuestas en color normal (blanco/negro), todo texto plano verbatim con auto-scroll.
   - Prompt: línea `esp32> ` + `QLineEdit` con **historial de comandos** (flechas ↑/↓, persistente en memoria durante la sesión).
   - Destino: `QComboBox` con peers conectados + "Todos (broadcast)"; se rellena con `clients_changed`.
   - Botones: **Enviar** (también con Enter), **Limpiar**, checkbox **Eco local** (mostrar el comando en la salida; default activado).
   - Re-imprimir el prompt `esp32> ` después de cada frame de respuesta (D2); sin estado de "esperando respuesta" (la consola nunca bloquea).
   - Límite de líneas en la salida (mismo enfoque que `MessagePanel`, ~5000 líneas) para no inflar memoria.
3. `MainWindow`: conectar `console_panel.send_requested(cmd, peer)` → `worker.send_command(...)`; `worker.console_output` → `console_panel.append_output(...)`; `worker.clients_changed` → combo + label de clientes del `ServerPanel`.
4. Indicador en la pestaña: título "Consola" con contador de clientes activos (opcional, barato con la señal existente).

### 4.4 Config — [`config.py`](../src/imop/config.py)

- Persistir solo `echo_local: bool` y la última pestaña activa. El resto (historial, salida) es efímero.

## 5. Plan de implementación (pasos de la entrega)

- [x] **Paso 0 — Rama:** crear `feature/consola-ssh` (según [GIT_WORKFLOW.md](../docs/GIT_WORKFLOW.md)).
- [x] **Paso 1 — Red:** `send_to()`, `peers()`, `resolve()`, `WebSocketServer.send_console_line()` (agrega `\n`) + tests de red (cliente eco real con `websockets`; envío dirigido, broadcast y peer desconocido).
- [x] **Paso 2 — Worker:** `send_command()`, señal `console_output`, enrutamiento JSON→pipeline / no-JSON→consola (pre-parseo en el worker), `clients_changed` con lista de peers + tests del worker y **test E2E** con worker real.
- [x] **Paso 3 — GUI:** `QTabWidget` en `MainWindow` (pestaña Telemetría sin cambios de comportamiento) + `ConsolePanel` completo + wiring de señales + smoke tests GUI offscreen.
- [x] **Paso 4 — Config y persistencia:** `console_echo`, `last_tab`; tests de config.
- [x] **Paso 5 — Firmware de referencia:** sketch mínimo del ESP32 (CLI `server` / `pass set <p>` / `pass get`) en [docs/user/protocol.md](../docs/user/protocol.md) §15 (protocolo **v1.2**).
- [x] **Paso 6 — Docs:** [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) §4.3 (diagrama de flujo bidireccional), [docs/user/faq.md](../docs/user/faq.md) (uso y diagnóstico), README.
- [x] **Paso 7 — QA y registro:** ruff ✓, ruff format ✓, mypy ✓, pytest **57 passed**; [plans/action-plan.md](action-plan.md) actualizado (fase 5b completada, Sesión 11).

> **Nota de implementación (2026-11-05):** el prompt `esp32> ` se muestra como eco del comando enviado (en verde) y el selector de destino usa `blockSignals` al rellenar el combo para no duplicar señales. Detalles en la [Sesión 11](action-plan.md).

## 6. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| La GUI se congela esperando la respuesta del ESP | Envío **sin esperar** respuesta: `run_coroutine_threadsafe` solo publica el frame; la respuesta llega por la señal `console_output` |
| El ESP envía una respuesta en JSON y aparece en Telemetría en vez de la Consola | Convención documentada (D5): el CLI del ESP responde texto plano. El routing es determinista: JSON → telemetría, texto → consola |
| Comando sin respuesta (el ESP no lo soporta) | La consola no bloquea nunca; el usuario puede seguir escribiendo; el prompt se re-muestra tras cada frame o al enviar el próximo comando |
| Varios ESP conectados responden a la vez con broadcast | Default del combo = primer cliente; broadcast es elección explícita del usuario |
| Espacios/`\n` de más en el input | La App recorta espacios en los extremos y agrega exactamente un `\n` final (D3) |
| Frames binarios mezclados | El handler ya los ignora con log DEBUG (sin cambio) |

## 7. Escalamientos futuros (fuera de esta entrega)

- Seguridad: TLS (wss://) y token de autenticación en el handshake.
- Marcador de fin de respuesta opcional (p. ej. línea `OK`/`ERROR` del CLI) para prompt más preciso.
- Consola CBOR (protocolo v2) si se necesita ahorro de bytes.
- Autocompletado de comandos conocidos del CLI del ESP.
- Historial persistente de comandos entre sesiones.
