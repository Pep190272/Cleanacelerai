"""Infrastructure: safe file system operations."""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

from send2trash import TrashPermissionError, send2trash


def _log_deletion(
    file_path: str,
    source: str | None = None,
    fallback_rename: bool = False,
) -> None:
    """
    Append a JSON record to ~/.cleanacelerai/deleted.log before every deletion.

    Args:
        file_path: Absolute path of the file about to be deleted.
        source: Optional source tag (e.g. 'asesor.orden-general'). When None,
                the key is omitted entirely to preserve backward-compatible log shape.
        fallback_rename: When True, adds 'fallback_rename': true to the log entry.
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
    entry: dict[str, object] = {
        'ts': datetime.datetime.now().isoformat(timespec='seconds'),
        'path': str(file_path),
        'size': size,
        'sha256_first_64k': file_hash,
    }
    # Only write optional fields when set, preserving existing log shape for
    # callers that pass no source (safe_delete for files).
    if source is not None:
        entry['source'] = source
    if fallback_rename:
        entry['fallback_rename'] = True
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


def safe_delete_dir(path: str, source: str = "asesor") -> tuple[bool, str]:
    """Delete a directory safely by sending it to the Recycle Bin.

    On TrashPermissionError (typically a non-C: drive where the shell refuses
    to recycle): fallback to in-place rename
        '{name}.UNSAFE-CANT-RECYCLE.{ISO-timestamp}.bak'
    The caller (presenter) is responsible for surfacing the fallback to the user
    via a view widget — this function only returns success=True and the rename
    is recorded in the deletion log with fallback_rename=True.

    Args:
        path: Absolute path to the directory to delete.
        source: Source tag for the audit log (e.g. 'asesor.orden-general').

    Returns:
        (True, '') on clean Recycle Bin success.
        (True, 'FALLBACK_RENAME:{new_path}') on fallback rename success.
        (False, error_msg) on hard failure.
    """
    if not os.path.isdir(path):
        return False, f"No es un directorio: {path}"

    try:
        _log_deletion(path, source=source, fallback_rename=False)
        send2trash(str(path))
        return True, ""
    except TrashPermissionError:
        # Drive does not allow Recycle Bin (e.g., D: on some configs).
        # Rename in-place so the data survives.
        try:
            parent = os.path.dirname(path)
            base = os.path.basename(path)
            ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
            new_name = f"{base}.UNSAFE-CANT-RECYCLE.{ts}.bak"
            new_path = os.path.join(parent, new_name)
            os.rename(path, new_path)
            _log_deletion(new_path, source=source, fallback_rename=True)
            return True, f"FALLBACK_RENAME:{new_path}"
        except OSError as e:
            return False, f"No se pudo eliminar ni renombrar: {e}"
    except PermissionError as e:
        return False, f"Permiso denegado: {e}"
    except FileNotFoundError:
        return True, ""  # Already gone
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
