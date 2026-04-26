"""Portable ExifTool path resolution (SPEC); shared with metadata pipeline."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from utils.runtime_paths import resolve_resource


def resolve_exiftool_path() -> Optional[str]:
    """Return executable path or None (caller uses OpenCV/Pillow fallback)."""
    candidates = [
        resolve_resource("exiftool.exe"),
        resolve_resource("exiftool_files/exiftool.exe"),
        resolve_resource("exiftool_files/exiftool(-k).exe"),
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return str(c)
    w = shutil.which("exiftool")
    return w
