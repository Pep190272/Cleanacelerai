"""Presenter: coordinates duplicate-finder service with the duplicates view."""
from __future__ import annotations

import datetime
import threading
from typing import TYPE_CHECKING, Callable

from ...domain.models import DuplicateGroup, RiskLevel
from ...domain.risk_evaluator import evaluate_file_risk, format_risk_label, get_risk_tag
from ...infrastructure.file_system import open_in_explorer, safe_delete
from ...services.duplicate_finder import find_duplicates

if TYPE_CHECKING:
    from ..views.duplicates_view import DuplicatesView


class DuplicatesPresenter:
    """Mediates between DuplicatesView and the duplicate-finder service."""

    def __init__(self, view: "DuplicatesView") -> None:
        self.view = view
        self._scanning = False
        self._protected_keywords: list[str] = []
        self._protected_folders: list[str] = []

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
        self._scanning = True
        self.view.on_scan_started()
        threading.Thread(
            target=self._scan_worker,
            args=(paths,),
            daemon=True,
        ).start()

    def cancel_scan(self) -> None:
        """Signal the background thread to stop."""
        self._scanning = False

    def _scan_worker(self, paths: list[str]) -> None:
        groups = find_duplicates(
            paths=paths,
            protected_keywords=self._protected_keywords,
            on_progress=self.view.log,
            should_continue=lambda: self._scanning,
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
