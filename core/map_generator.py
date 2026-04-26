import cv2
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any

from core.external_generator_hook import ExternalGeneratorHook

logger = logging.getLogger("SIGNUM_SENTINEL.FORGER")

class MapGenerator:
    """Genera algoritmicamente mappe PBR mancanti usando OpenCV."""

    def __init__(self, root_dir: Path | None = None):
        self.root = Path(root_dir).resolve() if root_dir else Path(__file__).parent.parent.resolve()
        self.external_hook = ExternalGeneratorHook(self.root)

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

    @staticmethod
    def generate_ao(albedo_path: Path, output_path: Path):
        img = cv2.imread(str(albedo_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False
        blur = cv2.GaussianBlur(img, (21, 21), 0)
        ao = cv2.normalize(cv2.bitwise_not(blur), None, 0, 255, cv2.NORM_MINMAX)
        cv2.imwrite(str(output_path), ao)
        return True

    @staticmethod
    def generate_height(albedo_path: Path, output_path: Path):
        img = cv2.imread(str(albedo_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False
        height = cv2.equalizeHist(img)
        cv2.imwrite(str(output_path), height)
        return True

    @staticmethod
    def generate_cavity(albedo_path: Path, output_path: Path):
        img = cv2.imread(str(albedo_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False
        blur = cv2.GaussianBlur(img, (5, 5), 0)
        lap = cv2.Laplacian(blur, cv2.CV_32F, ksize=3)
        cavity = cv2.normalize(np.abs(lap), None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        cv2.imwrite(str(output_path), cavity)
        return True

    @staticmethod
    def make_seamless(input_path: Path, output_path: Path):
        img = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
        if img is None:
            return False
        h, w = img.shape[:2]
        shifted = np.roll(img, shift=(h // 2, w // 2), axis=(0, 1))
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.rectangle(mask, (w // 4, h // 4), (3 * w // 4, 3 * h // 4), 255, -1)
        seamless = cv2.inpaint(shifted, cv2.bitwise_not(mask), 5, cv2.INPAINT_TELEA)
        out = np.roll(seamless, shift=(-h // 2, -w // 2), axis=(0, 1))
        cv2.imwrite(str(output_path), out)
        return True

    def generate_missing_maps(self, material_name: str, variant_dir: Path, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Se mancano mappe core, le genera a partire da albedo/color.
        """
        lower_types = {str(f.get("map_type", "")).lower() for f in files}
        albedo_rec = next((f for f in files if str(f.get("map_type", "")).lower() in {"albedo", "color", "basecolor"}), None)
        if not albedo_rec:
            return []
        albedo_path = Path(albedo_rec.get("path", ""))
        if not albedo_path.exists():
            return []

        generated: List[Dict[str, Any]] = []
        targets = [
            ("normal", self.generate_normal, "NORMAL"),
            ("roughness", self.generate_roughness, "ROUGHNESS"),
            ("ao", self.generate_ao, "AO"),
            ("height", self.generate_height, "HEIGHT"),
            ("cavity", self.generate_cavity, "CAVITY"),
        ]
        for key, fn, map_type in targets:
            if key in lower_types:
                continue
            out_name = f"{material_name}_{variant_dir.name}_{map_type}_GEN.png".replace("__", "_")
            out_path = variant_dir / out_name
            hook_result = self.external_hook.generate(
                input_path=albedo_path,
                output_path=out_path,
                map_type=key,
                material_name=material_name,
                variant_name=variant_dir.name,
            )
            ok = bool(hook_result.get("used", False))
            tool_name = "external_generator_hook" if ok else "opencv_map_generator"
            process_name = f"generated_{key}_external" if ok else f"generated_{key}_from_albedo"
            if not ok:
                ok = fn(albedo_path, out_path)
            if not ok:
                continue
            generated.append(
                {
                    "name": out_path.name,
                    "path": str(out_path),
                    "map_type": map_type,
                    "format": "PNG",
                    "resolution": albedo_rec.get("resolution", "UNKNOWN"),
                    "tech_res": albedo_rec.get("tech_res", "Unknown"),
                    "bit_depth": "8-bit",
                    "color_space": "Linear",
                    "is_custom": True,
                    "source_raw": albedo_rec.get("name", ""),
                    "derived_from": [albedo_rec.get("name", "")],
                    "process": process_name,
                    "tool": tool_name,
                    "ai_description": "",
                    "generator_details": hook_result if hook_result else {},
                }
            )
        return generated