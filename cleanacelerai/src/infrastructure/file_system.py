"""Infrastructure: safe file system operations."""
from __future__ import annotations

import os
import stat
import subprocess


def safe_delete(path: str) -> tuple[bool, str]:
    """
    Delete a file safely, handling read-only flags and long paths.

    Uses the MS-DOS NUL workaround for paths ending in '\\nul' or
    exceeding 250 characters.

    Args:
        path: Absolute path to the file.

    Returns:
        Tuple of (success: bool, error_message: str).
        error_message is empty on success.
    """
    # MS-DOS hechizo for problematic paths
    if path.lower().endswith("\nul") or len(path) > 250:
        try:
            subprocess.run(
                ["cmd", "/c", "del", "/f", "/q", f"\\\\?\\{path}"],
                check=True,
                capture_output=True,
            )
            return True, ""
        except subprocess.CalledProcessError as e:
            return False, str(e)
        except FileNotFoundError:
            return True, ""  # Already gone

    try:
        try:
            os.chmod(path, stat.S_IWRITE)
        except (PermissionError, OSError):
            pass  # Best-effort: remove read-only flag
        os.remove(path)
        return True, ""
    except PermissionError as e:
        return False, f"Permiso denegado: {e}"
    except FileNotFoundError:
        return True, ""  # Already deleted — treat as success
    except OSError as e:
        return False, str(e)


def open_in_explorer(path: str) -> None:
    """
    Open Windows Explorer with the given path selected.

    Args:
        path: Absolute path to highlight in Explorer.
    """
    try:
        subprocess.Popen(
            fr'explorer /select,"{os.path.normpath(path)}"'
        )
    except OSError:
        pass
