import json
from pathlib import Path
from typing import Any, Dict, List


class DatasetBuilder:
    """Build task-specific dataset indexes from processed and segmentation outputs."""

    TASKS = (
        "cataloging",
        "super_resolution",
        "artifact_fix",
        "missing_map_generation",
        "texture_generation",
    )

    def __init__(self, root_dir: Path):
        self.root = Path(root_dir).resolve()
        self.processed_dir = self.root / "03_PROCESSED"
        self.segment_dir = self.root / "04_SEGMENTATION"
        self.dataset_dir = self.root / "04_DATASET"
        self.dataset_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        records = self._collect_records()
        exports: Dict[str, str] = {}
        for task in self.TASKS:
            path = self.dataset_dir / f"{task}_dataset.jsonl"
            self._write_jsonl(path, [self._project_record(task, row) for row in records])
            exports[task] = str(path)
        summary = self._build_summary(records, exports)
        summary_path = self.dataset_dir / "dataset_summary.json"
        with open(summary_path, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2, ensure_ascii=False)
        summary["summary_path"] = str(summary_path)
        return summary

    def _collect_records(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for manifest_path in sorted(self.processed_dir.glob("*/*/manifest.json")):
            provider = manifest_path.parent.parent.name
            material = manifest_path.parent.name
            payload = self._load_json(manifest_path)
            variants = payload.get("variants", {})
            for variant_name, variant_data in variants.items():
                files = variant_data.get("files", [])
                seg_meta = self.segment_dir / provider / material / variant_name / "segmentation_metadata.json"
                rows.append(
                    {
                        "provider": provider,
                        "material": material,
                        "variant": variant_name,
                        "files": files,
                        "is_pbr_complete": self._is_pbr_complete(files),
                        "segmentation_metadata": str(seg_meta) if seg_meta.exists() else "",
                    }
                )
        return rows

    def _project_record(self, task: str, row: Dict[str, Any]) -> Dict[str, Any]:
        out = {
            "task": task,
            "provider": row["provider"],
            "material": row["material"],
            "variant": row["variant"],
            "is_pbr_complete": row["is_pbr_complete"],
            "segmentation_metadata": row["segmentation_metadata"],
            "files": row["files"],
        }
        if task == "super_resolution":
            out["target_resolution"] = "4K"
        elif task == "artifact_fix":
            out["target"] = "artifact_reduction_and_consistency"
        elif task == "missing_map_generation":
            out["required_maps"] = ["normal", "roughness", "ao", "height"]
        elif task == "texture_generation":
            out["target"] = "texture_synthesis_or_completion"
        return out

    def _build_summary(self, records: List[Dict[str, Any]], exports: Dict[str, str]) -> Dict[str, Any]:
        providers = sorted({row["provider"] for row in records})
        complete = [row for row in records if row["is_pbr_complete"]]
        segmented = [row for row in records if row["segmentation_metadata"]]
        by_provider: Dict[str, int] = {}
        for row in records:
            provider = row["provider"]
            by_provider[provider] = by_provider.get(provider, 0) + 1
        max_count = max(by_provider.values()) if by_provider else 0
        min_count = min(by_provider.values()) if by_provider else 0
        imbalance_ratio = round(max_count / min_count, 4) if min_count else 0.0
        return {
            "status": "ok",
            "total_variants": len(records),
            "providers": providers,
            "pbr_complete_variants": len(complete),
            "segmented_variants": len(segmented),
            "coverage_ratio": round(len(complete) / len(records), 4) if records else 0.0,
            "provider_distribution": by_provider,
            "imbalance_ratio": imbalance_ratio,
            "exports": exports,
        }

    @staticmethod
    def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    @staticmethod
    def _is_pbr_complete(files: List[Dict[str, Any]]) -> bool:
        found = {str(f.get("map_type", "")).lower().split("_")[0] for f in files}
        return {"albedo", "normal", "roughness"}.issubset(found)

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            return loaded if isinstance(loaded, dict) else {}
        except Exception:
            return {}
