"""Service: find duplicate files using size-first + SHA-256 hash strategy."""
from __future__ import annotations

import hashlib
import os
from collections import defaultdict
from typing import Callable, Iterator

from ..domain.constants import (
    ARCHIVOS_PROHIBIDOS,
    CARPETAS_SISTEMA,
    EXTENSIONES_SISTEMA,
    PATHS_BLOQUEADOS_SCAN,
)
from ..domain.models import DuplicateGroup, FileInfo
from ..domain.utils import normalizar_ruta


def _hash_file(filepath: str) -> str | None:
    """
    Compute SHA-256 hash of a file's content.

    Args:
        filepath: Absolute path to the file.

    Returns:
        Hex SHA-256 digest, or None if the file cannot be read.
    """
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (PermissionError, OSError, IOError):
        return None


def find_duplicates(
    paths: list[str],
    protected_keywords: list[str] | None = None,
    on_progress: Callable[[str], None] | None = None,
    should_continue: Callable[[], bool] | None = None,
    *,
    blocked_paths: tuple[str, ...] | None = None,
    allowed_extensions: tuple[str, ...] | None = None,
    min_size_bytes: int = 1024,
) -> list[DuplicateGroup]:
    """
    Find duplicate files across the given paths.

    Strategy:
        1. Group files by size (cheap — no I/O for content).
        2. Hash only files that share a size with another file.
        3. Return groups of 2+ files with identical hashes.

    Args:
        paths: List of root directories to scan.
        protected_keywords: Keywords — folders containing these are skipped.
        on_progress: Optional callback for status messages.
        should_continue: Callable returning False to cancel mid-scan.
        blocked_paths: Override for directory-level blocklist. Defaults to
            PATHS_BLOQUEADOS_SCAN (full union). Resolved at call time so
            unittest.mock.patch on the module-level constant still works.
        allowed_extensions: Tuple of lowercase extensions to accept (e.g.
            EXTENSIONES_ASSETS_BINARIOS). None means no extension filter.
            Applied BEFORE os.path.getsize for safety + performance.
        min_size_bytes: Files <= this size are skipped. Default 1024 (1 KB).

    Returns:
        List of DuplicateGroup, each with 2+ identical files.
    """
    if protected_keywords is None:
        protected_keywords = []
    if should_continue is None:
        should_continue = lambda: True
    if blocked_paths is None:
        blocked_paths = PATHS_BLOQUEADOS_SCAN

    def log(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    # ── Phase 1: group by size ──────────────────────────────────────────────
    archivos_por_tamano: defaultdict[int, list[str]] = defaultdict(list)
    procesados = 0

    for ruta_base in paths:
        log(f"Rastreando: {ruta_base}")
        for root, dirs, files in os.walk(ruta_base):
            if not should_continue():
                log("\n🛑 Búsqueda cancelada.")
                return []

            root_lower = root.lower()

            # Skip system folders
            dirs[:] = [d for d in dirs if d.lower() not in CARPETAS_SISTEMA]
            if CARPETAS_SISTEMA.intersection(normalizar_ruta(root)):
                continue

            # Skip globally blocked paths (dev/project folders).
            # Trailing sep makes blocklist entries like '\Mis_proyectos\' also
            # match a root that is exactly the blocked folder ('D:\Mis_proyectos').
            root_norm = os.path.normpath(root).lower() + os.sep
            if any(blocked.lower() in root_norm for blocked in blocked_paths):
                dirs.clear()
                continue

            # Skip protected keyword folders
            if any(kw.lower() in root_lower for kw in protected_keywords):
                dirs.clear()
                continue

            for file in files:
                if not should_continue():
                    log("\n🛑 Búsqueda cancelada.")
                    return []

                if file.lower() in ARCHIVOS_PROHIBIDOS:
                    continue
                if file.lower().endswith(EXTENSIONES_SISTEMA):
                    continue

                # Extension whitelist gate — runs BEFORE getsize (safety + perf).
                # None means no filter (default behavior, no extension rejected).
                if allowed_extensions is not None and not file.lower().endswith(allowed_extensions):
                    continue

                filepath = os.path.join(root, file)
                try:
                    size = os.path.getsize(filepath)
                    if size > min_size_bytes:
                        archivos_por_tamano[size].append(filepath)
                    procesados += 1
                    if procesados % 100 == 0:
                        log(f"Analizados {procesados} elementos...")
                except OSError:
                    pass

    # ── Phase 2: hash candidates ────────────────────────────────────────────
    candidatos = [rutas for rutas in archivos_por_tamano.values() if len(rutas) > 1]
    hashes: defaultdict[str, list[str]] = defaultdict(list)

    log("\nCruzando hashes de contenido (huella digital)...")
    for grupo in candidatos:
        if not should_continue():
            log("\n🛑 Búsqueda cancelada.")
            return []
        for filepath in grupo:
            h = _hash_file(filepath)
            if h:
                hashes[h].append(filepath)

    # ── Phase 3: build DuplicateGroup objects ───────────────────────────────
    groups: list[DuplicateGroup] = []
    for h, rutas in hashes.items():
        if len(rutas) < 2:
            continue
        file_infos: list[FileInfo] = []
        for ruta in rutas:
            try:
                size = os.path.getsize(ruta)
                mtime = os.path.getmtime(ruta)
                file_infos.append(FileInfo(path=ruta, size=size, mtime=mtime, hash=h))
            except OSError:
                pass
        if len(file_infos) >= 2:
            groups.append(DuplicateGroup(hash=h, files=file_infos))

    log("\nAnálisis completado.")
    return groups
