"""Tests for domain models."""
import pytest

from src.domain.models import CleanupResult, DuplicateGroup, FileInfo, RiskLevel


class TestFileInfo:
    def test_size_mb(self) -> None:
        fi = FileInfo(path=r"C:\foo\bar.txt", size=2 * 1024 * 1024, mtime=0.0)
        assert fi.size_mb == pytest.approx(2.0)

    def test_name(self) -> None:
        fi = FileInfo(path=r"C:\foo\bar.txt", size=100, mtime=0.0)
        assert fi.name == "bar.txt"

    def test_extension(self) -> None:
        fi = FileInfo(path=r"C:\foo\bar.TXT", size=100, mtime=0.0)
        assert fi.extension == ".txt"

    def test_hash_default_none(self) -> None:
        fi = FileInfo(path=r"C:\foo\file.dat", size=0, mtime=0.0)
        assert fi.hash is None

    def test_hash_set(self) -> None:
        fi = FileInfo(path=r"C:\foo\file.dat", size=0, mtime=0.0, hash="abc123")
        assert fi.hash == "abc123"


class TestDuplicateGroup:
    def _make_group(self, sizes: list[int]) -> DuplicateGroup:
        files = [
            FileInfo(path=f"C:\\folder\\file{i}.bin", size=s, mtime=float(i))
            for i, s in enumerate(sizes)
        ]
        return DuplicateGroup(hash="deadbeef", files=files)

    def test_size_mb_from_first_file(self) -> None:
        group = self._make_group([1024 * 1024, 1024 * 1024])
        assert group.size_mb == pytest.approx(1.0)

    def test_recoverable_mb_two_copies(self) -> None:
        group = self._make_group([1024 * 1024, 1024 * 1024])
        assert group.recoverable_mb == pytest.approx(1.0)

    def test_recoverable_mb_three_copies(self) -> None:
        group = self._make_group([1024 * 1024] * 3)
        assert group.recoverable_mb == pytest.approx(2.0)

    def test_empty_group(self) -> None:
        group = DuplicateGroup(hash="abc", files=[])
        assert group.size_mb == 0.0
        assert group.recoverable_mb == 0.0


class TestCleanupResult:
    def test_freed_gb(self) -> None:
        result = CleanupResult(deleted=5, freed_mb=2048.0)
        assert result.freed_gb == pytest.approx(2.0)

    def test_add_error(self) -> None:
        result = CleanupResult()
        result.add_error(r"C:\foo.txt", "Permission denied")
        assert len(result.errors) == 1
        assert "foo.txt" in result.errors[0]

    def test_initial_state(self) -> None:
        result = CleanupResult()
        assert result.deleted == 0
        assert result.freed_mb == 0.0
        assert result.errors == []


class TestRiskLevel:
    def test_all_values_exist(self) -> None:
        values = {r.value for r in RiskLevel}
        assert "SAFE" in values
        assert "CRITICAL" in values
        assert "SYSTEM" in values
        assert "DOTFILE" in values
        assert "PERSONAL" in values
        assert "PROJECT" in values
        assert "PROTECTED" in values
