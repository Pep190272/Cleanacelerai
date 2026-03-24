"""UI Presenters: mediate between views and services."""
from .dashboard_presenter import DashboardPresenter
from .duplicates_presenter import DuplicatesPresenter

__all__ = ["DashboardPresenter", "DuplicatesPresenter"]
