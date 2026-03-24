"""View: Chaos Advisor — passive widget layer with tabbed interface."""
from __future__ import annotations

from tkinter import filedialog, messagebox, ttk
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
    DEEP_CLEAN_BUNDLE_ICONS,
    DEEP_CLEAN_RISK_COLORS,
)
from ...domain.models import (
    DeepCleanBundle,
    DeepCleanEntry,
    DeepCleanResult,
    DeepCleanRisk,
    DocumentAnalysisResult,
    DocumentCategory,
)
from ...services.chaos_advisor import AdvisorEntry

if TYPE_CHECKING:
    from ..presenters.asesor_presenter import AsesorPresenter


# Mapping from DocumentCategory to display-friendly emoji + label
_CATEGORY_DISPLAY: dict[DocumentCategory, tuple[str, str]] = {
    DocumentCategory.INVOICE: ("icon_invoice", "Facturas"),
    DocumentCategory.RECEIPT: ("icon_receipt", "Recibos"),
    DocumentCategory.CONTRACT: ("icon_contract", "Contratos"),
    DocumentCategory.TUTORIAL: ("icon_tutorial", "Tutoriales"),
    DocumentCategory.BOOK: ("icon_book", "Libros"),
    DocumentCategory.MANUAL: ("icon_manual", "Manuales"),
    DocumentCategory.LETTER: ("icon_letter", "Cartas"),
    DocumentCategory.REPORT: ("icon_report", "Informes"),
    DocumentCategory.ACADEMIC: ("icon_academic", "Academicos"),
    DocumentCategory.UNKNOWN: ("icon_unknown", "Desconocidos"),
}

# Colors for category KPI cards
_CATEGORY_COLORS: dict[DocumentCategory, str] = {
    DocumentCategory.INVOICE: "#8B5CF6",
    DocumentCategory.RECEIPT: COLOR_SUCCESS,
    DocumentCategory.CONTRACT: COLOR_ACCENT,
    DocumentCategory.TUTORIAL: COLOR_WARNING,
    DocumentCategory.BOOK: "#EC4899",
    DocumentCategory.MANUAL: "#06B6D4",
    DocumentCategory.LETTER: "#F97316",
    DocumentCategory.REPORT: "#14B8A6",
    DocumentCategory.ACADEMIC: "#A78BFA",
    DocumentCategory.UNKNOWN: COLOR_TEXT_MUTED,
}


