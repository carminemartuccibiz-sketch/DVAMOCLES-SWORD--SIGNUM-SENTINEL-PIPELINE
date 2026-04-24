import cv2
import numpy as np

class VisualAnalyzer:
    """Usa la computer vision classica per validare il tipo di mappa (Pixel-Level)."""

    @staticmethod
    def identify_map_type(path: str) -> dict:
        img = cv2.imread(path)
        if img is None: return {"type": "Unknown", "conf": 0.0}

        # 1. TEST NORMAL (Il viola/azzurro 128,128,255)
        mean_bgr = cv2.mean(img)[:3]
        is_normal = 110 < mean_bgr[2] < 150 and 110 < mean_bgr[1] < 150 and mean_bgr[0] > 180
        
        # 2. TEST GRAYSCALE (Roughness, Metallic, AO)
        b, g, r = cv2.split(img)
        is_gray = np.allclose(r, g, atol=12) and np.allclose(g, b, atol=12)

        if is_normal: return {"type": "NORMAL", "conf": 0.95}
        
        if is_gray:
            brightness = np.mean(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
            if brightness > 230: return {"type": "METALLIC", "conf": 0.7}
            if brightness < 40: return {"type": "AO", "conf": 0.7}
            return {"type": "GRAYSCALE_DATA", "conf": 0.6}

        return {"type": "ALBEDO/COLOR", "conf": 0.8}