"""Tests for DuplicatesPresenter binary mode state machine."""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from src.ui.presenters.duplicates_presenter import DuplicatesPresenter


class FakeView:
    """Stub view that records calls for assertion."""

    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.scan_started: bool = False
        self.scan_finished: bool = False

    def show_error(self, title: str, message: str) -> None:
        self.errors.append((title, message))

    def on_scan_started(self) -> None:
        self.scan_started = True

    def on_scan_finished(self, count: int) -> None:
        self.scan_finished = True

    def after(self, ms: int, fn: object, *args: object) -> None:
        # Execute immediately for synchronous test use
        fn(*args)  # type: ignore[call-arg, operator]

    def log(self, msg: str) -> None:
        pass


class FakeConfigService:
    """Stub config service with controllable save failure."""

    def __init__(self, initial_data: dict | None = None, raise_on_save: Exception | None = None) -> None:
        self._data: dict = initial_data or {}
        self._raise_on_save = raise_on_save

    def load(self, defaults: dict) -> dict:
        return {**defaults, **self._data}

    def save(self, d: dict) -> None:
        if self._raise_on_save is not None:
            raise self._raise_on_save
        self._data = dict(d)


def make_presenter(
    binary_mode: bool = False,
    config_data: dict | None = None,
    raise_on_save: Exception | None = None,
) -> tuple[DuplicatesPresenter, FakeView, FakeConfigService]:
    view = FakeView()
    config = FakeConfigService(initial_data=config_data, raise_on_save=raise_on_save)
    presenter = DuplicatesPresenter(
        view,  # type: ignore[arg-type]
        config_service=config,
        initial_binary_mode=binary_mode,
    )
    return presenter, view, config


class TestPresenterBinaryModeState:
    """Verify _binary_mode state, set_binary_mode, and config persistence."""

    def test_default_binary_mode_is_false(self) -> None:
        presenter, _, _ = make_presenter()
        assert presenter._binary_mode is False

    def test_set_binary_mode_true(self) -> None:
        presenter, _, _ = make_presenter()
        presenter.set_binary_mode(True)
        assert presenter._binary_mode is True

    def test_set_binary_mode_false(self) -> None:
        presenter, _, _ = make_presenter(binary_mode=True)
        presenter.set_binary_mode(False)
        assert presenter._binary_mode is False

    def test_set_binary_mode_persists_to_config(self) -> None:
        presenter, _, config = make_presenter()
        presenter.set_binary_mode(True)
        assert config._data.get("binary_assets_mode_enabled") is True

    def test_set_binary_mode_false_persists(self) -> None:
        presenter, _, config = make_presenter(binary_mode=True)
        presenter.set_binary_mode(False)
        assert config._data.get("binary_assets_mode_enabled") is False

    def test_config_save_failure_shows_error(self) -> None:
        presenter, view, _ = make_presenter(raise_on_save=OSError("disk full"))
        presenter.set_binary_mode(True)
        # _binary_mode must still be updated (in-memory flag is set before save attempt)
        assert presenter._binary_mode is True
        # view.show_error must have been called
        assert len(view.errors) > 0
        assert any("binario" in msg.lower() or "guardando" in title.lower()
                   for title, msg in view.errors)

    def test_initial_binary_mode_true_via_constructor(self) -> None:
        presenter, _, _ = make_presenter(binary_mode=True)
        assert presenter._binary_mode is True


class TestPresenterIsPathBlockedModeAware:
    """Verify is_path_blocked is mode-aware."""

    def test_mode_off_blocks_mis_proyectos(self) -> None:
        presenter, _, _ = make_presenter(binary_mode=False)
        assert presenter.is_path_blocked(r"D:\Mis_proyectos") is True

    def test_mode_on_allows_mis_proyectos(self) -> None:
        presenter, _, _ = make_presenter(binary_mode=True)
        assert presenter.is_path_blocked(r"D:\Mis_proyectos\photos") is False

    def test_mode_on_still_blocks_node_modules_inside_project(self) -> None:
        presenter, _, _ = make_presenter(binary_mode=True)
        assert presenter.is_path_blocked(r"D:\Mis_proyectos\proj\node_modules") is True

    def test_mode_on_still_blocks_appdata(self) -> None:
        presenter, _, _ = make_presenter(binary_mode=True)
        assert presenter.is_path_blocked(r"C:\Users\X\AppData\Local\Temp") is True

    def test_mode_on_still_blocks_venv(self) -> None:
        presenter, _, _ = make_presenter(binary_mode=True)
        assert presenter.is_path_blocked(r"D:\Mis_proyectos\proj\venv") is True

    def test_mode_off_blocks_local_sites(self) -> None:
        presenter, _, _ = make_presenter(binary_mode=False)
        assert presenter.is_path_blocked(r"C:\Users\Josep\Local Sites") is True

    def test_mode_on_allows_local_sites(self) -> None:
        presenter, _, _ = make_presenter(binary_mode=True)
        assert presenter.is_path_blocked(r"C:\Users\Josep\Local Sites\mysite") is False


class TestPresenterAutoSelectAllowed:
    """Verify is_auto_select_allowed reflects binary mode."""

    def test_auto_select_allowed_when_mode_off(self) -> None:
        presenter, _, _ = make_presenter(binary_mode=False)
        assert presenter.is_auto_select_allowed() is True

    def test_auto_select_blocked_when_mode_on(self) -> None:
        presenter, _, _ = make_presenter(binary_mode=True)
        assert presenter.is_auto_select_allowed() is False

    def test_auto_select_updates_after_toggle(self) -> None:
        presenter, _, _ = make_presenter(binary_mode=False)
        assert presenter.is_auto_select_allowed() is True
        presenter.set_binary_mode(True)
        assert presenter.is_auto_select_allowed() is False
        presenter.set_binary_mode(False)
        assert presenter.is_auto_select_allowed() is True


class TestPresenterStartScanSnapshots:
    """Verify that start_scan snapshots binary mode before spawning the worker."""

    def test_mode_snapshot_at_scan_start(self, tmp_path: object) -> None:
        """Toggle mode to True, start scan, then toggle to False before thread completes.
        Worker must have been called with binary params (allowed_extensions is not None)."""
        import os as _os
        presenter, view, _ = make_presenter(binary_mode=True)

        captured_kwargs: list[dict] = []

        def fake_find_duplicates(*args: object, **kwargs: object) -> list:
            captured_kwargs.append(kwargs)
            return []

        with patch("src.ui.presenters.duplicates_presenter.find_duplicates", fake_find_duplicates):
            presenter.start_scan([str(tmp_path)])
            # Toggle mode to False after scan started (simulating user action mid-scan)
            presenter.set_binary_mode(False)
            # Allow thread to complete
            time.sleep(0.3)

        assert len(captured_kwargs) == 1
        # Worker must have used binary params (snapshot taken before toggle)
        assert captured_kwargs[0].get("allowed_extensions") is not None
        assert captured_kwargs[0].get("min_size_bytes") == 51_200
