import cv2
import numpy as np
import logging
from pathlib import Path

logger = logging.getLogger("SIGNUM_SENTINEL.FORGER")

class MapGenerator:
    """Genera algoritmicamente mappe PBR mancanti usando OpenCV."""

    @staticmethod
    def generate_roughness(albedo_path: Path, output_path: Path):
        img = cv2.imread(str(albedo_path), cv2.IMREAD_GRAYSCALE)
        if img is None: return False
        # Inversione e normalizzazione per creare una roughness base
        inv = cv2.bitwise_not(img)
        rough = cv2.normalize(inv, None, 0, 255, cv2.NORM_MINMAX)
        cv2.imwrite(str(output_path), rough)
        return True

    @staticmethod
    def generate_normal(albedo_path: Path, output_path: Path):
        img = cv2.imread(str(albedo_path), cv2.IMREAD_GRAYSCALE)
        if img is None: return False
        img = cv2.GaussianBlur(img, (3, 3), 0)
        # Filtro di Sobel per estrarre le pendenze
        sobelx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
        
        ones = np.ones(img.shape, dtype=np.float64)
        n = np.stack([-sobelx, -sobely, ones], axis=2)
        norm = np.linalg.norm(n, axis=2, keepdims=True)
        n /= norm
        
        normal_map = ((n + 1) / 2 * 255).astype(np.uint8)
        cv2.imwrite(str(output_path), cv2.cvtColor(normal_map, cv2.COLOR_RGB2BGR))
        return True