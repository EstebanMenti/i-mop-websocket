# Protocolo de comunicación i-mop — App ⇄ ESP32

> **Versión del protocolo:** 1.0 (borrador de referencia)
> **Fecha:** 2026-10-29 · **Estado:** Definido, pendiente de implementación (Fase 5)
>
> **Regla de oro:** todo comando o mecanismo nuevo **debe** ajustarse a este documento.
> Si no encaja, primero se discute y se actualiza aquí; después se implementa.

---

## 1. Principios

1. **Un solo canal, dos tipos de frame.** Todo viaja por la conexión WebSocket ya existente:
   - Frames de **texto**: comandos, respuestas, telemetría (JSON en UTF-8).
   - Frames **binarios**: exclusivamente datos de transferencia de archivos (bytes crudos).
2. **Base: JSON-RPC 2.0 en subconjunto.** Formato estandarizado, bidireccional y correlacionado por `id`.
3. **Siempre responder.** Toda petición con `id` recibe respuesta (`result` o `error`), incluso ante error interno. Una petición sin respuesta es un bug del protocolo.
4. **Retrocompatible por diseño.** Campos desconocidos se ignoran; métodos desconocidos responden error sin romper la conexión.
5. **Nombres en `snake_case`**, minúsculas, sin espacios ni acentos. El vocabulario de comandos es en **español** (coherente con el dominio del proyecto).
6. **Los datos son chicos y verificables.** Timestamps en epoch UTC, checksums CRC32 en archivos, tamaños explícitos. Nada se infiere.

## 2. Tipos de mensaje

| Tipo | Dirección | Frame | ¿Lleva `id`? | ¿Espera respuesta? |
|------|-----------|-------|--------------|--------------------|
| **Request** (comando) | App → ESP32 (y a futuro, inverso) | Texto JSON | Sí | Sí, siempre |
| **Response** (resultado o error) | Quien recibió el request → emisor | Texto JSON | Sí (el mismo `id`) | No |
| **Notification** (telemetría) | ESP32 → App | Texto JSON | No | No (la App confirma con ACK por `seq`) |
| **Binary chunk** (datos de archivo) | Ambos sentidos | Binario | No (identificado por la transferencia en curso) | No (validación al cierre) |

## 3. Sobre (envelope) de los frames de texto

### 3.1 Request

```json
{"jsonrpc": "2.0", "id": 1, "method": "set_hora", "params": {"epoch": 1795347930, "tz_offset": -180}}
```

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `jsonrpc` | string | Sí | Siempre `"2.0"` (identifica el sobre) |
| `id` | entero ≥ 1 | Sí en requests | No reutilizar mientras esté pendiente |
| `method` | string | Sí | Ver §5 |
| `params` | objeto | Sí | **Siempre objeto**, nunca array. Puede ser `{}` si no hay parámetros |

### 3.2 Response — éxito

```json
{"jsonrpc": "2.0", "id": 1, "result": {"ok": true}}
```

La presencia de `result` indica éxito. `result` es **siempre un objeto** (nunca escalar ni `null`), así extender la respuesta no rompe parsers.

### 3.3 Response — error

```json
{"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "metodo desconocido", "data": "get_ubw"}}
```

| Campo | Regla |
|-------|-------|
| `code` | Entero de la tabla de §7 |
| `message` | Breve, en inglés o español, sin tildes, una línea |
| `data` | Opcional: detalle (valor rechazado, nombre de archivo, etc.) |

`result` y `error` son **mutuamente excluyentes**.

### 3.4 Notification (telemetría ESP32 → App)

```json
{"seq": 42, "sensor_temp": {"value": 23.4, "unit": "C"}}
```

- Sin `jsonrpc` ni `id`: no espera respuesta.
- La clave **raíz** identifica el tipo de dato (misma regla que usan los filtros de la GUI).
- La App confirma su recepción con el ACK por `seq` ya implementado: `{"ack_seq": 42, "status": "ok"}`.

## 4. Asignación de identificadores

| Identificador | Ámbito | Regla |
|---------------|--------|-------|
| `id` de request | Por conexión | Contador incremental del emisor, comienza en **1**. La App usa `1, 2, 3, …`; si en el futuro el ESP32 inicia requests hacia la App, usará el rango reservado **≥ 1000000** (evita colisiones) |
| `seq` de telemetría | Por conexión | Contador uint32 del ESP32, arranca en 1 al conectar; se reinicia en cada reconexión |
| `transfer` de archivo | Por conexión | String `"t" + contador` (`"t1"`, `"t2"`…), lo asigna quien inicia la transferencia |

