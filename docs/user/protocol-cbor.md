# Protocolo i-mop v2 (propuesta) — Comandos en CBOR

> **Versión:** 2.0-draft · **Fecha:** 2026-10-30 · **Estado:** Propuesta — pendiente de aprobación
> **Base:** [protocol.md](protocol.md) v1.0 (JSON) — este documento define el formato binario CBOR equivalente y convive con v1.
>
> **Regla de oro:** igual que en v1 — todo comando nuevo debe ajustarse a este documento.
> Si no encaja, primero se discute y se actualiza aquí; después se implementa.

---

## 1. Alcance y coexistencia con v1 (JSON)

| Tipo de tráfico | Formato en el wire | Detección |
|-----------------|--------------------|-----------|
| Comandos y respuestas | **CBOR** en frames **binarios** de WebSocket | Frame binario y sin transferencia de archivo activa → CBOR |
| Transferencia de archivos | Datos crudos (sin cambio respecto a v1 §9); **control** pasa a CBOR | Durante una transferencia activa, los frames binarios son chunks |
| Telemetría existente (`{"sensor_temp": ...}`) | **JSON texto** (sin cambios) | Frame de texto → JSON v1 |
| Telemetría nueva (IMU, UWB, batería) | **CBOR** (§7) | Frame binario, envelope tipo 3 |

El decoder del servidor ramifica por tipo de frame: `str` → JSON v1, `bytes` → CBOR (o chunk de archivo). **Ninguna funcionalidad v1 se rompe**: ambos protocolos comparten semántica (§4) y tabla de errores (§8); solo cambia la codificación.

## 2. Perfil CBOR (restricciones obligatorias)

Codificación según RFC 8949 con estas reglas canónicas (ambos lados deben cumplirlas; garantiza que un mismo dato produce siempre los mismos bytes):

1. **Longitudes definidas** solamente: prohibidos arrays/strings/mapas indefinidos (`0x9F`, `0xBF`, `0x5F`, `0x7F`).
2. **Entros en forma preferida (minimal):** valores < 24 en 1 byte; < 256 en 2; < 65536 en 3; < 2³² en 5. Negativos en major type 1 (`-n` → codificar `n-1`).
3. **Claves de mapas ordenadas** canónicamente (por longitud de su codificación y luego byte a byte). En este protocolo las claves son enteros pequeños, así que basta orden numérico ascendente.
4. **Sin tags** semánticos (major type 6) y **sin floats** salvo necesidad explícita (en ese caso, siempre f32, prefijo `0xFA`).
5. Texto en **UTF-8** (major 3); bytes crudos en **bstr** (major 2).
6. Los comandos **no** incluyen strings de nombre de método: se usan **códigos numéricos** (§4). El string solo aparece en errores y nombres de archivo.

