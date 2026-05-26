# Plan de Ataque — Multiplataforma y Limpieza Universal

> Documento de planificación para llevar **Cleanacelerai PRO** de una utilidad Windows-only (CustomTkinter) a una solución multiplataforma (Windows, macOS, Linux, y eventualmente móvil) con un motor de limpieza agnóstico al dispositivo.

Autor: Claude · Fecha: 2026-04-21 · Rama: `claude/check-claude-md-vANUY`

---

## 1. Diagnóstico actual

| Área | Estado | Riesgo para multiplataforma |
|---|---|---|
| Arquitectura | Hexagonal + MVP, servicios stateless | ✅ Base sólida: el dominio ya es agnóstico |
| UI | CustomTkinter (Tk) | ⚠️ Portable, pero con look&feel pobre en móvil y tablet |
| Limpieza de archivos | `safe_delete` usa `cmd /c del` y `\\?\` (Windows) | ❌ Específico de Windows |
| Rutas del sistema | `%TEMP%`, `%USERPROFILE%`, `AppData`, dotfiles estilo Win | ❌ Hardcodeado a Windows |
| Detección de navegadores | Chrome/Edge/Brave con rutas de perfil de Windows | ❌ Rutas Windows-only |
| Deep scanner | 45+ carpetas Windows conocidas | ❌ Base de conocimiento solo Windows |
| Packaging | PyInstaller `.exe` | ⚠️ Falta `.app` (macOS), `.AppImage`/`.deb` (Linux) |
| Tests | pytest, 0% coverage en UI | ⚠️ Bloquea refactor con confianza |
| Accesibilidad / responsive | No hay escalado, temas, ni layouts adaptativos | ❌ |

---

## 2. Objetivos

1. **Motor de limpieza portable**: ejecutable en Windows, macOS y Linux sin ramas `if platform.system()` esparcidas por el código.
2. **UI multiplataforma y responsive**: misma experiencia en desktop (1920×1080), portátil (1366×768) y tablet (touch, ≥ 1024px). Móvil como objetivo a medio plazo.
3. **Limpieza universal**: reglas de riesgo por sistema operativo, no por hardcode.
4. **Distribución simple**: un binario por plataforma + fallback `pip install`.
5. **Calidad sostenida**: coverage subiendo gradualmente, CI automatizada.

---

## 3. Fases de ataque

### Fase 0 — Preparación (1 sprint)

**Meta**: dejar el repo listo para el cambio sin romper lo actual.

- [ ] Añadir CI (GitHub Actions) con matriz `windows-latest / ubuntu-latest / macos-latest` corriendo `pytest`.
- [ ] Subir el gate de cobertura a 25% añadiendo tests para `services/duplicate_finder.py`, `services/temp_cleaner.py`, `services/chaos_advisor.py`.
- [ ] Extraer constantes Windows (`%TEMP%`, rutas de navegador, `CARPETAS_SISTEMA`) a un módulo `domain/platforms/windows.py` y preparar estructura `domain/platforms/{linux,macos}.py` vacía.
- [ ] Introducir `platform_info.py` en `infrastructure/` que exponga `current_os()`, `temp_dirs()`, `browser_profiles()`, `home_dir()`.

**Entregable**: misma funcionalidad, código segregado por OS, CI en verde en las 3 plataformas para el dominio puro.

---

### Fase 1 — Portar el motor a Linux y macOS (2 sprints)

**Meta**: `python -m cleanacelerai.run` funciona en Ubuntu y macOS con la UI actual (Tk).

#### 1.1 Abstracción de filesystem
- Reemplazar `safe_delete` Windows-only por una interfaz:
  ```python
  # infrastructure/file_system.py
  class FileSystemAdapter(Protocol):
      def safe_delete(self, path: str) -> tuple[bool, str]: ...
      def open_in_file_manager(self, path: str) -> None: ...
  ```
- Implementaciones: `WindowsFileSystem` (actual), `PosixFileSystem` (usa `os.remove` + `send2trash` para enviar a papelera).
- Inyectar el adapter desde `main.py` según `platform_info.current_os()`.

#### 1.2 Rutas y temp
- `TempCleaner` recibe una lista de directorios de `platform_info.temp_dirs()`:
  - Windows: `%TEMP%`, `%TMP%`, `C:\Windows\Temp`
  - Linux: `/tmp`, `~/.cache`, `/var/tmp`
  - macOS: `$TMPDIR`, `~/Library/Caches`

#### 1.3 Navegadores
- Añadir rutas de perfil para Linux (`~/.config/google-chrome`, `~/.config/BraveSoftware/Brave-Browser`) y macOS (`~/Library/Application Support/Google/Chrome`, …).
- Añadir Firefox (importante en Linux).

#### 1.4 Knowledge base del deep scanner
- Dividir `DOTFILES_CRITICOS` y el KB del `deep_scanner` en tres archivos JSON por OS bajo `domain/knowledge/{windows,linux,macos}.json`. Cargar según plataforma.

**Entregable**: app arranca en las 3 plataformas; limpieza básica y bookmarks funcionan en al menos Chrome + Firefox.

---

### Fase 2 — Empaquetado multiplataforma (1 sprint)

- **Windows**: conservar PyInstaller `.spec`.
- **macOS**: `py2app` o `pyinstaller --windowed --osx-bundle-identifier=ai.cleanacelerai` → `.app` + notarización (opcional).
- **Linux**: `AppImage` con `python-appimage`; `.deb` secundario con `dh-virtualenv`.
- Documentar en README cómo correr desde código fuente en cada OS.
- Pipeline de release en Actions: al crear un tag `vX.Y.Z`, generar los 3 artefactos y adjuntarlos al Release.

---

### Fase 3 — UI responsive y accesible (2–3 sprints)

**Meta**: la app se ve y se usa bien en 1366×768, 1920×1080 y 1280×800 con touch.

Dos caminos; proponemos **Camino A** y mantenemos B como alternativa.

#### Camino A (recomendado): conservar CustomTkinter + hacerlo responsive
- Sustituir `geometry("1400x900")` por un layout con `grid_rowconfigure/columnconfigure(weight=1)` en todos los frames (ya hecho parcialmente en `main_window.py`).
- Añadir breakpoints:
  - `< 1100 px`: sidebar colapsable a iconos.
  - `< 900 px`: sidebar se convierte en barra inferior estilo tabs.
- Escalado DPI: `ctk.set_widget_scaling(auto)` + `set_window_scaling(auto)` basado en `self.winfo_fpixels('1i')`.
- Temas: `light / dark / system` configurables en `ReglasView`.
- Accesibilidad: `tab-order` correcto, atajos de teclado (`Ctrl+1..7` para navegar), `aria`-equivalente vía `ttk.Labelframe`.

#### Camino B (moonshot): reescribir UI en un framework web embebido
- Migrar vistas a **Flet** (Flutter for Python) o **Tauri + PyWebview** con frontend Svelte/Vue.
- Pro: móvil nativo casi gratis (Flet compila a Android/iOS).
- Contra: reescritura completa de 7 vistas + 6 presenters. 3–5× el esfuerzo.
- **Decisión recomendada**: Camino A ahora; evaluar B después de Fase 4.

**Entregable**: screenshots en README con los 3 breakpoints; test manual de QA en Windows/macOS/Linux.

---

### Fase 4 — Motor de limpieza "por dispositivo" (2 sprints)

**Meta**: el concepto "limpieza para cualquier dispositivo" se vuelve explícito.

- Nuevo servicio `services/device_profile.py` que detecta:
  - OS y versión
  - Tipo de disco (SSD / HDD / eMMC) — relevante para umbrales de borrado
  - RAM disponible — ajusta tamaño de chunks en el duplicate finder
  - Si es portátil (batería) → modo ahorro: un solo thread, sin hashing completo
- Perfiles predefinidos en `domain/device_profiles.py`:
  - `desktop-power` (paralelismo máximo)
  - `laptop-balanced` (default)
  - `low-end` (chunks pequeños, sin PDF parsing)
  - `server-headless` (CLI only)
- CLI `cleanacelerai --headless --profile=low-end --target=/tmp --dry-run` para poder usar la herramienta en servidores sin GUI.

---

### Fase 5 — Mobile y cloud (exploración)

Solo después de completar Fase 4. Opciones:
- **Flet** reexportación a Android/iOS.
- **CLI-as-a-service**: empaquetar el motor como librería `pip install cleanacelerai-core` y construir apps móviles nativas encima.
- **Dashboard web** (FastAPI + React) para usuarios que gestionan varios equipos.

---

## 4. Criterios de hecho (DoD)

Una fase se considera completada cuando:
1. CI verde en Windows + Linux + macOS.
2. Smoke test manual pasa en las 3 plataformas.
3. Coverage no disminuye.
4. README documenta las nuevas capacidades.
5. `CHANGELOG.md` actualizado con la versión.

---

## 5. Riesgos y mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| CustomTkinter se queda corto para responsive real | Media | Alto | Prototipar breakpoints en Fase 3 antes de comprometerse |
| Enviar a papelera en macOS requiere AppleScript/Finder | Media | Medio | Usar `send2trash` (cross-platform, mantenido) |
| Firmado de código en macOS complica distribución | Alta | Medio | Empezar con binario sin firmar + instrucciones; notarizar cuando tengamos Apple Dev ID |
| Knowledge base de carpetas del sistema crece mucho | Alta | Bajo | JSON externo, versionable, actualizable sin release |
| Romper workflow Windows actual durante el refactor | Alta | Alto | Fase 0 introduce CI antes de tocar código de features |

---

## 6. Orden sugerido de ejecución

```
Fase 0  ──▶  Fase 1  ──▶  Fase 2  ──▶  Fase 3  ──▶  Fase 4  ──▶  Fase 5
  │           │           │            │            │            │
  CI +       Linux/Mac   Packaging    Responsive   Device       Móvil /
  tests      core        multi-OS     UI           profiles     cloud
```

El valor aparece desde Fase 1: la app ya corre en Linux/macOS. Fase 2 la hace distribuible, Fase 3 la hace usable en cualquier pantalla, Fase 4 es la "limpieza universal" de la que habla el título del proyecto.

---

## 7. Primeros pasos concretos (siguiente PR)

1. Añadir workflow `.github/workflows/ci.yml` con matriz 3 OS.
2. Crear `cleanacelerai/src/infrastructure/platform_info.py` con stubs.
3. Añadir `send2trash` al `requirements.txt` como preparación de Fase 1.
4. Mover constantes Windows-only de `domain/constants.py` a `domain/platforms/windows.py`.

Estos cambios son reversibles, no tocan la UX actual y desbloquean todo el plan.
