"""View: Dashboard - KPI cards and quick advisor table."""
from __future__ import annotations

from tkinter import ttk

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


def build_dashboard_view(parent: ctk.CTkFrame) -> "DashboardView":
    """Factory: build and return a configured DashboardView."""
    view = DashboardView(parent)
    return view


class DashboardView(ctk.CTkFrame):
    """Dashboard frame with KPI cards and a quick advisor table."""

    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_explanation()
        self._build_kpis()
        self._build_activity_table()

    def _build_explanation(self) -> None:
        marco = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12,
                             border_width=1, border_color=COLOR_BORDER)
        marco.grid(row=0, column=0, columnspan=4, padx=10, pady=(0, 20), sticky="ew")

        ctk.CTkLabel(
            marco, text="💡 EXPLICACIÓN CLARA:",
            font=ctk.CTkFont(weight="bold"), text_color=COLOR_ACCENT,
        ).pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(
            marco,
            text=(
                "Este Dashboard te muestra el estado global de la limpieza de tu PC. "
                "Los KPIs superiores resumen el espacio recuperado. La tabla inferior muestra un "
                "análisis 'Asesor IA' rápido de tu disco principal C:\\. "
                "Usa el menú lateral para herramientas específicas."
            ),
            text_color=COLOR_TEXT_MAIN, wraplength=1000, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 15))

    def _make_kpi_card(
        self, titulo: str, valor: str, color_valor: str, fila: int, columna: int
    ) -> ctk.CTkLabel:
        tarjeta = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12,
                               border_width=1, border_color=COLOR_BORDER)
        tarjeta.grid(row=fila, column=columna, padx=10, pady=10, sticky="nsew")
        tarjeta.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            tarjeta, text=titulo,
            font=ctk.CTkFont("Segoe UI", size=14), text_color=COLOR_TEXT_MUTED,
        ).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        lbl = ctk.CTkLabel(
            tarjeta, text=valor,
            font=ctk.CTkFont("Segoe UI", size=32, weight="bold"), text_color=color_valor,
        )
        lbl.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        return lbl

    def _build_kpis(self) -> None:
        self._lbl_recuperado = self._make_kpi_card(
            "Total Espacio Recuperado", "0 GB", COLOR_SUCCESS, 1, 0)
        self._lbl_basura = self._make_kpi_card(
            "Archivos Basura Detectados", "0", COLOR_WARNING, 1, 1)
        self._lbl_duplicados = self._make_kpi_card(
            "Grupos Duplicados", "0", COLOR_DANGER, 1, 2)
        self._lbl_protegidos = self._make_kpi_card(
            "Escudos Activos (Dependencias)", "0", COLOR_ACCENT, 1, 3)

    def _build_activity_table(self) -> None:
        tarjeta = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12,
                               border_width=1, border_color=COLOR_BORDER)
        tarjeta.grid(row=2, column=0, columnspan=4, padx=10, pady=20, sticky="nsew")
        tarjeta.grid_columnconfigure(0, weight=1)
        tarjeta.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            tarjeta,
            text="Actividad Reciente",
            font=ctk.CTkFont("Segoe UI", size=16, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
        ).grid(row=0, column=0, padx=20, pady=15, sticky="w")

        self._tree = ttk.Treeview(
            tarjeta,
            columns=("Fecha", "Tipo", "Archivos", "Liberado"),
            show="headings",
            selectmode="none",
        )
        self._tree.heading("Fecha", text="Fecha")
        self._tree.heading("Tipo", text="Tipo de Análisis")
        self._tree.heading("Archivos", text="Archivos")
        self._tree.heading("Liberado", text="Espacio Liberado")
        self._tree.column("Fecha", width=180)
        self._tree.column("Tipo", width=300)
        self._tree.column("Archivos", width=120, anchor="center")
        self._tree.column("Liberado", width=180, anchor="center")
        self._tree.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))

        # Empty state label — hidden when rows are added
        self._lbl_empty = ctk.CTkLabel(
            tarjeta,
            text="Aún no hay análisis realizados.\nEjecuta un análisis desde el menú lateral para ver resultados aquí.",
            text_color=COLOR_TEXT_MUTED,
            font=ctk.CTkFont("Segoe UI", size=13),
            justify="center",
        )
        self._lbl_empty.grid(row=2, column=0, pady=30)

    # ── Public API (called by DashboardPresenter) ──────────────────────────
    def set_kpi_recuperado(self, text: str) -> None:
        self._lbl_recuperado.configure(text=text)

    def set_kpi_basura(self, text: str) -> None:
        self._lbl_basura.configure(text=text)

    def set_kpi_duplicados(self, text: str) -> None:
        self._lbl_duplicados.configure(text=text)

    def set_kpi_protegidos(self, text: str) -> None:
        self._lbl_protegidos.configure(text=text)

    def add_activity_row(
        self, fecha: str, tipo: str, archivos: int | str, liberado: str
    ) -> None:
        """Insert one row into the activity table.

        Called by DashboardPresenter (or directly from MainWindow) after a real scan
        completes. Hides the empty-state label on the first insertion.

        Args:
            fecha:    Human-readable timestamp (e.g. "22/03/2026 14:35").
            tipo:     Scan type label (e.g. "🗑️ Limpieza de Basura Temp").
            archivos: Number of files processed (int or pre-formatted string).
            liberado: Space freed, pre-formatted (e.g. "1.23 GB" or "0 MB").
        """
        self._tree.insert("", "end", values=(fecha, tipo, str(archivos), liberado))
        # Hide the empty-state label once we have at least one real row
        self._lbl_empty.grid_forget()

    def clear_activity(self) -> None:
        """Remove all rows from the activity table and restore the empty state."""
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._lbl_empty.grid(row=2, column=0, pady=30)
