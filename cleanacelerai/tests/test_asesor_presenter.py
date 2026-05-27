"""Tests for ui/presenters/asesor_presenter.py — safe delete refactor."""
from __future__ import annotations

from typing import Any, Callable
from unittest.mock import MagicMock, call, patch

import pytest

from src.domain.models import DeepCleanEntry, DeepCleanRisk, DeepCleanBundle, ProjectSignature


# ---------------------------------------------------------------------------
# FakeView — captures all view method calls; supports simulated dialog callbacks
# ---------------------------------------------------------------------------

class FakeView:
    """Fake view that records all show_* calls and supports dialog callbacks.

    Use a fresh FakeView instance per test (no class-level state).
    """

    def __init__(self) -> None:
        self.show_info_calls: list[tuple[str, str]] = []
        self.show_warning_calls: list[tuple[str, str]] = []
        self.show_error_calls: list[tuple[str, str]] = []
        self.remove_item_calls: list[str] = []
        self.remove_deep_entry_calls: list[str] = []
        self.show_project_confirm_dialog_calls: list[tuple[ProjectSignature, Callable]] = []
        self.show_project_move_warning_dialog_calls: list[tuple[ProjectSignature, Callable]] = []

    # --- View API ---

    def show_info(self, title: str, message: str) -> None:
        self.show_info_calls.append((title, message))

    def show_warning(self, title: str, message: str) -> None:
        self.show_warning_calls.append((title, message))

    def show_error(self, title: str, message: str) -> None:
        self.show_error_calls.append((title, message))

    def remove_item(self, item_id: str) -> None:
        self.remove_item_calls.append(item_id)

    def remove_deep_entry(self, path: str) -> None:
        self.remove_deep_entry_calls.append(path)

    def show_project_confirm_dialog(
        self,
        signature: ProjectSignature,
        on_confirm: Callable[[bool], None],
    ) -> None:
        self.show_project_confirm_dialog_calls.append((signature, on_confirm))

    def show_project_move_warning_dialog(
        self,
        signature: ProjectSignature,
        on_confirm: Callable[[bool], None],
    ) -> None:
        self.show_project_move_warning_dialog_calls.append((signature, on_confirm))

    # --- No-op stubs for presenter methods that call other view methods ---

    def set_deep_scan_enabled(self, enabled: bool) -> None:
        pass

    def set_deep_bulk_enabled(self, enabled: bool) -> None:
        pass

    def show_deep_progress(self, visible: bool) -> None:
        pass

    def update_entry_size(self, path: str, size: int) -> None:
        pass

    def show_deep_summary(self, count: int, total: int) -> None:
        pass

    def display_deep_entries(self, entries: list) -> None:
        pass

    def update_deep_progress(self, value: float) -> None:
        pass

    def after(self, delay: int, callback: Callable, *args: Any) -> None:
        """Immediate execution — no Tk event loop in tests."""
        callback(*args)


# ---------------------------------------------------------------------------
# Helper to build a DeepCleanEntry quickly
# ---------------------------------------------------------------------------

def _make_entry(
    path: str = r"C:\cache\entry",
    name: str = "entry",
    risk: DeepCleanRisk = DeepCleanRisk.CACHE,
    size_bytes: int = 1024,
    delete_instructions: str | None = None,
) -> DeepCleanEntry:
    return DeepCleanEntry(
        path=path,
        name=name,
        size_bytes=size_bytes,
        risk=risk,
        bundle=DeepCleanBundle.CACHE_TEMP,
        description="Cache folder",
        creator="Test",
        last_modified=None,
        is_in_use=False,
        special_note=None,
        delete_instructions=delete_instructions,
    )


# ---------------------------------------------------------------------------
# TASK 4 — delete_deep_entry tests
# ---------------------------------------------------------------------------

