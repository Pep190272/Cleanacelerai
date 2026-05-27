"""Tests for infrastructure/file_system.py — send2trash + deletion log."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from src.infrastructure.file_system import _log_deletion, safe_delete, safe_delete_dir


class TestLogDeletion:
    """Tests for the _log_deletion helper."""

    def test_creates_log_directory(self, tmp_path: Path) -> None:
        log_dir = tmp_path / ".cleanacelerai_test"
        target = tmp_path / "file.txt"
        target.write_bytes(b"hello world")

        with patch("src.infrastructure.file_system.Path.home", return_value=tmp_path):
            with patch("src.infrastructure.file_system.Path") as mock_path_class:
                # Use real Path for everything except home()
                real_path = Path
                mock_path_class.side_effect = real_path
                mock_path_class.home.return_value = tmp_path
                _log_deletion(str(target))

        # Simplified: just call with real home patched
        log_dir2 = tmp_path / ".cleanacelerai"
        log_dir2.mkdir(exist_ok=True)
        log_path = log_dir2 / "deleted.log"
        target2 = tmp_path / "file2.txt"
        target2.write_bytes(b"some content " * 10)

        import src.infrastructure.file_system as fs_module
        original_home = Path.home

        class FakePath(type(tmp_path)):
            @classmethod
            def home(cls):  # type: ignore[override]
                return tmp_path

        with patch.object(Path, "home", staticmethod(lambda: tmp_path)):
            _log_deletion(str(target2))

        assert log_path.exists()

    def test_writes_valid_json_line(self, tmp_path: Path) -> None:
        target = tmp_path / "deleteme.txt"
        target.write_bytes(b"data " * 200)

        with patch.object(Path, "home", staticmethod(lambda: tmp_path)):
            _log_deletion(str(target))

        log_path = tmp_path / ".cleanacelerai" / "deleted.log"
        assert log_path.exists()
        line = log_path.read_text(encoding="utf-8").strip()
        entry = json.loads(line)

        assert "ts" in entry
        assert "path" in entry
        assert "size" in entry
        assert "sha256_first_64k" in entry
        assert entry["path"] == str(target)
        assert entry["size"] == target.stat().st_size

    def test_appends_multiple_entries(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"content_a " * 100)
        f2.write_bytes(b"content_b " * 100)

        with patch.object(Path, "home", staticmethod(lambda: tmp_path)):
            _log_deletion(str(f1))
            _log_deletion(str(f2))

        log_path = tmp_path / ".cleanacelerai" / "deleted.log"
        lines = [l for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 2
        paths = [json.loads(l)["path"] for l in lines]
        assert str(f1) in paths
        assert str(f2) in paths

    def test_handles_missing_file_gracefully(self, tmp_path: Path) -> None:
        nonexistent = str(tmp_path / "ghost.txt")
        with patch.object(Path, "home", staticmethod(lambda: tmp_path)):
            # Should not raise
            _log_deletion(nonexistent)

        log_path = tmp_path / ".cleanacelerai" / "deleted.log"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert entry["size"] == -1
        assert entry["sha256_first_64k"] == "unreadable"

    def test_sha256_prefix_length(self, tmp_path: Path) -> None:
        target = tmp_path / "hashme.bin"
        target.write_bytes(b"x" * 1000)

        with patch.object(Path, "home", staticmethod(lambda: tmp_path)):
            _log_deletion(str(target))

        log_path = tmp_path / ".cleanacelerai" / "deleted.log"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert len(entry["sha256_first_64k"]) == 16


class TestSafeDelete:
    """Tests that safe_delete uses send2trash and logs before trashing."""

    def test_calls_send2trash_not_os_remove(self, tmp_path: Path) -> None:
        target = tmp_path / "victim.txt"
        target.write_bytes(b"bye " * 200)

        with (
            patch("src.infrastructure.file_system.send2trash") as mock_trash,
            patch.object(Path, "home", staticmethod(lambda: tmp_path)),
        ):
            ok, err = safe_delete(str(target))

        assert ok is True
        assert err == ""
        mock_trash.assert_called_once_with(str(target))

    def test_logs_before_trashing(self, tmp_path: Path) -> None:
        target = tmp_path / "logged.txt"
        target.write_bytes(b"log me " * 200)

        call_order: list[str] = []

        def fake_log(path: str) -> None:
            call_order.append("log")

        def fake_trash(path: str) -> None:
            call_order.append("trash")

        with (
            patch("src.infrastructure.file_system._log_deletion", side_effect=fake_log),
            patch("src.infrastructure.file_system.send2trash", side_effect=fake_trash),
        ):
            safe_delete(str(target))

        assert call_order == ["log", "trash"], "Log must happen BEFORE trash"

    def test_returns_false_on_permission_error(self, tmp_path: Path) -> None:
        target = tmp_path / "locked.txt"
        target.write_bytes(b"x" * 200)

        with (
            patch("src.infrastructure.file_system.send2trash", side_effect=PermissionError("locked")),
            patch("src.infrastructure.file_system._log_deletion"),
        ):
            ok, err = safe_delete(str(target))

        assert ok is False
        assert "Permiso" in err

    def test_nonexistent_file_returns_success(self, tmp_path: Path) -> None:
        ghost = str(tmp_path / "gone.txt")
        with (
            patch("src.infrastructure.file_system.send2trash", side_effect=FileNotFoundError()),
            patch("src.infrastructure.file_system._log_deletion"),
        ):
            ok, err = safe_delete(ghost)

        assert ok is True
        assert err == ""


class TestLogDeletionExtended:
    """Tests for the extended _log_deletion signature (source + fallback_rename)."""

    def test_log_deletion_with_source(self, tmp_path: Path) -> None:
        """GIVEN source is provided, THEN log line contains 'source' key."""
        target = tmp_path / "deleteme.txt"
        target.write_bytes(b"data " * 200)

        with patch.object(Path, "home", staticmethod(lambda: tmp_path)):
            _log_deletion(str(target), source="asesor.orden-general")

        log_path = tmp_path / ".cleanacelerai" / "deleted.log"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert "source" in entry
        assert entry["source"] == "asesor.orden-general"

    def test_log_deletion_without_source(self, tmp_path: Path) -> None:
        """GIVEN no source (existing callers), THEN log line has NO 'source' key."""
        target = tmp_path / "deleteme.txt"
        target.write_bytes(b"data " * 200)

        with patch.object(Path, "home", staticmethod(lambda: tmp_path)):
            _log_deletion(str(target))  # no source kwarg

        log_path = tmp_path / ".cleanacelerai" / "deleted.log"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert "source" not in entry  # backward-compatible shape

    def test_log_deletion_with_fallback_rename(self, tmp_path: Path) -> None:
        """GIVEN fallback_rename=True, THEN log line includes fallback_rename: true."""
        target = tmp_path / "deleteme.txt"
        target.write_bytes(b"data " * 200)

        with patch.object(Path, "home", staticmethod(lambda: tmp_path)):
            _log_deletion(str(target), source="asesor", fallback_rename=True)

        log_path = tmp_path / ".cleanacelerai" / "deleted.log"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert entry.get("fallback_rename") is True


class TestSafeDeleteDir:
    """Tests for safe_delete_dir — directory-safe deletion via send2trash."""

    def test_safe_delete_dir_success(self, tmp_path: Path) -> None:
        """GIVEN valid dir and send2trash succeeds, THEN returns (True, '') and logs."""
        target = tmp_path / "mydir"
        target.mkdir()

        with (
            patch("src.infrastructure.file_system.send2trash") as mock_trash,
            patch("src.infrastructure.file_system._log_deletion") as mock_log,
        ):
            ok, err = safe_delete_dir(str(target))

        assert ok is True
        assert err == ""
        mock_trash.assert_called_once()
        mock_log.assert_called()

    def test_safe_delete_dir_logs_before_trashing(self, tmp_path: Path) -> None:
        """Log call MUST happen BEFORE send2trash call."""
        target = tmp_path / "mydir"
        target.mkdir()

        call_order: list[str] = []

        def fake_log(path: str, source: str | None = None, fallback_rename: bool = False) -> None:
            call_order.append("log")

        def fake_trash(path: str) -> None:
            call_order.append("trash")

        with (
            patch("src.infrastructure.file_system._log_deletion", side_effect=fake_log),
            patch("src.infrastructure.file_system.send2trash", side_effect=fake_trash),
        ):
            safe_delete_dir(str(target))

        assert call_order[0] == "log", "Log must happen BEFORE trash"
        assert "trash" in call_order

    def test_safe_delete_dir_fallback_rename(self, tmp_path: Path) -> None:
        """GIVEN TrashPermissionError, THEN fallback rename happens and returns FALLBACK_RENAME prefix."""
        from send2trash import TrashPermissionError

        target = tmp_path / "mydir"
        target.mkdir()

        with (
            patch("src.infrastructure.file_system.send2trash", side_effect=TrashPermissionError("no recycle")),
            patch("src.infrastructure.file_system._log_deletion") as mock_log,
            patch("os.rename") as mock_rename,
        ):
            ok, err = safe_delete_dir(str(target), source="asesor.orden-general")

        assert ok is True
        assert err.startswith("FALLBACK_RENAME:")
        # _log_deletion should be called twice: once before send2trash, once for fallback
        assert mock_log.call_count == 2
        # Second call should have fallback_rename=True
        _, kwargs = mock_log.call_args_list[1]
        assert kwargs.get("fallback_rename") is True or mock_log.call_args_list[1][1].get("fallback_rename") is True

    def test_safe_delete_dir_hard_failure(self, tmp_path: Path) -> None:
        """GIVEN OSError (not TrashPermissionError), THEN returns (False, error_msg)."""
        target = tmp_path / "mydir"
        target.mkdir()

        with (
            patch("src.infrastructure.file_system.send2trash", side_effect=OSError("disk error")),
            patch("src.infrastructure.file_system._log_deletion"),
        ):
            ok, err = safe_delete_dir(str(target))

        assert ok is False
        assert "disk error" in err

    def test_safe_delete_dir_not_a_directory(self, tmp_path: Path) -> None:
        """GIVEN a file path (not a dir), THEN returns (False, ...) immediately."""
        target = tmp_path / "file.txt"
        target.write_bytes(b"hi")

        ok, err = safe_delete_dir(str(target))
        assert ok is False

    def test_safe_delete_dir_already_gone(self, tmp_path: Path) -> None:
        """GIVEN FileNotFoundError from send2trash, THEN returns (True, '') — already gone."""
        target = tmp_path / "mydir"
        target.mkdir()

        with (
            patch("src.infrastructure.file_system.send2trash", side_effect=FileNotFoundError()),
            patch("src.infrastructure.file_system._log_deletion"),
        ):
            ok, err = safe_delete_dir(str(target))

        assert ok is True
        assert err == ""

    def test_safe_delete_dir_source_passed_to_log(self, tmp_path: Path) -> None:
        """GIVEN source kwarg, THEN _log_deletion is called with that source."""
        target = tmp_path / "mydir"
        target.mkdir()

        with (
            patch("src.infrastructure.file_system.send2trash"),
            patch("src.infrastructure.file_system._log_deletion") as mock_log,
        ):
            safe_delete_dir(str(target), source="asesor.limpieza-profunda")

        first_call_kwargs = mock_log.call_args_list[0]
        # Check that source="asesor.limpieza-profunda" was passed
        args, kwargs = first_call_kwargs
        assert kwargs.get("source") == "asesor.limpieza-profunda" or (
            len(args) > 1 and args[1] == "asesor.limpieza-profunda"
        )
