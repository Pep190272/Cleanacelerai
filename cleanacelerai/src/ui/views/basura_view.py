"""View: Temp file cleaner — passive widget layer."""
from __future__ import annotations

import tkinter as tk
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
)

if TYPE_CHECKING:
    from ..presenters.basura_presenter import BasuraPresenter


class BasuraView(ctk.CTkFrame):
    """Passive view for the temporary-file cleaner module.

    Business logic lives in BasuraPresenter. This class only manages widgets
    and provides a public API for the presenter to call.
    """

    def __init__(self, parent: ctk.CTkFrame) -> None:
        super().__init__(parent, fg_color="transparent")

        self._presenter: "BasuraPresenter | None" = None

        self._build_explanation()
        self._build_content()

    def set_presenter(self, presenter: "BasuraPresenter") -> None:
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
                "Esta herramienta escanea las carpetas 'Temp' de Windows y de tu Usuario. "
                "Aquí se acumulan archivos que los programas crean al instalarse o ejecutarse "
                "y que olvidan borrar. Eliminarlos recupera espacio y mejora la velocidad del disco."
            ),
            text_color=COLOR_TEXT_MAIN, wraplength=1000, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 15))

    def _build_content(self) -> None:
        tarjeta = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12,
                               border_width=1, border_color=COLOR_BORDER)
        tarjeta.pack(fill="both", expand=True, padx=10)

        ctk.CTkLabel(
            tarjeta,
            text="Recupera espacio eliminando archivos temporales que Windows ya no necesita.",
            font=ctk.CTkFont(size=14), text_color=COLOR_TEXT_MUTED,
        ).pack(pady=20)

        self._lbl_info = ctk.CTkLabel(
            tarjeta, text="Haz clic en Analizar para buscar basura...",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_MAIN,
        )
        self._lbl_info.pack(pady=30)

        marco_botones = ctk.CTkFrame(tarjeta, fg_color="transparent")
        marco_botones.pack(pady=20)

        ctk.CTkButton(
            marco_botones, text="🔍 1. Analizar Basura",
            command=self._on_analyze,
            fg_color="#4B5563", hover_color="#374151",
            font=ctk.CTkFont(size=14, weight="bold"), height=40,
        ).pack(side="left", padx=10)

        self._btn_limpiar = ctk.CTkButton(
            marco_botones, text="✨ 2. Vaciar Temporales",
            command=self._on_clean,
            fg_color=COLOR_SUCCESS, hover_color="#059669",
            font=ctk.CTkFont(size=14, weight="bold"), height=40, state="disabled",
        )
        self._btn_limpiar.pack(side="left", padx=10)

        self._log_widget = tk.Text(
            tarjeta, height=15, font=("Consolas", 9),
            bg=COLOR_BG, fg=COLOR_TEXT_MAIN, borderwidth=1, relief="solid",
        )
        self._log_widget.pack(fill="both", expand=True, padx=30, pady=20)

    # ── User-action callbacks (delegate to presenter) ──────────────────────

    def _on_analyze(self) -> None:
        if self._presenter:
            self._presenter.start_scan()

    def _on_clean(self) -> None:
        from tkinter import messagebox
        if not messagebox.askyesno(
            "Confirmar Limpieza",
            "¿Estás seguro de vaciar todos los archivos temporales detectados?",
        ):
            return
        if self._presenter:
            self._presenter.start_clean()

    # ── Public API for presenter ───────────────────────────────────────────

    def log(self, text: str) -> None:
        """Append *text* to the log widget."""
        self._log_widget.insert(tk.END, text)
        self._log_widget.see(tk.END)

    def on_scan_started(self) -> None:
        """Reset UI state when a scan begins."""
        self._log_widget.delete(1.0, tk.END)
        self._btn_limpiar.configure(state="disabled")

    def on_scan_finished(self, archivos: list[str], total_mb: float) -> None:
        """Update UI after scan completes."""
        self._lbl_info.configure(
            text=f"Detectados {len(archivos)} archivos ({total_mb:.2f} MB recuperables)"
        )
        if archivos:
            self._btn_limpiar.configure(state="normal")

    def on_clean_started(self) -> None:
        """Reset log when a clean begins."""
        self._log_widget.delete(1.0, tk.END)

    def on_clean_finished(self, result: object) -> None:
        """Update UI after cleaning completes."""
        from ...domain.models import CleanupResult
        assert isinstance(result, CleanupResult)
        self.log(
            f"\n✅ LIMPIEZA EXITOSA:\n"
            f"- Archivos borrados: {result.deleted}\n"
            f"- Espacio liberado real: {result.freed_mb:.2f} MB\n"
        )
        self._btn_limpiar.configure(state="disabled")
        self._lbl_info.configure(text="Limpieza completada.")
