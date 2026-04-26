import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np


@dataclass
class MaterialAnalysis:
    provider: str
    material: str
    variant: str
    map_coverage: List[str]
    pbr_completeness: float
    generated_vs_reference: List[Dict[str, Any]]


class AnalysisBenchmarkEngine:
    """Analyze processed manifests and compare generated maps against references."""

    CORE_PBR_MAPS = ("albedo", "normal", "roughness", "ao", "height", "cavity")

    def __init__(self, root_dir: Path):
        self.root = Path(root_dir).resolve()
        self.processed_dir = self.root / "03_PROCESSED"
        self.report_dir = self.root / "06_KNOWLEDGE_BASE" / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        analyses: List[MaterialAnalysis] = []
        for manifest in sorted(self.processed_dir.glob("*/*/manifest.json")):
            payload = self._load_json(manifest)
            if not payload:
                continue
            material = manifest.parent.name
            provider = manifest.parent.parent.name
            variants = payload.get("variants", {})
            for variant_name, variant_data in variants.items():
                files = variant_data.get("files", [])
                analyses.append(
                    MaterialAnalysis(
                        provider=provider,
                        material=material,
                        variant=variant_name,
                        map_coverage=self._extract_coverage(files),
                        pbr_completeness=self._pbr_completeness(files),
                        generated_vs_reference=self._benchmark_variant(files),
                    )
                )

        report = self._build_report(analyses)
        out_path = self.report_dir / "analysis_benchmark_report.json"
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
        report["output_path"] = str(out_path)
        return report

    def _extract_coverage(self, files: List[Dict[str, Any]]) -> List[str]:
        found = {str(item.get("map_type", "")).lower().split("_")[0] for item in files}
        return sorted([f for f in found if f and f != "unknown"])

    def _pbr_completeness(self, files: List[Dict[str, Any]]) -> float:
        found = set(self._extract_coverage(files))
        required = {"albedo", "normal", "roughness"}
        return round(len(found.intersection(required)) / float(len(required)), 3)

    def _benchmark_variant(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for item in files:
            key = str(item.get("map_type", "")).lower().split("_")[0]
            if key not in self.CORE_PBR_MAPS:
                continue
            process = str(item.get("process", "")).lower()
            bucket = "generated" if process.startswith("generated_") else "reference"
            grouped.setdefault(key, {})[bucket] = item

        results: List[Dict[str, Any]] = []
        for map_type, candidates in grouped.items():
            gen = candidates.get("generated")
            ref = candidates.get("reference")
            if not gen or not ref:
                continue
            score, details = self._compare_images(Path(gen.get("path", "")), Path(ref.get("path", "")))
            results.append(
                {
                    "map_type": map_type,
                    "generated": gen.get("name", ""),
                    "reference": ref.get("name", ""),
                    "similarity_score": score,
                    "metrics": details,
                }
            )
        return results

    def _compare_images(self, generated: Path, reference: Path) -> Tuple[float, Dict[str, float]]:
        if not generated.exists() or not reference.exists():
            return 0.0, {"mae": 1.0, "hist_corr": 0.0}
        g_img = cv2.imread(str(generated), cv2.IMREAD_GRAYSCALE)
        r_img = cv2.imread(str(reference), cv2.IMREAD_GRAYSCALE)
        if g_img is None or r_img is None:
            return 0.0, {"mae": 1.0, "hist_corr": 0.0}
        if g_img.shape != r_img.shape:
            g_img = cv2.resize(g_img, (r_img.shape[1], r_img.shape[0]), interpolation=cv2.INTER_AREA)

        mae = float(np.mean(np.abs(g_img.astype(np.float32) - r_img.astype(np.float32))) / 255.0)
        h1 = cv2.calcHist([g_img], [0], None, [64], [0, 256])
        h2 = cv2.calcHist([r_img], [0], None, [64], [0, 256])
        cv2.normalize(h1, h1)
        cv2.normalize(h2, h2)
        corr = float(cv2.compareHist(h1, h2, cv2.HISTCMP_CORREL))
        similarity = max(0.0, min(1.0, (1.0 - mae) * 0.6 + max(0.0, corr) * 0.4))
        return round(similarity, 4), {"mae": round(mae, 4), "hist_corr": round(corr, 4)}

    def _build_report(self, analyses: List[MaterialAnalysis]) -> Dict[str, Any]:
        rows = [
            {
                "provider": item.provider,
                "material": item.material,
                "variant": item.variant,
                "map_coverage": item.map_coverage,
                "pbr_completeness": item.pbr_completeness,
                "generated_vs_reference": item.generated_vs_reference,
            }
            for item in analyses
        ]
        completeness_scores = [item.pbr_completeness for item in analyses]
        benchmark_scores = [
            rec["similarity_score"]
            for item in analyses
            for rec in item.generated_vs_reference
            if isinstance(rec.get("similarity_score"), float)
        ]
        per_map_scores: Dict[str, List[float]] = {}
        for item in analyses:
            for rec in item.generated_vs_reference:
                mtype = str(rec.get("map_type", "")).lower()
                score = rec.get("similarity_score")
                if isinstance(score, float):
                    per_map_scores.setdefault(mtype, []).append(score)
        per_map_summary = {
            map_type: {
                "count": len(scores),
                "avg_similarity": round(mean(scores), 4) if scores else 0.0,
                "min_similarity": round(min(scores), 4) if scores else 0.0,
                "max_similarity": round(max(scores), 4) if scores else 0.0,
            }
            for map_type, scores in sorted(per_map_scores.items(), key=lambda x: x[0])
        }
        return {
            "status": "ok",
            "materials_analyzed": len(rows),
            "avg_pbr_completeness": round(mean(completeness_scores), 4) if completeness_scores else 0.0,
            "avg_generated_similarity": round(mean(benchmark_scores), 4) if benchmark_scores else 0.0,
            "map_type_scores": per_map_summary,
            "materials": rows,
        }

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            return loaded if isinstance(loaded, dict) else {}
        except Exception:
            return {}
