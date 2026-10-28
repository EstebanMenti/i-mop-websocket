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

---

## 5. Convenciones transversales

- **Protocolo de mensajes ESP32 → App:** JSON con clave raíz identificadora, p. ej.
  `{"sensor_temp": {"value": 23.4, "unit": "C"}}` → el filtro `sensor_` lo captura.
- **Idioma del código:** identificadores en inglés, comentarios/DOCs en español.
- **Toda nueva fase debe registrarse aquí antes de implementarse.**
