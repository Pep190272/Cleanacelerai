"""Presenter: coordinates file-renamer service with RenombradoView."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ...services.file_renamer import RenameEntry, apply_rename_plan, build_rename_plan

if TYPE_CHECKING:
    from ..views.renombrado_view import RenombradoView


class RenombradoPresenter:
    """Mediates between RenombradoView and the file-renamer service."""

    def __init__(self, view: "RenombradoView") -> None:
        self.view = view
        self._plan: list[RenameEntry] = []

    # ── Public API ─────────────────────────────────────────────────────────

    def build_preview(self, ruta: str, base: str) -> None:
        """Build a rename plan from *ruta* + *base* and populate the view preview."""
        plan: list[RenameEntry] = []
        try:
            plan = build_rename_plan(ruta, base)
        except OSError as e:
            self.view.show_error("Error", f"No se pudo leer la carpeta: {e}")
            return

        self._plan = plan
        self.view.show_preview(plan)

    def apply(self, ruta: str, base: str) -> None:
        """Apply the current rename plan, then refresh the preview.

        Args:
            ruta: The folder path (needed to rebuild the preview after renaming).
            base: The base name used for renaming (needed to rebuild the preview).
        """
        if not self._plan:
            return

        exitos, errores = apply_rename_plan(self._plan)
        self.view.show_info("Éxito", f"Se han renombrado {exitos} archivos correctamente.")
        if errores:
            self.view.show_warning(
                "Errores",
                f"No se pudieron renombrar {len(errores)} archivos:\n"
                + "\n".join(errores[:5]),
            )
        # Refresh preview so the tree reflects the new names
        self.build_preview(ruta, base)