class TestDeleteDeepEntry:
    """Tests for delete_deep_entry using safe_delete_dir (no shutil.rmtree)."""

    def _make_presenter(self) -> tuple:
        """Return (presenter, fake_view) with one CACHE entry pre-loaded."""
        from src.ui.presenters.asesor_presenter import AsesorPresenter

        view = FakeView()
        presenter = AsesorPresenter(view)
        entry = _make_entry(path=r"C:\cache\node_modules", name="node_modules")
        presenter._deep_entries = [entry]
        return presenter, view

    def test_delete_deep_entry_uses_safe_delete_dir(self) -> None:
        """spec scenario 19: safe_delete_dir called, shutil.rmtree NOT called."""
        presenter, view = self._make_presenter()

        with (
            patch("src.ui.presenters.asesor_presenter.safe_delete_dir", return_value=(True, "")) as mock_sdd,
            patch("tkinter.messagebox.askyesno", return_value=True),
        ):
            presenter.delete_deep_entry(r"C:\cache\node_modules")

        mock_sdd.assert_called_once()
        assert view.show_info_calls, "show_info should be called on success"

    def test_delete_deep_entry_fallback_shows_warning(self) -> None:
        """spec scenario 20: FALLBACK_RENAME result triggers view.show_warning."""
        presenter, view = self._make_presenter()

        with (
            patch(
                "src.ui.presenters.asesor_presenter.safe_delete_dir",
                return_value=(True, r"FALLBACK_RENAME:C:\cache\node_modules.UNSAFE-CANT-RECYCLE.20250101T000000.bak"),
            ),
            patch("tkinter.messagebox.askyesno", return_value=True),
        ):
            presenter.delete_deep_entry(r"C:\cache\node_modules")

        assert view.show_warning_calls, "show_warning should be called for fallback rename"

    def test_delete_deep_entry_hard_failure_shows_error(self) -> None:
        """spec scenario 21: hard failure (False, error) triggers view.show_error."""
        presenter, view = self._make_presenter()

        with (
            patch(
                "src.ui.presenters.asesor_presenter.safe_delete_dir",
                return_value=(False, "disk error"),
            ),
            patch("tkinter.messagebox.askyesno", return_value=True),
        ):
            presenter.delete_deep_entry(r"C:\cache\node_modules")

        assert view.show_error_calls, "show_error should be called on hard failure"

    def test_delete_deep_entry_source_is_limpieza_profunda(self) -> None:
        """safe_delete_dir must be called with source='asesor.limpieza-profunda'."""
        presenter, view = self._make_presenter()

        with (
            patch("src.ui.presenters.asesor_presenter.safe_delete_dir", return_value=(True, "")) as mock_sdd,
            patch("tkinter.messagebox.askyesno", return_value=True),
        ):
            presenter.delete_deep_entry(r"C:\cache\node_modules")

        call_args = mock_sdd.call_args
        assert call_args is not None
        # Check source kwarg
        kwargs = call_args[1] if call_args[1] else {}
        args = call_args[0] if call_args[0] else ()
        source = kwargs.get("source") or (args[1] if len(args) > 1 else None)
        assert source == "asesor.limpieza-profunda"

    def test_delete_deep_entry_entry_removed_from_list(self) -> None:
        """After success, the entry is removed from _deep_entries."""
        presenter, view = self._make_presenter()

        with (
            patch("src.ui.presenters.asesor_presenter.safe_delete_dir", return_value=(True, "")),
            patch("tkinter.messagebox.askyesno", return_value=True),
        ):
            presenter.delete_deep_entry(r"C:\cache\node_modules")

        assert not any(e.path == r"C:\cache\node_modules" for e in presenter._deep_entries)


# ---------------------------------------------------------------------------
# TASK 4 — bulk_delete_safe tests
# ---------------------------------------------------------------------------

