"""Tests for path blocklist — Patch 4 safety guard."""
from __future__ import annotations

import pytest

from src.domain.constants import PATHS_BLOQUEADOS_SCAN
from src.ui.presenters.duplicates_presenter import DuplicatesPresenter


class FakeView:
    """Minimal stub so DuplicatesPresenter can be instantiated."""
    pass


def make_presenter() -> DuplicatesPresenter:
    return DuplicatesPresenter(FakeView())  # type: ignore[arg-type]


class TestPathsBlockeadosScanConstant:
    """Verify the constant itself has the expected entries."""

    def test_local_sites_is_blocked(self) -> None:
        assert any("local sites" in b.lower() for b in PATHS_BLOQUEADOS_SCAN)

    def test_mis_proyectos_is_blocked(self) -> None:
        assert any("mis_proyectos" in b.lower() for b in PATHS_BLOQUEADOS_SCAN)

    def test_git_is_blocked(self) -> None:
        assert any(".git" in b.lower() for b in PATHS_BLOQUEADOS_SCAN)

    def test_node_modules_is_blocked(self) -> None:
        assert any("node_modules" in b.lower() for b in PATHS_BLOQUEADOS_SCAN)

    def test_venv_is_blocked(self) -> None:
        assert any("venv" in b.lower() for b in PATHS_BLOQUEADOS_SCAN)


class TestPresenterIsPathBlocked:
    """Tests for DuplicatesPresenter.is_path_blocked()."""

    def test_local_sites_is_blocked(self) -> None:
        p = make_presenter()
        assert p.is_path_blocked(r"C:\Users\Josep\Local Sites\ladronesdebesos\app")

    def test_mis_proyectos_is_blocked(self) -> None:
        p = make_presenter()
        assert p.is_path_blocked(r"D:\Mis_proyectos\Cleanacelerai")

    def test_git_folder_is_blocked(self) -> None:
        p = make_presenter()
        assert p.is_path_blocked(r"D:\repos\myproject\.git\objects")

    def test_node_modules_is_blocked(self) -> None:
        p = make_presenter()
        assert p.is_path_blocked(r"D:\projects\app\node_modules\react")

    def test_venv_is_blocked(self) -> None:
        p = make_presenter()
        assert p.is_path_blocked(r"D:\projects\myapp\venv\Lib\site-packages")

    def test_safe_path_is_not_blocked(self) -> None:
        p = make_presenter()
        assert not p.is_path_blocked(r"C:\Users\Josep\Pictures\Vacation")

    def test_safe_downloads_not_blocked(self) -> None:
        p = make_presenter()
        assert not p.is_path_blocked(r"C:\Users\Josep\Downloads")

    def test_case_insensitive_match(self) -> None:
        """Blocklist matching must be case-insensitive."""
        p = make_presenter()
        # Mixed-case variant of Local Sites
        assert p.is_path_blocked(r"C:\Users\Josep\LOCAL SITES\mysite")

    def test_case_insensitive_mis_proyectos(self) -> None:
        p = make_presenter()
        assert p.is_path_blocked(r"D:\mis_proyectos\SomeProject")

    def test_build_folder_is_blocked(self) -> None:
        p = make_presenter()
        assert p.is_path_blocked(r"D:\projects\app\build\static")

    def test_dist_folder_is_blocked(self) -> None:
        p = make_presenter()
        assert p.is_path_blocked(r"D:\projects\app\dist\index.js")

    # ── Regression: parent folder picked exactly, no trailing separator ──
    def test_mis_proyectos_parent_exact_is_blocked(self) -> None:
        """User can pick D:\\Mis_proyectos itself — must still be refused."""
        p = make_presenter()
        assert p.is_path_blocked(r"D:\Mis_proyectos")

    def test_local_sites_parent_exact_is_blocked(self) -> None:
        """User can pick C:\\Users\\Josep\\Local Sites itself — must still be refused."""
        p = make_presenter()
        assert p.is_path_blocked(r"C:\Users\Josep\Local Sites")

    def test_mis_proyectos_with_trailing_sep_is_blocked(self) -> None:
        p = make_presenter()
        assert p.is_path_blocked("D:\\Mis_proyectos\\")

    def test_venv_parent_exact_is_blocked(self) -> None:
        p = make_presenter()
        assert p.is_path_blocked(r"D:\projects\myapp\venv")
