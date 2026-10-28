# Compilación y Despliegue — i-mop-websocket

> **Regla:** cada tag `vX.Y.Z` en `main` debe producir un ejecutable por plataforma (Windows `.exe`, Linux binario, macOS `.app`). Los pasos de este documento deben funcionar de forma idéntica en cualquier máquina limpia.

## 1. Herramienta de empaquetado

**PyInstaller** (estándar para apps PySide6):

- Modo **onedir** para desarrollo/QA (arranque rápido, más fácil de depurar).
- Modo **onefile** para distribución final (un solo `.exe`).
- PySide6 requiere excluir módulos Qt no usados para reducir tamaño.

## 2. Requisitos previos por plataforma

### Windows
- Python 3.10+ desde [python.org](https://www.python.org/downloads/) (marcar *Add to PATH*).
- No se necesitan compiladores (todas las dependencias tienen wheels).

### Linux (Debian/Ubuntu)
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
# Qt en headless/servidores:
sudo apt install -y libgl1 libegl1 libxkbcommon0 libdbus-1-3
```

### macOS
- Python 3.10+ (Homebrew: `brew install python@3.12`).
- Xcode Command Line Tools: `xcode-select --install`.

## 3. Setup común de desarrollo (los 3 SO)

```bash
git clone https://github.com/<usuario>/i-mop-websocket.git
cd i-mop-websocket

# Windows                          # Linux/macOS
python -m venv .venv               python3 -m venv .venv
.venv\Scripts\activate             source .venv/bin/activate

pip install -e .[dev]
pre-commit install
pytest
```

Ejecutar la app: `python -m imop` (o `imop` si la entrada de consola está instalada).

## 4. Compilar el ejecutable

### 4.1 Windows — generar `Imop.exe`

```bat
scripts\build_windows.bat
```

El script (a crear en Fase 6) equivale a:

```bat
pyinstaller imop.spec --clean --noconfirm
```

`imop.spec` (versionado en la raíz) incluirá:

```python
# Puntos clave del spec (referencia, se genera en Fase 6)
a = Analysis(
    ["src/imop/__main__.py"],
    pathex=["src"],
    hiddenimports=[],
    excludes=["tkinter", "matplotlib", "numpy"],   # recortar tamaño
    noarchive=False,
)
exe = EXE(..., name="Imop", console=False, icon="src/imop/gui/resources/icon.ico")
```

Resultado: `dist/Imop/Imop.exe` (onedir) o `dist/Imop.exe` (onefile).

> **Windows SmartScreen:** el `.exe` sin certificado de firma mostrará advertencia. Opciones: firmar con certificado de código (producción profesional) o documentar "Más información → Ejecutar de todas formas" en el manual de usuario.

### 4.2 Linux

```bash
scripts/build_linux.sh
# equivale a: pyinstaller imop.spec --clean --noconfirm
# resultado: dist/Imop/Imop
```

Distribución sencilla: comprimir `dist/Imop/` en `.tar.gz`. Opcional avanzado: AppImage con `appimagetool`.

### 4.3 macOS

```bash
scripts/build_macos.sh
# resultado: dist/Imop.app
```

Notas:

- El `.app` debe firmarse/ad-hoc firmarse (`codesign --force --deep -s - dist/Imop.app`) para Gatekeeper.
- **PyInstaller no hace cross-compilation**: cada binario se compila en su SO (macOS builds requieren una Mac, o CI con runners macOS).

## 5. Matriz de compatibilidad

| Plataforma | Estado soporte | Empaquetado | Notas |
|------------|----------------|-------------|-------|
| Windows 10/11 x64 | ✅ Primario | `.exe` (PyInstaller onefile/onedir) | Requiere VC++ Runtime (incluido por PyInstaller) |
| Linux x64 (Debian/Ubuntu/Fedora) | ✅ Soportado | binario onedir / tar.gz | Requiere libGL y libxkbcommon |
| macOS 12+ (Intel/Apple Silicon) | ✅ Soportado | `.app` | Firmar ad-hoc mínimo; notarización opcional |
| Windows x86 / ARM | ⚠️ No prioritario | — | Evaluar si surge demanda |

## 6. Testing del paquete (QA pre-release)

Checklist mínimo antes de publicar un release (en cada plataforma si es posible):

- [ ] El ejecutable arranca sin consola negra (`console=False`).
- [ ] Servidor inicia y escucha en el puerto configurado.
- [ ] Conexión desde `wscat -c ws://localhost:<puerto>` y recepción de JSON visible en el panel con colores.
- [ ] JSON inválido no tumba la app (se loguea y se ignora).
- [ ] Los 5 filtros funcionan: matching por prefijo, mostrar/ocultar en panel inferior.
- [ ] Guardado de logs activable; archivos creados en la carpeta elegida; rotación OK.
- [ ] Configuración persiste tras cerrar y reabrir.
- [ ] Firewall: primera ejecución pide permiso (documentar en `docs/user/faq.md`).

## 7. Publicación de releases

1. Merge de `release/vX.Y.Z` a `main` y tag (ver [GIT_WORKFLOW.md](GIT_WORKFLOW.md)).
2. GitHub Release con notas (extraídas de `CHANGELOG.md`) adjuntando `Imop.exe`, `Imop-linux.tar.gz`, `Imop-macos.app.zip` y checksums SHA-256.
3. *(Futuro)* GitHub Actions: workflow que en cada tag ejecuta PyInstaller en runners `windows-latest`, `ubuntu-latest`, `macos-latest` y adjunta artefactos automáticamente.

## 8. Solución de problemas comunes

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `Imop.exe` no abre, sin error visible | Falta dependencia oculta | Agregar `hiddenimports` al spec; probar `console=True` en build de debug |
| Antivirus/SmartScreen bloquea el .exe | Binario sin firmar | Firmar con certificado o usar onedir + instrucciones al usuario |
| macOS "dañado, no se puede abrir" | Sin firma / descargado por navegador | `xattr -cr /Applications/Imop.app` o firmar correctamente |
| Linux: `libGL error` | Sin libs Qt del sistema | `sudo apt install libgl1 libxkbcommon0` |
| Puerto en uso al iniciar | Otra instancia u otro proceso | Cambiar puerto en la GUI; documentado en FAQ |
| .exe muy grande (>150 MB) | PySide6 completo | Ajustar `excludes`; evaluar `--strip`, `upx` |
