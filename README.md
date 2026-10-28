# i-mop-websocket

Monitor y consola bidireccional WebSocket con visualizador de mensajes JSON en tiempo real, diseñado para depurar y controlar dispositivos **ESP32** (y cualquier cliente WebSocket).

![Estado](https://img.shields.io/badge/estado-en%20desarrollo-yellow) ![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Plataformas](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

## Características

- 🖥️ **Servidor WebSocket** en puerto configurable (GUI o línea de comandos).
- 📄 Recepción de mensajes **JSON** con validación robusta.
- 🎨 **Visualizador en tiempo real** con colores por tipo de mensaje, timestamps y auto-scroll.
- 🔍 **5 filtros por prefijo**: los JSON cuyo campo identificador comienza con un filtro se derivan a **archivos de log dedicados** (opcional) y se filtran en el panel inferior (sin filtros → se muestran todos).
- 💾 **Guardado de logs** con rotación, activable desde la GUI.
- ⌨️ *(Roadmap)* Teclas/botones configurables para **enviar datos** al ESP32.
- 📦 Empaquetado como `.exe` en Windows; también funciona en Linux y macOS.

## Capturas

> 📷 *Pendiente: agregar capturas cuando exista la primera versión de la GUI.*

## Requisitos

- Python **3.10 o superior**
- Un cliente WebSocket que envíe JSON (ESP32, wscat, navegador, etc.)

## Instalación rápida (desarrollo)

### Windows

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
python -m imop
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python -m imop
```

> La estructura completa del proyecto y sus entornos virtuales se detalla en [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Uso básico

1. Ejecutar la aplicación y elegir el **puerto** (por defecto `8765`).
2. Presionar **Iniciar servidor**.
3. Conectar el ESP32 (o `wscat -c ws://localhost:8765`) y enviar JSON:

   ```json
   {"sensor_temp": {"value": 23.4, "unit": "C"}}
   ```

4. Configurar hasta **5 filtros** (por ejemplo `sensor_`): los mensajes coincidentes se guardan en `logs/sensor_.log` si el guardado está habilitado, y se muestran en el panel inferior solo si pasan los filtros activos.

Para generar el ejecutable `.exe` ver [docs/BUILD_AND_DEPLOYMENT.md](docs/BUILD_AND_DEPLOYMENT.md).

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitectura, estructura de carpetas, entornos virtuales |
| [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) | Estándares y recomendaciones de programación en Python |
| [docs/DOCUMENTATION_RULES.md](docs/DOCUMENTATION_RULES.md) | Reglas de documentación (código, usuario y registro de IA) |
| [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md) | Flujo Git profesional (GitFlow) |
| [docs/BUILD_AND_DEPLOYMENT.md](docs/BUILD_AND_DEPLOYMENT.md) | Compilación `.exe` y guías Windows/Linux/macOS |
| [plans/action-plan.md](plans/action-plan.md) | Plan de acción y registro de decisiones/sesiones |
| [docs/user/manual.md](docs/user/manual.md) | Manual de usuario *(pendiente Fase 3)* |

## Contribuir

1. Leer [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) y [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md).
2. Crear rama `feature/<nombre>` desde `develop`.
3. Asegurar que pasan `ruff`, `mypy` y `pytest` (`pre-commit run --all-files`).
4. Abrir Pull Request hacia `develop` con descripción clara.

## Licencia

> 📝 *Pendiente de definir por el propietario del proyecto (sugerencia: MIT).*
