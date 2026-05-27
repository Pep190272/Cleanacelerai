"""Service: detect whether a folder looks like a live project."""
from __future__ import annotations

import os
import time

from ..domain.constants import (
    PROJECT_SIGNAL_HAS_CARGO_TOML,
    PROJECT_SIGNAL_HAS_COMPOSER_JSON,
    PROJECT_SIGNAL_HAS_CSPROJ,
    PROJECT_SIGNAL_HAS_GEMFILE,
    PROJECT_SIGNAL_HAS_GIT,
    PROJECT_SIGNAL_HAS_GO_MOD,
    PROJECT_SIGNAL_HAS_PACKAGE_JSON,
    PROJECT_SIGNAL_HAS_POM_XML,
    PROJECT_SIGNAL_HAS_PYPROJECT_TOML,
    PROJECT_SIGNAL_HAS_SOLUTION_FILE,
    PROJECT_SIGNAL_HAS_WP_CONFIG,
    PROJECT_SIGNAL_INSIDE_LOCAL_SITES,
    PROJECT_SIGNAL_INSIDE_MIS_PROYECTOS,
)
from ..domain.models import ProjectSignature


# Inlined path markers — kept independent of the Duplicados IA blocklist
# split so this service can ship without dependencies on that module's
# constant layout.
_PROJECT_PATH_MARKERS: tuple[str, ...] = (
    "\\Local Sites\\",
    "\\Mis_proyectos\\",
)


# Exact-name matches (lowercased). dir/file flag tells the detector
# how to verify the entry.
# Tuple format: (signal_constant, expected_name_lower, is_dir)
_NAME_SIGNALS: tuple[tuple[str, str, bool], ...] = (
    (PROJECT_SIGNAL_HAS_GIT,            ".git",            True),
    (PROJECT_SIGNAL_HAS_PACKAGE_JSON,   "package.json",    False),
    (PROJECT_SIGNAL_HAS_COMPOSER_JSON,  "composer.json",   False),
    (PROJECT_SIGNAL_HAS_PYPROJECT_TOML, "pyproject.toml",  False),
    (PROJECT_SIGNAL_HAS_CARGO_TOML,     "cargo.toml",      False),
    (PROJECT_SIGNAL_HAS_GO_MOD,         "go.mod",          False),
    (PROJECT_SIGNAL_HAS_POM_XML,        "pom.xml",         False),
    (PROJECT_SIGNAL_HAS_WP_CONFIG,      "wp-config.php",   False),
    (PROJECT_SIGNAL_HAS_GEMFILE,        "gemfile",         False),
)


def detect_project_signature(path: str) -> ProjectSignature | None:
    """Return a ProjectSignature if the folder looks like a project, else None.

    Pure-ish: only reads metadata of `path` itself + direct children (no recursive walk).
    Never raises; on any unexpected error returns None so the caller treats the folder
    as "not a project" (and the deletion still goes through safe_delete_dir).

    Symlinks are NOT followed: if `path` is a symlink we return None.
    """
    if not path or not os.path.isdir(path):
        return None
    if os.path.islink(path):
        return None

    signals: list[str] = []

    # Path-based signals: uses normpath().lower() + os.sep trick consistent
    # with DuplicatesPresenter.is_path_blocked.
    path_norm = os.path.normpath(path).lower() + os.sep
    for marker in _PROJECT_PATH_MARKERS:
        marker_l = marker.lower()
        if marker_l in path_norm:
            if "mis_proyectos" in marker_l:
                signals.append(PROJECT_SIGNAL_INSIDE_MIS_PROYECTOS)
            elif "local sites" in marker_l:
                signals.append(PROJECT_SIGNAL_INSIDE_LOCAL_SITES)

    # Direct-children scan (single os.listdir, no recursion)
    try:
        children = os.listdir(path)
    except (PermissionError, OSError):
        # If we cannot list, we cannot detect file-based signals.
        # If path-based signals already found something, still return them.
        if signals:
            return ProjectSignature(
                path=path,
                signals=tuple(signals),
                last_modified_days=None,
            )
        return None

    children_lower = {c.lower(): c for c in children}

    for signal, name_lower, is_dir in _NAME_SIGNALS:
        original = children_lower.get(name_lower)
        if original is None:
            continue
        full = os.path.join(path, original)
        try:
            if is_dir and os.path.isdir(full):
                signals.append(signal)
            elif (not is_dir) and os.path.isfile(full):
                signals.append(signal)
        except OSError:
            pass

    # Glob-style signals using the same listing (no second os.listdir)
    for name in children:
        if name.lower().endswith(".sln"):
            signals.append(PROJECT_SIGNAL_HAS_SOLUTION_FILE)
            break
    for name in children:
        if name.lower().endswith(".csproj"):
            signals.append(PROJECT_SIGNAL_HAS_CSPROJ)
            break

    if not signals:
        return None

    last_modified_days = _max_child_age_days(path, children)

    return ProjectSignature(
        path=path,
        signals=tuple(signals),
        last_modified_days=last_modified_days,
    )


def _max_child_age_days(path: str, children: list[str]) -> int | None:
    """Return the age (in days) of the most-recently-modified top-level child.

    Returns None if the folder is empty or all children are unreadable.
    """
    now = time.time()
    most_recent: float | None = None
    for name in children:
        full = os.path.join(path, name)
        try:
            mtime = os.path.getmtime(full)
        except OSError:
            continue
        if most_recent is None or mtime > most_recent:
            most_recent = mtime
    if most_recent is None:
        return None
    delta_seconds = max(0.0, now - most_recent)
    return int(delta_seconds // 86400)
