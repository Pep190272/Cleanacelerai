"""Config persistence service for Cleanacelerai PRO."""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".cleanacelerai"
CONFIG_FILE = CONFIG_DIR / "config.json"


class ConfigService:
    """Handles loading and saving user configuration to ~/.cleanacelerai/config.json."""

    def load(self, defaults: dict) -> dict:
        """Load config from disk. Falls back to defaults if missing or corrupt.

        Args:
            defaults: Default values to use if config file doesn't exist or is corrupt.

        Returns:
            Config dict merged with defaults for any missing keys.
        """
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            # Merge: ensure any key added in a later version is present
            return {**defaults, **data}
        except FileNotFoundError:
            return dict(defaults)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load config from %s: %s", CONFIG_FILE, exc)
            return dict(defaults)

    def save(self, config: dict) -> None:
        """Save config to disk.

        Args:
            config: Config dict to persist.
        """
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(
                json.dumps(config, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error("Could not save config to %s: %s", CONFIG_FILE, exc)
