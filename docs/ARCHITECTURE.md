# Arquitectura y Estructura del Proyecto — i-mop-websocket

> **Regla:** la estructura de carpetas definida aquí es el mapa de trabajo. Todo módulo nuevo debe encajar en ella; si no encaja, primero se discute y se actualiza este documento.

## 1. Arquitectura general

```mermaid
flowchart TB
    subgraph GUI[Capa GUI - PySide6 - hilo Qt]
        MW[MainWindow] --> PV[MessagePanel - panel inferior con colores]
        MW --> FP[FilterPanel - 5 filtros]
        MW --> SP[ServerPanel - puerto y estado]
        MW --> LP[LogSettingsPanel - guardar logs on/off]
    end

    subgraph Core[Capa de dominio - hilo worker asyncio]
        WS[WebSocketServer - websockets asyncio]
        JP[JsonParser / validador]
        FM[FilterManager - 5 filtros por prefijo]
        LH[LogHandlers - archivo por filtro]
    end

    subgraph IO[Salidas]
        LG[logs/*.log]
        SCR[Pantalla - panel inferior]
    end

    ESP[ESP32 cliente WebSocket] -->|JSON| WS
    WS --> JP --> FM
    FM -->|coincide y logs activos| LH --> LG
    FM -->|pasa filtros visuales| SCR
    Core <-->|Signals Qt thread-safe| GUI
    GUI -->|comandos futuros: teclas| WS --> ESP
```

Decisiones clave:

- **Red en hilo aparte**: asyncio corre en un worker thread; se comunica con Qt mediante señales (`Signal(dict)`), nunca tocando widgets desde otro hilo.
- **Dominio puro**: `FilterManager` y el parser son clases sin dependencias de Qt ni red → 100 % testeables.
- **Un solo flujo de datos**: todo mensaje entrante pasa por `parse → filter → (log + display)`.

## 2. Estructura de carpetas

```text
i-mop-websocket/
├── README.md
├── CHANGELOG.md                  # Historial de releases (Keep a Changelog)
├── pyproject.toml                # Metadatos, dependencias, tooling (PEP 621)
├── .gitignore
├── .pre-commit-config.yaml
├── imop.spec                     # Spec de PyInstaller (generada y versionada)
├── plans/                        # Plan de acción y registro IA
│   └── action-plan.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CODING_STANDARDS.md
│   ├── DOCUMENTATION_RULES.md
│   ├── GIT_WORKFLOW.md
│   ├── BUILD_AND_DEPLOYMENT.md
│   └── user/                     # Documentación para usuarios finales
│       ├── manual.md
│       ├── faq.md
│       └── protocol.md
├── src/
│   └── imop/
│       ├── __init__.py           # __version__, logger raíz
│       ├── __main__.py           # python -m imop
│       ├── app.py                # Punto de entrada: QApplication + bootstrap
│       ├── cli.py                # argparse: --port, --log-dir, --no-gui (futuro)
│       ├── config.py             # Carga/guardado de configuración (JSON, escritura atómica)
│       ├── constants.py          # DEFAULT_PORT, MAX_FILTERS = 5, colores por tipo
│       ├── theme.py              # Color estable por clave raíz (módulo puro, sin Qt)
│       ├── core/                 # Dominio puro (sin Qt, sin red)
│       │   ├── models.py         # JsonPayload, FilterRule, DisplayMessage, ServerStatus
│       │   ├── parser.py         # Validación y normalización de JSON
│       │   ├── filters.py        # FilterManager: matching por prefijo
│       │   └── pipeline.py       # MessagePipeline: parseo → filtros → logs → display
│       ├── network/
│       │   ├── server.py         # WebSocketServer (asyncio + websockets)
│       │   ├── discovery.py      # ServiceAnnouncer: anuncio mDNS/Zeroconf del servicio
│       │   └── client_registry.py# Clientes conectados + broadcast (base del envío futuro)
│       ├── logging_service/      # (no "logging": evita ambigüedad con el stdlib)
│       │   └── handlers.py       # FilterLogManager: RotatingFileHandler por filtro
│       └── gui/
│           ├── main_window.py    # MainWindow
│           ├── panels/
│           │   ├── server_panel.py
│           │   ├── message_panel.py
│           │   ├── filter_panel.py
│           │   └── log_settings_panel.py
│           ├── workers.py        # WorkerThread: puente asyncio <-> Qt signals
│           ├── theme.py          # Paleta de colores por tipo de mensaje
│           └── resources/        # Iconos, logos
├── tests/
│   ├── conftest.py
│   ├── unit/                     # core/filters, core/parser, config
│   ├── network/                  # servidor con cliente mock (websockets test utils)
│   └── gui/                      # smoke tests con pytest-qt
└── scripts/
    ├── build_windows.bat         # PyInstaller -> dist/Imop.exe
    ├── build_linux.sh
    └── build_macos.sh
```