- Un `id` no se reutiliza hasta recibir su respuesta o vencer el timeout (3 s por defecto).
- El `id` es opaco para el receptor: se devuelve **intacto**, sin interpretarlo.

## 5. Nomenclatura de métodos

Formato: `verbo_objeto[_detalle]` en `snake_case`, máximo 3 segmentos.

**Verbos permitidos (conjunto cerrado):**

| Verbo | Significado |
|-------|-------------|
| `get` | Lee el valor actual, **no modifica estado** |
| `set` | Escribe/configura un valor |
| `do` | Ejecuta una acción puntual (no idempotente) |
| `list` | Devuelve una colección (paginable) |
| `sub` / `unsub` | (Reservado) suscripción a eventos |

| ✅ Correcto | ❌ Incorrecto — por qué |
|-------------|--------------------------|
| `get_hora` | `GetHora` — mayúsculas |
| `set_uwb` | `uwb_set` — verbo no primero |
| `sd_list` | `listar_archivos_sd` — vocabulario fuera del conjunto |
| `file_cancel` | `cancelar_file` — mezcla de idiomas en la misma convención |

## 6. Convención de parámetros (`params`)

| Tipo de dato | Convención | Ejemplo |
|--------------|-----------|---------|
| Timestamp | `epoch` (uint32, segundos UTC) + `tz_offset` (minutos, opcional) | `{"epoch": 1795347930, "tz_offset": -180}` |
| MAC address | String hex, 6 pares separados por `:`, mayúsculas | `"1A:2B:3C:4D:5E:6F"` |
| Ruta de archivo | POSIX: separador `/`, absoluta empieza con `/`, **nunca** contiene `..` | `"/logs/data.csv"` |
| Tamaños | Siempre en **bytes**, campo `*_size` o `size` | `"size": 15230` |
| Duraciones | Segundos, campo `*_s` o sufijo de unidad explícito | `"uptime_s": 3600` |
| Enum | String minúscula sin espacios | `"role": "anchor"` |

- Parámetro desconocido → **se ignora** (permite extender sin romper versiones anteriores).
- Parámetro obligatorio faltante o inválido → error `-32602` con el nombre del parámetro en `data`.
- Todo parámetro con rango acotado (índices, tamaños) se valida antes de ejecutar la acción.

## 7. Códigos de error

| Código | Nombre | Uso |
|--------|--------|-----|
| `-32700` | Parse error | El frame no es JSON válido |
| `-32600` | Invalid request | JSON válido pero el sobre no cumple el protocolo (falta `method`, `params` no es objeto, etc.) |
| `-32601` | Method not found | El método no existe en el receptor |
| `-32602` | Invalid params | Falta un parámetro obligatorio o está fuera de rango |
| `-32603` | Internal error | Fallo interno no clasificado |
| `-32000` | Hardware error | Error de hardware/I/O genérico |
| `-32001` | SD not mounted | Tarjeta SD no disponible |
| `-32002` | File not found | Ruta inexistente |
| `-32003` | CRC mismatch | Checksum de transferencia inválido |
| `-32004` | Transfer busy | Ya hay una transferencia en curso |
| `-32005` | Not initialized | El subsistema pedido (UWB, RTC…) no está inicializado |

Reglas: los códigos `-326xx` son los estándar de JSON-RPC 2.0 (no redefinir). Los códigos de aplicación van en el rango `-32000 … -32099` y **se agregan solo a este documento**.

## 8. Handshake y versionado

Al conectar, el ESP32 envía como primera notification:

```json
{"seq": 1, "hello": {"proto": 1, "device": "imop-uwb", "fw": "1.2.0"}}
```

- `proto`: versión de este protocolo (entero). Cambios **aditivos** (comandos/campos nuevos) → mismo `proto` mayor. Cambios incompatibles → nuevo mayor y este documento se versiona junto.
- La App registra `hello` en la GUI (tipo de dispositivo y firmware visible en la lista de clientes).
- Si `hello` no llega en 5 s, la App igual acepta la conexión (modo degradado, solo telemetría).

## 9. Transferencia de archivos (canal binario)

### 9.1 Reglas generales

