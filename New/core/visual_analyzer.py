import gc
from typing import Any, Optional

try:
    import cv2
    import numpy as np

    HAS_CV = True
except ImportError:
    cv2 = None  # type: ignore
    np = None  # type: ignore
    HAS_CV = False


class VisualAnalyzer:
    """Usa la computer vision classica per validare il tipo di mappa (pixel-level)."""

    def __init__(self):
        self._active = False

    def load(self) -> bool:
        self._active = HAS_CV
        return self._active

    def unload(self) -> None:
        self._active = False
        gc.collect()

    def identify_map_type(self, path: str) -> dict[str, Any]:
        if not self._active and not self.load():
            return {"type": "Unknown", "conf": 0.0}

        img: Optional[Any] = cv2.imread(path) if cv2 is not None else None
        if img is None:
            return {"type": "Unknown", "conf": 0.0}

        mean_bgr = cv2.mean(img)[:3]
        is_normal = 110 < mean_bgr[2] < 150 and 110 < mean_bgr[1] < 150 and mean_bgr[0] > 180

        b, g, r = cv2.split(img)
        is_gray = np.allclose(r, g, atol=12) and np.allclose(g, b, atol=12) if np is not None else False

        if is_normal:
            return {"type": "NORMAL", "conf": 0.95}
        if is_gray:
            brightness = np.mean(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
            if brightness > 230:
                return {"type": "METALLIC", "conf": 0.7}
            if brightness < 40:
                return {"type": "AO", "conf": 0.7}
            return {"type": "GRAYSCALE_DATA", "conf": 0.6}
        return {"type": "ALBEDO/COLOR", "conf": 0.8}


__all__ = ["VisualAnalyzer"]
