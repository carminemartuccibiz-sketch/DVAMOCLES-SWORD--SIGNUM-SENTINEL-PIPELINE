"""Image helpers: Pillow for IO, OpenCV-friendly numpy where needed (SPEC PART 11)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore


def read_rgb(path: Path) -> Optional[np.ndarray]:
    """BGR uint8 array for OpenCV, or None."""
    if cv2 is None:
        return None
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    return img


def size_px(path: Path) -> Optional[Tuple[int, int]]:
    """(width, height) without full decode if possible."""
    if Image is None:
        if cv2 is None:
            return None
        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is None:
            return None
        return int(img.shape[1]), int(img.shape[0])
    with Image.open(path) as im:
        return im.size


def resolution_label(width: int, height: int) -> str:
    """Derive label from max edge (SPEC: never trust folder name alone)."""
    m = max(width, height)
    if m >= 7680:
        return "8K"
    if m >= 3840:
        return "4K"
    if m >= 1920:
        return "2K"
    if m >= 960:
        return "1K"
    return "UNKNOWN"
