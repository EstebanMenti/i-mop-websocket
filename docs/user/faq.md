# FAQ — Preguntas frecuentes

> **Regla:** cada problema operativo documentado aquí debe incluir síntoma, verificación y solución.

## ¿Cómo verifico que mi PC puede recibir datos y que el puerto está abierto?

### 1. Verificar que el servidor está en escucha (local)

Con la aplicación corriendo y el servidor **Iniciado**, en una terminal de Windows (cmd):

```bat
netstat -ano | findstr :1001 | findstr LISTENING
```

- Si devuelve una línea como `TCP 0.0.0.0:1001 ... LISTENING 22540` → el puerto está abierto y aceptando conexiones en **todas** las interfaces de red (`0.0.0.0`).
- Si no devuelve nada → el servidor no está iniciado o está en otro puerto (mirar el panel *Servidor WebSocket* de la GUI).
- El último número es el **PID** del proceso: `tasklist /FI "PID eq 22540"` confirma que es `python.exe` (o `Imop.exe`).

También aparece en el log de la consola al arrancar:
`INFO imop.network.server: Servidor WebSocket escuchando en 0.0.0.0:1001`

### 2. Probar recepción local (loopback)

```bat
.venv\Scripts\python scripts\e2e_send.py --port 1001
```

Si los mensajes aparecen en el panel inferior de la GUI (con colores y timestamps), todo el pipeline local funciona. Alternativa sin Python: en un navegador moderno la URL `ws://127.0.0.1:1001` no es navegable, pero una conexión WebSocket fallida a un puerto **cerrado** da error distinto que a un puerto **abierto**; para pruebas interactivas usar [`wscat`](https://github.com/websockets/wscat): `wscat -c ws://127.0.0.1:1001`.

### 3. Conocer la IP que debe usar el ESP32

```bat
ipconfig
```

Buscar `Dirección IPv4` del adaptador de la red **Wi-Fi o Ethernet** donde está el ESP32 (p. ej. `192.168.0.117`). La URL para el ESP32 será:

```
ws://192.168.0.117:1001
```

(ignorar IPs `192.168.x.1` de adaptadores virtuales VMware/Hyper-V y `10.45.x.x` si es VPN, salvo que el ESP32 esté en esa red).

### 4. Verificar el firewall de Windows (imprescindible para el ESP32)

El firewall bloquea conexiones **entrantes** de otros dispositivos por defecto. Al primer arranque, Windows debería haber mostrado el diálogo de permiso para `python.exe`; si se rechazó o no apareció:

```bat
:: Ver si hay reglas para python
netsh advfirewall firewall show rule name=all | findstr /i "python"

:: Crear regla de entrada para el puerto del servidor (ejecutar cmd como Administrador)
netsh advfirewall firewall add rule name="i-mop-websocket" dir=in action=allow protocol=TCP localport=1001
```

Para borrarla: `netsh advfirewall firewall delete rule name="i-mop-websocket"`.

> ⚠️ Recomendación de seguridad: limitar la regla a la red local (`localip=192.168.0.0/16` o perfil `private`) y borrarla cuando no se use.

### 5. Probar desde otro dispositivo (simula el ESP32)

Desde otro equipo/móvil en la misma red:
- Navegador (consola JS): `new WebSocket("ws://192.168.0.117:1001")` → debe conectar (`readyState` 1).
- Si no conecta: revisar paso 4 (firewall) y que ambos estén en la misma subred (el ESP32 con `WiFi.localIP()` del mismo rango).
- El contador **Clientes** del panel del servidor debe incrementarse a 1 al conectar.

### 6. Checklist rápido de diagnóstico

| Síntoma | Verificación | Solución |
|---------|--------------|----------|
| `netstat` no muestra el puerto | Servidor iniciado en la GUI | Presionar *Iniciar servidor* |
| "Puerto en uso" al iniciar | `netstat -ano | findstr :1001` | Cerrar el otro proceso o cambiar el puerto |
| Local funciona, ESP32 no conecta | Paso 4 y 5 | Regla de firewall / misma red / IP correcta |
| Conecta pero no llegan datos | Log de la consola | Verificar que el ESP32 envía **texto** JSON (no binario) |
| ESP32 en otra subred | `ipconfig` vs `WiFi.localIP()` | Conectar ambos a la misma red/ruteo |

## Ejemplo mínimo para el ESP32 (Arduino)

```cpp
#include <WiFi.h>
#include <WebSocketsClient.h>  // arduinoWebSockets (Links2004)

WebSocketsClient webSocket;

void setup() {
  Serial.begin(115200);
  WiFi.begin("TU_SSID", "TU_PASS");
  while (WiFi.status() != WL_CONNECTED) delay(500);
  webSocket.begin("192.168.0.117", 1001, "/");
  webSocket.setReconnectInterval(2000);
}

void loop() {
  webSocket.loop();
  static uint32_t last = 0;
  if (millis() - last > 1000) {
    last = millis();
    String msg = "{\"sensor_temp\":{\"value\":" + String(20.0 + random(0, 50) / 10.0) + "}}";
    webSocket.sendTXT(msg);  // texto JSON, NO sendBIN
  }
}
```

## ¿El puerto 1001 no funciona en la red de mi trabajo?

Redes corporativas suelen bloquear puertos no estándar. Probar con 80, 8080 u 8765 cambiando el puerto en la GUI (no requiere cambios de código).

## ¿Dónde se guardan los logs por filtro?

En la carpeta elegida en el panel *Guardado de logs* (por defecto `C:\Users\<usuario>\.imop\logs`). Cada filtro habilitado genera `<prefijo>.log`, una línea JSON por mensaje, con rotación a 5 MiB (3 backups).

## ¿Cómo hago que el ESP32 encuentre el servidor sin configurar la IP a mano? (mDNS / Zeroconf)

**Revisión del texto original:** la idea es correcta (publicar el servicio con mDNS para que los clientes lo descubran y evitar hardcodear IPs), pero con **dos imprecisiones para este proyecto**:

1. **Los roles están invertidos.** El texto original describe un cliente Node.js que *descubre* otros servicios. Aquí el escenario es al revés: **la notebook es el SERVIDOR** (anuncia `_imop._tcp` con la librería Python [`zeroconf`](https://github.com/python-zeroconf/python-zeroconf)) y **el ESP32 es el cliente que descubre** (con `ESPmDNS` incluido en el core de Arduino-ESP32; el `bonjour-service` de Node.js no aplica salvo que el descubridor sea otro PC).
2. **`Test-NetConnection DESKTOP-UDO7SS5.local -Port 1001`** solo sirve para verificar *a mano* desde otro PC con PowerShell. De hecho, mDNS ya resuelve el nombre → IP; si el ESP32 obtuvo host y puerto vía `queryService`, no hace falta esa prueba. Úsala solo como diagnóstico.

### Cómo funciona en la app

- Panel *Servidor WebSocket* → checkbox **"Anunciar servicio en la red (mDNS/Zeroconf)"** (activado por defecto).
- Al iniciar el servidor, se publica el servicio `_imop._tcp.local.` con nombre de instancia `i-mop-<hostname>` y el puerto configurado.
- Al detener el servidor o cerrar la app, el anuncio se retira correctamente (goodbye packet).

### Código de ejemplo para el ESP32 (descubrimiento)

```cpp
#include <WiFi.h>
#include <ESPmDNS.h>

void setup() {
  Serial.begin(115200);
  WiFi.begin("TU_SSID", "TU_PASS");
  while (WiFi.status() != WL_CONNECTED) delay(500);

  if (!MDNS.begin("esp32-sensor")) {   // nombre propio en la red
    Serial.println("mDNS fallo"); while (true) delay(1000);
  }
  // Buscar el servidor i-mop: consulta "_imop._tcp"
  int n = MDNS.queryService("imop", "tcp");
  if (n == 0) {
    Serial.println("Servidor i-mop no encontrado");
  } else {
    Serial.printf("Servidor: %s:%u\n", MDNS.hostname(0).c_str(), MDNS.port(0));
    webSocket.begin(MDNS.hostname(0), MDNS.port(0), "/");  // o resolver a IP
    webSocket.setReconnectInterval(2000);
  }
}
```

### Requisitos y límites (diagnóstico)

| Síntoma | Verificación | Solución |
|---------|--------------|----------|
| `queryService` devuelve 0 | ¿Checkbox activado y servidor iniciado? | Activar el anuncio / iniciar servidor |
| Firewall bloquea el anuncio | UDP **5353** entrante debe estar permitido | `netsh advfirewall firewall add rule name="mDNS" dir=in action=allow protocol=UDP localport=5353` |
| No se descubre nunca | ESP32 y PC en el **mismo segmento** (mismo SSID/AP) | El multicast no atraviesa routers ni redes con *client isolation* |
| Funciona por IP pero no por mDNS | `ping DESKTOP-XXX.local` desde otro PC | Problema de mDNS en la red: usar IP directa como fallback |

> ℹ️ El anuncio es **opcional y no bloqueante**: si mDNS falla (permisos, red corporativa, etc.), se registra en el log y el servidor sigue funcionando normalmente por conexión directa a la IP.

## ¿Cómo uso la consola para enviar comandos al ESP32?

La pestaña **"Consola"** envía comandos de **texto plano** al ESP32 por la misma conexión WebSocket que ya usa para la telemetría (no hay que configurar nada nuevo).

### Paso a paso

1. Iniciar el servidor (pestaña *Telemetría* → *Iniciar servidor*).
2. Conectar el ESP32 (el selector **Destino** de la consola muestra `ip:puerto` cuando se conecta; con un solo ESP lo selecciona automáticamente).
3. Ir a la pestaña **Consola**, escribir el comando y presionar **Enter** (o el botón *Enviar*). La app agrega el salto de línea final.
4. La respuesta del ESP aparece en la salida con timestamp; **↑/↓** recorre el historial de comandos; *Eco local* muestra el comando enviado en verde.

### Diagnóstico de la consola

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| No puedo escribir / nada se envía | El servidor no está iniciado | Iniciar el servidor en la pestaña *Telemetría* (la barra de estado avisa) |
| El comando se envía pero no responde | El firmware del ESP no implementa el intérprete de texto | Implementar el CLI según [protocol.md](protocol.md) §15.5 |
| La respuesta aparece en *Telemetría* y no en *Consola* | El ESP respondió con JSON válido | El firmware debe responder **texto plano** (regla §15.3) |
| El ESP está conectado pero no aparece en *Destino* | La conexión se cayó o aún no se registró | Verificar el contador *Clientes* del panel del servidor |

> ⚠️ **Sin seguridad (por ahora):** no hay TLS ni autenticación; cualquier equipo de la red puede conectarse y enviar comandos. Usar solo en redes confiables.