class TestBulkDeleteSafe:
    """Tests for bulk_delete_safe using safe_delete_dir (no shutil.rmtree)."""

    def _make_presenter_with_entries(self, n: int = 2) -> tuple:
        from src.ui.presenters.asesor_presenter import AsesorPresenter

        view = FakeView()
        presenter = AsesorPresenter(view)
        entries = [
            _make_entry(path=rf"C:\cache\entry{i}", name=f"entry{i}", size_bytes=1024)
            for i in range(n)
        ]
        presenter._deep_entries = entries
        return presenter, view

    def test_bulk_delete_safe_uses_safe_delete_dir(self) -> None:
        """spec scenario 22: each entry deleted via safe_delete_dir, not shutil.rmtree."""
        presenter, view = self._make_presenter_with_entries(2)

        with (
            patch("src.ui.presenters.asesor_presenter.safe_delete_dir", return_value=(True, "")) as mock_sdd,
            patch("tkinter.messagebox.askyesno", return_value=True),
        ):
            presenter.bulk_delete_safe()

        assert mock_sdd.call_count == 2

    def test_bulk_delete_safe_fallback_in_errors(self) -> None:
        """spec scenario 23: one entry returns fallback → appears in errors / warning."""
        presenter, view = self._make_presenter_with_entries(2)

        side_effects = [
            (True, ""),
            (True, r"FALLBACK_RENAME:C:\cache\entry1.UNSAFE-CANT-RECYCLE.20250101T000000.bak"),
        ]

        with (
            patch("src.ui.presenters.asesor_presenter.safe_delete_dir", side_effect=side_effects),
            patch("tkinter.messagebox.askyesno", return_value=True),
        ):
            presenter.bulk_delete_safe()

        # The fallback should be surfaced via show_warning
        assert view.show_warning_calls, "show_warning should be called when fallback occurred"

    def test_bulk_delete_safe_source_is_bulk_safe(self) -> None:
        """safe_delete_dir must be called with source='asesor.bulk-safe'."""
        presenter, view = self._make_presenter_with_entries(1)

        with (
            patch("src.ui.presenters.asesor_presenter.safe_delete_dir", return_value=(True, "")) as mock_sdd,
            patch("tkinter.messagebox.askyesno", return_value=True),
        ):
            presenter.bulk_delete_safe()

        call_args = mock_sdd.call_args
        assert call_args is not None
        kwargs = call_args[1] if call_args[1] else {}
        args = call_args[0] if call_args[0] else ()
        source = kwargs.get("source") or (args[1] if len(args) > 1 else None)
        assert source == "asesor.bulk-safe"

    def test_bulk_delete_safe_deleted_count_correct(self) -> None:
        """Deleted count in summary should match number of successful deletions."""
        presenter, view = self._make_presenter_with_entries(3)

        with (
            patch("src.ui.presenters.asesor_presenter.safe_delete_dir", return_value=(True, "")),
            patch("tkinter.messagebox.askyesno", return_value=True),
        ):
            presenter.bulk_delete_safe()

        # All 3 should be in remove_deep_entry calls
        assert len(view.remove_deep_entry_calls) == 3


# ---------------------------------------------------------------------------
# TASK 5 — delete_items tests
# ---------------------------------------------------------------------------