**Bibliotecas de referencia:** Python [`cbor2`](https://pypi.org/project/cbor2/) (definir `canonical=True`); ESP32: `TinyCBOR`, `QCBOR` o `CBOR-Lite`. Cualquiera respeta este perfil configurando codificación mínima y longitudes definidas.

## 3. Envelope

Todo frame CBOR es un **array de 4 elementos**:

```cbordiag
[tipo, cid, cmd, payload]
```

| Campo | Tipo CBOR | Valores |
|-------|-----------|---------|
| `tipo` | uint 0-3 | `0` request (App→ESP32) · `1` respuesta OK · `2` respuesta error · `3` notificación (telemetría, ESP32→App) |
| `cid` | uint | Id de correlación: sustituye al `id` (requests) y al `seq` (telemetría). Mismas reglas de asignación que v1 §4 |
| `cmd` | uint | Código del comando (§4) |
| `payload` | mapa o array | Por tipo: request/respuesta → **mapa con claves enteras** (§5); telemetría de alta frecuencia → **array posicional** (§7, para máxima compacidad) |

Ejemplo mínimo — `ping` completo en 5 bytes:

```text
[0, 1, 2, {}]  (request ping, cid=1, cmd=2)
hex: 84 00 01 02 A0
```

**Siempre responder:** igual que v1 §3, toda request con `cid` recibe tipo `1` o `2` con el mismo `cid` y `cmd`.

## 4. Registro de comandos (asignación de códigos)

| Rango | Dominio | Comandos definidos |
|-------|---------|--------------------|
| `0x0001-0x00FF` | Sistema | `0x0001 get_info` · `0x0002 ping` · `0x0003 set_hora` · `0x0004 get_hora` |
| `0x0020-0x002F` | Archivos/SD | `0x0020 sd_list` · `0x0021 file_pull` · `0x0022 file_push` · `0x0023 file_cancel` · `0x0024 file_ack` |
| `0x1000-0x1FFF` | Periféricos | `0x1010 set_uwb` · `0x1011 get_uwb` |
| `0x8000-0x8FFF` | Telemetría (ESP32→App) | `0x8001 imu` · `0x8002 imu_batch` · `0x8003 uwb_range` · `0x8004 bat` · `0x8005 temp` · `0x8006 imu_full_batch` |

Reglas para asignar códigos nuevos (mismo espíritu que v1 §11):

1. El código se asigna **solo en este documento**, tomando el primer libre del rango del dominio; nunca reutilizar códigos retirados.
2. Un comando nuevo agrega fila a §4, especificación completa en §6 (o §7 si es telemetría) y entrada en §10.
3. `get_x`/`set_x` del mismo objeto usan códigos consecutivos (`set` par, `get` impar cuando sea posible: 0x1010/0x1011).

## 5. Convención de claves y valores en payloads (mapas)

Claves enteras, **ámbito por comando** (el significado de la clave 1 lo define cada comando). Convenciones transversales:

| Concepto | Clave habitual | Codificación |
|----------|----------------|--------------|
| Timestamp de alta frecuencia | `1` (telemetría) | `t_ms`: uint, ms desde boot (wrap a los 49,7 días; la hora absoluta se sincroniza con `set_hora`) |
| Timestamp absoluto | — | `epoch` uint (segundos UTC) + `tz` i16 (minutos) — igual que v1 §6 |
| MAC | — | **bstr de 6 bytes** (orden de transmisión tal cual se configura) |
| Ruta de archivo | — | text UTF-8 estilo POSIX, empieza con `/`, sin `..` |
| Tamaños | — | bytes (uint) |
| Enums | — | uint: `role`: 0=tag, 1=anchor; entry type: 0=dir, 1=file |
| Booleanos | — | `true`/`false` nativos de CBOR |

## 6. Especificación de comandos (guía de implementación)

> Cada comando incluye el ejemplo en notación diagnóstica CBOR y su **hex exacto**. Los hex son normativos: un test de round-trip debe reproducirlos byte a byte (codificación canónica del §2).

### 6.1 `get_info` — 0x0001

Request: payload vacío.

```text
[0, 1, 1, {}]
hex: 84 00 01 01 A0                                        (5 bytes)
```

Respuesta — claves: `1` device (text) · `2` fw (text) · `3` proto (uint) · `4` uptime_s (uint).

```text
[1, 1, 1, {1: "imop-uwb", 2: "1.2.0", 3: 1, 4: 3600}]
hex: 84 01 01 01 A4 01 68 696D6F702D757762 02 65 312E322E30
     03 01 04 19 0E10                                      (28 bytes)
```

Errores: ninguno previsto (si el dispositivo responde, puede responder esto).

### 6.2 `ping` — 0x0002

Request: `[]` → `84 00 01 02 A0` (ver §3). Respuesta — claves: `1` ok (bool) · `2` uptime_s (uint).

```text
[1, 3, 2, {1: true, 2: 3661}]
hex: 84 01 02 02 A2 01 F5 02 19 0E4D                       (11 bytes)
```

Timeout de la App: 3 s (igual que v1).

### 6.3 `set_hora` — 0x0003

Claves del request: `1` epoch (uint, segundos UTC) · `2` tz (i16, minutos, opcional).

```text
[0, 2, 3, {1: 1795347930, 2: -180}]
hex: 84 00 02 03 A2 01 1A 6B02D5DA 02 18 B5                (14 bytes)
```

Respuesta: `{1: true}` → `84 01 02 03 A1 01 F5` (7 bytes).
Errores: `-32602` si falta `epoch` o es absurdo (antes de 2020 o después de 2100).

### 6.4 `get_hora` — 0x0004

Request: `{}` → `84 00 03 04 A0` (5 bytes).
Respuesta — claves: `1` hms (text `hh:mm:ss`) · `2` dma (text `dd/mm/aaaa`) · `3` epoch (uint) · `4` tz (i16).

```text
[1, 3, 4, {1: "10:35:30", 2: "29/10/2026", 3: 1795347930, 4: -180}]
hex: 84 01 03 04 A4 01 68 31303A33353A3330 02 6A 32392F31302F
     32303236 03 1A 6B02D5DA 04 38 B3                      (36 bytes)
```

Errores: `-32005` si el RTC no está inicializado (sugerir `set_hora`).

### 6.5 `set_uwb` — 0x1010

Claves: `1` mac (bstr 6) · `2` session (uint 0-9) · `3` role (uint: 0=tag, 1=anchor) · `4` channel (uint). Otros parámetros futuros usan las siguientes claves libres (5, 6, …) documentadas aquí.

```text
[0, 4, 0x1010, {1: h'1A2B3C4D5E6F', 2: 1, 3: 1, 4: 5}]
hex: 84 00 04 19 1010 A4 01 46 1A2B3C4D5E6F 02 01 03 01 04 05   (22 bytes)
```

Respuesta: `{1: true}` → `84 01 04 191010 A1 01 F5` (8 bytes).
Errores: `-32602` (mac de longitud ≠ 6, session fuera de rango, channel inválido), `-32005` (UWB no inicializado).

### 6.6 `get_uwb` — 0x1011

Request: `{}`. Respuesta: el estado real completo con las mismas claves que `set_uwb`.

```text
[1, 4, 0x1011, {1: h'1A2B3C4D5E6F', 2: 1, 3: 1, 4: 5}]
hex: 84 01 04 19 1011 A4 01 46 1A2B3C4D5E6F 02 01 03 01 04 05   (22 bytes)
```

### 6.7 `sd_list` — 0x0020

Claves del request: `1` path (text) · `2` offset (uint, opcional, 0 por defecto) · `3` limit (uint, opcional, máx. 200).

```text
[0, 5, 0x20, {1: "/", 2: 0, 3: 100}]
hex: 84 00 05 20 A3 01 61 2F 02 00 03 18 64                (13 bytes)
```

Respuesta — claves: `1` total (uint) · `2` count (uint) · `3` entries (array de mapas `{1: name, 2: type (0=dir,1=file), 3: size (uint, solo files)}`).

```text
[1, 5, 0x20, {1: 3, 2: 2, 3: [
    {1: "logs",    2: 0},
    {1: "data.csv", 2: 1, 3: 15230}]}]
hex: 84 01 05 20 A3 01 03 02 02 03 82
     A2 01 64 6C6F6773 02 00
     A3 01 68 646174612E637376 02 01 03 19 3B7E            (37 bytes)
```

Navegación en cascada igual que v1 §10.1: entry `type=0` → nuevo `sd_list` con esa ruta. Errores: `-32001` (SD no montada), `-32002` (ruta inexistente), `-32602` (path con `..`).

### 6.8 `file_pull` — 0x0021 (descarga ESP32 → App)

Claves del request: `1` path · `2` offset (uint, opcional — reanudación).

```text
[0, 6, 0x21, {1: "/logs/data.csv"}]
hex: 84 00 06 21 A1 01 6D 2F6C6F67732F646174612E637376     (21 bytes)
```

Respuesta — claves: `1` transfer (text `"t<N>"`) · `2` size (uint) · `3` chunk (uint, bytes) · `4` crc32 (bstr 4, del archivo completo).

```text
[1, 6, 0x21, {1: "t1", 2: 15230, 3: 4096, 4: h'A1B2C3D4'}]
hex: 84 01 06 21 A4 01 62 7431 02 19 3B7E 03 19 1000 04 44 A1B2C3D4   (23 bytes)
```

A continuación la App recibe `size` bytes en frames **binarios crudos** (chunks de `chunk`, el último puede ser menor) y el flujo termina igual que v1 §9.2 con notification `file_end` y el `file_ack` (6.11). Errores: `-32001`, `-32002`, `-32004` (ya hay una transferencia activa).

### 6.9 `file_push` — 0x0022 (subida App → ESP32)

Claves del request: `1` path · `2` size (uint) · `3` chunk (uint) · `4` crc32 (bstr 4).

```text
[0, 8, 0x22, {1: "/fw/app.bin", 2: 1048576, 3: 4096, 4: h'DEADC0DE'}]
hex: 84 00 08 22 A4 01 6B 2F66772F6170702E62696E 02 1A 00100000
     03 19 1000 04 44 DEADC0DE                             (30 bytes)
```

Respuesta: `{1: "t2"}`. Luego la App envía los chunks binarios y cierra con `file_ack` (6.11). Este es además el camino del OTA futuro (v1 §9.3).

### 6.10 `file_cancel` — 0x0023

Claves: `1` transfer (text). Ambos lados pueden enviarlo.

```text
[0, 9, 0x23, {1: "t1"}]
hex: 84 00 09 23 A1 01 62 7431                             (10 bytes)
```

### 6.11 `file_ack` — 0x0024

Claves: `1` transfer · `2` crc32_ok (bool).

```text
[0, 10, 0x24, {1: "t1", 2: true}]
hex: 84 00 0A 24 A2 01 62 7431 02 F5                       (11 bytes)
```

Respuesta: `{1: true}` (el receptor confirmó y cerró la transferencia). Si `crc32_ok=false`, el emisor reintenta desde el último offset confirmado (v1 §9.4).

### 6.12 Ejemplo de error (aplica a todos los comandos)

Request con método inexistente:

```text
[0, 5, 0x7777, {}]
hex: 84 00 05 19 7777 A0                                   (7 bytes)
```

Respuesta error — claves: `1` code (i32, tabla §8) · `2` message (text) · `3` data (opcional):

```text
[2, 5, 0x7777, {1: -32601, 2: "metodo desconocido"}]
hex: 84 02 05 19 7777 A2 01 39 7F58 02 72 6D65746F646F2064
     6573636F6E6F6369646F                                  (31 bytes)
```

## 7. Telemetría en CBOR

Envelope tipo `3`. Para máxima compacidad el payload de telemetría es un **array posicional** (no mapa): el orden de campos está fijado por esta especificación. `cid` lleva el **número de muestra** (equivalente al `seq` de v1; la App puede seguir enviando ACK por `seq` JSON, o CBOR — indiferente, se define en implementación).

### 7.1 `imu` — 0x8001 (muestra individual, baja frecuencia)

Payload array de 7 elementos:

| Pos. | Campo | Tipo | Unidad / escala |
|------|-------|------|-----------------|
| 0 | `t_ms` | uint | ms desde boot |
| 1-3 | `ax`, `ay`, `az` | i16 ×3 | **milig** (1 LSB = 0.001 g = 0.00980665 m/s²) — rango ±32.7 g |
| 4-6 | `gx`, `gy`, `gz` | i16 ×3 | **0.1 dps** (1 LSB = 0.1 °/s) — rango ±3276.7 dps |

```text
[3, 42, 0x8001, [123456, 120, -15, 985, 12, -30, 2567]]
→ t=123456 ms; accel=(0.120, -0.015, 0.985) g; gyro=(1.2, -3.0, 256.7) dps
hex: 84 03 18 2A 19 8001 87 1A 0001E240 18 78 2E 19 03D9
     0C 38 1D 19 0A07                                      (25 bytes)
```

*(El mismo sample en JSON v1 pesaría ~200 bytes: CBOR lo reduce ~8×.)*

### 7.2 `imu_batch` — 0x8002 (ráfaga de alta frecuencia, 100 Hz+)

Payload **mapa**: `1` t0_ms (uint, timestamp del primer sample) · `2` period_us (uint, período entre samples) · `3` samples (array de arrays `[ax, ay, az, gx, gy, gz]` i16 ×6 cada uno).

```cbordiag
[3, 100, 0x8002, {1: 1000000, 2: 10000, 3: [[12, -4, 1000, 5, 10, -20],
                                            [14, -2, 1001, 6, 9, -22]]}]
```

- 100 Hz con batch de 20 muestras: **1 frame/s** de ~260 bytes en lugar de 100 frames sueltos → menos overhead de WebSocket y menos interrupciones en el ESP32.
- Regla: `t(k) = t0_ms + k × period_us / 1000`.

### 7.3 `uwb_range` — 0x8003 (medición UWB)

Payload array de 4: `t_ms` (uint) · `peer` (uint, dirección UWB del remoto) · `dist_mm` (uint, milímetros) · `rssi_dbm` (i16, entero, p. ej. -68).

```cbordiag
[3, 43, 0x8003, [124000, 0x2B, 4820, -68]]
```

### 7.4 `bat` — 0x8004 (batería)

Payload array de 3: `t_ms` · `mv` (uint, milivoltios) · `pct` (uint 0-100).

```cbordiag
[3, 44, 0x8004, [125000, 3700, 78]]
```

### 7.5 `temp` — 0x8005 (temperatura)

Payload array de 2: `t_ms` · `centi_c` (i32, °C × 100; 23.45 °C → 2345). Reemplaza gradualmente a la telemetría JSON `sensor_temp`; mientras coexistan, la GUI acepta ambas.

### 7.6 `imu_full_batch` — 0x8006 (ráfaga de la IMU completa, 100 Hz+)

Lleva **los mismos datos que la telemetría IMU en JSON** (acelerómetro, aceleración lineal, giroscopio, magnetómetro, cuaternión y la
máscara de sensores recibidos), a diferencia de `imu_batch` (0x8002), que solo trae acelerómetro y giroscopio.

- `cid` = número de muestra (`seq`) de la **primera** muestra del lote. La muestra `k` (desde 0) tiene `seq = cid + k`.
- Un lote solo contiene muestras de `seq` **consecutivos**.
- Payload **mapa**: `1` t0_ms (uint, instante de la primera muestra, ms desde boot) · `2` period_us (uint, período nominal entre muestras)
  · `3` samples (array de arrays de 17 enteros) · `4` sid (uint, identificador de sesión: aleatorio por arranque, distingue una placa
  reiniciada de un reenvío).
- `t(k) = t0_ms + k × period_us / 1000` (la marca individual de cada muestra no viaja).

Cada muestra es un array posicional de 17 enteros:

| Pos. | Campo | Tipo | Unidad / escala | Rango |
|------|-------|------|-----------------|-------|
| 0-2 | `ax`, `ay`, `az` | i16 | mili-g (como 0x8001) | ±32,7 g |
| 3-5 | `lx`, `ly`, `lz` (aceleración lineal, sin gravedad) | i16 | mili-g | ±32,7 g |
| 6-8 | `gx`, `gy`, `gz` | i16 | 0,1 °/s (como 0x8001) | ±3276,7 °/s |
| 9-11 | `mx`, `my`, `mz` | i16 | 0,1 µT | ±3276,7 µT |
| 12-15 | `qx`, `qy`, `qz`, `qw` (i, j, k, real) | i16 | Q14 (1 LSB = 1/16384) | ±2 |
| 16 | `valid` | uint | máscara de sensores recibidos (bit 0 acelerómetro … bit 4 cuaternión; 31 = todos) | 0-31 |

Valores fuera de rango se **saturan** al extremo del i16; valores no numéricos (NaN) se envían como 0.

Ejemplo normativo — lote de 2 muestras, `cid` = 100, t0 = 1 000 000 ms, 10 ms entre muestras, sid = 0xDEADBEEF:

```text
[3, 100, 0x8006, {1: 1000000, 2: 10000, 3: [
    [12, -4, 1000, 12, -4, 0, 5, 10, -20, 234, -123, -412, 0, 0, 11585, 11585, 31],
    [14, -2, 1001, 14, -2, 1, 6, 9, -22, 235, -124, -411, 1, -1, 11585, 11585, 31]], 4: 3735928559}]
hex: 84 03 18 64 19 8006 A4 01 1A 000F4240 02 19 2710 03 82
     91 0C 23 19 03E8 0C 23 00 05 0A 33 18 EA 38 7A 39 019B 00 00 19 2D41 19 2D41 18 1F
     91 0E 21 19 03E9 0E 21 01 06 09 35 18 EB 38 7B 39 019A 01 20 19 2D41 19 2D41 18 1F
     04 1A DEADBEEF                                        (84 bytes)
```

Tamaño típico con valores reales del BNO085: **~34 bytes por muestra** (un lote de 25 muestras ≈ 855 bytes, entra en un solo paquete);
la misma muestra en JSON v1 con claves largas ocupa ~424 bytes.

### 7.7 Confirmación de `imu_full_batch`

A diferencia del resto de la telemetría (§3: las notificaciones no tienen respuesta), `imu_full_batch` **se confirma** porque la placa
guarda las muestras hasta que la App las recibe y reenvía lo no confirmado tras una reconexión.

- Cuando la App procesa el lote responde **tipo `1`** con el mismo `cid` y `cmd`, y en la clave `1` el `seq` de la **última** muestra del
  lote. La confirmación es **acumulativa**: vale para todas las muestras con `seq` menor o igual.
- Si no pudo procesarlo responde **tipo `2`** con el código y el mensaje (§8). La placa lo cuenta como error y lo da igual por confirmado
  (reenviar el mismo lote no lo arreglaría).
- Tras una reconexión llegan lotes repetidos: la App los confirma igual y descarta las muestras con `seq` ya recibido para ese `sid`.

```text
[1, 100, 0x8006, {1: 101}]
hex: 84 01 18 64 19 8006 A1 01 18 65                      (11 bytes)

[2, 100, 0x8006, {1: -32603, 2: "error interno"}]
hex: 84 02 18 64 19 8006 A2 01 39 7F5A 02 6D 6572726F7220696E7465726E6F   (27 bytes)
```

## 8. Códigos de error

Misma tabla numérica que v1 §7 (los códigos negativos viajan como enteros CBOR major 1). Resumen:

| Código | Significado |
|--------|-------------|
| `-32700` / `-32600` | Frame no decodificable / envelope inválido |
| `-32601` | Comando desconocido |
| `-32602` | Parámetros inválidos (falta, tipo o fuera de rango) |
| `-32603` | Error interno |
| `-32000` | Error de hardware/I/O genérico |
| `-32001` | SD no montada · `-32002` archivo no encontrado · `-32003` CRC inválido |
| `-32004` | Transferencia en curso · `-32005` subsistema no inicializado |

Frame binario CBOR **corrupto** (no decodifica o `version` de perfil violado): se descarta con log y `-32700` como respuesta si el `cid` pudo recuperarse; nunca se cierra la conexión.

## 9. Reglas de compatibilidad

- Cambios **aditivos** (claves nuevas en mapas, comandos nuevos): mismo `proto` reportado por `get_info`.
- Claves desconocidas en un mapa → **se ignoran** (herencia directa de v1 §12).
- Prohibido: cambiar el significado de una clave, su posición en arrays de telemetría, o el tipo de un valor. Eso exige versión mayor (2.x → 3.0).
- Frames de telemetría cuyo `cmd` no reconoce la App: se muestran como fila genérica con hex (tipo ERROR suave), no se descartan silenciosamente.

## 10. Checklist para agregar un comando nuevo (CBOR)

1. **Código**: primer libre del rango del dominio (§4); `get`/`set` consecutivos. Registrar en §4.
2. **Especificación** en §6 (o §7 si es telemetría): tabla de claves/posiciones con tipo, unidad y rango; respuesta exacta; errores aplicables de §8.
3. **Ejemplo normativo**: notación diagnóstica **+ hex exacto** (obligatorio: será el golden test del round-trip).
4. **Simetría** `get`/`set` cuando corresponda.
5. **Implementación** con codificación canónica (§2): ambos lados deben reproducir el hex del ejemplo.
6. **GUI**: entrada en el registro de comandos (v1 §11 paso 6) mapeando botón → código CBOR.
7. **Tests**: round-trip encode/decode contra el hex del ejemplo + test de rechazo de parámetros inválidos.
8. **Registro**: fila en §11 de este documento.

## 11. Registro de cambios

| Fecha | Versión | Cambio |
|-------|---------|--------|
| 2026-10-30 | 2.0-draft | Agregado `imu_full_batch` (0x8006, §7.6) con los 16 valores de la IMU y la máscara `valid`, y su confirmación CBOR (§7.7). Corregido el tamaño del ejemplo `imu` §7.1 (25 bytes) |
| 2026-10-30 | 2.0-draft | Propuesta inicial: perfil CBOR canónico, envelope `[tipo, cid, cmd, payload]`, registro de códigos, especificaciones completas con hex normativo (get_info, ping, set/get_hora, set/get_uwb, sd_list, file_*), telemetría IMU (imu/imu_batch), uwb_range, bat, temp |
