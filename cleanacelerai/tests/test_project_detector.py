"""Tests for services/project_detector.py — detect_project_signature."""
from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.project_detector import detect_project_signature


class TestPathSignals:
    """Path-based signal detection (no filesystem listing needed)."""

    def test_path_signal_mis_proyectos(self, tmp_path: Path) -> None:
        """GIVEN a path containing \\Mis_proyectos\\, THEN signal is present."""
        folder = tmp_path / "Mis_proyectos" / "myapp"
        folder.mkdir(parents=True)
        path_str = str(folder)

        result = detect_project_signature(path_str)
        assert result is not None
        assert "inside-mis-proyectos" in result.signals

    def test_path_signal_local_sites(self, tmp_path: Path) -> None:
        """GIVEN a path containing \\Local Sites\\, THEN signal is present."""
        folder = tmp_path / "Local Sites" / "mysite"
        folder.mkdir(parents=True)
        path_str = str(folder)

        result = detect_project_signature(path_str)
        assert result is not None
        assert "inside-local-sites" in result.signals


class TestFileSignals:
    """File-based signal detection using real tmp_path directories."""

    def test_file_signal_has_git(self, tmp_path: Path) -> None:
        """GIVEN a folder containing .git dir, THEN has-git signal."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        result = detect_project_signature(str(tmp_path))
        assert result is not None
        assert "has-git" in result.signals

    def test_file_signal_has_package_json(self, tmp_path: Path) -> None:
        """GIVEN a folder containing package.json, THEN has-package-json signal."""
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")

        result = detect_project_signature(str(tmp_path))
        assert result is not None
        assert "has-package-json" in result.signals

    def test_file_signal_has_composer_json(self, tmp_path: Path) -> None:
        """GIVEN a folder containing composer.json, THEN has-composer-json signal."""
        (tmp_path / "composer.json").write_text("{}", encoding="utf-8")

        result = detect_project_signature(str(tmp_path))
        assert result is not None
        assert "has-composer-json" in result.signals

    @pytest.mark.parametrize("filename,expected_signal", [
        ("pyproject.toml", "has-pyproject-toml"),
        ("Cargo.toml", "has-cargo-toml"),
        ("go.mod", "has-go-mod"),
        ("pom.xml", "has-pom-xml"),
        ("MyProject.sln", "has-solution-file"),
        ("MyProject.csproj", "has-csproj"),
        ("wp-config.php", "has-wp-config"),
        ("Gemfile", "has-gemfile"),
    ])
    def test_file_signal_other_markers(
        self,
        tmp_path: Path,
        filename: str,
        expected_signal: str,
    ) -> None:
        """GIVEN a folder containing a known marker file, THEN the correct signal."""
        (tmp_path / filename).write_text("", encoding="utf-8")

        result = detect_project_signature(str(tmp_path))
        assert result is not None, f"Expected signal for {filename!r}"
        assert expected_signal in result.signals, (
            f"Expected {expected_signal!r} for {filename!r}, got {result.signals}"
        )


class TestSignalStacking:
    """Multiple signals stack into one ProjectSignature."""

    def test_multiple_signals_combined(self, tmp_path: Path) -> None:
        """GIVEN Mis_proyectos path + .git dir + package.json, THEN 3 signals."""
        # Build Mis_proyectos path
        mis_path = tmp_path / "Mis_proyectos" / "myapp"
        mis_path.mkdir(parents=True)
        (mis_path / ".git").mkdir()
        (mis_path / "package.json").write_text("{}")

        result = detect_project_signature(str(mis_path))
        assert result is not None
        assert "inside-mis-proyectos" in result.signals
        assert "has-git" in result.signals
        assert "has-package-json" in result.signals


class TestNoSignal:
    """Plain folder with no signals returns None."""

    def test_no_signals_returns_none(self, tmp_path: Path) -> None:
        """GIVEN a folder with no recognised markers, THEN result is None."""
        (tmp_path / "readme.txt").write_text("hello")

        result = detect_project_signature(str(tmp_path))
        assert result is None

    def test_empty_folder_returns_none(self, tmp_path: Path) -> None:
        """GIVEN an empty folder, THEN result is None."""
        result = detect_project_signature(str(tmp_path))
        assert result is None

    def test_nonexistent_path_returns_none(self) -> None:
        """GIVEN a path that does not exist, THEN result is None."""
        result = detect_project_signature(r"C:\does\not\exist\ever")
        assert result is None


class TestErrorHandling:
    """Safe error handling — never raises."""

    def test_permission_error_returns_none(self, tmp_path: Path) -> None:
        """GIVEN os.listdir raises PermissionError, THEN result is None."""
        with patch("os.listdir", side_effect=PermissionError("denied")):
            result = detect_project_signature(str(tmp_path))
        assert result is None

    def test_symlink_path_returns_none(self, tmp_path: Path) -> None:
        """GIVEN path is a symlink, THEN result is None (not followed)."""
        with patch("os.path.islink", return_value=True):
            result = detect_project_signature(str(tmp_path))
        assert result is None


class TestLastModifiedDays:
    """last_modified_days calculation."""

    def test_last_modified_days(self, tmp_path: Path) -> None:
        """GIVEN folder with signal and child mtime 3 days ago, THEN last_modified_days == 3."""
        # Create a .git dir so signal is detected
        (tmp_path / ".git").mkdir()
        child = tmp_path / "some_file.txt"
        child.write_text("content")

        # Patch getmtime to return 3 days ago for all children
        three_days_ago = time.time() - 3 * 86400

        original_getmtime = os.path.getmtime

        def fake_getmtime(path: str) -> float:
            return three_days_ago

        with patch("os.path.getmtime", side_effect=fake_getmtime):
            result = detect_project_signature(str(tmp_path))

        assert result is not None
        assert result.last_modified_days == 3

    def test_last_modified_days_none_on_empty_signals_folder(self, tmp_path: Path) -> None:
        """With signal but empty folder, last_modified_days may be None."""
        # Make a project path so signal fires from path (not file listing)
        mis_path = tmp_path / "Mis_proyectos" / "emptyapp"
        mis_path.mkdir(parents=True)

        result = detect_project_signature(str(mis_path))
        assert result is not None
        # last_modified_days may be None (empty folder) or an integer
        assert result.last_modified_days is None or isinstance(
            result.last_modified_days, int
        )


class TestProjectSignatureShape:
    """Returned ProjectSignature has correct shape."""

    def test_path_field_matches_input(self, tmp_path: Path) -> None:
        """THEN result.path equals the input path."""
        (tmp_path / ".git").mkdir()
        result = detect_project_signature(str(tmp_path))
        assert result is not None
        assert result.path == str(tmp_path)

    def test_signals_is_tuple(self, tmp_path: Path) -> None:
        """THEN result.signals is a tuple."""
        (tmp_path / ".git").mkdir()
        result = detect_project_signature(str(tmp_path))
        assert result is not None
        assert isinstance(result.signals, tuple)