- **Control por JSON, datos por frames binarios.** Los bytes viajan crudos, sin envoltura ni codificación.
- **Una transferencia a la vez por conexión.** Un segundo `file_pull`/`file_push` mientras hay una activa → error `-32004`.
- **Chunk fijo anunciado:** por defecto **4096 bytes**; el último puede ser menor. Todo frame binario debe respetar el tamaño anunciado.
- **Integridad:** CRC32 (IEEE, hex de 8 dígitos) del archivo completo, calculado al vuelo por el emisor.
- **RAM constante:** el ESP32 lee/escribe la SD por bloques de 4 KB; **nunca** carga el archivo completo en memoria.
- **Timeos:** si pasan más de **5 s** sin recibir el chunk siguiente, la transferencia se aborta con notification `file_end` con `status: "timeout"`.
- **Límite:** tamaño máximo por transferencia: 1 GiB (protección ante `size` mentiroso).

### 9.2 Descarga ESP32 → App (`file_pull`)

```text
App → ESP32 (texto):   {"jsonrpc":"2.0","id":10,"method":"file_pull","params":{"path":"/logs/data.csv"}}
ESP32 → App (texto):   {"jsonrpc":"2.0","id":10,"result":{"transfer":"t1","size":15230,"chunk":4096,"crc32":"A1B2C3D4"}}
ESP32 → App (binario): [4096 bytes] [4096 bytes] [4096 bytes] [2942 bytes]
ESP32 → App (texto):   {"seq":99,"file_end":{"transfer":"t1","status":"complete","sent":15230}}
App → ESP32 (texto):   {"jsonrpc":"2.0","id":11,"method":"file_ack","params":{"transfer":"t1","crc32_ok":true}}
```

### 9.3 Subida App → ESP32 (`file_push`)

```text
App → ESP32 (texto):   {"jsonrpc":"2.0","id":20,"method":"file_push","params":{"path":"/fw/app.bin","size":1048576,"chunk":4096,"crc32":"DEADC0DE"}}
ESP32 → App (texto):   {"jsonrpc":"2.0","id":20,"result":{"transfer":"t2"}}
App → ESP32 (binario): [4096 bytes] … hasta completar size
App → ESP32 (texto):   {"jsonrpc":"2.0","id":21,"method":"file_ack","params":{"transfer":"t2","crc32_ok":true}}
ESP32 → App (texto):   {"jsonrpc":"2.0","id":21,"result":{"ok":true}}
```

### 9.4 Reanudación y cancelación

- **Reanudación:** `file_pull` acepta `offset` (bytes ya recibidos): `{"path": "...", "offset": 8192}`. El CRC32 anunciado sigue siendo el del archivo **completo**.
- **Cancelación:** cualquiera de los lados envía `file_cancel {"transfer": "t1"}` → el receptor corta y confirma con `file_end {"status": "cancelled"}`.

## 10. Catálogo de comandos v1

| Método | Dirección | Params (obligatorios) | Params (opcionales) | Devuelve |
|--------|-----------|----------------------|---------------------|----------|
| `get_info` | App → ESP32 | — | — | `{"device", "fw", "proto", "uptime_s"}` |
| `ping` | App → ESP32 | — | — | `{"pong": true, "uptime_s"}` |
| `set_hora` | App → ESP32 | `epoch` | `tz_offset` | `{"ok": true}` |
| `get_hora` | App → ESP32 | — | — | `{"hms", "dma"}` (formato `hh:mm:ss`, `dd/mm/aaaa`) |
| `set_uwb` | App → ESP32 | `mac`, `session` | `role`, `channel`, … | `{"ok": true}` |
| `get_uwb` | App → ESP32 | — | — | `{"mac", "session", "role", "channel", …}` |
| `sd_list` | App → ESP32 | `path` | `offset`, `limit` | `{"path", "total", "count", "entries": [...]}` |
| `file_pull` | App → ESP32 | `path` | `offset`, `chunk` | `{"transfer", "size", "chunk", "crc32"}` |
| `file_push` | App → ESP32 | `path`, `size`, `crc32` | `chunk` | `{"transfer"}` |
| `file_ack` | App → ESP32 | `transfer`, `crc32_ok` | — | `{"ok": true}` |
| `file_cancel` | Ambos | `transfer` | — | `{"ok": true}` |

Errores típicos por comando: `sd_list`/`file_*` → `-32001` (SD), `-32002` (ruta), `-32004` (ocupado); `set/get_uwb` → `-32005` (UWB no inicializado); `set_hora` → `-32602` (epoch inválido).

