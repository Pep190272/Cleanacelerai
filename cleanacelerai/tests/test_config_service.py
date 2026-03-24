"""Tests for ConfigService — config persistence."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.infrastructure.config_service import ConfigService


class TestConfigServiceLoad:
    def test_returns_defaults_when_file_missing(self, tmp_path: Path) -> None:
        service = ConfigService()
        defaults = {"keywords": [".git", ".ssh"], "folders": []}
        config_file = tmp_path / "nonexistent.json"

        with patch("src.infrastructure.config_service.CONFIG_FILE", config_file):
            result = service.load(defaults)

        assert result == defaults

    def test_returns_saved_values_when_file_exists(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.json"
        saved = {"keywords": [".vscode", ".docker"], "folders": [r"C:\projects"]}
        config_file.write_text(json.dumps(saved), encoding="utf-8")

        service = ConfigService()
        with patch("src.infrastructure.config_service.CONFIG_FILE", config_file):
            result = service.load({"keywords": [], "folders": []})

        assert result["keywords"] == [".vscode", ".docker"]
        assert result["folders"] == [r"C:\projects"]

    def test_returns_defaults_when_file_is_corrupt(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.json"
        config_file.write_text("{ this is not valid json !!!", encoding="utf-8")

        service = ConfigService()
        defaults = {"keywords": [".git"], "folders": []}
        with patch("src.infrastructure.config_service.CONFIG_FILE", config_file):
            result = service.load(defaults)

        assert result == defaults

    def test_merges_missing_keys_from_defaults(self, tmp_path: Path) -> None:
        """Keys present in defaults but absent in stored file are merged in."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"keywords": [".git"]}), encoding="utf-8")

        service = ConfigService()
        defaults = {"keywords": [], "folders": [], "new_key": "default_value"}
        with patch("src.infrastructure.config_service.CONFIG_FILE", config_file):
            result = service.load(defaults)

        assert result["new_key"] == "default_value"
        assert result["keywords"] == [".git"]

    def test_does_not_mutate_defaults_dict(self, tmp_path: Path) -> None:
        service = ConfigService()
        defaults = {"keywords": [".git"], "folders": []}
        original_defaults = dict(defaults)
        config_file = tmp_path / "nonexistent.json"

        with patch("src.infrastructure.config_service.CONFIG_FILE", config_file):
            service.load(defaults)

        assert defaults == original_defaults


class TestConfigServiceSave:
    def test_creates_directory_if_not_exists(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "subdir" / ".cleanacelerai"
        config_file = config_dir / "config.json"
        assert not config_dir.exists()

        service = ConfigService()
        with (
            patch("src.infrastructure.config_service.CONFIG_DIR", config_dir),
            patch("src.infrastructure.config_service.CONFIG_FILE", config_file),
        ):
            service.save({"keywords": [".git"], "folders": []})

        assert config_dir.exists()
        assert config_file.exists()

    def test_persists_values_readable_by_load(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".cleanacelerai"
        config_file = config_dir / "config.json"
        payload = {"keywords": [".ssh", ".docker"], "folders": [r"D:\projects"]}

        service = ConfigService()
        with (
            patch("src.infrastructure.config_service.CONFIG_DIR", config_dir),
            patch("src.infrastructure.config_service.CONFIG_FILE", config_file),
        ):
            service.save(payload)
            result = service.load({"keywords": [], "folders": []})

        assert result["keywords"] == [".ssh", ".docker"]
        assert result["folders"] == [r"D:\projects"]

    def test_saved_file_is_valid_json(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".cleanacelerai"
        config_file = config_dir / "config.json"

        service = ConfigService()
        with (
            patch("src.infrastructure.config_service.CONFIG_DIR", config_dir),
            patch("src.infrastructure.config_service.CONFIG_FILE", config_file),
        ):
            service.save({"keywords": [".git"], "folders": []})

        raw = config_file.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert parsed["keywords"] == [".git"]

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        config_dir = tmp_path / ".cleanacelerai"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"keywords": ["old"]}), encoding="utf-8")

        service = ConfigService()
        with (
            patch("src.infrastructure.config_service.CONFIG_DIR", config_dir),
            patch("src.infrastructure.config_service.CONFIG_FILE", config_file),
        ):
            service.save({"keywords": ["new"], "folders": []})
            result = service.load({})

        assert result["keywords"] == ["new"]
