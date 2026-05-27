"""Tests for path blocklist — Patch 4 safety guard."""
from __future__ import annotations

import pytest

from src.domain.constants import (
    BINARY_MODE_SIZE_FLOOR_BYTES,
    EXTENSIONES_ASSETS_BINARIOS,
    PATHS_BLOQUEADOS_SCAN,
    PATHS_BLOQUEADOS_SCAN_PROJECTS,
    PATHS_BLOQUEADOS_SCAN_TECH,
)
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


class TestBlocklistSplit:
    """Verify PATHS_BLOQUEADOS_SCAN_TECH + PATHS_BLOQUEADOS_SCAN_PROJECTS split."""

    def test_alias_equals_union(self) -> None:
        assert PATHS_BLOQUEADOS_SCAN == PATHS_BLOQUEADOS_SCAN_TECH + PATHS_BLOQUEADOS_SCAN_PROJECTS

    def test_appdata_broad_in_tech(self) -> None:
        assert "\\AppData\\" in PATHS_BLOQUEADOS_SCAN_TECH

    def test_appdata_roaming_local_absent_from_tech(self) -> None:
        assert "\\AppData\\Roaming\\Local\\" not in PATHS_BLOQUEADOS_SCAN_TECH

    def test_appdata_roaming_local_absent_from_projects(self) -> None:
        assert "\\AppData\\Roaming\\Local\\" not in PATHS_BLOQUEADOS_SCAN_PROJECTS

    def test_appdata_roaming_local_absent_from_alias(self) -> None:
        assert "\\AppData\\Roaming\\Local\\" not in PATHS_BLOQUEADOS_SCAN

    def test_mis_proyectos_in_projects(self) -> None:
        assert "\\Mis_proyectos\\" in PATHS_BLOQUEADOS_SCAN_PROJECTS

    def test_local_sites_in_projects(self) -> None:
        assert "\\Local Sites\\" in PATHS_BLOQUEADOS_SCAN_PROJECTS

    def test_node_modules_in_tech(self) -> None:
        assert "\\node_modules\\" in PATHS_BLOQUEADOS_SCAN_TECH

    def test_legacy_alias_still_has_9_entries(self) -> None:
        assert len(PATHS_BLOQUEADOS_SCAN) == 9


class TestExtensionWhitelistConstant:
    """Verify EXTENSIONES_ASSETS_BINARIOS contains expected and excludes forbidden."""

    def test_whitelist_contains_png(self) -> None:
        assert ".png" in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_contains_jpg(self) -> None:
        assert ".jpg" in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_contains_jpeg(self) -> None:
        assert ".jpeg" in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_contains_gif(self) -> None:
        assert ".gif" in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_contains_webp(self) -> None:
        assert ".webp" in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_contains_pdf(self) -> None:
        assert ".pdf" in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_contains_mp4(self) -> None:
        assert ".mp4" in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_contains_mov(self) -> None:
        assert ".mov" in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_contains_mp3(self) -> None:
        assert ".mp3" in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_contains_zip(self) -> None:
        assert ".zip" in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_contains_psd(self) -> None:
        assert ".psd" in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_contains_fig(self) -> None:
        assert ".fig" in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_excludes_py(self) -> None:
        assert ".py" not in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_excludes_js(self) -> None:
        assert ".js" not in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_excludes_php(self) -> None:
        assert ".php" not in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_excludes_json(self) -> None:
        assert ".json" not in EXTENSIONES_ASSETS_BINARIOS

    def test_whitelist_excludes_md(self) -> None:
        assert ".md" not in EXTENSIONES_ASSETS_BINARIOS


class TestBinaryModeSizeFloor:
    """Verify BINARY_MODE_SIZE_FLOOR_BYTES constant."""

    def test_size_floor_value(self) -> None:
        assert BINARY_MODE_SIZE_FLOOR_BYTES == 51_200
