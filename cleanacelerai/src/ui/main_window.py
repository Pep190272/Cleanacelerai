"""Main application window: thin orchestrator - layout + navigation only."""
from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk

from ..domain.constants import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    DOTFILES_CRITICOS,
)
from ..infrastructure.config_service import ConfigService
from .presenters.asesor_presenter import AsesorPresenter
from .presenters.basura_presenter import BasuraPresenter
from .presenters.dashboard_presenter import DashboardPresenter
from .presenters.duplicates_presenter import DuplicatesPresenter
from .presenters.marcador_presenter import MarcadorPresenter
from .presenters.renombrado_presenter import RenombradoPresenter
from .views.asesor_view import AsesorView
from .views.basura_view import BasuraView
from .views.dashboard_view import DashboardView
from .views.duplicates_view import DuplicatesView
from .views.marcador_view import MarcadorView
from .views.reglas_view import ReglasView
from .views.renombrado_view import RenombradoView


class MainWindow(ctk.CTk):
    """Top-level application window. Orchestrates views and presenters."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Cleanacelerai PRO - V25 Dashboard")
        self.geometry("1400x900")
        self.configure(fg_color=COLOR_BG)

        # Config persistence
        self._config_service = ConfigService()
        _defaults = {
            "keywords": sorted(DOTFILES_CRITICOS),
            "folders": [],
        }
        self._config = self._config_service.load(_defaults)

        # State for cross-callback coordination
        self._last_basura_count: int = 0

        self._setup_table_style()
        self._build_layout()
        self._wire_presenters()

        # Show dashboard on startup
        self._select_frame("dashboard")

    # ── Setup ──────────────────────────────────────────────────────────────
    def _setup_table_style(self) -> None:
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Treeview",
            background=COLOR_CARD, foreground=COLOR_TEXT_MAIN,
            rowheight=28, fieldbackground=COLOR_CARD,
            borderwidth=0, font=("Segoe UI", 9),
        )
        style.map("Treeview",
                  background=[("selected", COLOR_ACCENT)],
                  foreground=[("selected", "#ffffff")])
        style.configure(
            "Treeview.Heading",
            background=COLOR_BORDER, foreground=COLOR_TEXT_MAIN,
            font=("Segoe UI", 10, "bold"), borderwidth=0,
        )
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    def _build_layout(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_header()
        self._build_content_area()

    def _build_sidebar(self) -> None:
        self._sidebar = ctk.CTkFrame(
            self, width=260, corner_radius=0,
            fg_color=COLOR_CARD, border_width=1, border_color=COLOR_BORDER,
        )
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(
            self._sidebar, text="Cleanacelerai\nPRO V25",
            font=ctk.CTkFont("Segoe UI", size=24, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
        ).grid(row=0, column=0, padx=20, pady=(35, 45))

        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        nav_items = [
            ("📊 Dashboard", "dashboard", 1),
            ("🗑️ Limpiar Basura Temp", "basura", 2),
            ("🔍 Duplicados IA", "duplicados", 3),
            ("🧠 Asesor de Orden", "asesor", 4),
            ("🔖 Marcadores Navegador", "marcadores", 5),
            ("🛡️ Escudo y Reglas", "reglas", 6),
            ("✏️ Renombrado Masivo", "renombrado", 7),
        ]
        for texto, nombre, fila in nav_items:
            btn = ctk.CTkButton(
                self._sidebar, text=texto,
                fg_color="transparent", text_color=COLOR_TEXT_MUTED,
                hover_color=COLOR_BORDER, anchor="w",
                command=lambda n=nombre: self._select_frame(n),
                font=ctk.CTkFont("Segoe UI", size=15), height=45,
            )
            btn.grid(row=fila, column=0, padx=15, pady=5, sticky="ew")
            self._nav_buttons[nombre] = btn

    def _build_header(self) -> None:
        self._header = ctk.CTkFrame(
            self, height=70, corner_radius=0,
            fg_color=COLOR_BG, border_width=1, border_color=COLOR_BORDER,
        )
        self._header.grid(row=0, column=1, sticky="new")
        self._header.grid_columnconfigure(1, weight=1)

        self._lbl_titulo = ctk.CTkLabel(
            self._header, text="Visión General",
            font=ctk.CTkFont("Segoe UI", size=22, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
        )
        self._lbl_titulo.grid(row=0, column=0, padx=30, pady=20, sticky="w")

        ctk.CTkLabel(
            self._header, text="👤 Josep | Desarrollador",
            font=ctk.CTkFont(size=14), text_color=COLOR_TEXT_MUTED,
        ).grid(row=0, column=2, padx=30, pady=20, sticky="e")

    def _build_content_area(self) -> None:
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.grid(row=0, column=1, sticky="nsew", padx=30, pady=(100, 30))
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        # Rules view is instantiated first so other presenters can reference its callbacks
        self._reglas_view = ReglasView(
            self._content,
            initial_keywords=self._config.get("keywords"),
            initial_folders=self._config.get("folders"),
            on_config_change=self._config_service.save,
        )

        self._dashboard_view = DashboardView(self._content)
        self._basura_view = BasuraView(self._content)
        self._duplicates_view = DuplicatesView(self._content)
        self._asesor_view = AsesorView(self._content)
        self._marcadores_view = MarcadorView(self._content)
        self._renombrado_view = RenombradoView(self._content)

        self._frames: dict[str, ctk.CTkFrame] = {
            "dashboard": self._dashboard_view,
            "basura": self._basura_view,
            "duplicados": self._duplicates_view,
            "asesor": self._asesor_view,
            "marcadores": self._marcadores_view,
            "reglas": self._reglas_view,
            "renombrado": self._renombrado_view,
        }

    def _wire_presenters(self) -> None:
        """Instantiate all presenters and inject them into their views."""
        # Dashboard
        self._dashboard_presenter = DashboardPresenter(self._dashboard_view)
        self._dashboard_presenter.update_shields_kpi(
            self._reglas_view.get_shields_count()
        )

        # Basura
        self._basura_presenter = BasuraPresenter(self._basura_view)
        self._basura_presenter.set_on_freed_mb(self._on_freed_mb)
        self._basura_presenter.set_on_count_changed(self._on_basura_count)
        self._basura_view.set_presenter(self._basura_presenter)

        # Duplicates
        self._duplicates_presenter = DuplicatesPresenter(self._duplicates_view)
        self._duplicates_presenter.set_protection(
            keywords=self._reglas_view.get_keywords(),
            folders=self._reglas_view.get_protected_folders(),
        )
        self._duplicates_view.set_presenter(self._duplicates_presenter)

        # Asesor
        self._asesor_presenter = AsesorPresenter(
            self._asesor_view,
            get_keywords=self._reglas_view.get_keywords,
            get_folders=self._reglas_view.get_protected_folders,
        )
        self._asesor_view.set_presenter(self._asesor_presenter)

        # Marcadores
        self._marcador_presenter = MarcadorPresenter(self._marcadores_view)
        self._marcadores_view.set_presenter(self._marcador_presenter)

        # Renombrado
        self._renombrado_presenter = RenombradoPresenter(self._renombrado_view)
        self._renombrado_view.set_presenter(self._renombrado_presenter)

    # ── Navigation ─────────────────────────────────────────────────────────
    _TITULOS: dict[str, str] = {
        "dashboard": "Visión General (Resumen)",
        "basura": "Limpiador de Archivos Temporales y Cachés",
        "duplicados": "Buscador Inteligente de Duplicados (IA Hash)",
        "asesor": "Asesor de Orden de Inteligencia Artificial",
        "marcadores": "Limpiador de Marcadores de Navegador Repetidos",
        "reglas": "Escudo del Sistema y Reglas de Protección",
        "renombrado": "Renombrado Masivo y Profesional de Archivos",
    }

    def _select_frame(self, nombre: str) -> None:
        # Update sidebar button styles
        for key, btn in self._nav_buttons.items():
            if key == nombre:
                btn.configure(fg_color=COLOR_ACCENT, text_color="#ffffff",
                              font=ctk.CTkFont(weight="bold"))
            else:
                btn.configure(fg_color="transparent", text_color=COLOR_TEXT_MUTED,
                              font=ctk.CTkFont(weight="normal"))

        # Update header title
        self._lbl_titulo.configure(text=self._TITULOS.get(nombre, nombre))

        # Refresh presenter protection before switching to duplicados
        if nombre == "duplicados":
            self._duplicates_presenter.set_protection(
                keywords=self._reglas_view.get_keywords(),
                folders=self._reglas_view.get_protected_folders(),
            )

        # Show selected frame
        for frame in self._frames.values():
            frame.grid_forget()
        self._frames[nombre].grid(row=0, column=0, sticky="nsew")

    # ── Callbacks from presenters ──────────────────────────────────────────
    def _on_freed_mb(self, mb: float) -> None:
        self._dashboard_presenter.update_recovered_kpi(mb)
        # Record activity only when space was actually freed (mb > 0)
        if mb > 0:
            self._dashboard_presenter.record_activity(
                tipo="🗑️ Limpieza de Basura Temp",
                archivos=self._last_basura_count,
                freed_mb=mb,
            )

    def _on_basura_count(self, count: int) -> None:
        self._last_basura_count = count
        self._dashboard_presenter.update_basura_kpi(count)
