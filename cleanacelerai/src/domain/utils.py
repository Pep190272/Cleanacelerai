"""Shared utilities for the domain layer."""
from __future__ import annotations


def normalizar_ruta(ruta: str) -> set[str]:
    """Split a path into lowercase parts for set-based matching.

    Args:
        ruta: Filesystem path (Windows or POSIX).

    Returns:
        Set of lowercase path components.
    """
    return set(ruta.replace("\\", "/").lower().split("/"))