### 10.1 Esquemas detallados

**`set_hora` / `get_hora`**

```json
→ {"jsonrpc":"2.0","id":1,"method":"set_hora","params":{"epoch":1795347930,"tz_offset":-180}}
← {"jsonrpc":"2.0","id":1,"result":{"ok":true}}

→ {"jsonrpc":"2.0","id":2,"method":"get_hora","params":{}}
← {"jsonrpc":"2.0","id":2,"result":{"hms":"10:35:30","dma":"29/10/2026"}}
```

**`set_uwb` / `get_uwb`** (los campos extra son aditivos; `get_uwb` devuelve el estado real completo)

```json
→ {"jsonrpc":"2.0","id":3,"method":"set_uwb","params":{"mac":"1A:2B:3C:4D:5E:6F","session":1,"role":"anchor","channel":5}}
← {"jsonrpc":"2.0","id":3,"result":{"ok":true}}

→ {"jsonrpc":"2.0","id":4,"method":"get_uwb","params":{}}
← {"jsonrpc":"2.0","id":4,"result":{"mac":"1A:2B:3C:4D:5E:6F","session":1,"role":"anchor","channel":5}}
```

**`sd_list`** — `entries` es una lista de `{"name", "type": "dir"|"file", "size"?}` (solo `size` en archivos). Navegación en cascada: `dir` de la respuesta → nuevo `sd_list` con esa ruta. `total` = cantidad real en la carpeta; `count` = entradas devueltas en esta página.

```json
→ {"jsonrpc":"2.0","id":5,"method":"sd_list","params":{"path":"/","limit":100}}
← {"jsonrpc":"2.0","id":5,"result":{"path":"/","total":3,"count":3,"entries":[
     {"name":"logs","type":"dir"},
     {"name":"data.csv","type":"file","size":15230},
     {"name":"config.json","type":"file","size":512}]}}
```

**Seguridad de rutas:** el ESP32 debe rechazar (`-32602`) rutas que contengan `..`, que no empiecen con `/`, o que escapen de la raíz de la SD.

## 11. Cómo agregar un comando nuevo (checklist obligatorio)

1. **Nombre** según §5: `verbo_objeto[_detalle]`, `snake_case`, verbo del conjunto cerrado. Verificar que no exista otro comando que ya lo haga.
2. **Especificación:** agregar fila a la tabla del §10 con params obligatorios/opcionales y el objeto `result` exacto. Si devuelve un error nuevo de aplicación, agregarlo a §7 (rango `-320xx`).
3. **Ejemplo:** un par request/response real en §10.1 (los ejemplos son la referencia de los implementadores).
4. **Simetría:** si existe el `set_x`, evaluar si hace falta `get_x` (y viceversa) para poder verificar lo configurado.
5. **Implementación en ambos lados**, garantizando: siempre responder con `id`; validar `params` antes de actuar; jamás responder dos veces.
6. **GUI:** registrar el comando en el registro de comandos de la app (`~/.imop/config.json`), con su botón y, si tiene params, el mini-esquema de formulario:

```json
{
  "method": "set_uwb",
  "label": "Set UWB",
  "params": [
    {"name": "mac", "type": "string", "default": "1A:2B:3C:4D:5E:6F", "required": true},
    {"name": "session", "type": "int", "min": 0, "max": 9, "default": 1, "required": true},
    {"name": "role", "type": "enum", "options": ["anchor", "tag"], "default": "anchor"}
  ]
}
```

7. **Tests** del lado App (serialización del request, parseo de la respuesta, timeout) y prueba E2E con el ESP32.
8. **Versión:** cambio aditivo → no se altera `proto`. Documentar en el registro de cambios de este documento (§13).

## 12. Reglas de compatibilidad

- Los receptores **ignoran** todo campo desconocido (del sobre, de `params` y de `result`).
- Método desconocido → `-32601`; la conexión **no** se cierra.
- Queda prohibido: renombrar campos existentes, cambiar el tipo de un campo, o reutilizar un código de error con otro significado. Esos cambios requieren versión mayor del protocolo.
- Frame binario recibido sin transferencia activa → se descarta silenciosamente y se registra en el log (no es error fatal).

## 13. Registro de cambios del protocolo

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-10-29 | 1.0 | Definición inicial: sobre JSON-RPC 2.0, IDs, nomenclatura, errores, handshake, catálogo v1 (§10), transferencia de archivos por canal binario |
