"""Infrastructure: safe file system operations."""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

from send2trash import send2trash


def _log_deletion(file_path: str) -> None:
    """
    Append a JSON record to ~/.cleanacelerai/deleted.log before every deletion.

    Args:
        file_path: Absolute path of the file about to be deleted.
    """
    log_dir = Path.home() / '.cleanacelerai'
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / 'deleted.log'
    try:
        size = Path(file_path).stat().st_size
    except OSError:
        size = -1
    try:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read(65536)).hexdigest()[:16]
    except OSError:
        file_hash = 'unreadable'
    entry = {
        'ts': datetime.datetime.now().isoformat(timespec='seconds'),
        'path': str(file_path),
        'size': size,
        'sha256_first_64k': file_hash,
    }
    with log_path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def safe_delete(path: str) -> tuple[bool, str]:
    """
    Delete a file safely by sending it to the Recycle Bin.

    Logs the deletion to ~/.cleanacelerai/deleted.log before trashing.
    Handles read-only flags and long paths (MS-DOS NUL workaround).

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
        _log_deletion(path)
        send2trash(str(path))
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
