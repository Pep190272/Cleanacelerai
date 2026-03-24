"""Presenter: coordinates summary KPI updates for the dashboard view."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..views.dashboard_view import DashboardView


class DashboardPresenter:
    """Updates KPI labels on the dashboard from scan/cleanup results."""

    def __init__(self, view: "DashboardView") -> None:
        self.view = view

    def update_basura_kpi(self, count: int) -> None:
        self.view.set_kpi_basura(str(count))

    def update_duplicados_kpi(self, count: int) -> None:
        self.view.set_kpi_duplicados(str(count))

    def update_recovered_kpi(self, freed_mb: float) -> None:
        gb = freed_mb / 1024
        self.view.set_kpi_recuperado(f"{gb:.2f} GB")

    def update_shields_kpi(self, count: int) -> None:
        self.view.set_kpi_protegidos(str(count))

    def record_activity(
        self, tipo: str, archivos: int, freed_mb: float
    ) -> None:
        """Add one row to the activity table with the current timestamp.

        Args:
            tipo:      Human-readable scan label (e.g. "🗑️ Limpieza de Basura Temp").
            archivos:  Number of files affected.
            freed_mb:  Space freed in megabytes (will be formatted automatically).
        """
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        if freed_mb >= 1024:
            liberado = f"{freed_mb / 1024:.2f} GB"
        else:
            liberado = f"{freed_mb:.1f} MB"
        self.view.add_activity_row(fecha, tipo, archivos, liberado)
