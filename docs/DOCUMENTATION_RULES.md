# Reglas de Documentación — i-mop-websocket

> **Regla general:** la documentación es parte del código. Un cambio sin su documentación correspondiente no está completo. Idioma: **español** para toda documentación; identificadores de código en inglés.

Este documento define tres niveles de documentación obligatorios:

1. Documentación **dentro del código**.
2. Documentación **a nivel de usuario**.
3. Documentación **de resultados de IA / plan de acción** (trazabilidad).

---

## 1. Documentación dentro del código

### 1.1 Docstrings — estilo Google, obligatorios en

- Cabecera de **cada módulo** (qué hace, a qué capa pertenece).
- **Clases** y sus atributos relevantes.
- **Métodos/funciones públicas** (`Args`, `Returns`, `Raises`).
- Métodos privados complejos (> 10 líneas o lógica no obvia).

```python
"""Servidor WebSocket asíncrono para recepción de mensajes JSON.

Pertenece a la capa de red. No debe importar nada de la capa GUI.
"""
```

### 1.2 Comentarios

- Solo para explicar el **porqué**, nunca el qué (eso lo dice el código).
- Referencias a issues/tareas: `# TODO(fase-5): soportar múltiples clientes` con issue si existe.
- Prohibido dejar código comentado "por las dudas": eso es trabajo de Git.

### 1.3 Tipado como documentación

Los type hints son documentación ejecutable y **obligatorios** (ver [CODING_STANDARDS.md](CODING_STANDARDS.md) §5).

---

## 2. Documentación a nivel de usuario

Ubicación: `docs/user/`. Objetivo: que alguien sin conocimientos de programación pueda instalar y usar la app.

| Archivo | Contenido obligatorio |
|---------|----------------------|
| `docs/user/manual.md` | Manual completo: instalación, primer arranque, cada panel de la GUI con captura, uso de filtros, guardado de logs, solución de problemas |
| `docs/user/faq.md` | Preguntas frecuentes (puerto ocupado, firewall, ESP32 no conecta) |
| `docs/user/protocol.md` | Formato de mensajes JSON aceptados/enviados, con ejemplos reales del ESP32 |

Reglas:

- Toda función de la GUI debe tener su sección con **captura de pantalla** y explicación paso a paso.
- Los cambios que afecten la UI requieren actualizar el manual **en el mismo PR**.
- Incluir ejemplos copiables (bloques de código JSON, comandos `wscat`).
- Tabla de versiones al final del manual: qué cambió para el usuario en cada release.

---

## 3. Documentación de resultados de IA (trazabilidad obligatoria)

Todo trabajo asistido por IA debe quedar registrado. **Ninguna sesión termina sin actualizar:**

### 3.1 [`plans/action-plan.md`](../plans/action-plan.md)

- **Decisiones**: tabla con fecha, decisión, motivo, estado (propuesta / aprobada).
- **Registro de sesiones**: una entrada por sesión con objetivo, resultado y pendientes.
- **Roadmap**: marcar casillas `[x]` de las fases completadas.

### 3.2 Commits

- Commits **convencionales** (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) — ver [GIT_WORKFLOW.md](GIT_WORKFLOW.md).
- El cuerpo del commit puede resumir qué generó la IA, pero la responsabilidad del contenido es de quien aprueba el PR.

### 3.3 Archivos generados por IA

- Todo documento nuevo va en `docs/` (temas técnicos) o `docs/user/` (usuario) o `plans/` (planificación).
- Nunca generar archivos sueltos en la raíz del proyecto sin registrarlos en `plans/action-plan.md`.

---

## 4. Documentación técnica del proyecto

| Documento | Cuándo actualizarlo |
|-----------|--------------------|
| `README.md` | Al cambiar instalación, uso básico, features visibles |
| `docs/ARCHITECTURE.md` | Al agregar/mover módulos, cambiar flujos de datos o hilos |
| `docs/CODING_STANDARDS.md` | Al adoptar nuevas herramientas o reglas de estilo |
| `docs/GIT_WORKFLOW.md` | Al cambiar el flujo de ramas/versionado |
| `docs/BUILD_AND_DEPLOYMENT.md` | Al cambiar dependencias que afecten el empaquetado o agregar plataformas |
| `CHANGELOG.md` (raíz) | En cada release, formato [Keep a Changelog](https://keepachangelog.com/) |

### 4.1 Estilo común de documentación

- Markdown con encabezados jerárquicos (`#` solo para el título del documento).
- Tablas para comparaciones, listas para pasos, bloques de código con lenguaje.
- Rutas de archivos como enlaces relativos clicables: [`README.md`](../README.md).
- Diagramas Mermaid para arquitectura y flujos (ver ejemplos en [ARCHITECTURE.md](ARCHITECTURE.md)).
- Cada documento empieza con un blockquote `> **Regla:**` que resume su propósito.

---

## 5. Checklist antes de cerrar cualquier tarea

- [ ] Docstrings actualizados (módulos/clases/funciones tocadas).
- [ ] `docs/user/manual.md` actualizado si cambió la UI.
- [ ] `CHANGELOG.md` actualizado si es un cambio visible al usuario.
- [ ] `plans/action-plan.md` con la entrada de sesión y decisiones.
- [ ] README sin referencias rotas.
- [ ] Commit convencional correcto.