class AsesorView(ctk.CTkFrame):
    """Passive view for the AI Chaos Advisor module.

    Business logic (file I/O, service calls) lives in AsesorPresenter.
    This class only manages widgets and provides a public API for the presenter.
    """

    def __init__(
        self,
        parent: ctk.CTkFrame,
    ) -> None:
        super().__init__(parent, fg_color="transparent")

        self._presenter: "AsesorPresenter | None" = None

        self._doc_selected_folder: str | None = None
        self._doc_category_labels: dict[DocumentCategory, ctk.CTkLabel] = {}

        # Deep clean state
        self._deep_entry_cards: dict[str, ctk.CTkFrame] = {}  # path -> card frame
        self._deep_size_labels: dict[str, ctk.CTkLabel] = {}   # path -> size label
        self._deep_risk_labels: dict[str, ctk.CTkLabel] = {}   # path -> risk badge

        self._build_tabs()

    def set_presenter(self, presenter: "AsesorPresenter") -> None:
        self._presenter = presenter

    # ── Tab structure ───────────────────────────────────────────────────────

    def _build_tabs(self) -> None:
        self._tabview = ctk.CTkTabview(
            self,
            fg_color=COLOR_CARD,
            segmented_button_fg_color=COLOR_BORDER,
            segmented_button_selected_color=COLOR_ACCENT,
            segmented_button_selected_hover_color="#2563EB",
            segmented_button_unselected_color=COLOR_BORDER,
            segmented_button_unselected_hover_color="#4B5563",
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self._tabview.pack(fill="both", expand=True, padx=10)

        self._tabview.add("Orden General")
        self._tabview.add("Documentos")
        self._tabview.add("Limpieza Profunda")

        self._build_tab_orden_general()
        self._build_tab_documentos()
        self._build_tab_limpieza_profunda()

    # ── Tab 1: Orden General (existing functionality) ───────────────────────

    def _build_tab_orden_general(self) -> None:
        tab = self._tabview.tab("Orden General")

        # Explanation card
        marco = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12,
                             border_width=1, border_color=COLOR_BORDER)
        marco.pack(fill="x", padx=10, pady=(0, 20))
        ctk.CTkLabel(marco, text="EXPLICACION CLARA:",
                     font=ctk.CTkFont(weight="bold"), text_color=COLOR_ACCENT,
                     ).pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(
            marco,
            text=(
                "Esta es la IA mas inteligente. Usala para limpiar el Escritorio o Descargas. "
                "Clasifica archivos personales para mover a un disco grande (D:) y protege "
                "automaticamente las 'Tuberias' de programacion (.vscode, .conda) y carpetas "
                "de Windows para que NO las muevas por error."
            ),
            text_color=COLOR_TEXT_MAIN, wraplength=1000, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 15))

        # Content card
        tarjeta = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12,
                               border_width=1, border_color=COLOR_BORDER)
        tarjeta.pack(fill="both", expand=True, padx=10)

        ctk.CTkLabel(
            tarjeta,
            text="Selecciona una carpeta caotica (ej. C:\\Users\\Josep\\Downloads o Escritorio) "
                 "y la IA te dira que hacer.",
            font=ctk.CTkFont(size=14), text_color=COLOR_TEXT_MUTED,
        ).pack(pady=(20, 10))

        marco_botones = ctk.CTkFrame(tarjeta, fg_color="transparent")
        marco_botones.pack(pady=10)

        ctk.CTkButton(
            marco_botones, text="1. Analizar Carpeta Caotica",
            command=self._on_analyze,
            fg_color="#8B5CF6", hover_color="#7C3AED",
            font=ctk.CTkFont(size=14, weight="bold"), height=40,
        ).grid(row=0, column=0, padx=5, pady=5)

        self._btn_mover = ctk.CTkButton(
            marco_botones, text="2. Mover Seleccion",
            command=self._on_move,
            fg_color=COLOR_SUCCESS, hover_color="#059669",
            font=ctk.CTkFont(size=14, weight="bold"), height=40, state="disabled",
        )
        self._btn_mover.grid(row=0, column=1, padx=5, pady=5)

        self._btn_borrar = ctk.CTkButton(
            marco_botones, text="3. Borrar Seleccion",
            command=self._on_delete,
            fg_color=COLOR_DANGER, hover_color="#B91C1C",
            font=ctk.CTkFont(size=14, weight="bold"), height=40, state="disabled",
        )
        self._btn_borrar.grid(row=0, column=2, padx=5, pady=5)

        self._btn_explicar = ctk.CTkButton(
            marco_botones, text="4. Explicar Elemento (Forense)",
            command=self._on_explain,
            fg_color=COLOR_ACCENT, hover_color="#1D4ED8",
            font=ctk.CTkFont(size=14, weight="bold"), height=40, state="disabled",
        )
        self._btn_explicar.grid(row=0, column=3, padx=5, pady=5)

        self._tree = ttk.Treeview(
            tarjeta,
            columns=("Ruta", "Archivo", "Tipo", "Detalles", "Accion"),
            show="headings",
            selectmode="extended",
        )
        self._tree.heading("Archivo", text="Archivo / Carpeta Detectado")
        self._tree.heading("Tipo", text="Categoria IA")
        self._tree.heading("Detalles", text="Inspeccion Heuristica")
        self._tree.heading("Accion", text="Sugerencia de Accion Pro")

        self._tree.column("Ruta", width=0, stretch=False)
        self._tree.column("Archivo", width=250)
        self._tree.column("Tipo", width=150)
        self._tree.column("Detalles", width=200)
        self._tree.column("Accion", width=350)

        self._tree.tag_configure("borrar", foreground=COLOR_DANGER)
        self._tree.tag_configure("mover", foreground=COLOR_SUCCESS)
        self._tree.tag_configure("notocar", foreground=COLOR_WARNING,
                                 font=("Segoe UI", 9, "bold"))
        self._tree.tag_configure("perfil", foreground="#8B5CF6",
                                 font=("Segoe UI", 9, "bold"))
        self._tree.pack(fill="both", expand=True, padx=30, pady=20)

    # ── Tab 2: Documentos ──────────────────────────────────────────────────

    def _build_tab_documentos(self) -> None:
        tab = self._tabview.tab("Documentos")

        # --- Header section: folder selection + analyze ---
        header_card = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12,
                                   border_width=1, border_color=COLOR_BORDER)
        header_card.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(header_card, text="CLASIFICADOR INTELIGENTE DE DOCUMENTOS PDF:",
                     font=ctk.CTkFont(weight="bold"), text_color=COLOR_ACCENT,
                     ).pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(
            header_card,
            text=(
                "Selecciona una carpeta con documentos PDF. La IA leera el contenido de cada uno, "
                "los clasificara por categoria (Factura, Contrato, Libro, etc.) y te sugerira "
                "como organizarlos en carpetas."
            ),
            text_color=COLOR_TEXT_MAIN, wraplength=1000, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 10))

        marco_seleccion = ctk.CTkFrame(header_card, fg_color="transparent")
        marco_seleccion.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkButton(
            marco_seleccion, text="Seleccionar Carpeta",
            command=self._on_select_doc_folder,
            fg_color="#4B5563", hover_color="#374151",
            font=ctk.CTkFont(weight="bold"), height=36,
        ).pack(side="left", padx=(0, 10))

        self._lbl_doc_folder = ctk.CTkLabel(
            marco_seleccion, text="Ninguna carpeta seleccionada",
            text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(size=13),
        )
        self._lbl_doc_folder.pack(side="left", fill="x", expand=True)

        self._btn_doc_analyze = ctk.CTkButton(
            marco_seleccion, text="Analizar",
            command=self._on_analyze_docs,
            fg_color=COLOR_WARNING, hover_color="#D97706",
            text_color="#000000", font=ctk.CTkFont(size=14, weight="bold"),
            height=36, state="disabled",
        )
        self._btn_doc_analyze.pack(side="right")

        # --- Progress bar (hidden initially) ---
        self._doc_progress = ctk.CTkProgressBar(
            tab, progress_color=COLOR_ACCENT, fg_color=COLOR_BORDER,
            height=6, corner_radius=3,
        )
        # Not packed initially — shown/hidden via show_doc_progress()

        # --- Results section ---
        results_card = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12,
                                    border_width=1, border_color=COLOR_BORDER)
        results_card.pack(fill="both", expand=True, padx=10, pady=(0, 0))

        # Summary frame (KPI cards for category counts)
        self._doc_summary_frame = ctk.CTkFrame(results_card, fg_color="transparent")
        self._doc_summary_frame.pack(fill="x", padx=20, pady=(15, 10))

        # Treeview for document results
        self._doc_tree = ttk.Treeview(
            results_card,
            columns=("Documento", "Categoria", "Confianza", "CarpetaSugerida"),
            show="headings",
            selectmode="extended",
        )
        self._doc_tree.heading("Documento", text="Documento")
        self._doc_tree.heading("Categoria", text="Categoria")
        self._doc_tree.heading("Confianza", text="Confianza")
        self._doc_tree.heading("CarpetaSugerida", text="Carpeta Sugerida")

        self._doc_tree.column("Documento", width=350)
        self._doc_tree.column("Categoria", width=150, anchor="center")
        self._doc_tree.column("Confianza", width=100, anchor="center")
        self._doc_tree.column("CarpetaSugerida", width=300)

        self._doc_tree.tag_configure("high_conf", foreground=COLOR_SUCCESS)
        self._doc_tree.tag_configure("med_conf", foreground=COLOR_WARNING)
        self._doc_tree.tag_configure("low_conf", foreground=COLOR_DANGER)
        self._doc_tree.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Organize button
        self._btn_doc_organize = ctk.CTkButton(
            results_card, text="Organizar Documentos",
            command=self._on_organize_docs,
            fg_color=COLOR_SUCCESS, hover_color="#059669",
            font=ctk.CTkFont(size=14, weight="bold"), height=40,
            state="disabled",
        )
        self._btn_doc_organize.pack(pady=(0, 15))

    # ── User-action callbacks (delegate to presenter) — Tab 1 ──────────────

    def _on_analyze(self) -> None:
        carpeta = filedialog.askdirectory(
            title="Selecciona la carpeta caotica (Escritorio o Descargas)"
        )
        if not carpeta or not self._presenter:
            return
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._presenter.analyze(
            carpeta,
            keywords=self._presenter.get_keywords(),
            folders=self._presenter.get_folders(),
        )

    def _on_move(self) -> None:
        if not self._presenter:
            return
        seleccion = self._tree.selection()
        item_ids = seleccion if seleccion else self._tree.get_children()
        if not item_ids:
            messagebox.showinfo("Sin elementos", "No hay elementos para mover.")
            return
        destino = filedialog.askdirectory(
            title="Selecciona la carpeta de destino para mover los archivos"
        )
        if not destino:
            return
        items = [
            (iid, self._tree.item(iid, "values")[0], self._tree.item(iid, "values")[1])
            for iid in item_ids
        ]
        self._presenter.move_items(items, destino)

    def _on_delete(self) -> None:
        if not self._presenter:
            return
        seleccion = self._tree.selection()
        item_ids = seleccion if seleccion else self._tree.get_children()
        if not item_ids:
            messagebox.showinfo("Sin elementos", "No hay elementos para borrar.")
            return
        cantidad = len(item_ids)
        if not messagebox.askyesno(
            "Confirmar borrado",
            f"Estas seguro que queres eliminar {cantidad} archivo(s)/carpeta(s)?\n\n"
            "Esta accion no se puede deshacer.",
            icon="warning",
        ):
            return
        items = [
            (iid, self._tree.item(iid, "values")[0], self._tree.item(iid, "values")[1])
            for iid in item_ids
        ]
        self._presenter.delete_items(items)

    def _on_explain(self) -> None:
        if not self._presenter:
            return
        seleccion = self._tree.selection()
        if not seleccion:
            return
        valores = self._tree.item(seleccion[0], "values")
        nombre, tipo = valores[1], valores[2]
        texto = self._presenter.explain(nombre, tipo)
        self._show_explanation(nombre, texto)

    def _show_explanation(self, nombre: str, texto: str) -> None:
        w = ctk.CTkToplevel(self)
        w.title(nombre)
        w.geometry("600x400")
        w.attributes("-topmost", True)
        tb = ctk.CTkTextbox(
            w, font=("Segoe UI", 12),
            text_color=COLOR_TEXT_MAIN, wrap="word", fg_color=COLOR_CARD,
        )
        tb.pack(fill="both", expand=True, padx=20, pady=20)
        tb.insert("0.0", texto)
        tb.configure(state="disabled")

    # ── User-action callbacks (delegate to presenter) — Tab 2 ──────────────

    def _on_select_doc_folder(self) -> None:
        if self._presenter:
            self._presenter.on_select_doc_folder()

    def _on_analyze_docs(self) -> None:
        if self._presenter:
            self._presenter.analyze_documents()

    def _on_organize_docs(self) -> None:
        if self._presenter:
            self._presenter.organize_documents()

    # ── Public API for presenter — Tab 1 (Orden General) ───────────────────

    def show_entries(self, entries: list[AdvisorEntry]) -> None:
        """Populate the tree with advisor entries."""
        for item in self._tree.get_children():
            self._tree.delete(item)
        for entry in entries:
            self._tree.insert(
                "", "end",
                values=(entry.path, entry.name, entry.tipo, entry.detalles, entry.accion),
                tags=(entry.tag,),
            )
        self._btn_mover.configure(state="normal")
        self._btn_borrar.configure(state="normal")
        self._btn_explicar.configure(state="normal")

    def remove_item(self, item_id: str) -> None:
        """Remove one row from the tree."""
        self._tree.delete(item_id)

    def show_info(self, title: str, message: str) -> None:
        messagebox.showinfo(title, message)

    def show_warning(self, title: str, message: str) -> None:
        messagebox.showwarning(title, message)

    def show_error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message)

    # ── Public API for presenter — Tab 2 (Documentos) ──────────────────────

    def set_doc_folder_label(self, path: str) -> None:
        """Update the selected folder label."""
        self._doc_selected_folder = path
        self._lbl_doc_folder.configure(text=path, text_color=COLOR_TEXT_MAIN)

    def show_doc_progress(self, visible: bool) -> None:
        """Show or hide the document analysis progress bar."""
        if visible:
            self._doc_progress.pack(fill="x", padx=20, pady=(0, 5))
            self._doc_progress.set(0)
        else:
            self._doc_progress.pack_forget()

    def update_doc_progress(self, value: int) -> None:
        """Update document analysis progress (0-100)."""
        self._doc_progress.set(value / 100)

    def display_doc_results(self, result: DocumentAnalysisResult) -> None:
        """Display the document analysis results in summary + treeview."""
        # Clear previous results
        self.clear_doc_results()

        # Build summary KPI cards
        self._build_doc_summary(result)

        # Populate treeview
        for doc in result.classifications:
            confidence_pct = f"{doc.confidence * 100:.0f}%"
            if doc.confidence >= 0.7:
                tag = "high_conf"
            elif doc.confidence >= 0.4:
                tag = "med_conf"
            else:
                tag = "low_conf"

            self._doc_tree.insert(
                "", "end",
                values=(doc.name, doc.category.value, confidence_pct, doc.suggested_folder),
                tags=(tag,),
            )

        # Show unreadable files warning if any
        if result.unreadable:
            count = len(result.unreadable)
            self.show_warning(
                "Archivos no legibles",
                f"{count} archivo(s) no se pudieron leer:\n"
                + "\n".join(result.unreadable[:10])
                + ("\n..." if count > 10 else ""),
            )

    def clear_doc_results(self) -> None:
        """Clear all document analysis results."""
        for item in self._doc_tree.get_children():
            self._doc_tree.delete(item)
        # Clear summary cards
        for widget in self._doc_summary_frame.winfo_children():
            widget.destroy()
        self._doc_category_labels.clear()

    def set_doc_analyze_enabled(self, enabled: bool) -> None:
        """Enable or disable the Analizar button."""
        self._btn_doc_analyze.configure(state="normal" if enabled else "disabled")

    def set_doc_organize_enabled(self, enabled: bool) -> None:
        """Enable or disable the Organizar Documentos button."""
        self._btn_doc_organize.configure(state="normal" if enabled else "disabled")

    def get_selected_doc_folder(self) -> str | None:
        """Return the currently selected document folder path."""
        return self._doc_selected_folder

    # ── Internal helpers — Tab 2 ───────────────────────────────────────────

    # ── Tab 3: Limpieza Profunda ──────────────────────────────────────────

    def _build_tab_limpieza_profunda(self) -> None:
        tab = self._tabview.tab("Limpieza Profunda")

        # --- Header card ---
        header_card = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12,
                                   border_width=1, border_color=COLOR_BORDER)
        header_card.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(header_card, text="LIMPIEZA PROFUNDA DEL SISTEMA:",
                     font=ctk.CTkFont(weight="bold"), text_color=COLOR_ACCENT,
                     ).pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(
            header_card,
            text=(
                "Escanea carpetas de configuracion, cache y temporales de herramientas "
                "de IA, editores, compiladores y el sistema operativo. Identifica que se "
                "puede eliminar con seguridad y que es critico para el funcionamiento."
            ),
            text_color=COLOR_TEXT_MAIN, wraplength=1000, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 10))

        marco_botones = ctk.CTkFrame(header_card, fg_color="transparent")
        marco_botones.pack(fill="x", padx=20, pady=(0, 15))

        self._btn_deep_scan = ctk.CTkButton(
            marco_botones, text="Escanear Sistema",
            command=self._on_deep_scan,
            fg_color="#8B5CF6", hover_color="#7C3AED",
            font=ctk.CTkFont(size=14, weight="bold"), height=40,
        )
        self._btn_deep_scan.pack(side="left", padx=(0, 10))

        self._btn_deep_bulk = ctk.CTkButton(
            marco_botones, text="Limpiar Todo lo Seguro",
            command=self._on_deep_bulk_delete,
            fg_color=COLOR_SUCCESS, hover_color="#059669",
            font=ctk.CTkFont(size=14, weight="bold"), height=40,
            state="disabled",
        )
        self._btn_deep_bulk.pack(side="left")

        # --- Progress bar (hidden initially) ---
        self._deep_progress = ctk.CTkProgressBar(
            tab, progress_color=COLOR_ACCENT, fg_color=COLOR_BORDER,
            height=6, corner_radius=3,
        )
        # Not packed initially — shown/hidden via show_deep_progress()

        # --- Summary frame (KPI cards) ---
        self._deep_summary_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self._deep_summary_frame.pack(fill="x", padx=10, pady=(0, 5))

        # --- Scrollable frame for entry cards ---
        self._deep_scroll = ctk.CTkScrollableFrame(
            tab, fg_color=COLOR_CARD, corner_radius=12,
            border_width=1, border_color=COLOR_BORDER,
        )
        self._deep_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 0))

    def _create_deep_entry_card(
        self, parent: ctk.CTkFrame, entry: DeepCleanEntry,
    ) -> ctk.CTkFrame:
        """Build a single entry card for the deep cleaner results."""
        risk_color = DEEP_CLEAN_RISK_COLORS.get(entry.risk.value, COLOR_TEXT_MUTED)
        bundle_icon = DEEP_CLEAN_BUNDLE_ICONS.get(entry.bundle.value, "")

        card = ctk.CTkFrame(parent, fg_color=COLOR_BORDER, corner_radius=10,
                            border_width=1, border_color="#4B5563")
        card.pack(fill="x", padx=10, pady=4)

        # --- Top row: icon + name | size + risk badge ---
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=15, pady=(10, 2))

        ctk.CTkLabel(
            top_row,
            text=f"{bundle_icon}  {entry.name}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
        ).pack(side="left")

        # Risk badge
        risk_badge = ctk.CTkLabel(
            top_row, text=f" {entry.risk.value} ",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=risk_color,
            fg_color=COLOR_CARD, corner_radius=4,
        )
        risk_badge.pack(side="right", padx=(5, 0))
        self._deep_risk_labels[entry.path] = risk_badge

        # Size label
        from ...services.deep_scanner import format_size
        size_text = format_size(entry.size_bytes) if entry.size_bytes is not None else "Calculando..."
        size_label = ctk.CTkLabel(
            top_row, text=size_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
        )
        size_label.pack(side="right", padx=(0, 10))
        self._deep_size_labels[entry.path] = size_label

        # --- Description row ---
        ctk.CTkLabel(
            card, text=f"{entry.description}",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED, wraplength=900, justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 2))

        # --- Creator row ---
        ctk.CTkLabel(
            card, text=f"Creado por: {entry.creator}",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=15, pady=(0, 2))

        # --- Special note (if any) ---
        if entry.special_note:
            ctk.CTkLabel(
                card, text=f"  {entry.special_note}",
                font=ctk.CTkFont(size=11),
                text_color=COLOR_WARNING, wraplength=900, justify="left",
            ).pack(anchor="w", padx=15, pady=(0, 2))

        # --- Recommendation + action row ---
        action_frame = ctk.CTkFrame(card, fg_color="transparent")
        action_frame.pack(fill="x", padx=15, pady=(2, 10))

        if entry.risk == DeepCleanRisk.SYSTEM:
            ctk.CTkLabel(
                action_frame, text="🛑 NO ELIMINAR — Necesario para el sistema",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLOR_DANGER,
            ).pack(side="left")
        elif entry.risk == DeepCleanRisk.CRITICAL:
            ctk.CTkLabel(
                action_frame, text="⚠️ PRECAUCIÓN — Contiene datos importantes, revisá antes",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#F97316",
            ).pack(side="left")
            ctk.CTkButton(
                action_frame, text="Eliminar bajo tu responsabilidad",
                command=lambda p=entry.path: self._on_deep_delete_single(p),
                fg_color="#F97316", hover_color="#EA580C",
                font=ctk.CTkFont(size=11), height=28, width=220,
            ).pack(side="right")
        elif entry.delete_instructions:
            ctk.CTkLabel(
                action_frame, text="📋 Requiere eliminación manual",
                font=ctk.CTkFont(size=12),
                text_color=COLOR_WARNING,
            ).pack(side="left")
            ctk.CTkButton(
                action_frame, text="Ver instrucciones",
                command=lambda p=entry.path: self._on_deep_delete_single(p),
                fg_color=COLOR_ACCENT, hover_color="#1D4ED8",
                font=ctk.CTkFont(size=12), height=30,
            ).pack(side="right")
        else:
            ctk.CTkLabel(
                action_frame, text="✅ Se puede eliminar — se regenera si se necesita",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLOR_SUCCESS,
            ).pack(side="left")
            ctk.CTkButton(
                action_frame, text="Eliminar",
                command=lambda p=entry.path: self._on_deep_delete_single(p),
                fg_color=COLOR_DANGER, hover_color="#B91C1C",
                font=ctk.CTkFont(size=12), height=30,
            ).pack(side="right")

        self._deep_entry_cards[entry.path] = card
        return card

    # ── User-action callbacks (delegate to presenter) — Tab 3 ──────────────

    def _on_deep_scan(self) -> None:
        if self._presenter:
            self._presenter.start_deep_scan()

    def _on_deep_delete_single(self, path: str) -> None:
        if self._presenter:
            self._presenter.delete_deep_entry(path)

    def _on_deep_bulk_delete(self) -> None:
        if self._presenter:
            self._presenter.bulk_delete_safe()

    # ── Public API for presenter — Tab 3 (Limpieza Profunda) ───────────────

    def show_deep_progress(self, visible: bool) -> None:
        """Show/hide deep scan progress bar."""
        if visible:
            self._deep_progress.pack(fill="x", padx=20, pady=(0, 5))
            self._deep_progress.set(0)
        else:
            self._deep_progress.pack_forget()

    def update_deep_progress(self, value: int) -> None:
        """Update progress bar (0-100)."""
        self._deep_progress.set(value / 100)

    def display_deep_entries(self, entries: list[DeepCleanEntry]) -> None:
        """Build all entry cards grouped by bundle. Clear previous cards first."""
        self.clear_deep_results()

        if not entries:
            ctk.CTkLabel(
                self._deep_scroll, text="No se encontraron carpetas para analizar.",
                text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(size=14),
            ).pack(pady=30)
            return

        # Define risk sort order
        _risk_order = {
            DeepCleanRisk.SYSTEM: 0,
            DeepCleanRisk.CRITICAL: 1,
            DeepCleanRisk.ACTIVE: 2,
            DeepCleanRisk.CACHE: 3,
            DeepCleanRisk.EMPTY: 4,
        }

        # Define bundle display order
        _bundle_order = {
            DeepCleanBundle.AI_TOOLS: 0,
            DeepCleanBundle.EDITORS_DEV: 1,
            DeepCleanBundle.CACHE_TEMP: 2,
            DeepCleanBundle.WINDOWS_SYSTEM: 3,
            DeepCleanBundle.UNKNOWN: 4,
        }

        # Sort entries: by bundle order first, then by risk within bundle
        sorted_entries = sorted(
            entries,
            key=lambda e: (_bundle_order.get(e.bundle, 99), _risk_order.get(e.risk, 99)),
        )

        # Group by bundle and render
        current_bundle: DeepCleanBundle | None = None
        for entry in sorted_entries:
            if entry.bundle != current_bundle:
                current_bundle = entry.bundle
                icon = DEEP_CLEAN_BUNDLE_ICONS.get(entry.bundle.value, "")
                ctk.CTkLabel(
                    self._deep_scroll,
                    text=f"{icon} {entry.bundle.value}",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=COLOR_ACCENT,
                ).pack(anchor="w", padx=10, pady=(15, 5))

            self._create_deep_entry_card(self._deep_scroll, entry)

    def update_entry_size(self, path: str, size_bytes: int) -> None:
        """Update a single entry's size label after async calculation."""
        from ...services.deep_scanner import format_size

        if path in self._deep_size_labels:
            self._deep_size_labels[path].configure(text=format_size(size_bytes))

        # Update risk badge to EMPTY if size is 0
        if size_bytes == 0 and path in self._deep_risk_labels:
            self._deep_risk_labels[path].configure(
                text=f" {DeepCleanRisk.EMPTY.value} ",
                text_color=DEEP_CLEAN_RISK_COLORS.get(DeepCleanRisk.EMPTY.value, COLOR_TEXT_MUTED),
            )

    def remove_deep_entry(self, path: str) -> None:
        """Remove a card from the scrollable frame after deletion."""
        if path in self._deep_entry_cards:
            self._deep_entry_cards[path].destroy()
            del self._deep_entry_cards[path]
        self._deep_size_labels.pop(path, None)
        self._deep_risk_labels.pop(path, None)

    def set_deep_scan_enabled(self, enabled: bool) -> None:
        self._btn_deep_scan.configure(state="normal" if enabled else "disabled")

    def set_deep_bulk_enabled(self, enabled: bool) -> None:
        self._btn_deep_bulk.configure(state="normal" if enabled else "disabled")

    def show_deep_summary(self, total: int, recoverable_bytes: int) -> None:
        """Show summary KPI cards."""
        from ...services.deep_scanner import format_size

        # Clear previous summary
        for widget in self._deep_summary_frame.winfo_children():
            widget.destroy()

        # Total found card
        total_card = ctk.CTkFrame(self._deep_summary_frame, fg_color=COLOR_BORDER,
                                  corner_radius=8, width=130, height=70)
        total_card.pack(side="left", padx=(0, 8), pady=5)
        total_card.pack_propagate(False)
        ctk.CTkLabel(total_card, text=str(total),
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=COLOR_TEXT_MAIN).pack(pady=(10, 0))
        ctk.CTkLabel(total_card, text="Carpetas",
                     font=ctk.CTkFont(size=11),
                     text_color=COLOR_TEXT_MUTED).pack()

        # Recoverable space card
        recov_card = ctk.CTkFrame(self._deep_summary_frame, fg_color=COLOR_BORDER,
                                  corner_radius=8, width=160, height=70)
        recov_card.pack(side="left", padx=4, pady=5)
        recov_card.pack_propagate(False)
        ctk.CTkLabel(recov_card, text=format_size(recoverable_bytes),
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=COLOR_SUCCESS).pack(pady=(10, 0))
        ctk.CTkLabel(recov_card, text="Recuperable",
                     font=ctk.CTkFont(size=11),
                     text_color=COLOR_TEXT_MUTED).pack()

    def clear_deep_results(self) -> None:
        """Remove all cards and summary."""
        for widget in self._deep_scroll.winfo_children():
            widget.destroy()
        for widget in self._deep_summary_frame.winfo_children():
            widget.destroy()
        self._deep_entry_cards.clear()
        self._deep_size_labels.clear()
        self._deep_risk_labels.clear()

    # ── Internal helpers — Tab 2 ───────────────────────────────────────────

    def _build_doc_summary(self, result: DocumentAnalysisResult) -> None:
        """Build category KPI cards in the summary frame."""
        # Total documents card
        total_frame = ctk.CTkFrame(self._doc_summary_frame, fg_color=COLOR_BORDER,
                                   corner_radius=8, width=120, height=70)
        total_frame.pack(side="left", padx=(0, 8), pady=5)
        total_frame.pack_propagate(False)
        ctk.CTkLabel(total_frame, text=str(result.total_documents),
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=COLOR_TEXT_MAIN).pack(pady=(10, 0))
        ctk.CTkLabel(total_frame, text="Total PDFs",
                     font=ctk.CTkFont(size=11),
                     text_color=COLOR_TEXT_MUTED).pack()

        # Category cards (only show categories with count > 0)
        for category, count in sorted(
            result.category_summary.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            if count == 0:
                continue

            _tag, display_name = _CATEGORY_DISPLAY.get(
                category, ("icon_unknown", category.value),
            )
            color = _CATEGORY_COLORS.get(category, COLOR_TEXT_MUTED)

            card = ctk.CTkFrame(self._doc_summary_frame, fg_color=COLOR_BORDER,
                                corner_radius=8, width=110, height=70)
            card.pack(side="left", padx=4, pady=5)
            card.pack_propagate(False)

            lbl_count = ctk.CTkLabel(card, text=str(count),
                                     font=ctk.CTkFont(size=22, weight="bold"),
                                     text_color=color)
            lbl_count.pack(pady=(10, 0))
            ctk.CTkLabel(card, text=display_name,
                         font=ctk.CTkFont(size=11),
                         text_color=COLOR_TEXT_MUTED).pack()

            self._doc_category_labels[category] = lbl_count
