"""Tests for the duplicate finder service."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.duplicate_finder import _hash_file, find_duplicates


class TestHashFile:
    def test_hash_identical_content(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        content = b"hello world" * 100
        f1.write_bytes(content)
        f2.write_bytes(content)
        assert _hash_file(str(f1)) == _hash_file(str(f2))

    def test_hash_different_content(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"content A" * 100)
        f2.write_bytes(b"content B" * 100)
        assert _hash_file(str(f1)) != _hash_file(str(f2))

    def test_hash_nonexistent_file_returns_none(self) -> None:
        assert _hash_file(r"Z:\does\not\exist.bin") is None

    def test_hash_returns_string(self, tmp_path: Path) -> None:
        f = tmp_path / "test.bin"
        f.write_bytes(b"data" * 200)
        result = _hash_file(str(f))
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex digest length


class TestFindDuplicates:
    def test_finds_duplicate_pair(self, tmp_path: Path) -> None:
        content = b"duplicate content" * 100  # > 1KB
        (tmp_path / "file1.bin").write_bytes(content)
        (tmp_path / "file2.bin").write_bytes(content)
        (tmp_path / "unique.bin").write_bytes(b"different" * 200)

        with patch("src.services.duplicate_finder.CARPETAS_SISTEMA", set()):
            groups = find_duplicates([str(tmp_path)])

        assert len(groups) == 1
        assert len(groups[0].files) == 2

    def test_no_duplicates_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "a.bin").write_bytes(b"content A" * 200)
        (tmp_path / "b.bin").write_bytes(b"content B" * 200)

        groups = find_duplicates([str(tmp_path)])
        assert groups == []

    def test_skips_small_files(self, tmp_path: Path) -> None:
        # Files < 1KB should be ignored
        (tmp_path / "small1.txt").write_bytes(b"tiny")
        (tmp_path / "small2.txt").write_bytes(b"tiny")

        groups = find_duplicates([str(tmp_path)])
        assert groups == []

    def test_cancellation(self, tmp_path: Path) -> None:
        content = b"data" * 1000
        (tmp_path / "f1.bin").write_bytes(content)
        (tmp_path / "f2.bin").write_bytes(content)

        groups = find_duplicates(
            [str(tmp_path)],
            should_continue=lambda: False,
        )
        assert groups == []

    def test_three_copies_in_one_group(self, tmp_path: Path) -> None:
        content = b"triplicate" * 500
        (tmp_path / "copy1.bin").write_bytes(content)
        (tmp_path / "copy2.bin").write_bytes(content)
        (tmp_path / "copy3.bin").write_bytes(content)

        with patch("src.services.duplicate_finder.CARPETAS_SISTEMA", set()):
            groups = find_duplicates([str(tmp_path)])
        assert len(groups) == 1
        assert len(groups[0].files) == 3

    def test_protected_keyword_skips_folder(self, tmp_path: Path) -> None:
        protected = tmp_path / ".vscode"
        protected.mkdir()
        content = b"same content" * 300

        (tmp_path / "file.bin").write_bytes(content)
        (protected / "settings.bin").write_bytes(content)

        groups = find_duplicates(
            [str(tmp_path)],
            protected_keywords=[".vscode"],
        )
        # Only one file remains after protection → no duplicate group
        assert groups == []

    def test_progress_callback_called(self, tmp_path: Path) -> None:
        content = b"progress test" * 300
        (tmp_path / "a.bin").write_bytes(content)
        (tmp_path / "b.bin").write_bytes(content)

        messages: list[str] = []
        find_duplicates([str(tmp_path)], on_progress=messages.append)
        assert len(messages) > 0


class TestBlocklistedPathsSkipped:
    """Patch 4: paths matching PATHS_BLOQUEADOS_SCAN are skipped during walk."""

    def test_node_modules_subfolder_is_skipped(self, tmp_path: Path) -> None:
        """Files inside node_modules must not appear in duplicate results."""
        import os as _os
        node_mod = tmp_path / "node_modules" / "react"
        node_mod.mkdir(parents=True)
        content = b"duplicate content" * 100

        (tmp_path / "file.bin").write_bytes(content)
        (node_mod / "file.bin").write_bytes(content)

        # Use os.sep to match normalised paths on any OS
        blocked = (_os.sep + "node_modules" + _os.sep,)
        with patch("src.services.duplicate_finder.PATHS_BLOQUEADOS_SCAN", blocked):
            with patch("src.services.duplicate_finder.CARPETAS_SISTEMA", set()):
                groups = find_duplicates([str(tmp_path)])

        # node_modules copy was skipped → only 1 file remains → no group
        assert groups == []

    def test_venv_subfolder_is_skipped(self, tmp_path: Path) -> None:
        import os as _os
        venv_dir = tmp_path / "venv" / "Lib"
        venv_dir.mkdir(parents=True)
        content = b"venv content data" * 100

        (tmp_path / "original.bin").write_bytes(content)
        (venv_dir / "copy.bin").write_bytes(content)

        blocked = (_os.sep + "venv" + _os.sep,)
        with patch("src.services.duplicate_finder.PATHS_BLOQUEADOS_SCAN", blocked):
            with patch("src.services.duplicate_finder.CARPETAS_SISTEMA", set()):
                groups = find_duplicates([str(tmp_path)])

        assert groups == []

    def test_unblocked_subfolder_still_scanned(self, tmp_path: Path) -> None:
        """Non-blocked subfolders must still be included in the scan."""
        subdir = tmp_path / "photos"
        subdir.mkdir()
        content = b"photo data duplicated" * 100

        (tmp_path / "photo.bin").write_bytes(content)
        (subdir / "photo_copy.bin").write_bytes(content)

        blocked = (r"\node_modules\\",)  # Doesn't match 'photos'
        with patch("src.services.duplicate_finder.PATHS_BLOQUEADOS_SCAN", blocked):
            with patch("src.services.duplicate_finder.CARPETAS_SISTEMA", set()):
                groups = find_duplicates([str(tmp_path)])

        assert len(groups) == 1
