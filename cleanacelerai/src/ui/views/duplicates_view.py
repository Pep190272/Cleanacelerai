"""View: Duplicate Finder - input, treeview, and console output."""
from __future__ import annotations

import tkinter as tk
from tkinter import Menu, filedialog, messagebox, ttk
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
from ...domain.models import DuplicateGroup

if TYPE_CHECKING:
    from ..presenters.duplicates_presenter import DuplicatesPresenter


class DuplicatesView(ctk.CTkFrame):
    """View for the duplicate-file finder module."""

    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._presenter: DuplicatesPresenter | None = None
        self._rutas_analisis: list[str] = []

        self._build_explanation()
        self._build_controls()
        self._build_results()
        self._build_context_menu()

    def set_presenter(self, presenter: "DuplicatesPresenter") -> None:
        self._presenter = presenter

    # ── UI Construction ────────────────────────────────────────────────────
    def _build_explanation(self) -> None:
        marco = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12,
                             border_width=1, border_color=COLOR_BORDER)
        marco.grid(row=0, column=0, padx=10, pady=(0, 20), sticky="ew")
        ctk.CTkLabel(marco, text="💡 EXPLICACIÓN CLARA:",
                     font=ctk.CTkFont(weight="bold"), text_color=COLOR_ACCENT,
                     ).pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(
            marco,
            text=(
                "Esta IA no solo mira el nombre; genera un 'Hash' (huella dactilar única) "
                "leyendo el contenido del archivo. Si dos fotos tienen nombres diferentes pero "
                "son idénticas, las detectará. La IA protege automáticamente los archivos de "
                "sistema para que no borres copias vitales."
            ),
            text_color=COLOR_TEXT_MAIN, wraplength=1000, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 15))

    def _build_controls(self) -> None:
        tarjeta = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12,
                               border_width=1, border_color=COLOR_BORDER)
        tarjeta.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        marco_rutas = ctk.CTkFrame(tarjeta, fg_color="transparent")
        marco_rutas.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(marco_rutas, text="Carpetas o Discos a analizar:",
                     text_color=COLOR_TEXT_MAIN,
                     font=ctk.CTkFont(weight="bold"),
                     ).pack(side="left", padx=(0, 10))
        self._lista_rutas = tk.Listbox(
            marco_rutas, height=2, bg=COLOR_BG, fg=COLOR_TEXT_MAIN,
            borderwidth=1, relief="solid", highlightthickness=0, font=("Segoe UI", 9),
        )
        self._lista_rutas.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(marco_rutas, text="+ Añadir Origen",
                      command=self._add_ruta,
                      fg_color="#4B5563", hover_color="#374151",
                      ).pack(side="right")

        marco_botones = ctk.CTkFrame(tarjeta, fg_color="transparent")
        marco_botones.pack(pady=(0, 15))
        self._btn_buscar = ctk.CTkButton(
            marco_botones, text="▶ 1. Iniciar Análisis IA",
            command=self._on_start,
            fg_color=COLOR_WARNING, hover_color="#D97706",
            text_color="#000000", font=ctk.CTkFont(weight="bold"),
        )
        self._btn_buscar.grid(row=0, column=0, padx=5)
        self._btn_cancelar = ctk.CTkButton(
            marco_botones, text="🛑 Cancelar",
            command=self._on_cancel,
            fg_color="#4B5563", text_color=COLOR_TEXT_MAIN, state="disabled",
        )
        self._btn_cancelar.grid(row=0, column=1, padx=5)

    def _build_results(self) -> None:
        tarjeta = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12,
                               border_width=1, border_color=COLOR_BORDER)
        tarjeta.grid(row=2, column=0, padx=10, pady=(10, 0), sticky="nsew")
        tarjeta.grid_rowconfigure(1, weight=1)
        tarjeta.grid_columnconfigure(0, weight=1)

        marco_acciones = ctk.CTkFrame(tarjeta, fg_color="transparent")
        marco_acciones.grid(row=0, column=0, sticky="ew", padx=20, pady=15)
        ctk.CTkButton(marco_acciones,
                      text="✨ Auto-Seleccionar (Mantenimiento Inteligente)",
                      command=self._on_auto_select,
                      fg_color=COLOR_ACCENT, font=ctk.CTkFont(weight="bold"),
                      ).pack(side="left")
        ctk.CTkButton(marco_acciones, text="🗑️ Eliminar Selección",
                      command=self._on_delete,
                      fg_color=COLOR_DANGER, font=ctk.CTkFont(weight="bold"),
                      ).pack(side="right")

        self._tree = ttk.Treeview(
            tarjeta,
            columns=("Ruta", "Tamaño", "Fecha", "Riesgo"),
            show="headings",
            selectmode="extended",
        )
        self._tree.heading("Ruta", text="Ruta del Archivo")
        self._tree.heading("Tamaño", text="Tamaño (MB)")
        self._tree.heading("Fecha", text="Modificación")
        self._tree.heading("Riesgo", text="Evaluación de Riesgo de la IA")
        self._tree.column("Ruta", width=450)
        self._tree.column("Tamaño", width=80, anchor="center")
        self._tree.column("Fecha", width=120, anchor="center")
        self._tree.column("Riesgo", width=250, anchor="center")

        self._tree.tag_configure("critico", foreground=COLOR_DANGER, font=("Segoe UI", 9, "bold"))
        self._tree.tag_configure("dependencia", foreground=COLOR_ACCENT)
        self._tree.tag_configure("protegido", foreground=COLOR_WARNING, font=("Segoe UI", 9, "bold"))
        self._tree.tag_configure("seguro", foreground=COLOR_SUCCESS)
        self._tree.tag_configure("grupo", background=COLOR_BG,
                                 font=("Segoe UI", 9, "bold"), foreground=COLOR_TEXT_MAIN)
        self._tree.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))

        self._consola = tk.Text(
            tarjeta, height=2, font=("Consolas", 9),
            bg=COLOR_BG, fg=COLOR_TEXT_MUTED, borderwidth=0,
        )
        self._consola.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 15))

    def _build_context_menu(self) -> None:
        self._menu_ctx = Menu(self, tearoff=0, bg=COLOR_CARD, fg=COLOR_TEXT_MAIN)
        self._menu_ctx.add_command(label="📁 Abrir ubicación",
                                   command=self._on_open_location)
        self._tree.bind("<Button-3>", self._show_context_menu)

    # ── User event handlers ────────────────────────────────────────────────
    def _add_ruta(self) -> None:
        carpeta = filedialog.askdirectory()
        if carpeta and carpeta not in self._rutas_analisis:
            self._rutas_analisis.append(carpeta)
            self._lista_rutas.insert(tk.END, carpeta)

    def _on_start(self) -> None:
        if self._presenter:
            self._presenter.start_scan(self._rutas_analisis)

    def _on_cancel(self) -> None:
        if self._presenter:
            self._presenter.cancel_scan()
        self._btn_cancelar.configure(state="disabled")

    def _on_auto_select(self) -> None:
        if self._presenter:
            count = self._presenter.auto_select()
            messagebox.showinfo(
                "Listo",
                f"La IA ha seleccionado {count} archivos seguros para eliminar.\n"
                "Revisa la selección y dale a 'Eliminar Selección'.",
            )

    def _on_delete(self) -> None:
        seleccion = self._tree.selection()
        if not seleccion:
            return
        if not messagebox.askyesno(
            "Confirmar",
            f"Vas a ELIMINAR PERMANENTEMENTE {len(seleccion)} archivos.\n¿Estás seguro?",
        ):
            return
        if self._presenter:
            self._presenter.delete_selected()

    def _on_open_location(self) -> None:
        sel = self._tree.selection()
        if sel and self._presenter:
            ruta = self._tree.item(sel[0], "values")[0]
            self._presenter.open_in_explorer(ruta)

    def _show_context_menu(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        item = self._tree.identify_row(event.y)
        if item:
            self._tree.selection_set(item)
            self._menu_ctx.post(event.x_root, event.y_root)

    # ── Public API (called by DuplicatesPresenter) ─────────────────────────
    def log(self, message: str) -> None:
        self._consola.insert(tk.END, message + "\n")
        self._consola.see(tk.END)

    def on_scan_started(self) -> None:
        self._btn_buscar.configure(state="disabled")
        self._btn_cancelar.configure(state="normal")
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._consola.delete(1.0, tk.END)

    def on_scan_finished(self, grupos_count: int) -> None:
        self._btn_buscar.configure(state="normal")
        self._btn_cancelar.configure(state="disabled")
        for item in self._tree.get_children():
            self._tree.item(item, open=True)

    def add_duplicate_group(
        self,
        group: DuplicateGroup,
        evaluaciones: list[tuple],  # (path, label, risk, mtime, fecha_str)
    ) -> None:
        from ...domain.risk_evaluator import get_risk_tag

        size_mb = group.size_mb
        id_grupo = self._tree.insert(
            "", "end",
            values=(f"📁 GRUPO DUPLICADO (MD5: {group.hash[:8]})", f"{size_mb:.2f} MB", "", ""),
            tags=("grupo",),
        )
        for p, label, risk, _mtime, fecha_str in evaluaciones:
            tag = get_risk_tag(risk)
            self._tree.insert(
                id_grupo, "end",
                values=(p, f"{size_mb:.2f}", fecha_str, label),
                tags=(tag,),
            )

    def auto_select_safe_files(self) -> int:
        """Select safe files for deletion. Returns count selected."""
        self._tree.selection_remove(self._tree.selection())
        items_a_borrar = []
        for grupo in self._tree.get_children():
            hijos = self._tree.get_children(grupo)
            seguros = [h for h in hijos if "seguro" in self._tree.item(h, "tags")]
            protegidos = [
                h for h in hijos
                if any(t in self._tree.item(h, "tags")
                       for t in ["protegido", "critico", "dependencia"])
            ]
            if protegidos:
                items_a_borrar.extend(seguros)
            elif len(seguros) > 1:
                items_a_borrar.extend(seguros[1:])
        if items_a_borrar:
            self._tree.selection_set(items_a_borrar)
        return len(items_a_borrar)

    def get_selected_deletable_items(self) -> list[tuple[str, str, str]]:
        """Return list of (item_id, path, risk_label) for non-group selected items."""
        result = []
        for item in self._tree.selection():
            if "grupo" in self._tree.item(item, "tags"):
                continue
            vals = self._tree.item(item, "values")
            result.append((item, vals[0], vals[3]))
        return result

    def remove_item(self, item_id: str) -> None:
        self._tree.delete(item_id)

    def cleanup_orphan_groups(self) -> None:
        for grupo in self._tree.get_children():
            if len(self._tree.get_children(grupo)) < 2:
                self._tree.delete(grupo)

    def show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message)

    def show_warning(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message)

    def show_info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message)
