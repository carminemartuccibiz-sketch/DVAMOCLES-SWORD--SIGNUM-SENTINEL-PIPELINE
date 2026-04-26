import json
import logging
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List

from core.metadata_extractor import MetadataExtractor
from core.naming_intelligence import NamingIntelligence
from core.quality_gates import KnowledgeBaseQualityGates

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SIGNUM_SENTINEL.INGESTOR")


class Ingestor:
    """Ingestione strutturata Material -> Variant -> FileRecord."""

    VALID_TEXTURE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".tga"}
    VALID_AUX_EXT = {".mtlx", ".tres", ".usdc", ".blend", ".uasset", ".json"}
    SCHEMA_VERSION = "1.0.0"

    def __init__(self, root_dir: str | None = None):
        self.root = Path(root_dir).resolve() if root_dir else Path(__file__).parent.parent.resolve()
        self.raw_dir = self.root / "01_RAW_ARCHIVE"
        self.custom_dir = self.root / "02_CUSTOM"
        self.processed_dir = self.root / "03_PROCESSED"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.naming = NamingIntelligence(str(self.root / "06_KNOWLEDGE_BASE" / "mappings" / "naming_map.json"))
        self.metadata = MetadataExtractor(self.root)

    def run_full_ingestion(self) -> Dict[str, Any]:
        logger.info("Start ingestion RAW + CUSTOM")
        total = 0
        errors = 0
        manifests: List[str] = []

        for source_root, source_label in ((self.raw_dir, "RAW"), (self.custom_dir, "CUSTOM")):
            if not source_root.exists():
                continue
            for provider_dir in sorted(source_root.iterdir(), key=lambda p: p.name.lower()):
                if not provider_dir.is_dir():
                    continue
                for material_dir in sorted(provider_dir.iterdir(), key=lambda p: p.name.lower()):
                    if not material_dir.is_dir():
                        continue
                    try:
                        out = self._ingest_material(provider_dir.name, material_dir, source_label)
                        if out:
                            manifests.append(out)
                            total += 1
                    except Exception:
                        errors += 1
                        logger.exception("Ingest failed: %s/%s", provider_dir.name, material_dir.name)

        gates_report = KnowledgeBaseQualityGates(self.root).run()
        if gates_report["status"] != "ok":
            errors += len(gates_report.get("errors", []))
            logger.error("KB quality gates failed: %s", gates_report.get("errors", []))
        logger.info("Ingestion done. materials=%s errors=%s", total, errors)
        return {
            "status": "success" if errors == 0 else "partial_success",
            "processed": total,
            "errors": errors,
            "manifests": manifests,
            "quality_gates": gates_report,
        }

    def _ingest_material(self, provider: str, material_dir: Path, source_label: str) -> str | None:
        material_info = self._read_json(material_dir / "material_info.json")
        process_info = self._read_json(material_dir / "process.json")

        material_name = material_info.get("identity", {}).get("material_name", material_dir.name)
        tags = material_info.get("tags", [])
        description = material_info.get("description", "")
        profile = process_info.get("profile", "dielectric")

        variant_map = self._collect_variants(material_dir)
        if not variant_map:
            logger.warning("No variants detected in %s", material_dir)
            return None

        output_dir = self.processed_dir / provider / material_name
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        variants_payload: Dict[str, Any] = {}
        coverage = set()
        total_files = 0

        for variant_name, files in variant_map.items():
            variant_out = output_dir / "variants" / variant_name
            variant_out.mkdir(parents=True, exist_ok=True)
            payload_files = []
            for src in files:
                dst = variant_out / src.name
                if src.resolve() != dst.resolve():
                    shutil.copy2(src, dst)
                detected = self.naming.classify_filename(src.name)
                meta = self.metadata.extract_all(dst)
                if detected.map_type != "unknown":
                    coverage.add(detected.map_type)
                payload_files.append(
                    {
                        "original_filename": src.name,
                        "path": str(dst),
                        "map_type": detected.map_type,
                        "confidence": detected.confidence,
                        "convention": detected.convention,
                        "specs": meta.get("image_specs", {}),
                        "software_origin": meta.get("software_origin", "Unknown"),
                    }
                )
                total_files += 1
            variants_payload[variant_name] = {
                "format": self._infer_format(files),
                "resolution": self._infer_resolution(variant_name, files),
                "files": payload_files,
            }

        flattened_files = [item for var in variants_payload.values() for item in var.get("files", [])]
        manifest = {
            "schema_version": self.SCHEMA_VERSION,
            "metadata": {
                "material_name": material_name,
                "provider": provider,
                "source_origin": source_label,
                "tags": tags,
                "description": description,
                "profile": profile,
                "source_path": str(material_dir),
            },
            "coverage": {
                "maps_found": sorted(list(coverage)),
                "is_pbr_complete": self._is_pbr_complete(coverage),
            },
            "derivation": process_info if process_info else {"is_raw": source_label == "RAW"},
            "variants": variants_payload,
            "files": flattened_files,
            "stats": {"variant_count": len(variants_payload), "file_count": total_files},
        }

        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4, ensure_ascii=False)
        logger.info("Manifest generated: %s", manifest_path)
        return str(manifest_path)

    def _collect_variants(self, material_dir: Path) -> Dict[str, List[Path]]:
        """
        Auto-nesting:
        - cartelle variante (Rock_055_1K_PNG)
        - struttura flat (deduce da filename)
        """
        variants: Dict[str, List[Path]] = {}
        for child in sorted(material_dir.iterdir(), key=lambda p: p.name.lower()):
            if child.is_dir():
                key = self._variant_name_from_folder(child.name)
                textures = [f for f in sorted(child.iterdir(), key=lambda p: p.name.lower()) if f.is_file() and f.suffix.lower() in self.VALID_TEXTURE_EXT]
                if textures:
                    variants.setdefault(key, []).extend(sorted(textures))

        if not variants:
            for f in sorted(material_dir.iterdir(), key=lambda p: p.name.lower()):
                if not f.is_file() or f.suffix.lower() not in self.VALID_TEXTURE_EXT:
                    continue
                key = self._variant_name_from_filename(f.name)
                variants.setdefault(key, []).append(f)

        return variants

    @staticmethod
    def _variant_name_from_folder(folder_name: str) -> str:
        normalized = folder_name.replace("-", "_")
        m = re.search(r"(\d+K)_(PNG|JPG|JPEG|TIF|TIFF|EXR)", normalized, re.IGNORECASE)
        if not m:
            m = re.search(r"(\d+K)[_\-]?(PNG|JPG|JPEG|TIF|TIFF|EXR)", normalized, re.IGNORECASE)
        if m:
            return f"{m.group(1).upper()}_{m.group(2).upper().replace('JPEG', 'JPG').replace('TIFF', 'TIF')}"
        return "SOURCE"

    @staticmethod
    def _variant_name_from_filename(filename: str) -> str:
        stem = Path(filename).stem.replace("-", "_")
        m = re.search(r"(\d+K)_(PNG|JPG|JPEG|TIF|TIFF|EXR)", stem, re.IGNORECASE)
        if m:
            return f"{m.group(1).upper()}_{m.group(2).upper().replace('JPEG', 'JPG').replace('TIFF', 'TIF')}"
        return "SOURCE"

    @staticmethod
    def _infer_format(files: List[Path]) -> str:
        if not files:
            return "UNKNOWN"
        ext = files[0].suffix.lower().replace(".", "").upper()
        return "JPG" if ext == "JPEG" else "TIF" if ext == "TIFF" else ext

    @staticmethod
    def _infer_resolution(variant_name: str, files: List[Path]) -> str:
        m = re.search(r"(\d+K)", variant_name, re.IGNORECASE)
        if m:
            return m.group(1).upper()
        if files:
            meta_tag = re.search(r"(1K|2K|4K|8K|16K)", files[0].name, re.IGNORECASE)
            if meta_tag:
                return meta_tag.group(1).upper()
        return "UNKNOWN"

    @staticmethod
    def _is_pbr_complete(coverage: set) -> bool:
        return {"albedo", "normal", "roughness"}.issubset(coverage)

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}


if __name__ == "__main__":
    ingestor = Ingestor()
    print(json.dumps(ingestor.run_full_ingestion(), indent=2))