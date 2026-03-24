"""Service: batch file renaming with date-based sequential naming."""
from __future__ import annotations

import datetime
import os
from dataclasses import dataclass


@dataclass
class RenameEntry:
    """Preview entry for a rename operation."""
    original_path: str
    new_path: str
    original_name: str
    new_name: str


def build_rename_plan(
    folder: str,
    base_name: str,
) -> list[RenameEntry]:
    """
    Build a rename plan for all files in a folder.

    Files are sorted by modification date and renamed as:
        {base_name}_{YYYYMMDD}_{NNN}{ext}

    Args:
        folder: Absolute path to the target folder.
        base_name: The prefix to use for new names (e.g. "Vacaciones").

    Returns:
        Ordered list of RenameEntry pairs (original → new).

    Raises:
        OSError: If the folder cannot be read.
    """
    archivos = [
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
    ]

    # Sort by modification time
    archivos.sort(key=lambda x: os.path.getmtime(os.path.join(folder, x)))

    plan: list[RenameEntry] = []
    for idx, filename in enumerate(archivos, 1):
        ext = os.path.splitext(filename)[1]
        try:
            mtime = os.path.getmtime(os.path.join(folder, filename))
            fecha = datetime.datetime.fromtimestamp(mtime).strftime("%Y%m%d")
        except OSError:
            fecha = "00000000"

        new_name = f"{base_name}_{fecha}_{idx:03d}{ext}"
        plan.append(
            RenameEntry(
                original_path=os.path.join(folder, filename),
                new_path=os.path.join(folder, new_name),
                original_name=filename,
                new_name=new_name,
            )
        )

    return plan


def apply_rename_plan(plan: list[RenameEntry]) -> tuple[int, list[str]]:
    """
    Execute a rename plan built by build_rename_plan.

    Args:
        plan: List of RenameEntry objects.

    Returns:
        Tuple of (success_count, list_of_error_messages).
    """
    exitos = 0
    errores: list[str] = []

    for entry in plan:
        try:
            if entry.original_path != entry.new_path and not os.path.exists(entry.new_path):
                os.rename(entry.original_path, entry.new_path)
                exitos += 1
        except OSError as e:
            errores.append(f"{entry.original_name}: {e}")

    return exitos, errores
