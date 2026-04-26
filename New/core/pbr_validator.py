import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np

from core.map_generator import MapGenerator
from core.naming_intelligence import NamingIntelligence

logger = logging.getLogger("SIGNUM_SENTINEL.PBR_VALIDATOR")


class PBRValidator:
    """
    Single validation engine:
    - rule-based physical checks from KB JSON
    - optional map generation for missing core maps
    """

    def __init__(self, root_dir=None):
        self.root = Path(root_dir) if root_dir else Path(__file__).parent.parent
        self.processed_dir = self.root / "03_PROCESSED"
        self.rules_path = self.root / "06_KNOWLEDGE_BASE" / "rules" / "pbr_rules.json"
        self.rules = self._load_rules()
        self.generator = MapGenerator()
        self.naming = NamingIntelligence(str(self.root / "06_KNOWLEDGE_BASE" / "mappings" / "naming_map.json"))

    def _load_rules(self) -> Dict[str, Any]:
        if not self.rules_path.exists():
            logger.warning("PBR rules not found: %s", self.rules_path)
            return {"profiles": {}, "map_rules": {}}
        with open(self.rules_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def process_all(self):
        """Scan 03_PROCESSED and auto-fix incomplete materials."""
        if not self.processed_dir.exists():
            return
        for provider_dir in self.processed_dir.iterdir():
            if provider_dir.is_dir():
                for mat_dir in provider_dir.iterdir():
                    if mat_dir.is_dir():
                        self._check_and_fix(mat_dir)

    def _check_and_fix(self, mat_dir: Path):
        manifest_path = mat_dir / "manifest.json"
        if not manifest_path.exists():
            return

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        found = set((data.get("coverage", {}) or {}).get("maps_found", []))
        files = data.get("files", [])
        variants = data.get("variants", {})
        if not files and isinstance(variants, dict):
            files = [item for var in variants.values() for item in var.get("files", [])]
        albedo_file = next(
            (
                Path(str(f.get("path", ""))).name
                for f in files
                if str(f.get("map_type", "")).lower().split("_")[0] in {"albedo", "color", "basecolor"}
            ),
            None,
        )

        if not albedo_file:
            return

        if "normal" not in found:
            out = mat_dir / f"{mat_dir.name}_Normal_GEN.png"
            if self.generator.generate_normal(self._resolve_existing_file(mat_dir, albedo_file), out):
                found.add("normal")
                files.append({"original_name": out.name, "path": str(out), "map_type": "normal", "is_generated": True})

        if "roughness" not in found:
            out = mat_dir / f"{mat_dir.name}_Roughness_GEN.png"
            if self.generator.generate_roughness(self._resolve_existing_file(mat_dir, albedo_file), out):
                found.add("roughness")
                files.append({"original_name": out.name, "path": str(out), "map_type": "roughness", "is_generated": True})

        data.setdefault("coverage", {})["maps_found"] = list(found)
        data["files"] = files
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def _resolve_existing_file(mat_dir: Path, filename: str) -> Path:
        direct = mat_dir / filename
        if direct.exists():
            return direct
        found = next((p for p in mat_dir.rglob(filename) if p.is_file()), direct)
        return found

    def validate_material(self, material_dir: Path, profile: str = "dielectric") -> Dict[str, Any]:
        findings: List[str] = []
        files = [f for f in material_dir.iterdir() if f.is_file()]
        map_rules = self.rules.get("map_rules", {})
        profile_rules = self.rules.get("profiles", {}).get(profile, {})

        for file_path in files:
            map_type = self.naming.classify_filename(file_path.name).map_type
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
            "issues": findings,
        }

    @staticmethod
    def _is_grayscale(img: np.ndarray) -> bool:
        if len(img.shape) < 3 or img.shape[2] == 1:
            return True
        b, g, r = cv2.split(img[:, :, :3])
        return np.allclose(r, g, atol=10) and np.allclose(g, b, atol=10)
