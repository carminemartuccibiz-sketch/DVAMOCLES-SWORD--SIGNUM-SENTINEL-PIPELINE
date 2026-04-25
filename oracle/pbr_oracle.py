import json
import logging
from pathlib import Path
from typing import Dict, Any, List

import cv2
import numpy as np

logger = logging.getLogger("SIGNUM_SENTINEL.ORACLE")


class PBRoracle:
    """
    The Oracle: valida le mappe contro regole fisiche lette dalla KB JSON.
    """

    def __init__(self, root_dir: Path | None = None):
        self.root = Path(root_dir) if root_dir else Path(__file__).parent.parent
        self.rules_path = self.root / "06_KNOWLEDGE_BASE" / "rules" / "pbr_oracle_rules.json"
        self.rules = self._load_rules()

    def _load_rules(self) -> Dict[str, Any]:
        if not self.rules_path.exists():
            logger.warning("Regole Oracle non trovate: %s", self.rules_path)
            return {"profiles": {}, "map_rules": {}}
        with open(self.rules_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def validate_material(self, material_dir: Path, profile: str = "dielectric") -> Dict[str, Any]:
        findings: List[str] = []
        files = [f for f in material_dir.iterdir() if f.is_file()]
        map_rules = self.rules.get("map_rules", {})
        profile_rules = self.rules.get("profiles", {}).get(profile, {})

        for file_path in files:
            map_type = self._infer_map_type(file_path.name)
            if not map_type or map_type not in map_rules:
                continue

            img = cv2.imread(str(file_path), cv2.IMREAD_UNCHANGED)
            if img is None:
                findings.append(f"[{file_path.name}] non leggibile.")
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            is_gray = self._is_grayscale(img)
            mean_val = float(np.mean(gray))
            rule = map_rules[map_type]

            if rule.get("grayscale_required") and not is_gray:
                findings.append(f"[{file_path.name}] {map_type} deve essere grayscale.")
            if rule.get("grayscale_forbidden") and is_gray:
                findings.append(f"[{file_path.name}] {map_type} non deve essere grayscale.")
            if "brightness_min" in rule and mean_val < rule["brightness_min"]:
                findings.append(f"[{file_path.name}] {map_type} troppo scura ({mean_val:.1f}).")
            if "brightness_max" in rule and mean_val > rule["brightness_max"]:
                findings.append(f"[{file_path.name}] {map_type} troppo luminosa ({mean_val:.1f}).")

            if map_type == "normal" and len(img.shape) == 3:
                blue_mean = float(np.mean(img[:, :, 0]))
                if blue_mean < rule.get("blue_channel_mean_min", 0):
                    findings.append(f"[{file_path.name}] normal map sospetta (B medio {blue_mean:.1f}).")

            if map_type == "roughness":
                if "roughness_mean_min" in profile_rules and mean_val < profile_rules["roughness_mean_min"]:
                    findings.append(
                        f"[{file_path.name}] Roughness troppo scura per profilo {profile} ({mean_val:.1f})."
                    )
                if "roughness_mean_max" in profile_rules and mean_val > profile_rules["roughness_mean_max"]:
                    findings.append(
                        f"[{file_path.name}] Roughness troppo luminosa per profilo {profile} ({mean_val:.1f})."
                    )

        return {
            "material": material_dir.name,
            "profile": profile,
            "status": "error" if findings else "ok",
            "issues": findings
        }

    @staticmethod
    def _is_grayscale(img: np.ndarray) -> bool:
        if len(img.shape) < 3 or img.shape[2] == 1:
            return True
        b, g, r = cv2.split(img[:, :, :3])
        return np.allclose(r, g, atol=10) and np.allclose(g, b, atol=10)

    @staticmethod
    def _infer_map_type(name: str) -> str:
        n = name.lower()
        if "rough" in n:
            return "roughness"
        if "normal" in n or "_nrm" in n:
            return "normal"
        if "metal" in n:
            return "metallic"
        if "ao" in n or "occlusion" in n:
            return "ao"
        return ""
