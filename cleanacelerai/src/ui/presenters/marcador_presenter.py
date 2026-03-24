"""Presenter: coordinates bookmark-manager service with MarcadorView."""
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import subprocess
import threading

from ...services.bookmark_manager import (
    clean_bookmark_name,
    deep_categorize_bookmarks,
    delete_bookmarks_by_id,
    detect_browsers,
    load_bookmarks,
    organize_bookmarks_into_folders,
    subcategorize_url,
)

if TYPE_CHECKING:
    from ..views.marcador_view import MarcadorView


class MarcadorPresenter:
    """Mediates between MarcadorView and the bookmark-manager service."""

    def __init__(self, view: "MarcadorView") -> None:
        self.view = view
        self._navegadores: dict[str, str] = detect_browsers()
        self._ruta_actual: str | None = None
        self._last_bookmarks: list | None = None
        self._already_organized: bool = False

    # ── Browser detection ────────────────────────────────────────────────

    @staticmethod
    def _get_browser_process(nav_name: str) -> str | None:
        """Map a browser display name to its process name."""
        nav_lower = nav_name.lower()
        if "chrome" in nav_lower:
            return "chrome.exe"
        if "edge" in nav_lower:
            return "msedge.exe"
        if "brave" in nav_lower:
            return "brave.exe"
        return None

    def _check_browser_closed(self) -> bool:
        """Check if the SELECTED browser is closed. Returns True if OK."""
        nav = self.view._cmb_nav.get() if hasattr(self.view, '_cmb_nav') else ""
        process_name = self._get_browser_process(nav)
        if not process_name:
            return True

        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=5,
            )
            if process_name.lower() in result.stdout.lower():
                browser = nav.split(" —")[0].split(" (")[0]
                self.view.show_error(
                    "Navegador abierto",
                    f"¡{browser} está abierto!\n\n"
                    "DEBES cerrar {browser} COMPLETAMENTE antes de organizar o limpiar marcadores.\n\n"
                    "Si lo cerraste pero sigue apareciendo, revisá la bandeja del sistema "
                    "(esquina inferior derecha) y cerralo desde ahí.",
                )
                return False
        except Exception:
            pass
        return True

    # ── Public API ─────────────────────────────────────────────────────────

    def get_browser_names(self) -> list[str]:
        """Return the list of detected browser names."""
        return list(self._navegadores.keys()) if self._navegadores else [
            "Ningún navegador compatible detectado"
        ]

    def analyze(self, nav: str) -> None:
        """Load and categorize bookmarks for the selected browser."""
        if nav not in self._navegadores:
            self.view.show_error("Error", "No se encontró el archivo de marcadores.")
            return

        self._ruta_actual = self._navegadores[nav]
        self.view.clear_tree()

        try:
            bookmarks = load_bookmarks(self._ruta_actual)

            if not bookmarks:
                self.view.show_info("Aviso", f"No tienes ningún marcador guardado en {nav}.")
                return

            # Apply clean names and store originals
            for b in bookmarks:
                b.original_name = b.name
                b.name = clean_bookmark_name(b.name, b.url)

            self._last_bookmarks = bookmarks
            self._already_organized = False

            agrupados: dict[str, list] = defaultdict(list)
            for b in bookmarks:
                agrupados[b.category].append(b)

            self.view.show_bookmarks(agrupados)

        except Exception as e:
            self.view.show_error("Error de Lectura", f"No se pudo leer el archivo: {e}")

    def delete_bookmarks(self, ids: list[str]) -> None:
        """Delete bookmarks by ID from the current bookmark file."""
        if not ids or not self._ruta_actual:
            return

        if not self._check_browser_closed():
            return

        try:
            delete_bookmarks_by_id(self._ruta_actual, ids)
            self.view.show_info(
                "Éxito",
                f"Se han eliminado {len(ids)} marcadores repetidos.\n"
                "¡Abre tu navegador para comprobarlo!\n\n"
                "(Se guardó una copia de seguridad en la misma carpeta por si acaso).",
                refresh=True,
            )
        except PermissionError:
            self.view.show_error(
                "Error de Permisos",
                "No se pudo modificar el archivo. "
                "Asegúrate de CERRAR el navegador por completo e inténtalo de nuevo.",
            )
        except Exception as e:
            self.view.show_error("Error Inesperado", f"Ocurrió un error: {e}")

    def organize(self, nav: str) -> None:
        """Organize bookmarks into category folders in the browser's Bookmarks file."""
        if nav not in self._navegadores:
            self.view.show_error("Error", "No se encontró el archivo de marcadores.")
            return

        if not self._last_bookmarks:
            self.view.show_warning(
                "Aviso",
                "Primero debes categorizar los marcadores con '1. Categorizar con IA'.",
            )
            return

        if not self._check_browser_closed():
            return

        # Check if already organized
        if self._already_organized:
            from tkinter import messagebox
            if not messagebox.askyesno(
                "Ya organizado",
                "Los marcadores ya fueron organizados en esta sesión.\n\n"
                "¿Querés volver a organizar? (Esto reconstruye las carpetas desde cero)",
            ):
                return

        self._ruta_actual = self._navegadores[nav]

        try:
            count = organize_bookmarks_into_folders(self._ruta_actual, self._last_bookmarks)
            self._already_organized = True
            if count > 0:
                self.view.show_info(
                    "Organización Completada",
                    f"Se han organizado {count} marcadores en carpetas por categoría.\n"
                    "Abre tu navegador para comprobarlo.\n\n"
                    "(Se guardó una copia de seguridad en la misma carpeta por si acaso).",
                )
            else:
                self.view.show_warning(
                    "Sin Cambios",
                    "No se encontraron marcadores para organizar.",
                )
        except PermissionError:
            self.view.show_error(
                "Error de Permisos",
                "No se pudo modificar el archivo. "
                "Asegurate de CERRAR el navegador por completo e intentalo de nuevo.",
            )
        except Exception as e:
            self.view.show_error("Error Inesperado", f"Ocurrio un error: {e}")

    def deep_categorize(self) -> None:
        """Fetch uncategorized bookmark pages and re-categorize by content."""
        if not self._last_bookmarks:
            self.view.show_warning(
                "Aviso",
                "Primero debes categorizar los marcadores con '1. Categorizar con IA'.",
            )
            return

        uncategorized = sum(1 for b in self._last_bookmarks if "Generales" in b.category)
        if uncategorized == 0:
            self.view.show_info("Todo categorizado", "No quedan marcadores sin categorizar.")
            return

        self.view.set_deep_categorize_enabled(False)
        self.view.show_deep_progress(True)

        threading.Thread(
            target=self._run_deep_categorize,
            daemon=True,
        ).start()

    def _run_deep_categorize(self) -> None:
        """Background thread for deep categorization."""
        try:
            recategorized = deep_categorize_bookmarks(
                self._last_bookmarks,
                progress_cb=lambda v: self.view.after(
                    0, self.view.update_deep_progress, v,
                ),
            )
            self.view.after(0, self._on_deep_categorize_done, recategorized)
        except Exception as e:
            self.view.after(0, self._on_deep_categorize_error, str(e))

    def _on_deep_categorize_done(self, recategorized: int) -> None:
        """Main thread callback when deep categorization completes."""
        self.view.show_deep_progress(False)
        self.view.set_deep_categorize_enabled(True)

        remaining = sum(1 for b in self._last_bookmarks if "Generales" in b.category)

        # Refresh the view with updated categories
        from collections import defaultdict
        agrupados: dict[str, list] = defaultdict(list)
        for b in self._last_bookmarks:
            agrupados[b.category].append(b)
        self.view.clear_tree()
        self.view.show_bookmarks(agrupados)

        # Mark as not organized since categories changed
        self._already_organized = False

        from tkinter import messagebox
        if recategorized > 0:
            do_organize = messagebox.askyesno(
                "Categorización Profunda Completada",
                f"Se re-categorizaron {recategorized} marcadores visitando sus páginas web.\n"
                f"Quedan {remaining} sin categorizar.\n\n"
                "¿Querés organizar en carpetas ahora? (Cerrá el navegador primero)",
            )
            if do_organize:
                self.organize(self.view._cmb_nav.get())
        else:
            self.view.show_info(
                "Categorización Profunda",
                f"No se pudieron re-categorizar marcadores adicionales.\n"
                f"Quedan {remaining} sin categorizar (páginas sin contenido identificable).",
            )

    def _on_deep_categorize_error(self, error_msg: str) -> None:
        self.view.show_deep_progress(False)
        self.view.set_deep_categorize_enabled(True)
        self.view.show_error("Error", f"Error durante la categorización profunda:\n{error_msg}")
