"""Upload sidecar: make re-running a folder upload cheap and idempotent.

A JSON map ``{filename: {content_id, modified}}`` recording what was uploaded
and when. On the next run, files whose modification time is unchanged are
skipped, so re-uploading the same folder uploads 0 files instead of creating
duplicates on the TV.

All functions are synchronous and do blocking file I/O — call them from the
executor (``hass.async_add_executor_job``), never directly on the event loop.
"""

from __future__ import annotations

import json
import os

# Image extensions the batch uploader considers.
IMAGE_EXTS = (".jpg", ".jpeg", ".png")


def list_images(folder: str) -> list[str]:
    """Return the sorted absolute paths of the images directly in ``folder``."""
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    out = [
        os.path.join(folder, n)
        for n in sorted(names)
        if n.lower().endswith(IMAGE_EXTS) and os.path.isfile(os.path.join(folder, n))
    ]
    return out


def safe_mtime(path: str) -> float:
    """Return the file's mtime, or 0.0 if it can't be read."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def load_sidecar(path: str) -> dict:
    """Load the sidecar map, or {} if it does not exist / is unreadable."""
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_sidecar(path: str, data: dict) -> None:
    """Persist the sidecar map (best effort)."""
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


def needs_upload(filename: str, mtime: float, sidecar: dict) -> bool:
    """True if the file is new or its mtime changed since the last upload."""
    entry = sidecar.get(filename)
    if not entry:
        return True
    return entry.get("modified") != mtime
