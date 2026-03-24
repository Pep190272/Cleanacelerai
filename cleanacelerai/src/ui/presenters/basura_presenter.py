"""Presenter: coordinates temp-file cleaner service with BasuraView."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Callable

from ...services.temp_cleaner import clean_temp_files, scan_temp_files

if TYPE_CHECKING:
    from ..views.basura_view import BasuraView


class BasuraPresenter:
    """Mediates between BasuraView and the temp-cleaner service."""

    def __init__(self, view: "BasuraView") -> None:
        self.view = view
        self._archivos_basura: list[str] = []
        self._on_freed_mb: Callable[[float], None] | None = None
        self._on_count_changed: Callable[[int], None] | None = None

    def set_on_freed_mb(self, callback: Callable[[float], None]) -> None:
        """Register a callback fired after a successful cleanup (freed MB)."""
        self._on_freed_mb = callback

    def set_on_count_changed(self, callback: Callable[[int], None]) -> None:
        """Register a callback fired when the detected file count changes."""
        self._on_count_changed = callback

    # ── Public API ─────────────────────────────────────────────────────────

    def start_scan(self) -> None:
        """Start the temp-file scan in a background thread."""
        self._archivos_basura = []
        self.view.on_scan_started()

        def _progress(msg: str) -> None:
            self.view.after(0, self.view.log, msg + "\n")

        def _run() -> None:
            archivos, total_mb = scan_temp_files(on_progress=_progress)
            self.view.after(0, self._on_scan_done, archivos, total_mb)

        threading.Thread(target=_run, daemon=True).start()

    def start_clean(self) -> None:
        """Clean the previously scanned temp files in a background thread."""
        if not self._archivos_basura:
            return
        self.view.on_clean_started()

        def _progress(msg: str) -> None:
            self.view.after(0, self.view.log, msg + "\n")

        def _run() -> None:
            result = clean_temp_files(self._archivos_basura, on_progress=_progress)
            self.view.after(0, self._on_clean_done, result)

        threading.Thread(target=_run, daemon=True).start()

    # ── Private callbacks (always called on the main thread via after(0,...)) ──

    def _on_scan_done(self, archivos: list[str], total_mb: float) -> None:
        self._archivos_basura = archivos
        self.view.on_scan_finished(archivos, total_mb)
        if self._on_count_changed:
            self._on_count_changed(len(archivos))

    def _on_clean_done(self, result: object) -> None:
        from ...domain.models import CleanupResult
        assert isinstance(result, CleanupResult)
        self._archivos_basura = []
        self.view.on_clean_finished(result)
        if self._on_freed_mb:
            self._on_freed_mb(result.freed_mb)
        if self._on_count_changed:
            self._on_count_changed(0)