class TestDeleteItems:
    """Tests for the refactored delete_items (queue-based, no shutil.rmtree)."""

    def _make_presenter(self) -> tuple:
        from src.ui.presenters.asesor_presenter import AsesorPresenter

        view = FakeView()
        presenter = AsesorPresenter(view)
        return presenter, view

    def test_delete_items_file_uses_safe_delete(self) -> None:
        """spec scenario 12: file item -> safe_delete called, NOT safe_delete_dir."""
        presenter, view = self._make_presenter()

        with (
            patch("src.ui.presenters.asesor_presenter.safe_delete", return_value=(True, "")) as mock_sd,
            patch("src.ui.presenters.asesor_presenter.safe_delete_dir") as mock_sdd,
            patch("os.path.isdir", return_value=False),
        ):
            presenter.delete_items([("id1", r"C:\folder\file.txt", "file.txt")])

        mock_sd.assert_called_once()
        mock_sdd.assert_not_called()

    def test_delete_items_plain_dir_uses_safe_delete_dir(self) -> None:
        """spec scenario 13: dir + detector returns None -> safe_delete_dir called, no dialog."""
        presenter, view = self._make_presenter()

        with (
            patch("src.ui.presenters.asesor_presenter.safe_delete_dir", return_value=(True, "")) as mock_sdd,
            patch("src.ui.presenters.asesor_presenter.detect_project_signature", return_value=None),
            patch("os.path.isdir", return_value=True),
        ):
            presenter.delete_items([("id1", r"C:\plain\folder", "folder")])

        mock_sdd.assert_called_once()
        assert not view.show_project_confirm_dialog_calls

    def test_delete_items_project_dir_shows_dialog(self) -> None:
        """spec scenario 14: dir + ProjectSignature -> show_project_confirm_dialog called."""
        presenter, view = self._make_presenter()

        sig = ProjectSignature(
            path=r"C:\Mis_proyectos\myapp",
            signals=("inside-mis-proyectos",),
            last_modified_days=1,
        )

        with (
            patch("src.ui.presenters.asesor_presenter.detect_project_signature", return_value=sig),
            patch("os.path.isdir", return_value=True),
        ):
            presenter.delete_items([("id1", r"C:\Mis_proyectos\myapp", "myapp")])

        assert len(view.show_project_confirm_dialog_calls) == 1

    def test_delete_items_dialog_confirmed_calls_safe_delete_dir(self) -> None:
        """spec scenario 15: on_confirm(True) -> safe_delete_dir called."""
        presenter, view = self._make_presenter()

        sig = ProjectSignature(
            path=r"C:\Mis_proyectos\myapp",
            signals=("inside-mis-proyectos",),
            last_modified_days=1,
        )

        with (
            patch("src.ui.presenters.asesor_presenter.safe_delete_dir", return_value=(True, "")) as mock_sdd,
            patch("src.ui.presenters.asesor_presenter.detect_project_signature", return_value=sig),
            patch("os.path.isdir", return_value=True),
        ):
            presenter.delete_items([("id1", r"C:\Mis_proyectos\myapp", "myapp")])
            # Simulate user confirming
            assert view.show_project_confirm_dialog_calls
            _, on_confirm = view.show_project_confirm_dialog_calls[0]
            on_confirm(True)

        mock_sdd.assert_called_once()

    def test_delete_items_dialog_cancelled_skips_delete(self) -> None:
        """spec scenario 16: on_confirm(False) -> safe_delete_dir NOT called."""
        presenter, view = self._make_presenter()

        sig = ProjectSignature(
            path=r"C:\Mis_proyectos\myapp",
            signals=("inside-mis-proyectos",),
            last_modified_days=1,
        )

        with (
            patch("src.ui.presenters.asesor_presenter.safe_delete_dir") as mock_sdd,
            patch("src.ui.presenters.asesor_presenter.detect_project_signature", return_value=sig),
            patch("os.path.isdir", return_value=True),
        ):
            presenter.delete_items([("id1", r"C:\Mis_proyectos\myapp", "myapp")])
            assert view.show_project_confirm_dialog_calls
            _, on_confirm = view.show_project_confirm_dialog_calls[0]
            on_confirm(False)

        mock_sdd.assert_not_called()

    def test_delete_items_source_is_orden_general(self) -> None:
        """safe_delete_dir must be called with source='asesor.orden-general'."""
        presenter, view = self._make_presenter()

        with (
            patch("src.ui.presenters.asesor_presenter.safe_delete_dir", return_value=(True, "")) as mock_sdd,
            patch("src.ui.presenters.asesor_presenter.detect_project_signature", return_value=None),
            patch("os.path.isdir", return_value=True),
        ):
            presenter.delete_items([("id1", r"C:\plain\folder", "folder")])

        call_args = mock_sdd.call_args
        kwargs = call_args[1] if call_args[1] else {}
        args = call_args[0] if call_args[0] else ()
        source = kwargs.get("source") or (args[1] if len(args) > 1 else None)
        assert source == "asesor.orden-general"

    def test_delete_items_fallback_surfaces_warning(self) -> None:
        """spec scenario 31: FALLBACK_RENAME -> view.show_warning called."""
        presenter, view = self._make_presenter()

        with (
            patch(
                "src.ui.presenters.asesor_presenter.safe_delete_dir",
                return_value=(True, r"FALLBACK_RENAME:C:\plain\folder.UNSAFE-CANT-RECYCLE.20250101T000000.bak"),
            ),
            patch("src.ui.presenters.asesor_presenter.detect_project_signature", return_value=None),
            patch("os.path.isdir", return_value=True),
        ):
            presenter.delete_items([("id1", r"C:\plain\folder", "folder")])

        assert view.show_warning_calls

    def test_delete_items_multiple_items_queue_processes_all(self) -> None:
        """Queue processes all plain items correctly."""
        presenter, view = self._make_presenter()

        items = [
            ("id1", r"C:\plain\folder1", "folder1"),
            ("id2", r"C:\plain\folder2", "folder2"),
        ]

        with (
            patch("src.ui.presenters.asesor_presenter.safe_delete_dir", return_value=(True, "")) as mock_sdd,
            patch("src.ui.presenters.asesor_presenter.detect_project_signature", return_value=None),
            patch("os.path.isdir", return_value=True),
        ):
            presenter.delete_items(items)

        assert mock_sdd.call_count == 2
        assert len(view.remove_item_calls) == 2

    def test_delete_items_fallback_and_error_both_surfaced(self) -> None:
        """Regression for W-2: when a batch has BOTH fallback renames AND hard errors,
        both summaries must reach the user. Old elif-only branch suppressed the error
        summary when any fallback existed."""
        presenter, view = self._make_presenter()

        items = [
            ("id1", r"C:\plain\folder1", "folder1"),
            ("id2", r"C:\plain\folder2", "folder2"),
        ]

        with (
            patch(
                "src.ui.presenters.asesor_presenter.safe_delete_dir",
                side_effect=[
                    (True, r"FALLBACK_RENAME:C:\plain\folder1.UNSAFE-CANT-RECYCLE.20250101T000000.bak"),
                    (False, "OSError: permission denied"),
                ],
            ),
            patch("src.ui.presenters.asesor_presenter.detect_project_signature", return_value=None),
            patch("os.path.isdir", return_value=True),
        ):
            presenter.delete_items(items)

        warning_titles = [title.lower() for title, _msg in view.show_warning_calls]
        assert any("fallback" in t for t in warning_titles), (
            f"Missing fallback warning. Got titles: {warning_titles}"
        )
        assert any("error" in t for t in warning_titles), (
            f"Missing error warning. Got titles: {warning_titles}"
        )


