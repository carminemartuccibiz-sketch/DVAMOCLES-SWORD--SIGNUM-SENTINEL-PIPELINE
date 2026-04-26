import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np


class SegmentationEngine:
    """Build ID and feature-guided masks from texture sets."""

    def __init__(self, root_dir: Path):
        self.root = Path(root_dir).resolve()
        self.processed_dir = self.root / "03_PROCESSED"
        self.segment_dir = self.root / "04_SEGMENTATION"
        self.segment_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        generated = 0
        material_reports: List[Dict[str, Any]] = []
        for manifest in sorted(self.processed_dir.glob("*/*/manifest.json")):
            payload = self._load_json(manifest)
            variants = payload.get("variants", {})
            provider = manifest.parent.parent.name
            material = manifest.parent.name
            for variant_name, variant_data in variants.items():
                file_rows = variant_data.get("files", [])
                generated_paths, metadata = self._segment_variant(provider, material, variant_name, file_rows)
                if generated_paths:
                    generated += len(generated_paths)
                    material_reports.append(
                        {
                            "provider": provider,
                            "material": material,
                            "variant": variant_name,
                            "outputs": [str(p) for p in generated_paths],
                            "metadata_path": str(metadata),
                        }
                    )
        return {"status": "ok", "masks_generated": generated, "variants": material_reports}

    def _segment_variant(
        self, provider: str, material: str, variant: str, files: List[Dict[str, Any]]
    ) -> Tuple[List[Path], Path | None]:
        albedo = self._find_map(files, ("albedo", "color", "basecolor"))
        if not albedo:
            return [], None

        out_dir = self.segment_dir / provider / material / variant
        out_dir.mkdir(parents=True, exist_ok=True)
        outputs: List[Path] = []

        color_id_path = out_dir / f"{material}_{variant}_idmask_color.png"
        cluster_count = self._kmeans_color_mask(Path(albedo["path"]), color_id_path)
        if cluster_count > 0:
            outputs.append(color_id_path)

        normal = self._find_map(files, ("normal",))
        roughness = self._find_map(files, ("roughness",))
        height = self._find_map(files, ("height", "displacement"))
        feature_mask_path = out_dir / f"{material}_{variant}_pbrmask_feature.png"
        channels = [Path(albedo["path"])]
        for candidate in (normal, roughness, height):
            if candidate and Path(candidate["path"]).exists():
                channels.append(Path(candidate["path"]))
        confidence = self._feature_guided_mask(channels, feature_mask_path)
        if confidence > 0.0:
            outputs.append(feature_mask_path)

        metadata = {
            "provider": provider,
            "material": material,
            "variant": variant,
            "strategies": [
                {"name": "color_kmeans_idmask", "classes": cluster_count, "confidence": 0.7 if cluster_count else 0.0},
                {"name": "multi_feature_pbrmask", "inputs": [p.name for p in channels], "confidence": confidence},
            ],
            "description": "Segmentation metadata for dataset usage and auditability.",
        }
        metadata_path = out_dir / "segmentation_metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2, ensure_ascii=False)
        return outputs, metadata_path

    def _kmeans_color_mask(self, image_path: Path, output_path: Path) -> int:
        img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if img is None:
            return 0
        z = img.reshape((-1, 3)).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        k = 4
        _, labels, _ = cv2.kmeans(z, k, None, criteria, 5, cv2.KMEANS_PP_CENTERS)
        mask = labels.reshape((img.shape[0], img.shape[1])).astype(np.uint8)
        normalized = cv2.normalize(mask, None, 0, 255, cv2.NORM_MINMAX)
        cv2.imwrite(str(output_path), normalized)
        return int(k)

    def _feature_guided_mask(self, image_paths: List[Path], output_path: Path) -> float:
        stacks = []
        base_shape = None
        for path in image_paths:
            img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            if base_shape is None:
                base_shape = img.shape
            elif img.shape != base_shape:
                img = cv2.resize(img, (base_shape[1], base_shape[0]), interpolation=cv2.INTER_AREA)
            stacks.append(img.astype(np.float32) / 255.0)
        if not stacks:
            return 0.0
        fused = np.mean(np.stack(stacks, axis=2), axis=2)
        edges = cv2.Canny((fused * 255).astype(np.uint8), 80, 160)
        dilated = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
        cv2.imwrite(str(output_path), dilated)
        density = float(np.count_nonzero(dilated) / dilated.size)
        return round(min(1.0, density * 8.0), 4)

    @staticmethod
    def _find_map(files: List[Dict[str, Any]], keys: Tuple[str, ...]) -> Dict[str, Any] | None:
        keyset = set(keys)
        for item in files:
            map_type = str(item.get("map_type", "")).lower().split("_")[0]
            if map_type in keyset and str(item.get("path", "")):
                return item
        return None

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            return loaded if isinstance(loaded, dict) else {}
        except Exception:
            return {}
