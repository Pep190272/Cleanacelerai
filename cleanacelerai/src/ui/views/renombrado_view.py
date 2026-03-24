"""View: Batch File Renamer — passive widget layer."""
from __future__ import annotations

from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

import customtkinter as ctk

from ...domain.constants import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_SUCCESS,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    COLOR_WARNING,
)
from ...services.file_renamer import RenameEntry

if TYPE_CHECKING:
    from ..presenters.renombrado_presenter import RenombradoPresenter


class RenombradoView(ctk.CTkFrame):
    """Passive view for the batch file renaming module.

    Business logic lives in RenombradoPresenter. This class only manages
    widgets and provides a public API for the presenter to call.
    """

    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, fg_color="transparent")

        self._presenter: "RenombradoPresenter | None" = None
        self._ruta_renombrar: str | None = None

        self._build_explanation()
        self._build_content()

    def set_presenter(self, presenter: "RenombradoPresenter") -> None:
        self._presenter = presenter

    # ── Widget construction ────────────────────────────────────────────────

    def _build_explanation(self) -> None:
        marco = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12,
                             border_width=1, border_color=COLOR_BORDER)
        marco.pack(fill="x", padx=10, pady=(0, 20))
        ctk.CTkLabel(marco, text="💡 EXPLICACIÓN CLARA:",
                     font=ctk.CTkFont(weight="bold"), text_color=COLOR_ACCENT,
                     ).pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(
            marco,
            text=(
                "Esta herramienta organiza el caos de nombres. Selecciona una carpeta, "
                "escribe un nombre base (ej: 'Vacaciones') y la IA ordenará los archivos "
                "por fecha de modificación, renombrándolos secuencialmente "
                "(Vacaciones_20260320_001.jpg)."
            ),
            text_color=COLOR_TEXT_MAIN, wraplength=1000, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 15))

    def _build_content(self) -> None:
        tarjeta = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12,
                               border_width=1, border_color=COLOR_BORDER)
        tarjeta.pack(fill="both", expand=True, padx=10)

        controles = ctk.CTkFrame(tarjeta, fg_color="transparent")
        controles.pack(fill="x", padx=20, pady=20)

        self._lbl_ruta = ctk.CTkLabel(
            controles, text="Ninguna carpeta seleccionada", text_color=COLOR_TEXT_MUTED,
        )
        self._lbl_ruta.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ctk.CTkButton(
            controles, text="📁 Seleccionar Carpeta",
            command=self._on_select_folder,
            fg_color="#4B5563", hover_color="#374151",
        ).grid(row=1, column=0, padx=(0, 10))

        self._entry_base = ctk.CTkEntry(
            controles, placeholder_text="Nombre base (ej: Proyecto_X)",
            width=200, fg_color=COLOR_BG, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_MAIN,
        )
        self._entry_base.grid(row=1, column=1, padx=10)

        ctk.CTkButton(
            controles, text="👁️ Previsualizar",
            command=self._on_preview,
            fg_color=COLOR_WARNING, hover_color="#D97706", text_color="black",
        ).grid(row=1, column=2, padx=10)

        self._btn_aplicar = ctk.CTkButton(
            controles, text="✨ Aplicar Cambios",
            command=self._on_apply,
            fg_color=COLOR_SUCCESS, hover_color="#059669",
            state="disabled", text_color="white",
        )
        self._btn_aplicar.grid(row=1, column=3, padx=10)

        self._tree = ttk.Treeview(
            tarjeta,
            columns=("Original", "Nuevo"),
            show="headings",
            selectmode="none",
        )
        self._tree.heading("Original", text="Nombre Original")
        self._tree.heading("Nuevo", text="Nuevo Nombre Proyectado")
        self._tree.column("Original", width=400)
        self._tree.column("Nuevo", width=400)
        self._tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    # ── User-action callbacks (delegate to presenter) ──────────────────────

    def _on_select_folder(self) -> None:
        carpeta = filedialog.askdirectory()
        if carpeta:
            self._ruta_renombrar = carpeta
            self._lbl_ruta.configure(text=carpeta)

    def _on_preview(self) -> None:
        if not self._ruta_renombrar:
            messagebox.showwarning("Aviso", "Selecciona una carpeta primero.")
            return
        base = self._entry_base.get().strip()
        if not base:
            messagebox.showwarning("Aviso", "Escribe un nombre base (ejemplo: Vacaciones).")
            return
        if self._presenter:
            self._presenter.build_preview(self._ruta_renombrar, base)

    def _on_apply(self) -> None:
        if not self._presenter or not self._ruta_renombrar:
            return
        base = self._entry_base.get().strip()
        if not messagebox.askyesno(
            "Confirmar",
            "Se renombrarán los archivos del plan actual.\n¿Continuar?",
        ):
            return
        self._presenter.apply(self._ruta_renombrar, base)

    # ── Public API for presenter ───────────────────────────────────────────

    def show_preview(self, plan: list[RenameEntry]) -> None:
        """Populate the tree with the rename plan preview."""
        for item in self._tree.get_children():
            self._tree.delete(item)
        for entry in plan:
            self._tree.insert("", "end", values=(entry.original_name, entry.new_name))
        if plan:
            self._btn_aplicar.configure(state="normal")
        else:
            self._btn_aplicar.configure(state="disabled")

    def show_info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message)

    def show_warning(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message)

    def show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message)
