"""Presenter: coordinates chaos-advisor service with AsesorView."""
from __future__ import annotations

import concurrent.futures
import os
import shutil
import threading
from tkinter import filedialog
from typing import TYPE_CHECKING, Callable

from ...domain.models import (
    DeepCleanEntry,
    DeepCleanResult,
    DeepCleanRisk,
    DocumentAnalysisResult,
)
from ...infrastructure.file_system import safe_delete
from ...services.chaos_advisor import analyze_folder, explain_element

if TYPE_CHECKING:
    from ..views.asesor_view import AsesorView


class AsesorPresenter:
    """Mediates between AsesorView and the chaos-advisor / file-system services."""

    def __init__(
        self,
        view: "AsesorView",
        get_keywords: Callable[[], list[str]] | None = None,
        get_folders: Callable[[], list[str]] | None = None,
    ) -> None:
        self.view = view
        self._get_keywords = get_keywords or (lambda: [])
        self._get_folders = get_folders or (lambda: [])

        # Document analysis state
        self._doc_folder: str | None = None
        self._doc_result: DocumentAnalysisResult | None = None

        # Deep scan state
        self._deep_result: DeepCleanResult | None = None
        self._deep_entries: list[DeepCleanEntry] = []

    # ── Public API — Orden General (existing) ──────────────────────────────

    def get_keywords(self) -> list[str]:
        return self._get_keywords()

    def get_folders(self) -> list[str]:
        return self._get_folders()

    def analyze(self, carpeta: str, keywords: list[str], folders: list[str]) -> None:
        """Analyze a folder and populate the view with results."""
        try:
            entries = analyze_folder(
                carpeta,
                protected_keywords=keywords,
                protected_folders=folders,
            )
        except PermissionError:
            self.view.show_error("Error", "No tienes permisos para leer esta carpeta.")
            return
        except FileNotFoundError:
            self.view.show_error("Error", "La carpeta ya no existe o fue movida.")
            return
        except OSError as e:
            self.view.show_error("Error", f"No se pudo leer la carpeta: {e}")
            return

        self.view.show_entries(entries)

    def move_items(self, items: list[tuple[str, str, str]], destino: str) -> None:
        """Move the given (item_id, ruta, nombre) tuples to *destino* folder."""
        movidos = 0
        errores: list[str] = []

        for item_id, ruta, nombre in items:
            try:
                shutil.move(ruta, destino)
                movidos += 1
                self.view.remove_item(item_id)
            except shutil.Error as e:
                errores.append(f"{nombre}: {e}")
            except PermissionError as e:
                errores.append(f"{nombre}: Permiso denegado — {e}")
            except OSError as e:
                errores.append(f"{nombre}: {e}")

        msg = f"{movidos} elemento(s) movido(s) a:\n{destino}"
        if errores:
            msg += f"\n\n{len(errores)} error(es):\n" + "\n".join(errores)
            self.view.show_warning("Mover — con errores", msg)
        else:
            self.view.show_info("Mover — completado", msg)

    def delete_items(self, items: list[tuple[str, str, str]]) -> None:
        """Delete the given (item_id, ruta, nombre) tuples."""
        borrados = 0
        errores: list[str] = []

        for item_id, ruta, nombre in items:
            if os.path.isdir(ruta):
                try:
                    shutil.rmtree(ruta)
                    borrados += 1
                    self.view.remove_item(item_id)
                except PermissionError as e:
                    errores.append(f"{nombre}: Permiso denegado — {e}")
                except OSError as e:
                    errores.append(f"{nombre}: {e}")
            else:
                ok, error = safe_delete(ruta)
                if ok:
                    borrados += 1
                    self.view.remove_item(item_id)
                else:
                    errores.append(f"{nombre}: {error}")

        msg = f"{borrados} elemento(s) eliminado(s)."
        if errores:
            msg += f"\n\n{len(errores)} error(es):\n" + "\n".join(errores)
            self.view.show_warning("Borrar — con errores", msg)
        else:
            self.view.show_info("Borrar — completado", msg)

    def explain(self, nombre: str, tipo: str) -> str:
        """Return a forensic explanation for the given element."""
        return explain_element(nombre, tipo)

    # ── Public API — Documentos (new) ──────────────────────────────────────

    def on_select_doc_folder(self) -> None:
        """Called when user clicks select folder button."""
        carpeta = filedialog.askdirectory(
            title="Selecciona la carpeta con documentos PDF"
        )
        if not carpeta:
            return
        self._doc_folder = carpeta
        self.view.set_doc_folder_label(carpeta)
        self.view.set_doc_analyze_enabled(True)
        self.view.set_doc_organize_enabled(False)
        self.view.clear_doc_results()

    def analyze_documents(self) -> None:
        """Start document analysis in a background thread."""
        if not self._doc_folder:
            return

        # Disable buttons and show progress
        self.view.set_doc_analyze_enabled(False)
        self.view.set_doc_organize_enabled(False)
        self.view.show_doc_progress(True)
        self.view.clear_doc_results()

        threading.Thread(
            target=self._run_doc_analysis,
            args=(self._doc_folder,),
            daemon=True,
        ).start()

    def _run_doc_analysis(self, folder: str) -> None:
        """Background thread target for document analysis."""
        from ...services.document_classifier import classify_documents

        try:
            result = classify_documents(
                folder,
                progress_cb=lambda v: self.view.after(
                    0, self.view.update_doc_progress, v,
                ),
            )
            self.view.after(0, self._on_doc_analysis_done, result)
        except Exception as e:
            self.view.after(
                0, self._on_doc_analysis_error, str(e),
            )

    def _on_doc_analysis_done(self, result: DocumentAnalysisResult) -> None:
        """Called on main thread when analysis completes."""
        self._doc_result = result
        self.view.show_doc_progress(False)
        self.view.display_doc_results(result)
        self.view.set_doc_analyze_enabled(True)

        # Enable organize only if there are classified documents
        if result.classifications:
            self.view.set_doc_organize_enabled(True)

    def _on_doc_analysis_error(self, error_msg: str) -> None:
        """Called on main thread when analysis fails."""
        self.view.show_doc_progress(False)
        self.view.set_doc_analyze_enabled(True)
        self.view.show_error(
            "Error en analisis",
            f"No se pudieron analizar los documentos:\n{error_msg}",
        )

    def organize_documents(self) -> None:
        """Move documents into suggested category folders."""
        if not self._doc_result or not self._doc_folder:
            return

        classifications = self._doc_result.classifications
        if not classifications:
            self.view.show_info("Sin documentos", "No hay documentos para organizar.")
            return

        movidos = 0
        errores: list[str] = []

        for doc in classifications:
            suggested = doc.suggested_folder
            if not suggested:
                continue

            # Build target directory (relative to the analyzed folder)
            target_dir = os.path.join(self._doc_folder, suggested)
            target_path = os.path.join(target_dir, doc.name)

            # Skip if source == destination
            if os.path.normpath(doc.path) == os.path.normpath(target_path):
                continue

            try:
                os.makedirs(target_dir, exist_ok=True)
                shutil.move(doc.path, target_path)
                movidos += 1
            except shutil.Error as e:
                errores.append(f"{doc.name}: {e}")
            except PermissionError as e:
                errores.append(f"{doc.name}: Permiso denegado — {e}")
            except OSError as e:
                errores.append(f"{doc.name}: {e}")

        msg = f"{movidos} documento(s) organizados en carpetas."
        if errores:
            msg += f"\n\n{len(errores)} error(es):\n" + "\n".join(errores)
            self.view.show_warning("Organizar — con errores", msg)
        else:
            self.view.show_info("Organizar — completado", msg)

        # Disable organize after execution (files have moved)
        self.view.set_doc_organize_enabled(False)
        self._doc_result = None

    # ── Public API — Limpieza Profunda ─────────────────────────────────────

    def start_deep_scan(self) -> None:
        """Launch deep scan in background thread."""
        self.view.set_deep_scan_enabled(False)
        self.view.set_deep_bulk_enabled(False)
        self.view.show_deep_progress(True)
        self.view.clear_deep_results()
        threading.Thread(target=self._run_deep_scan, daemon=True).start()

    def _run_deep_scan(self) -> None:
        """Background: run scan_deep, then post to main thread."""
        from ...services.deep_scanner import scan_deep

        try:
            result = scan_deep(
                progress_cb=lambda v: self.view.after(0, self.view.update_deep_progress, v),
            )
            self.view.after(0, self._on_deep_scan_done, result)
        except Exception as e:
            self.view.after(0, self._on_deep_scan_error, str(e))

    def _on_deep_scan_done(self, result: DeepCleanResult) -> None:
        """Main thread: display results, then kick off async size calculations."""
        self._deep_result = result
        self._deep_entries = list(result.entries)
        self.view.show_deep_progress(False)
        self.view.display_deep_entries(result.entries)
        self.view.set_deep_scan_enabled(True)

        if result.scan_errors:
            self.view.show_warning(
                "Errores de escaneo",
                "\n".join(result.scan_errors),
            )

        # Kick off async size calculations
        self._calculate_sizes_async(result.entries)

    def _on_deep_scan_error(self, error_msg: str) -> None:
        self.view.show_deep_progress(False)
        self.view.set_deep_scan_enabled(True)
        self.view.show_error(
            "Error en escaneo",
            f"No se pudo completar el escaneo:\n{error_msg}",
        )

    def _calculate_sizes_async(self, entries: list[DeepCleanEntry]) -> None:
        """Calculate folder sizes in parallel background threads."""

        def calc_one(entry: DeepCleanEntry) -> tuple[str, int]:
            from ...services.deep_scanner import calculate_folder_size

            size = calculate_folder_size(entry.path)
            return entry.path, size

        def on_size_done(future: concurrent.futures.Future) -> None:  # type: ignore[type-arg]
            try:
                path, size = future.result()
                # Update entry in our list
                for e in self._deep_entries:
                    if e.path == path:
                        e.size_bytes = size
                        if size == 0:
                            e.risk = DeepCleanRisk.EMPTY
                        break
                self.view.after(0, self.view.update_entry_size, path, size)
                # Recalculate total recoverable
                self.view.after(0, self._update_recoverable_total)
            except Exception:
                pass

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        for entry in entries:
            future = executor.submit(calc_one, entry)
            future.add_done_callback(on_size_done)

    def _update_recoverable_total(self) -> None:
        """Recalculate total recoverable bytes and update summary."""
        total = sum(
            e.size_bytes
            for e in self._deep_entries
            if e.size_bytes is not None
            and e.risk in (DeepCleanRisk.CACHE, DeepCleanRisk.EMPTY)
        )
        if self._deep_result:
            self._deep_result.total_recoverable_bytes = total
        has_recoverable = total > 0
        self.view.set_deep_bulk_enabled(has_recoverable)
        self.view.show_deep_summary(len(self._deep_entries), total)

    def delete_deep_entry(self, path: str) -> None:
        """Delete a single deep-clean entry."""
        # Find the entry
        entry = None
        for e in self._deep_entries:
            if e.path == path:
                entry = e
                break
        if not entry:
            return

        # Check for special delete instructions (e.g., Windows.old)
        if entry.delete_instructions:
            self.view.show_info("Instrucciones de eliminacion", entry.delete_instructions)
            return

        # Block SYSTEM entries
        if entry.risk == DeepCleanRisk.SYSTEM:
            self.view.show_error(
                "No permitido",
                "Esta carpeta es del sistema y no se puede eliminar.",
            )
            return

        # Extra warning for CRITICAL
        from tkinter import messagebox

        if entry.risk == DeepCleanRisk.CRITICAL:
            if not messagebox.askyesno(
                "Carpeta critica",
                f"'{entry.name}' contiene datos importantes:\n{entry.description}\n\n"
                f"Creado por: {entry.creator}\n\n"
                "Estas SEGURO que queres eliminarla? Esta accion no se puede deshacer.",
                icon="warning",
            ):
                return
        else:
            from ...services.deep_scanner import format_size

            size_str = format_size(entry.size_bytes)
            if not messagebox.askyesno(
                "Confirmar eliminacion",
                f"Eliminar '{entry.name}' ({size_str})?\n\n{entry.description}",
            ):
                return

        # Execute deletion
        try:
            shutil.rmtree(path)
            self._deep_entries = [e for e in self._deep_entries if e.path != path]
            self.view.remove_deep_entry(path)
            self.view.show_info("Eliminado", f"'{entry.name}' eliminado correctamente.")
            self._update_recoverable_total()
        except PermissionError:
            self.view.show_error(
                "Error",
                f"Permiso denegado para eliminar '{entry.name}'.\n"
                "Cerra los programas que la usen e intenta de nuevo.",
            )
        except OSError as e:
            self.view.show_error("Error", f"No se pudo eliminar '{entry.name}':\n{e}")

    def bulk_delete_safe(self) -> None:
        """Delete all CACHE + EMPTY entries."""
        from tkinter import messagebox

        from ...services.deep_scanner import format_size

        safe_entries = [
            e
            for e in self._deep_entries
            if e.risk in (DeepCleanRisk.CACHE, DeepCleanRisk.EMPTY)
            and e.size_bytes is not None
            and e.delete_instructions is None
        ]

        if not safe_entries:
            self.view.show_info("Sin elementos", "No hay elementos seguros para eliminar.")
            return

        total_size = sum(e.size_bytes or 0 for e in safe_entries)
        if not messagebox.askyesno(
            "Limpiar todo lo seguro",
            f"Se van a eliminar {len(safe_entries)} carpeta(s) "
            f"({format_size(total_size)}):\n\n"
            + "\n".join(
                f"  - {e.name} ({format_size(e.size_bytes)})"
                for e in safe_entries[:15]
            )
            + ("\n  ..." if len(safe_entries) > 15 else "")
            + "\n\nContinuar?",
        ):
            return

        deleted_paths: set[str] = set()
        deleted = 0
        errors: list[str] = []

        for entry in safe_entries:
            try:
                shutil.rmtree(entry.path)
                self.view.remove_deep_entry(entry.path)
                deleted_paths.add(entry.path)
                deleted += 1
            except (PermissionError, OSError) as e:
                errors.append(f"{entry.name}: {e}")

        self._deep_entries = [
            e for e in self._deep_entries if e.path not in deleted_paths
        ]

        msg = f"{deleted} carpeta(s) eliminada(s) ({format_size(total_size)})."
        if errors:
            msg += f"\n\n{len(errors)} error(es):\n" + "\n".join(errors)
            self.view.show_warning("Limpieza — con errores", msg)
        else:
            self.view.show_info("Limpieza completada", msg)

        self._update_recoverable_total()
