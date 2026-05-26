"""Presenter: coordinates duplicate-finder service with the duplicates view."""
from __future__ import annotations

import datetime
import threading
from typing import TYPE_CHECKING, Callable

from ...domain.constants import (
    BINARY_MODE_SIZE_FLOOR_BYTES,
    EXTENSIONES_ASSETS_BINARIOS,
    PATHS_BLOQUEADOS_SCAN,
    PATHS_BLOQUEADOS_SCAN_TECH,
)
from ...domain.models import DuplicateGroup, RiskLevel
from ...domain.risk_evaluator import evaluate_file_risk, format_risk_label, get_risk_tag
from ...infrastructure.config_service import ConfigService
from ...infrastructure.file_system import open_in_explorer, safe_delete
from ...services.duplicate_finder import find_duplicates

if TYPE_CHECKING:
    from ..views.duplicates_view import DuplicatesView


class DuplicatesPresenter:
    """Mediates between DuplicatesView and the duplicate-finder service."""

    def __init__(
        self,
        view: "DuplicatesView",
        config_service: ConfigService | None = None,
        initial_binary_mode: bool = False,
    ) -> None:
        self.view = view
        self._config_service = config_service
        self._scanning = False
        self._protected_keywords: list[str] = []
        self._protected_folders: list[str] = []
        self._binary_mode: bool = initial_binary_mode

    def is_path_blocked(self, path: str) -> bool:
        """
        Return True if the given path matches any entry in the effective blocklist.

        In normal mode (binary_mode=False): checks against PATHS_BLOQUEADOS_SCAN
        (full union). In binary mode: checks against PATHS_BLOQUEADOS_SCAN_TECH
        only, so project paths like \\Mis_proyectos\\ and \\Local Sites\\ are allowed.

        Normalizes separators and appends a trailing separator before comparing,
        so blocklist entries like '\\Mis_proyectos\\' also match a path that is
        exactly the blocked folder (e.g. 'D:\\Mis_proyectos').

        Args:
            path: Folder path chosen by the user.

        Returns:
            True if the path must be refused.
        """
        import os
        path_norm = os.path.normpath(path).lower() + os.sep
        blocklist = (
            PATHS_BLOQUEADOS_SCAN_TECH
            if self._binary_mode
            else PATHS_BLOQUEADOS_SCAN
        )
        return any(blocked.lower() in path_norm for blocked in blocklist)

    def set_binary_mode(self, enabled: bool) -> None:
        """Update binary mode flag and persist to config. Surfaces save errors via the view."""
        self._binary_mode = enabled
        if self._config_service is None:
            return
        try:
            current = self._config_service.load(defaults={})
            current["binary_assets_mode_enabled"] = enabled
            self._config_service.save(current)
        except Exception as exc:  # OSError, PermissionError, JSONDecodeError, etc.
            self.view.show_error(
                "Error guardando configuración",
                f"No se pudo guardar la preferencia de modo binario:\n\n{exc}\n\n"
                "El modo está activo en esta sesión pero no persistirá al reiniciar.",
            )

    def is_auto_select_allowed(self) -> bool:
        """Return False when binary mode is ON — auto-select is unsafe in that mode."""
        return not self._binary_mode

    def set_protection(
        self,
        keywords: list[str],
        folders: list[str],
    ) -> None:
        """Update the protection lists used during scanning."""
        self._protected_keywords = keywords
        self._protected_folders = folders

    def start_scan(self, paths: list[str]) -> None:
        """Start the duplicate scan in a background thread."""
        if not paths:
            return

        # Snapshot mode at scan-start time (threading rule: worker never reads _binary_mode).
        binary = self._binary_mode
        blocked_paths = (
            PATHS_BLOQUEADOS_SCAN_TECH if binary else PATHS_BLOQUEADOS_SCAN
        )
        allowed_extensions = EXTENSIONES_ASSETS_BINARIOS if binary else None
        min_size = BINARY_MODE_SIZE_FLOOR_BYTES if binary else 1024

        self._scanning = True
        self.view.on_scan_started()
        threading.Thread(
            target=self._scan_worker,
            args=(paths, blocked_paths, allowed_extensions, min_size),
            daemon=True,
        ).start()

    def cancel_scan(self) -> None:
        """Signal the background thread to stop."""
        self._scanning = False

    def _scan_worker(
        self,
        paths: list[str],
        blocked_paths: tuple[str, ...],
        allowed_extensions: tuple[str, ...] | None,
        min_size_bytes: int,
    ) -> None:
        groups = find_duplicates(
            paths=paths,
            protected_keywords=self._protected_keywords,
            on_progress=self.view.log,
            should_continue=lambda: self._scanning,
            blocked_paths=blocked_paths,
            allowed_extensions=allowed_extensions,
            min_size_bytes=min_size_bytes,
        )
        self.view.after(0, self._display_results, groups)

    def _display_results(self, groups: list[DuplicateGroup]) -> None:
        """Populate the view with scan results (called on main thread)."""
        grupos_count = 0
        self.view.log("\nResultados de la IA:")

        for group in groups:
            evaluaciones = []
            for fi in group.files:
                risk = evaluate_file_risk(
                    fi.path,
                    self._protected_keywords,
                    self._protected_folders,
                )
                label = format_risk_label(risk)
                try:
                    fecha_str = datetime.datetime.fromtimestamp(fi.mtime).strftime("%d/%m/%Y %H:%M")
                except OSError:
                    fecha_str = "Desconocida"
                evaluaciones.append((fi.path, label, risk, fi.mtime, fecha_str))

            # Only show groups that have at least one safe file
            if not any(e[2] == RiskLevel.SAFE for e in evaluaciones):
                continue

            # Sort: protected first, then by date descending, then by path length
            evaluaciones.sort(
                key=lambda item: (
                    0 if item[2] not in (RiskLevel.SAFE, RiskLevel.PERSONAL) else (
                        1 if item[2] == RiskLevel.PERSONAL else 2
                    ),
                    -item[3],
                    len(item[0]),
                )
            )

            self.view.add_duplicate_group(group, evaluaciones)
            grupos_count += 1

        if grupos_count == 0:
            self.view.log(
                "No se encontraron duplicados eliminables. "
                "Si esperabas resultados, revisa que la carpeta no contenga código de proyecto "
                "(estarían protegidos) y que tenga archivos > 1 KB."
            )

        self.view.on_scan_finished(grupos_count)

    def auto_select(self) -> int:
        """Auto-select safe files for deletion. Returns count selected."""
        return self.view.auto_select_safe_files()

    def delete_selected(self) -> None:
        """Delete the currently selected files in the view."""
        items = self.view.get_selected_deletable_items()
        if not items:
            return

        exitos = 0
        errores = 0

        for item_id, ruta, risk_label in items:
            if any(k in risk_label for k in ("CRÍTICO", "PROYECTO", "DOTFILE")):
                self.view.show_error(
                    "Error de Seguridad",
                    f"DENEGADO:\n{ruta}\n\nLa IA ha bloqueado el borrado de este archivo porque está protegido.",
                )
                return

            ok, err = safe_delete(ruta)
            if ok:
                self.view.remove_item(item_id)
                exitos += 1
            else:
                errores += 1
                self.view.log(f"Error borrando {ruta}: {err}")

        self.view.cleanup_orphan_groups()

        if errores > 0:
            self.view.show_warning(
                "Limpieza Incompleta",
                f"Se eliminaron {exitos} archivos.\n\n"
                f"⚠️ {errores} archivos no se pudieron borrar porque Windows los está usando. "
                "Cierra todo e inténtalo de nuevo.",
            )
        else:
            self.view.show_info(
                "Éxito",
                f"¡Limpieza perfecta! Se han eliminado {exitos} archivos duplicados.",
            )

    def open_in_explorer(self, path: str) -> None:
        open_in_explorer(path)
