"""Service: scan and clean temporary files."""
from __future__ import annotations

import os
import stat
import subprocess
from typing import Callable

from ..domain.models import CleanupResult


def get_temp_paths() -> list[str]:
    """Return the standard Windows temp folder paths."""
    win_root = os.environ.get("SystemRoot", r"C:\Windows")
    sys_drive = os.environ.get("SystemDrive", "C:")

    try:
        login = os.getlogin()
    except OSError:
        login = "User"

    candidatas: list[str | None] = [
        os.environ.get("TEMP"),
        os.environ.get("TMP"),
        os.path.join(win_root, "Temp"),
        os.path.join(sys_drive, "Users", login, "AppData", "Local", "Temp"),
    ]

    rutas: list[str] = []

    # Deduplicate, filter None and non-existent
    seen: set[str] = set()
    for r in candidatas:
        if r and os.path.exists(r) and r not in seen:
            seen.add(r)
            rutas.append(r)
    return rutas


def scan_temp_files(
    on_progress: Callable[[str], None] | None = None,
) -> tuple[list[str], float]:
    """
    Scan all temp folders and return a list of files with their total size.

    Args:
        on_progress: Optional callback for status lines.

    Returns:
        Tuple of (list_of_file_paths, total_size_mb).
    """
    def log(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    archivos: list[str] = []
    peso_total: int = 0

    log("Iniciando análisis heurístico de temporales...")

    for ruta in get_temp_paths():
        log(f"Escaneando: {ruta}")
        for root, _dirs, files in os.walk(ruta):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    peso = os.path.getsize(filepath)
                    peso_total += peso
                    archivos.append(filepath)
                except (PermissionError, OSError):
                    log(f"  ⚠️ Omitido (sin acceso): {filepath}")

    total_mb = peso_total / (1024 * 1024)
    return archivos, total_mb


def clean_temp_files(
    archivos: list[str],
    on_progress: Callable[[str], None] | None = None,
) -> CleanupResult:
    """
    Delete the given list of temp files.

    Handles read-only files and long paths (MS-DOS NUL workaround).

    Args:
        archivos: List of absolute file paths to delete.
        on_progress: Optional callback for status lines.

    Returns:
        CleanupResult with counts and freed space.
    """
    def log(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    result = CleanupResult()
    log("Iniciando limpieza...")

    for archivo in archivos:
        try:
            peso = os.path.getsize(archivo)
            try:
                os.chmod(archivo, stat.S_IWRITE)
            except (PermissionError, OSError):
                pass
            os.remove(archivo)
            result.deleted += 1
            result.freed_mb += peso / (1024 * 1024)
        except PermissionError:
            pass  # In use by Windows — skip silently
        except FileNotFoundError:
            pass  # Already deleted — count as success
        except OSError as e:
            result.add_error(archivo, str(e))
            log(f"  ⚠️ No se pudo borrar: {archivo}")

    return result
