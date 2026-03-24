"""View: Browser Bookmark Manager — passive widget layer."""
from __future__ import annotations

from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

import customtkinter as ctk

from ...domain.constants import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_DANGER,
    COLOR_SUCCESS,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    COLOR_WARNING,
)

if TYPE_CHECKING:
    from ..presenters.marcador_presenter import MarcadorPresenter


class MarcadorView(ctk.CTkFrame):
    """Passive view for the bookmark organizer module.

    Business logic lives in MarcadorPresenter. This class only manages widgets
    and provides a public API for the presenter to call.
    """

    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, fg_color="transparent")

        self._presenter: "MarcadorPresenter | None" = None

        self._build_explanation()
        self._build_content()

    def set_presenter(self, presenter: "MarcadorPresenter") -> None:
        self._presenter = presenter
        # Populate browser dropdown now that presenter is wired
        nombres = presenter.get_browser_names()
        self._cmb_nav.configure(values=nombres)
        if nombres:
            self._cmb_nav.set(nombres[0])

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
                "El Asesor IA extrae TODOS tus marcadores, los clasifica por 'Categoría Lógica' "
                "y te sugiere una estrategia de organización (ej: 'Mover a carpeta de Trabajo'). "
                "Usa 'Seleccionar Repetidos' para marcar automáticamente los duplicados."
            ),
            text_color=COLOR_TEXT_MAIN, wraplength=1000, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 15))

    def _build_content(self) -> None:
        tarjeta = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12,
                               border_width=1, border_color=COLOR_BORDER)
        tarjeta.pack(fill="both", expand=True, padx=10)

        controles = ctk.CTkFrame(tarjeta, fg_color="transparent")
        controles.pack(fill="x", padx=20, pady=20)

        # Placeholder values — will be replaced in set_presenter
        self._cmb_nav = ctk.CTkOptionMenu(
            controles,
            values=["Cargando..."],
            fg_color=COLOR_BG,
            button_color=COLOR_BORDER,
        )
        self._cmb_nav.pack(side="left", padx=(0, 10))

        ctk.CTkButton(controles, text="🔍 1. Categorizar con IA",
                      command=self._on_analyze,
                      fg_color="#8B5CF6", hover_color="#7C3AED",
                      font=ctk.CTkFont(weight="bold"),
                      ).pack(side="left", padx=10)
        ctk.CTkButton(controles, text="✨ 2. Seleccionar Repetidos",
                      command=self._on_auto_select,
                      fg_color=COLOR_ACCENT, font=ctk.CTkFont(weight="bold"),
                      ).pack(side="left", padx=10)
        ctk.CTkButton(controles, text="📁 3. Organizar en Carpetas",
                      command=self._on_organize,
                      fg_color=COLOR_SUCCESS, font=ctk.CTkFont(weight="bold"),
                      ).pack(side="left", padx=10)
        self._btn_limpiar = ctk.CTkButton(
            controles, text="🗑️ 5. Limpiar Seleccionados",
            command=self._on_delete,
            fg_color=COLOR_DANGER, font=ctk.CTkFont(weight="bold"), state="disabled",
        )
        self._btn_limpiar.pack(side="right", padx=10)

        # Second row of controls: deep categorize + progress
        controles2 = ctk.CTkFrame(tarjeta, fg_color="transparent")
        controles2.pack(fill="x", padx=20, pady=(0, 10))

        self._btn_deep = ctk.CTkButton(
            controles2, text="🌐 4. Categorización Profunda (busca en web)",
            command=self._on_deep_categorize,
            fg_color="#F97316", hover_color="#EA580C",
            font=ctk.CTkFont(weight="bold"), state="disabled",
        )
        self._btn_deep.pack(side="left", padx=(0, 10))

        self._deep_progress = ctk.CTkProgressBar(
            controles2, progress_color=COLOR_ACCENT, fg_color=COLOR_BORDER,
            height=6, corner_radius=3, width=300,
        )
        # Not packed initially — shown via show_deep_progress()

        self._lbl_deep_status = ctk.CTkLabel(
            controles2, text="",
            font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED,
        )
        self._lbl_deep_status.pack(side="left", padx=10)

        self._tree = ttk.Treeview(
            tarjeta,
            columns=("ID", "Carpeta", "Nombre", "URL", "Sugerencia", "NombreOriginal"),
            show="headings",
            selectmode="extended",
        )
        self._tree.heading("Carpeta", text="Ubicación Actual (Donde lo tienes)")
        self._tree.heading("Nombre", text="Nombre del Marcador")
        self._tree.heading("URL", text="Dirección Web (URL)")
        self._tree.heading("Sugerencia", text="Sugerencia Estratégica IA")
        self._tree.heading("NombreOriginal", text="Nombre Original")

        self._tree.column("ID", width=0, stretch=False)
        self._tree.column("Carpeta", width=180)
        self._tree.column("Nombre", width=220)
        self._tree.column("URL", width=250)
        self._tree.column("Sugerencia", width=350)
        self._tree.column("NombreOriginal", width=0, stretch=False)

        self._tree.tag_configure("grupo", background=COLOR_BG,
                                 font=("Segoe UI", 9, "bold"), foreground=COLOR_TEXT_MAIN)
        self._tree.tag_configure("item", foreground=COLOR_TEXT_MUTED)
        self._tree.tag_configure("repetido", foreground=COLOR_WARNING,
                                 font=("Segoe UI", 9, "bold"))
        self._tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    # ── User-action callbacks (delegate to presenter) ──────────────────────

    def _on_analyze(self) -> None:
        if self._presenter:
            self._presenter.analyze(self._cmb_nav.get())

    def _on_auto_select(self) -> None:
        """Select duplicate bookmark items directly in the tree (pure UI logic)."""
        self._tree.selection_remove(self._tree.selection())
        urls_vistas: set[str] = set()
        items_a_borrar = []

        # Reset all item tags first
        for grupo in self._tree.get_children():
            for hijo in self._tree.get_children(grupo):
                self._tree.item(hijo, tags=("item",))

        for grupo in self._tree.get_children():
            for hijo in self._tree.get_children(grupo):
                valores = self._tree.item(hijo, "values")
                url = valores[3].strip().lower()
                if url:
                    if url in urls_vistas:
                        items_a_borrar.append(hijo)
                        self._tree.item(hijo, tags=("repetido",))
                    else:
                        urls_vistas.add(url)

        if items_a_borrar:
            self._tree.selection_set(items_a_borrar)
            messagebox.showinfo(
                "Auto-Selección",
                f"Se han encontrado {len(items_a_borrar)} enlaces repetidos.\n"
                "Están seleccionados y resaltados en amarillo listos para borrar.",
            )
        else:
            messagebox.showinfo("Excelente", "No tienes enlaces duplicados. Tu orden actual es limpio.")

    def _on_organize(self) -> None:
        if not self._presenter:
            return
        self._presenter.organize(self._cmb_nav.get())

    def _on_deep_categorize(self) -> None:
        if self._presenter:
            self._presenter.deep_categorize()

    def _on_delete(self) -> None:
        if not self._presenter:
            return
        seleccion = self._tree.selection()
        ids = [
            self._tree.item(item, "values")[0]
            for item in seleccion
            if self._tree.item(item, "values")[0]
        ]
        if not ids:
            return
        if not messagebox.askyesno(
            "Atención",
            "⚠️ IMPORTANTE: Debes tener el navegador (Chrome/Edge) CERRADO para aplicar "
            "los cambios.\n\n¿Tienes el navegador cerrado y deseas continuar?",
        ):
            return
        self._presenter.delete_bookmarks(ids)

    # ── Public API for presenter ───────────────────────────────────────────

    def clear_tree(self) -> None:
        """Remove all rows from the bookmark tree."""
        for item in self._tree.get_children():
            self._tree.delete(item)

    def show_bookmarks(self, agrupados: dict) -> None:
        """Populate the tree with grouped bookmark data.

        Args:
            agrupados: dict mapping category -> list[Bookmark]
        """
        for categoria, lista in sorted(agrupados.items()):
            sug_grupo = lista[0].suggestion if lista else ""
            id_grupo = self._tree.insert(
                "", "end",
                values=("", "", f"{categoria} ({len(lista)} enlaces)", "", sug_grupo, ""),
                tags=("grupo",),
            )
            for b in lista:
                original = getattr(b, "original_name", b.name)
                self._tree.insert(
                    id_grupo, "end",
                    values=(b.id, b.path, b.name, b.url, b.suggestion, original),
                    tags=("item",),
                )

        for item in self._tree.get_children():
            self._tree.item(item, open=True)
        self._btn_limpiar.configure(state="normal")
        self._btn_deep.configure(state="normal")

    def set_deep_categorize_enabled(self, enabled: bool) -> None:
        self._btn_deep.configure(state="normal" if enabled else "disabled")

    def show_deep_progress(self, visible: bool) -> None:
        if visible:
            self._deep_progress.pack(side="left", padx=(0, 10))
            self._deep_progress.set(0)
            self._lbl_deep_status.configure(text="Visitando páginas web...")
        else:
            self._deep_progress.pack_forget()
            self._lbl_deep_status.configure(text="")

    def update_deep_progress(self, value: int) -> None:
        self._deep_progress.set(value / 100)
        self._lbl_deep_status.configure(text=f"Analizando... {value}%")

    def refresh_after_delete(self) -> None:
        """Trigger a fresh analysis after bookmarks were deleted."""
        if self._presenter:
            self._presenter.analyze(self._cmb_nav.get())

    def show_info(self, title: str, message: str, refresh: bool = False) -> None:
        messagebox.showinfo(title, message)
        if refresh:
            self.refresh_after_delete()

    def show_warning(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message)

    def show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message)
