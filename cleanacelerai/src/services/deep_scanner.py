"""Deep scanner service: scans system for cleanable config/cache folders."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from cleanacelerai.src.domain.constants import SYSTEM_ROOT_PROTECTED
from cleanacelerai.src.domain.models import (
    DeepCleanBundle,
    DeepCleanEntry,
    DeepCleanResult,
    DeepCleanRisk,
)


@dataclass(frozen=True)
class FolderProfile:
    """Static knowledge about a known folder."""
    description: str
    creator: str
    risk: DeepCleanRisk
    bundle: DeepCleanBundle
    delete_instructions: str | None = None


# ── Knowledge Base ──────────────────────────────────────────────────────

KNOWLEDGE_BASE: dict[str, FolderProfile] = {
    # AI Tools
    ".agents":           FolderProfile("Skills y agentes de Claude Code. Si lo borrás, perdés las skills instaladas (code-review, plan, playwright, etc.)", "Claude Code", DeepCleanRisk.CRITICAL, DeepCleanBundle.AI_TOOLS),
    ".aitk":             FolderProfile("AI Toolkit para VS Code. Descarga modelos de IA y guarda logs. Se puede borrar y se regenera si volvés a usar la extensión.", "AI Toolkit (VS Code)", DeepCleanRisk.CACHE, DeepCleanBundle.AI_TOOLS),
    ".claude":           FolderProfile("Tu configuración de Claude Code: settings, memoria, reglas personalizadas. Si lo borrás, perdés toda tu configuración.", "Claude Code", DeepCleanRisk.SYSTEM, DeepCleanBundle.AI_TOOLS),
    ".claude-worktrees": FolderProfile("Worktrees temporales de Claude Code. Se puede borrar, se regenera solo cuando se necesite.", "Claude Code", DeepCleanRisk.CACHE, DeepCleanBundle.AI_TOOLS),
    ".codex":            FolderProfile("Configuración de OpenAI Codex CLI. Si solo usás Codex vía web o Gentle AI, se puede borrar.", "OpenAI Codex CLI", DeepCleanRisk.CACHE, DeepCleanBundle.AI_TOOLS),
    ".continue":         FolderProfile("Extensión Continue para autocompletado con IA en VS Code. Si la usás, dejala. Si no, se puede borrar.", "Continue.dev", DeepCleanRisk.CACHE, DeepCleanBundle.AI_TOOLS),
    ".copilot":          FolderProfile("Configuración de GitHub Copilot. Si usás Copilot en GitHub o VS Code, dejala.", "GitHub Copilot", DeepCleanRisk.CACHE, DeepCleanBundle.AI_TOOLS),
    ".cursor":           FolderProfile("Configuración del editor Cursor. Si no lo tenés instalado, se puede borrar. Se recrea al reinstalar.", "Cursor Editor", DeepCleanRisk.CACHE, DeepCleanBundle.AI_TOOLS),
    ".gemini":           FolderProfile("Google Gemini CLI. Si solo usás Gemini vía web o Gentle AI, se puede borrar. Puede pesar GBs por modelos descargados.", "Google Gemini CLI", DeepCleanRisk.CACHE, DeepCleanBundle.AI_TOOLS),
    ".gentle-ai":        FolderProfile("Tu herramienta principal para gestionar agentes de IA. Contiene backups y configuración. NO ELIMINAR.", "Gentle AI", DeepCleanRisk.SYSTEM, DeepCleanBundle.AI_TOOLS),
    ".mistralcode":      FolderProfile("Extensión de Mistral AI para editores. Si no la usás activamente, se puede borrar sin problema.", "Mistral Code", DeepCleanRisk.CACHE, DeepCleanBundle.AI_TOOLS),
    ".ollama":           FolderProfile("Claves de identidad y configuración de Ollama. Si usás Ollama para modelos locales, NO lo borres — perdés las claves.", "Ollama", DeepCleanRisk.CRITICAL, DeepCleanBundle.AI_TOOLS),
    ".zencoder":         FolderProfile("Sesiones y cache de ZenCoder. Si no lo usás activamente, se puede borrar.", "ZenCoder", DeepCleanRisk.CACHE, DeepCleanBundle.AI_TOOLS),
    ".zenflow":          FolderProfile("Workflows de ZenCoder. Si no lo usás activamente, se puede borrar.", "ZenCoder", DeepCleanRisk.CACHE, DeepCleanBundle.AI_TOOLS),
    ".engram":           FolderProfile("Memoria persistente de Claude Code entre sesiones. Si lo borrás, perdés todo el historial de decisiones y contexto.", "Claude Code / Engram", DeepCleanRisk.SYSTEM, DeepCleanBundle.AI_TOOLS),

    # Editors & Development
    ".git":              FolderProfile("Repositorio Git. Si está en tu carpeta de usuario es ACCIDENTAL y desperdicia GBs. En carpetas de proyecto es normal.", "Git", DeepCleanRisk.CACHE, DeepCleanBundle.EDITORS_DEV),
    ".gk":               FolderProfile("Configuración de GitKraken (cliente visual de Git). Si no lo usás, se puede borrar.", "GitKraken", DeepCleanRisk.CACHE, DeepCleanBundle.EDITORS_DEV),
    ".ssh":              FolderProfile("Tus claves SSH para conectarte a GitHub y servidores remotos. NUNCA BORRAR — perdés acceso a todos tus repos.", "OpenSSH", DeepCleanRisk.SYSTEM, DeepCleanBundle.EDITORS_DEV),
    ".vscode":           FolderProfile("Tu configuración personal de VS Code: themes, keybindings, snippets. Si lo borrás, perdés toda tu personalización.", "VS Code", DeepCleanRisk.CRITICAL, DeepCleanBundle.EDITORS_DEV),
    ".config":           FolderProfile("Configuración de herramientas CLI (git, opencode, etc.). Pesa poco y es necesario para varias herramientas.", "Varias herramientas", DeepCleanRisk.CRITICAL, DeepCleanBundle.EDITORS_DEV),
    ".local":            FolderProfile("Binarios (claude.exe, uv.exe) y datos de apps. Contiene herramientas activas. Revisá subcarpetas — puede acumular GBs en cache/snapshots.", "Apps estilo Linux", DeepCleanRisk.CRITICAL, DeepCleanBundle.EDITORS_DEV),
    ".bun":              FolderProfile("Runtime Bun (alternativa a Node.js). Si no lo usás conscientemente, se puede borrar sin problema.", "Bun", DeepCleanRisk.CACHE, DeepCleanBundle.EDITORS_DEV),
    ".dotnet":           FolderProfile("Runtime .NET de Microsoft. Pesa muy poco y lo usan muchas apps de Windows internamente.", "Microsoft .NET", DeepCleanRisk.CACHE, DeepCleanBundle.EDITORS_DEV),
    ".cargo":            FolderProfile("Cache de paquetes de Rust. Si no programás en Rust, se puede borrar. Puede pesar varios GB.", "Rust/Cargo", DeepCleanRisk.CACHE, DeepCleanBundle.EDITORS_DEV),
    ".rustup":           FolderProfile("Toolchains de Rust. Si no programás en Rust, se puede borrar.", "Rustup", DeepCleanRisk.CACHE, DeepCleanBundle.EDITORS_DEV),
    ".conda":            FolderProfile("Entornos Python de Conda/Anaconda. Si usás conda, NO borrar — perdés todos los entornos.", "Anaconda/Miniconda", DeepCleanRisk.CRITICAL, DeepCleanBundle.EDITORS_DEV),
    ".antigravity":      FolderProfile("Tu editor de código Antigravity. Contiene configuración y extensiones. NO ELIMINAR si lo usás.", "Antigravity", DeepCleanRisk.CRITICAL, DeepCleanBundle.EDITORS_DEV),
    ".quokka":           FolderProfile("Quokka.js — playground de JavaScript en VS Code. Si no lo usás, se puede borrar.", "Quokka.js", DeepCleanRisk.CACHE, DeepCleanBundle.EDITORS_DEV),
    ".wallaby":          FolderProfile("Wallaby.js — testing en tiempo real de JavaScript. Si no lo usás, se puede borrar.", "Wallaby.js", DeepCleanRisk.CACHE, DeepCleanBundle.EDITORS_DEV),
    ".npm":              FolderProfile("Cache global de npm. Se puede borrar, se regenera al instalar paquetes.", "npm", DeepCleanRisk.CACHE, DeepCleanBundle.EDITORS_DEV),
    ".yarn":             FolderProfile("Cache global de Yarn. Se puede borrar, se regenera al instalar paquetes.", "Yarn", DeepCleanRisk.CACHE, DeepCleanBundle.EDITORS_DEV),
    ".pnpm":             FolderProfile("Cache global de pnpm. Se puede borrar, se regenera al instalar paquetes.", "pnpm", DeepCleanRisk.CACHE, DeepCleanBundle.EDITORS_DEV),
    ".nvm":              FolderProfile("Node Version Manager — versiones de Node.js. Si no lo usás, se puede borrar.", "nvm", DeepCleanRisk.CACHE, DeepCleanBundle.EDITORS_DEV),
    ".fnm":              FolderProfile("Fast Node Manager — versiones de Node.js. Si no lo usás, se puede borrar.", "fnm", DeepCleanRisk.CACHE, DeepCleanBundle.EDITORS_DEV),

    # Cache & Temp
    ".cache":            FolderProfile("Cache de aplicaciones. Se puede borrar sin problema, se regenera solo.", "Varias apps", DeepCleanRisk.CACHE, DeepCleanBundle.CACHE_TEMP),
    ".thumbnails":       FolderProfile("Cache de miniaturas de imágenes. Se puede borrar, se regenera al abrir carpetas con fotos.", "Gestor de archivos", DeepCleanRisk.CACHE, DeepCleanBundle.CACHE_TEMP),
    ".streamlit":        FolderProfile("Configuración de Streamlit. Si usás Streamlit en tus proyectos, dejala. Pesa muy poco.", "Streamlit", DeepCleanRisk.CACHE, DeepCleanBundle.CACHE_TEMP),
    ".ms-ad":            FolderProfile("Datos temporales de Microsoft Active Directory. Se puede borrar sin problema.", "Microsoft", DeepCleanRisk.CACHE, DeepCleanBundle.CACHE_TEMP),
    ".gsutil":           FolderProfile("Google Cloud Storage CLI. Si no usás Google Cloud, se puede borrar.", "Google Cloud", DeepCleanRisk.CACHE, DeepCleanBundle.CACHE_TEMP),
    ".aws":              FolderProfile("Credenciales de AWS. Si usás Amazon Web Services, NO borrar — perdés acceso. Si no, se puede eliminar.", "AWS CLI", DeepCleanRisk.CRITICAL, DeepCleanBundle.EDITORS_DEV),
    ".azure":            FolderProfile("Credenciales de Azure. Si usás Microsoft Azure, NO borrar — perdés acceso. Si no, se puede eliminar.", "Azure CLI", DeepCleanRisk.CRITICAL, DeepCleanBundle.EDITORS_DEV),
    ".docker":           FolderProfile("Configuración de Docker. Si usás contenedores, NO borrar. Si no tenés Docker instalado, se puede eliminar.", "Docker", DeepCleanRisk.CRITICAL, DeepCleanBundle.EDITORS_DEV),
}

SYSTEM_ROOT_KNOWLEDGE: dict[str, FolderProfile] = {
    "windows.old": FolderProfile(
        "Copia de la instalación anterior de Windows (normalmente 15-30 GB). Seguro después de una actualización exitosa.",
        "Windows Update", DeepCleanRisk.CACHE, DeepCleanBundle.WINDOWS_SYSTEM,
        delete_instructions="No se puede borrar desde esta app.\n\n"
        "Pasos para eliminarlo:\n"
        "1. Abrí Configuración (Windows + I)\n"
        "2. Andá a Sistema → Almacenamiento\n"
        "3. Esperá que cargue y hacé clic en 'Archivos temporales'\n"
        "4. Marcá 'Instalación(es) anterior(es) de Windows'\n"
        "5. Hacé clic en 'Quitar archivos'",
    ),
    "esd": FolderProfile("Archivos de descarga de Windows Update", "Windows Update", DeepCleanRisk.CACHE, DeepCleanBundle.WINDOWS_SYSTEM),
    "drivers": FolderProfile("Backups de instaladores de drivers", "Fabricantes de hardware", DeepCleanRisk.CACHE, DeepCleanBundle.WINDOWS_SYSTEM),
    "onedrivetemp": FolderProfile("Archivos temporales de sincronización de OneDrive", "Microsoft OneDrive", DeepCleanRisk.CACHE, DeepCleanBundle.WINDOWS_SYSTEM),
    "inetpub": FolderProfile("Servidor web IIS (vacío = nunca usado)", "Windows IIS", DeepCleanRisk.CACHE, DeepCleanBundle.WINDOWS_SYSTEM),
    "mats": FolderProfile("Logs de diagnóstico de Microsoft", "Microsoft Support", DeepCleanRisk.CACHE, DeepCleanBundle.WINDOWS_SYSTEM),
    "msocache": FolderProfile("Cache del instalador de Microsoft Office", "Microsoft Office", DeepCleanRisk.CACHE, DeepCleanBundle.WINDOWS_SYSTEM),
    "intel": FolderProfile("Archivos temporales de drivers Intel", "Intel", DeepCleanRisk.CACHE, DeepCleanBundle.WINDOWS_SYSTEM),
}

# Map folder names to known process names for in-use detection
_PROCESS_MAP: dict[str, str] = {
    ".ollama": "ollama",
    ".vscode": "Code.exe",
    ".cursor": "Cursor.exe",
    ".antigravity": "antigravity",
    ".docker": "Docker Desktop.exe",
}


# ── Scanner Functions ────────────────────────────────────────────────────

def scan_deep(
    progress_cb: Callable[[int], None] | None = None,
) -> DeepCleanResult:
    """Scan user HOME and system root for cleanable folders.

    Returns DeepCleanResult with entries. Sizes are set to None initially;
    the presenter should calculate them asynchronously.
    """
    home = os.path.expanduser("~")
    entries: list[DeepCleanEntry] = []
    errors: list[str] = []

    # Phase 1: Scan home dotfiles
    try:
        home_entries = _scan_home_dotfiles(home)
        entries.extend(home_entries)
    except OSError as e:
        errors.append(f"Error escaneando HOME: {e}")

    if progress_cb:
        progress_cb(50)

    # Phase 2: Scan system root
    try:
        root_entries = _scan_system_root("C:\\")
        entries.extend(root_entries)
    except OSError as e:
        errors.append(f"Error escaneando C:\\: {e}")

    if progress_cb:
        progress_cb(90)

    # Apply special intelligence
    running_processes = _get_running_processes()
    for entry in entries:
        entry.is_in_use = _check_in_use(entry.name, running_processes)
        note = _detect_special_intelligence(entry.name, entry.path, home)
        if note:
            entry.special_note = note
        # Override risk for in-use entries
        if entry.is_in_use and entry.risk == DeepCleanRisk.CACHE:
            entry.risk = DeepCleanRisk.ACTIVE

    if progress_cb:
        progress_cb(100)

    return DeepCleanResult(
        entries=entries,
        total_scanned=len(entries),
        total_recoverable_bytes=0,  # Updated after async size calculation
        scan_errors=errors,
    )


def calculate_folder_size(path: str) -> int:
    """Recursively calculate folder size in bytes. Handles permission errors."""
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += calculate_folder_size(entry.path)
            except (PermissionError, OSError):
                continue
    except (PermissionError, OSError):
        pass
    return total


def _scan_home_dotfiles(home: str) -> list[DeepCleanEntry]:
    """Scan user home for dot-prefixed folders."""
    entries: list[DeepCleanEntry] = []
    try:
        for item in os.scandir(home):
            if not item.is_dir(follow_symlinks=False):
                continue
            if not item.name.startswith("."):
                continue

            name_lower = item.name.lower()
            profile = KNOWLEDGE_BASE.get(name_lower) or KNOWLEDGE_BASE.get(item.name)

            if profile:
                entry = DeepCleanEntry(
                    path=item.path,
                    name=item.name,
                    size_bytes=None,
                    risk=profile.risk,
                    bundle=profile.bundle,
                    description=profile.description,
                    creator=profile.creator,
                    last_modified=_get_mtime(item.path),
                    is_in_use=False,
                    special_note=None,
                    delete_instructions=profile.delete_instructions,
                )
            else:
                entry = _classify_unknown_folder(item.name, item.path)

            entries.append(entry)
    except PermissionError:
        pass
    return entries


def _scan_system_root(root: str) -> list[DeepCleanEntry]:
    """Scan C:\\ for non-system directories matching knowledge base."""
    entries: list[DeepCleanEntry] = []
    try:
        for item in os.scandir(root):
            if not item.is_dir(follow_symlinks=False):
                continue

            name_lower = item.name.lower()

            # Skip protected system folders
            if name_lower in SYSTEM_ROOT_PROTECTED:
                continue

            # Skip user-data folders
            if name_lower in ("users",):
                continue

            profile = SYSTEM_ROOT_KNOWLEDGE.get(name_lower)
            if profile:
                entry = DeepCleanEntry(
                    path=item.path,
                    name=item.name,
                    size_bytes=None,
                    risk=profile.risk,
                    bundle=profile.bundle,
                    description=profile.description,
                    creator=profile.creator,
                    last_modified=_get_mtime(item.path),
                    is_in_use=False,
                    special_note=None,
                    delete_instructions=profile.delete_instructions,
                )
                entries.append(entry)
    except PermissionError:
        pass
    return entries


def _get_mtime(path: str) -> float | None:
    """Get last modification time, or None on error."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def _get_running_processes() -> set[str]:
    """Get set of currently running process names (lowercase)."""
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        processes = set()
        for line in result.stdout.splitlines():
            parts = line.strip().strip('"').split('","')
            if parts:
                processes.add(parts[0].lower())
        return processes
    except (subprocess.TimeoutExpired, OSError):
        return set()