# ---------------------------------------------------------------------------
# TASK 6 — move_items tests
# ---------------------------------------------------------------------------

class TestMoveItems:
    """Tests for the refactored move_items (queue-based, project warning)."""

    def _make_presenter(self) -> tuple:
        from src.ui.presenters.asesor_presenter import AsesorPresenter

        view = FakeView()
        presenter = AsesorPresenter(view)
        return presenter, view

    def test_move_items_non_project_no_dialog(self) -> None:
        """spec scenario 17: dir + detector returns None -> no dialog, shutil.move called."""
        presenter, view = self._make_presenter()

        with (
            patch("src.ui.presenters.asesor_presenter.detect_project_signature", return_value=None),
            patch("os.path.isdir", return_value=True),
            patch("shutil.move") as mock_move,
        ):
            presenter.move_items([("id1", r"C:\plain\folder", "folder")], r"C:\dest")

        mock_move.assert_called_once()
        assert not view.show_project_move_warning_dialog_calls

    def test_move_items_project_shows_warning_dialog(self) -> None:
        """spec scenario 18: dir + ProjectSignature -> show_project_move_warning_dialog called."""
        presenter, view = self._make_presenter()

        sig = ProjectSignature(
            path=r"C:\Mis_proyectos\myapp",
            signals=("inside-mis-proyectos",),
            last_modified_days=1,
        )

        with (
            patch("src.ui.presenters.asesor_presenter.detect_project_signature", return_value=sig),
            patch("os.path.isdir", return_value=True),
        ):
            presenter.move_items([("id1", r"C:\Mis_proyectos\myapp", "myapp")], r"C:\dest")

        assert len(view.show_project_move_warning_dialog_calls) == 1

    def test_move_items_project_confirmed_proceeds(self) -> None:
        """Simulate on_continue(True) -> shutil.move called."""
        presenter, view = self._make_presenter()

        sig = ProjectSignature(
            path=r"C:\Mis_proyectos\myapp",
            signals=("inside-mis-proyectos",),
            last_modified_days=1,
        )

        with (
            patch("src.ui.presenters.asesor_presenter.detect_project_signature", return_value=sig),
            patch("os.path.isdir", return_value=True),
            patch("shutil.move") as mock_move,
        ):
            presenter.move_items([("id1", r"C:\Mis_proyectos\myapp", "myapp")], r"C:\dest")
            _, on_confirm = view.show_project_move_warning_dialog_calls[0]
            on_confirm(True)

        mock_move.assert_called_once()

    def test_move_items_project_cancelled_aborts(self) -> None:
        """Simulate on_continue(False) -> shutil.move NOT called."""
        presenter, view = self._make_presenter()

        sig = ProjectSignature(
            path=r"C:\Mis_proyectos\myapp",
            signals=("inside-mis-proyectos",),
            last_modified_days=1,
        )

        with (
            patch("src.ui.presenters.asesor_presenter.detect_project_signature", return_value=sig),
            patch("os.path.isdir", return_value=True),
            patch("shutil.move") as mock_move,
        ):
            presenter.move_items([("id1", r"C:\Mis_proyectos\myapp", "myapp")], r"C:\dest")
            _, on_confirm = view.show_project_move_warning_dialog_calls[0]
            on_confirm(False)

        mock_move.assert_not_called()
