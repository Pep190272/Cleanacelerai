"""Model cache manager for Cleanacelerai PRO."""
from __future__ import annotations

from pathlib import Path

from cleanacelerai.src.domain.constants import MODEL_CACHE_DIR


class ModelManager:
    """Manages model cache on D: drive for AI-powered features."""

    def __init__(self) -> None:
        self._cache_dir = MODEL_CACHE_DIR

    def ensure_cache_dir(self, subdirectory: str = "") -> Path:
        """Create and return cache directory path.

        Args:
            subdirectory: Optional subdirectory within the cache root.

        Returns:
            Path to the (now existing) cache directory.
        """
        target = self._cache_dir / subdirectory if subdirectory else self._cache_dir
        target.mkdir(parents=True, exist_ok=True)
        return target

    def get_model_path(self, model_name: str, subdirectory: str = "") -> Path | None:
        """Return model path if it exists in cache, None otherwise.

        Args:
            model_name: Name of the model file or directory.
            subdirectory: Optional subdirectory within the cache root.

        Returns:
            Path if model exists, None otherwise.
        """
        path = self._cache_dir / subdirectory / model_name
        return path if path.exists() else None

    def clear_cache(self) -> None:
        """Remove all cached models."""
        import shutil

        if self._cache_dir.exists():
            shutil.rmtree(self._cache_dir)