def _check_in_use(folder_name: str, running_processes: set[str]) -> bool:
    """Check if a folder's associated process is currently running."""
    process_name = _PROCESS_MAP.get(folder_name.lower(), "").lower()
    if not process_name:
        return False
    return any(process_name in p for p in running_processes)


def _detect_special_intelligence(name: str, path: str, home: str) -> str | None:
    """Apply special detection rules."""
    name_lower = name.lower()

    # .git in HOME = accidental
    if name_lower == ".git" and os.path.dirname(path) == home:
        return ("⚠️ ACCIDENTAL — Probablemente creado por una herramienta. "
                "Tu carpeta de usuario NO debería ser un repositorio git. "
                "Esto puede desperdiciar GIGAS de espacio.")

    # .local with large share subfolder
    if name_lower == ".local":
        share_path = os.path.join(path, "share")
        if os.path.isdir(share_path):
            try:
                for item in os.scandir(share_path):
                    if item.is_dir(follow_symlinks=False):
                        return ("⚠️ Contiene subcarpetas en .local/share que pueden "
                                "acumular GBs de datos (snapshots, logs). "
                                "Revisá cada subcarpeta individualmente.")
            except PermissionError:
                pass

    return None


def _classify_unknown_folder(name: str, path: str) -> DeepCleanEntry:
    """Classify a dot-folder not in the knowledge base."""
    return DeepCleanEntry(
        path=path,
        name=name,
        size_bytes=None,
        risk=DeepCleanRisk.CACHE,
        bundle=DeepCleanBundle.UNKNOWN,
        description=f"Carpeta de configuración desconocida ({name})",
        creator="Desconocido",
        last_modified=_get_mtime(path),
        is_in_use=False,
        special_note=None,
        delete_instructions=None,
    )


def format_size(size_bytes: int | None) -> str:
    """Format bytes into a human-readable string."""
    if size_bytes is None:
        return "Calculando..."
    if size_bytes == 0:
        return "Vacío"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