Notas de estructura:

- Layout **`src/`**: evita importar el paquete sin instalarlo; obliga a probar la versión instalada (`pip install -e .`).
- `imop/core/` **no importa** `PySide6` ni `websockets` → pruebas unitarias rápidas y puras.
- El nombre del ejecutable y del paquete: `imop` / `Imop.exe`.

## 3. Entornos virtuales por plataforma

Un único `pyproject.toml`; el venv se crea localmente en cada sistema:

| SO | Comando de creación | Activación |
|----|--------------------|------------|
| Windows | `python -m venv .venv` | `.venv\Scripts\activate` |
| Linux | `python3 -m venv .venv` | `source .venv/bin/activate` |
| macOS | `python3 -m venv .venv` | `source .venv/bin/activate` |

Instalación (idéntica en los 3 SO): `pip install -e .[dev]`.

> **Alternativa recomendada:** usar [`uv`](https://docs.astral.sh/uv/) (`uv sync`) — más rápido y con lockfile reproducible (`uv.lock` versionado). Decisión final en Fase 1.

### Dependencias previstas

| Paquete | Rol |
|---------|-----|
| `PySide6` | GUI |
| `websockets` | Servidor WebSocket asyncio |
| `zeroconf` | Anuncio mDNS/Zeroconf del servidor en la red local |
| `pyinstaller` *(dev)* | Empaquetado |
| `pytest`, `pytest-qt`, `pytest-asyncio`, `ruff`, `mypy`, `pre-commit` *(dev)* | Calidad |

## 4. Flujo de un mensaje (secuencia)

```mermaid
sequenceDiagram
    participant ESP as ESP32
    participant WS as WebSocketServer
    participant JP as Parser
    participant FM as FilterManager
    participant LG as LogHandlers
    participant QT as WorkerThread Signal
    participant UI as MessagePanel

    ESP->>WS: frame JSON
    WS->>JP: text
    JP-->>WS: JsonPayload valido
    WS->>FM: payload
    FM-->>LG: filtros coincidentes
    LG-->>LG: escribe en logs si activo
    FM-->>QT: pasa filtros visuales
    QT->>UI: signal message_received
    UI->>UI: pinta fila con color y timestamp
```

### 4.1 Protocolo de confirmación (ACK por `seq`)

Si el mensaje del cliente incluye un campo `"seq"` **entero**, el servidor responde
en la misma conexión después de procesarlo:

| Mensaje del cliente | Respuesta del servidor |
|---------------------|------------------------|
| `{"seq": 7, "sensor_temp": {"value": 23.4}}` | `{"ack_seq": 7, "status": "ok"}` |
| `{"seq": 8, ...}` con fallo interno del callback | `{"ack_seq": 8, "status": "error"}` |
| Mensaje sin `seq`, o con `seq` no entero | *(sin respuesta — retrocompatible)* |
| Frame no parseable como JSON (texto plano) | *(sin respuesta — va a la consola remota, §4.3)* |

Implementación: [`network/server.py`](../src/imop/network/server.py) (`_extract_seq` / `_send_ack`).
El ESP32 puede usar el `status` del ACK para retransmitir mensajes perdidos.

### 4.2 Descubrimiento automático del servidor (mDNS / Zeroconf)

Para evitar configurar a mano la IP del PC en cada ESP32, la app puede **anunciar** el
servidor WebSocket en la red local mediante mDNS (Bonjour / Zeroconf / Avahi):

| Aspecto | Valor |
|---------|-------|
| Servicio anunciado | `_imop._tcp.local.` |
| Nombre de instancia | `i-mop-<hostname>` (p. ej. `i-mop-DESKTOP-UDO7SS5.local.`) |
| Puerto anunciado | el puerto configurado del servidor |
| TXT records | `proto=ws`, `app=imop` |
| Biblioteca | [`zeroconf`](https://github.com/python-zeroconf/python-zeroconf) |

- Activación: checkbox **"Anunciar servicio en la red (mDNS/Zeroconf)"** en el panel
  *Servidor WebSocket* (persistido en la configuración como `announce_enabled`).
- El anuncio arranca/para junto con el servidor y se cierra limpiamente al salir.
- El ESP32 (rol de **cliente** que descubre) usa `ESPmDNS`:

```cpp
#include <ESPmDNS.h>
// ...
if (MDNS.begin("esp32-sensor")) {
    int n = MDNS.queryService("imop", "tcp");   // busca "_imop._tcp"
    if (n > 0) {
        String host = MDNS.hostname(0);          // p. ej. "DESKTOP-UDO7SS5"
        uint16_t port = MDNS.port(0);            // p. ej. 1001
        // conectar a host.local / IP resuelta
    }
}
```

Implementación: [`network/discovery.py`](../src/imop/network/discovery.py)
(`ServiceAnnouncer`, `default_instance_name`, `SERVICE_TYPE`).

> ⚠️ Limitaciones: el multicast mDNS solo funciona dentro del **mismo segmento de red**
> (no atraviesa routers/AP con aislamiento de clientes) y requiere UDP **5353** abierto
> en el firewall. Si falla, es solo un error logueado: el anuncio es opcional y el
> servidor funciona igual sin él (conexión directa por IP siempre disponible).

### 4.3 Consola remota bidireccional (texto plano)

La app incorpora una pestaña **"Consola"**: comandos de texto plano estilo CLI
(`server`, `pass set <password>`, `pass get`...) que viajan por la **misma conexión**
y puerto ya existentes, con la respuesta del ESP32 impresa verbatim.

```mermaid
sequenceDiagram
    participant UI as ConsolePanel (Consola)
    participant QT as ServerWorker
    participant WS as WebSocketServer
    participant ESP as ESP32

    UI->>QT: send_command("pass get", peer)  [run_coroutine_threadsafe]
    QT->>WS: send_console_line("pass get\\n")
    WS->>ESP: frame de texto (comando + \\n)
    ESP-->>WS: frame de texto (respuesta, texto plano)
    WS->>QT: on_message(raw)
    QT->>QT: parse_message falla → no es JSON
    QT->>UI: signal console_output(raw)
    UI->>UI: imprime verbatim con timestamp
```

- **Enrutamiento por tipo de frame** en [`gui/workers.py`](../src/imop/gui/workers.py)
  (`_handle_raw`): JSON válido → pipeline de telemetría (§4, sin cambios); cualquier
  otro texto → consola. Convención: el CLI del ESP responde **solo texto plano**
  ([docs/user/protocol.md](user/protocol.md) §15).
- **Envío thread-safe:** `ServerWorker.send_command()` publica en el loop asyncio del
  hilo worker con `asyncio.run_coroutine_threadsafe`; la GUI nunca bloquea esperando
  la respuesta.
- **Destino:** [`network/client_registry.py`](../src/imop/network/client_registry.py) expone
  `peers()`, `resolve()` y `send_to()`; la consola elige un cliente puntual o difunde a
  todos (`WebSocketServer.send_console_line`, que agrega el `\n` final).
- **Panel:** [`gui/panels/console_panel.py`](../src/imop/gui/panels/console_panel.py)
  (salida con `QPlainTextEdit`, tope de 5000 líneas, historial ↑/↓, selector de destino,
  eco local configurable).

## 5. Configuración persistente

- Ubicación: perfil de usuario (portable-friendly) — `QSettings("imop", "i-mop-websocket")` o `~/.imop/config.json`.
- Contenido: puerto, 5 filtros (nombre + habilitado), carpeta de logs, flag "guardar logs", atajos de teclas (futuro).
- Escritura atómica (temporal + rename) para evitar corrupción.

## 6. Estrategia de pruebas

| Capa | Herramienta | Qué se prueba |
|------|-------------|---------------|
| `core/` | pytest unitario | Prefijos, JSON inválido, mayúsculas/minúsculas, payload vacío |
| `network/` | pytest-asyncio + cliente mock | Conexión, desconexión, mensajes malformados, múltiples clientes |
| `gui/` | pytest-qt | Panel recibe señal, filtros aplican en pantalla, límite de filas |
| E2E manual | ESP32 / `wscat` | Checklist por release |

## 7. Extensibilidad futura (envío de teclas)

- `ClientRegistry` ya contempla múltiples clientes: el panel de teclas futuras solo necesita `registry.broadcast(json)` (o `send_to()` ya implementados para la consola).
- Los atajos se definirán en configuración como pares *(tecla → JSON)*, renderizados como botones configurables (generados desde el registro de comandos).
- **Protocolo definido:** comandos por JSON-RPC 2.0 (subconjunto) y archivos por frames binarios → ver [docs/user/protocol.md](user/protocol.md) (v1.0). Toda extensión debe seguir sus reglas.
- **Consola remota: implementada** (§4.3) sobre `send_to()`/`broadcast()`; TLS/autenticación queda como escalamiento ([docs/user/protocol.md](user/protocol.md) §15.4).
