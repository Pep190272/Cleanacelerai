"""View: Shield & Rules - protection keywords and folders configuration."""
from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from ...domain.constants import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_TEXT_MAIN,
    DOTFILES_CRITICOS,
)


class ReglasView(ctk.CTkFrame):
    """View for shield and protection rules configuration."""

    def __init__(
        self,
        parent: ctk.CTkFrame,
        initial_keywords: list[str] | None = None,
        initial_folders: list[str] | None = None,
        on_config_change: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        super().__init__(parent, fg_color="transparent")

        self._on_config_change = on_config_change

        # State — use provided initial values or fall back to defaults
        self._palabras_clave: list[str] = (
            list(initial_keywords) if initial_keywords is not None else list(DOTFILES_CRITICOS)
        )
        self._carpetas_protegidas: list[str] = (
            list(initial_folders) if initial_folders is not None else []
        )

        self._build_explanation()
        self._build_keywords_section()
        self._build_folders_section()

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
                "Aquí configuras el 'Cerebro' de protección de la app. Los 'Buscadores' y el "
                "'Asesor' NUNCA tocarán nada que esté en estas listas. Los 'Dotfiles' son las "
                "'Tuberías' de configuración de tus programas (como .vscode o .ssh); "
                "moverlas rompe tus herramientas de trabajo."
            ),
            text_color=COLOR_TEXT_MAIN, wraplength=1000, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 15))

    def _build_keywords_section(self) -> None:
        tarjeta = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12,
                               border_width=1, border_color=COLOR_BORDER)
        tarjeta.pack(fill="x", padx=10, pady=(0, 15))

        ctk.CTkLabel(
            tarjeta,
            text="🛡️ DOTFILES Y PALABRAS CLAVE PROTEGIDAS (Las Tuberías)",
            font=ctk.CTkFont(weight="bold"), text_color=COLOR_TEXT_MAIN,
        ).pack(pady=(20, 5))

        self._lista_kw = tk.Listbox(
            tarjeta, height=5, bg=COLOR_BG, fg=COLOR_TEXT_MAIN,
            borderwidth=1, relief="solid", highlightthickness=0, font=("Consolas", 9),
        )
        self._lista_kw.pack(fill="x", padx=30, pady=10)
        for kw in self._palabras_clave:
            self._lista_kw.insert(tk.END, kw)

        m_add = ctk.CTkFrame(tarjeta, fg_color="transparent")
        m_add.pack(pady=(0, 20))
        self._entry_kw = ctk.CTkEntry(
            m_add, placeholder_text="Ej: .vscode",
            fg_color=COLOR_BG, text_color=COLOR_TEXT_MAIN, border_color=COLOR_BORDER,
        )
        self._entry_kw.pack(side="left", padx=10)
        ctk.CTkButton(
            m_add, text="+ Añadir",
            command=self._add_keyword,
            fg_color="#4B5563", hover_color="#374151",
        ).pack(side="left")

    def _build_folders_section(self) -> None:
        tarjeta = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12,
                               border_width=1, border_color=COLOR_BORDER)
        tarjeta.pack(fill="both", expand=True, padx=10)

        ctk.CTkLabel(
            tarjeta,
            text="📁 CARPETAS DE PROYECTOS PROTEGIDAS (No tocar)",
            font=ctk.CTkFont(weight="bold"), text_color=COLOR_TEXT_MAIN,
        ).pack(pady=(20, 5))

        self._lista_protegidas = tk.Listbox(
            tarjeta, bg=COLOR_BG, fg=COLOR_TEXT_MAIN,
            borderwidth=1, relief="solid", highlightthickness=0, font=("Segoe UI", 9),
        )
        self._lista_protegidas.pack(fill="both", expand=True, padx=30, pady=10)

        ctk.CTkButton(
            tarjeta, text="+ Proteger Carpeta de Proyecto",
            command=self._add_folder,
            fg_color="#4B5563", hover_color="#374151",
        ).pack(pady=(0, 20))

    # ── Event handlers ─────────────────────────────────────────────────────
    def _notify_change(self) -> None:
        """Fire on_config_change callback if one was provided."""
        if self._on_config_change is not None:
            self._on_config_change({
                "keywords": list(self._palabras_clave),
                "folders": list(self._carpetas_protegidas),
            })

    def _add_keyword(self) -> None:
        kw = self._entry_kw.get().strip()
        if kw and kw not in self._palabras_clave:
            self._palabras_clave.append(kw)
            self._lista_kw.insert(tk.END, kw)
            self._entry_kw.delete(0, tk.END)
            self._notify_change()

    def _add_folder(self) -> None:
        carpeta = filedialog.askdirectory()
        if carpeta and carpeta not in self._carpetas_protegidas:
            self._carpetas_protegidas.append(carpeta)
            self._lista_protegidas.insert(tk.END, carpeta)
            self._notify_change()

    # ── Public API ─────────────────────────────────────────────────────────
    def get_keywords(self) -> list[str]:
        return list(self._palabras_clave)

    def get_protected_folders(self) -> list[str]:
        return list(self._carpetas_protegidas)

    def get_shields_count(self) -> int:
        return len(self._palabras_clave)
