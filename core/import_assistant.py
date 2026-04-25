import gc
import json
import logging
import os
import re
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from PIL import Image

from core.asset_parser import UniversalParser
from core.metadata_extractor import MetadataExtractor
from core.naming_intelligence import NamingIntelligence
from core.process_parser import ProcessDescriptionParser

try:
    import cv2
    import numpy as np

    HAS_CV = True
except ImportError:
    HAS_CV = False

try:
    import torch
    from transformers import BlipForConditionalGeneration, BlipProcessor

    HAS_AI_LIBS = True
except ImportError:
    torch = None  # type: ignore
    HAS_AI_LIBS = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SIGNUM_SENTINEL.ADV_IMPORTER")


class AdvancedImporter:
    """
    Orchestratore SIGNUM SENTINEL (Advanced Importer Assistant):
    ponte tra file system, KB JSON, metadati fisici e (opzionale) visione AI.
    Flusso auto_detect: metadati → validazione pixel (OpenCV) → NID (KB) → caption BLIP.
    """

    VALID_TEXTURE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".tga"}
    VALID_SIDECAR_EXT = {".mtlx", ".tres", ".usdc", ".blend", ".uasset"}

    def __init__(self, root_dir: Union[str, Path] = None):
        self.root = Path(root_dir) if root_dir else Path.cwd()
        self.raw_dir = self.root / "01_RAW_ARCHIVE"
        self.custom_dir = self.root / "02_CUSTOM"
        self.manifest_dir = self.root / "06_KNOWLEDGE_BASE" / "Manifests"
        self.kb_path = self.root / "06_KNOWLEDGE_BASE" / "mappings" / "naming_map.json"
        self.learning_path = self.root / "06_KNOWLEDGE_BASE" / "patterns" / "import_learning.json"
        self.ui_prefs_path = self.root / "config" / "ui_prefs.json"

        self.naming = NamingIntelligence(str(self.kb_path))
        self.metadata = MetadataExtractor()
        self.process_parser = ProcessDescriptionParser()
        self._universal_parser = UniversalParser(str(self.kb_path))

        self.ai_model = None
        self.ai_processor = None
        self.device = "cuda" if HAS_AI_LIBS and torch is not None and torch.cuda.is_available() else "cpu"
        self.vault_file_index = set()
        self._processed_counter = 0

        self.ui_prefs = self._load_json(self.ui_prefs_path, {"providers": [], "formats": [], "resolutions": [], "map_types": []})

    # ----------------------- AI lifecycle -----------------------
    def load_ai(self):
        if not HAS_AI_LIBS or self.ai_model is not None:
            return
        try:
            logger.info("Loading BLIP on %s", self.device)
            self.ai_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            self.ai_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
        except Exception:
            logger.exception("AI loading failed")

    def unload_ai(self):
        if self.ai_model is None:
            return
        try:
            del self.ai_model
            del self.ai_processor
            self.ai_model = None
            self.ai_processor = None
            gc.collect()
            if HAS_AI_LIBS and torch is not None and torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            logger.exception("AI unload failed")

    @contextmanager
    def ai_inference_scope(self):
        try:
            yield
        finally:
            self._processed_counter += 1
            if HAS_AI_LIBS and torch is not None and torch.cuda.is_available() and self._processed_counter % 20 == 0:
                torch.cuda.empty_cache()
            gc.collect()

    # ----------------------- Entry unification -----------------------
    def ingest_paths(self, paths: List[str], max_depth: int = 3) -> Dict[str, Any]:
        """Common entry per drag&drop / browser: scan con profondità limitata + build progetto."""
        staged_files = self.collect_staging_file_paths(paths, max_depth=max_depth)
        return self.build_staging_project(staged_files)

    def collect_staging_file_paths(self, paths: List[str], max_depth: int = 3) -> List[Path]:
        """
        Scan ricorsivo con limite profondità (cartelle sotto la root di drop).
        max_depth = numero massimo di segmenti relativi (cartelle) sotto la root.
        """
        exts = self.VALID_TEXTURE_EXT | self.VALID_SIDECAR_EXT
        out: List[Path] = []
        for p_str in paths:
            root = Path(p_str)
            if not root.exists():
                continue
            if root.is_file():
                if root.suffix.lower() in exts:
                    out.append(root)
                continue
            if not root.is_dir():
                continue
            try:
                root_resolved = root.resolve()
            except OSError:
                root_resolved = root
            for f in root.rglob("*"):
                if not f.is_file() or f.suffix.lower() not in exts:
                    continue
                try:
                    rel = f.relative_to(root_resolved)
                except ValueError:
                    rel = f.relative_to(root)
                folder_depth = len(rel.parts) - 1
                if folder_depth > max_depth:
                    continue
                out.append(f)
        return out

    def _collect_files(self, paths: List[str]) -> List[Path]:
        """Alias senza limite (uso interno legacy)."""
        return self.collect_staging_file_paths(paths, max_depth=32)

    def build_staging_project(self, files: List[Path]) -> Dict[str, Any]:
        """
        Auto detect:
        Material -> Variants -> Maps
        """
        self._sync_mtlx_kb_from_file_list(files)
        project: Dict[str, Any] = {}
        for file_path in files:
            material_name, variant = self._extract_material_and_variant(file_path)
            material = project.setdefault(
                material_name,
                {
                    "provider": self._detect_provider_hint(file_path),
                    "asset_type": "RAW",
                    "tags": [],
                    "desc": "",
                    "process_description": "",
                    "relationships": [],
                    "folders": {},
                },
            )
            variant_folder = material["folders"].setdefault(
                variant,
                {"is_custom": False, "files": [], "variant_tags": self._variant_folder_tags(variant)},
            )
            record = self.auto_detect_file(str(file_path), provider=material["provider"])
            variant_folder["files"].append(record)
        return project

    def _sync_mtlx_kb_from_file_list(self, files: List[Path]) -> None:
        """Trova .mtlx nelle directory coinvolte e aggiorna naming_map.json via UniversalParser."""
        seen_dirs: set[Path] = set()
        for fp in files:
            for parent in [fp.parent, fp.parent.parent]:
                if parent in seen_dirs:
                    continue
                seen_dirs.add(parent)
                for mtlx in parent.glob("*.mtlx"):
                    try:
                        self._universal_parser.parse_file(mtlx)
                    except Exception:
                        logger.exception("MTLX ingest fallito: %s", mtlx)
        self.naming.reload_kb()

    def parse_mtlx(self, folder_path: Path) -> Dict[str, str]:
        """Parser MaterialX: aggiorna KB e ritorna filename -> tipo mappa (UPPER)."""
        merged: Dict[str, str] = {}
        folder_path = Path(folder_path)
        if not folder_path.is_dir():
            return merged
        for mtlx in folder_path.glob("*.mtlx"):
            merged.update(self._universal_parser.parse_file(mtlx))
        self.naming.reload_kb()
        return merged

    def visual_check(self, path: Path) -> tuple[str, float]:
        """
        OpenCV: firma cromatica NORMAL (R,G ~128, B alto) vs GRAYSCALE (canali allineati).
        Ritorna (etichetta, confidence 0..1).
        """
        if not HAS_CV:
            return "Unknown", 0.0
        try:
            img = cv2.imread(str(path))
            if img is None:
                return "Unknown", 0.0
            b, g, r = cv2.split(img)
            if np.allclose(r, g, atol=10) and np.allclose(g, b, atol=10):
                return "GRAYSCALE", 0.88
            mean_bgr = cv2.mean(img)[:3]
            if 110 < mean_bgr[2] < 150 and 110 < mean_bgr[1] < 150 and mean_bgr[0] > 180:
                return "NORMAL", 0.95
            return "COLOR", 0.75
        except Exception:
            logger.exception("visual_check fallito: %s", path)
            return "Unknown", 0.0

    def ai_describe(self, path: Path) -> str:
        """BLIP: didascalia tecnica materiale (lazy load su load_ai)."""
        if not HAS_AI_LIBS or self.ai_model is None or self.ai_processor is None:
            return ""
        try:
            with self.ai_inference_scope():
                with Image.open(path) as pil_img:
                    raw_image = pil_img.convert("RGB")
                    inputs = self.ai_processor(
                        raw_image, "a technical PBR material texture showing", return_tensors="pt"
                    ).to(self.device)
                    ctx = torch.no_grad() if torch is not None else _NoopContext()
                    with ctx:
                        out = self.ai_model.generate(**inputs)
                return self.ai_processor.decode(out[0], skip_special_tokens=True).capitalize()
        except Exception:
            logger.exception("ai_describe fallito: %s", path)
            return ""

    # ----------------------- Detection helpers -----------------------
    @staticmethod
    def _variant_folder_tags(variant_key: str) -> List[str]:
        if variant_key in ("SOURCE", "unknown"):
            return []
        parts = variant_key.split("_", 1)
        tags: List[str] = []
        if len(parts) >= 1 and re.match(r"^\d+K$", parts[0], re.I):
            tags.append(parts[0].upper())
        if len(parts) >= 2:
            tags.append(parts[1].upper().replace("JPEG", "JPG").replace("TIFF", "TIF"))
        return tags

    def _extract_material_and_variant(self, file_path: Path) -> tuple[str, str]:
        """
        Root = materiale (es. Roccia_555); Texture Set = cartella variante (es. 1K_PNG o Roccia_555_1K_PNG).
        """
        parents = list(file_path.parents)
        variant = "SOURCE"
        material_name = file_path.parent.name

        def parse_variant_token(token: str) -> tuple[str | None, str | None]:
            t = token.replace("-", "_")
            m = re.search(r"(.+?)_(\d+K)_(PNG|JPG|JPEG|TIF|TIFF|EXR)$", t, re.IGNORECASE)
            if m:
                return m.group(1), f"{m.group(2).upper()}_{m.group(3).upper().replace('JPEG', 'JPG').replace('TIFF', 'TIF')}"
            m2 = re.match(r"^(\d+K)_(PNG|JPG|JPEG|TIF|TIFF|EXR)$", t, re.IGNORECASE)
            if m2:
                return None, f"{m2.group(1).upper()}_{m2.group(2).upper().replace('JPEG', 'JPG').replace('TIFF', 'TIF')}"
            return None, None

        for par in parents[:5]:
            mat_candidate, var_candidate = parse_variant_token(par.name)
            if var_candidate:
                variant = var_candidate
                if mat_candidate:
                    material_name = mat_candidate
                elif par.parent.name:
                    material_name = par.parent.name
                break
        else:
            m2 = re.search(
                r"(.+?)[_\- ](\d+K)[_\- ](PNG|JPG|JPEG|TIF|TIFF|EXR)", file_path.stem, re.IGNORECASE
            )
            if m2:
                material_name = m2.group(1)
                variant = f"{m2.group(2).upper()}_{m2.group(3).upper().replace('JPEG', 'JPG').replace('TIFF', 'TIF')}"

        material_name = re.sub(r"[_\s]+", "_", material_name).strip("_")
        return material_name or "UnknownMaterial", variant

    @staticmethod
    def _detect_provider_hint(path: Path) -> str:
        parts = [p.lower() for p in path.parts]
        if any("ambient" in p and "cg" in p for p in parts):
            return "AmbientCG"
        if any("quixel" in p or "megascans" in p for p in parts):
            return "Quixel"
        if any("poliigon" in p for p in parts):
            return "Poliigon"
        return "UnknownProvider"

    def auto_detect_file(self, file_path: str, provider: str = "Generic") -> Dict[str, Any]:
        """
        Decision matrix (4 step):
        1) Metadati fisici (ExifTool/OpenCV + Pillow)
        2) Validazione visiva OpenCV
        3) NID da naming_map.json
        4) Arricchimento BLIP (se load_ai attivo e texture a colori)
        """
        p = Path(file_path)
        result: Dict[str, Any] = {
            "name": p.name,
            "path": str(p),
            "provider_hint": provider,
            "format": p.suffix.lower().replace(".", "").upper(),
            "map_type": "unknown",
            "naming_confidence": 0.0,
            "resolution": "UNKNOWN",
            "tech_res": "Unknown",
            "bit_depth": "Unknown",
            "color_space": "Unknown",
            "is_duplicate": False,
            "derived_from": [],
            "source_raw": "",
            "process": "",
            "tool": "",
            "ai_description": "",
            "visual_validation": "Unknown",
            "visual_confidence": 0.0,
            "metadata_confidence": 0.0,
        }

        if p.suffix.lower() not in self.VALID_TEXTURE_EXT:
            result["map_type"] = "auxiliary"
            logger.info("[auto_detect] %s -> auxiliary (non texture)", p.name)
            return result

        # Step 1 — Metadati
        meta_conf = 0.55
        try:
            with Image.open(p) as img:
                w, h = img.width, img.height
                result["tech_res"] = f"{w}x{h}"
                result["resolution"] = self._derive_resolution_label(w, h)
                meta_conf = 0.85
        except Exception:
            logger.debug("Pillow quick read fallito per %s", p.name)

        meta = self.metadata.extract_all(p)
        specs = meta.get("image_specs", {})
        if specs.get("width"):
            result["tech_res"] = f"{specs.get('width', 0)}x{specs.get('height', 0)}"
            result["bit_depth"] = specs.get("bit_depth", "Unknown")
            result["color_space"] = specs.get("color_space", "Unknown")
            result["resolution"] = self._derive_resolution_label(
                int(specs.get("width", 0) or 0), int(specs.get("height", 0) or 0)
            )
            meta_conf = max(meta_conf, 0.92)
        result["metadata_confidence"] = meta_conf
        logger.info(
            "[auto_detect] step1 metadata %s res=%s bit=%s conf=%.2f",
            p.name,
            result["tech_res"],
            result["bit_depth"],
            meta_conf,
        )

        # Step 2 — Pixel / OpenCV
        vis_label, vis_conf = self.visual_check(p)
        result["visual_validation"] = vis_label
        result["visual_confidence"] = vis_conf
        logger.info("[auto_detect] step2 visual %s -> %s conf=%.2f", p.name, vis_label, vis_conf)

        # Step 3 — Naming Intelligence (KB)
        detected = self.naming.classify_filename(p.name)
        result["map_type"] = detected.map_type
        result["naming_confidence"] = detected.confidence
        if detected.convention:
            result["map_type"] = f"{detected.map_type}_{detected.convention.lower()}"
        logger.info(
            "[auto_detect] step3 naming %s -> %s conf=%.2f (%s)",
            p.name,
            result["map_type"],
            detected.confidence,
            detected.source,
        )
        if vis_label == "NORMAL" and str(result["map_type"]).lower().startswith("albedo"):
            logger.warning(
                "[auto_detect] mismatch %s: visual NORMAL vs map_type albedo — verificare naming.",
                p.name,
            )

        # Step 4 — BLIP
        if self.ai_model is not None and vis_label == "COLOR":
            cap = self.ai_describe(p)
            result["ai_description"] = cap
            logger.info("[auto_detect] step4 BLIP %s caption_len=%s", p.name, len(cap))

        fingerprint = f"{p.name.lower()}_{result['tech_res']}"
        result["is_duplicate"] = fingerprint in self.vault_file_index

        return result

    @staticmethod
    def _derive_resolution_label(width: int, height: int) -> str:
        mx = max(width, height)
        if mx >= 7600:
            return "8K"
        if mx >= 3800:
            return "4K"
        if mx >= 1900:
            return "2K"
        if mx >= 900:
            return "1K"
        return "UNKNOWN"

    # ----------------------- Import execution -----------------------
    def run_import(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        User-controlled import.
        Expects optional manual override fields per material:
        provider, asset_type, tags, process_description, relationships.
        """
        summary = {"status": "success", "processed_materials": 0, "processed_files": 0, "skipped_files": 0, "errors": []}

        for material_name, material_data in project_data.items():
            provider = material_data.get("provider", "UnknownProvider")
            asset_type = str(material_data.get("asset_type", "RAW")).upper()
            dest_root = self.raw_dir if asset_type == "RAW" else self.custom_dir
            dest_dir = dest_root / provider / material_name
            dest_dir.mkdir(parents=True, exist_ok=True)

            variants_payload: Dict[str, Any] = {}
            all_files_for_info: List[Dict[str, Any]] = []
            relationships = material_data.get("relationships", [])

            for variant_name, folder_data in material_data.get("folders", {}).items():
                variant_dir = dest_dir / "variants" / variant_name
                variant_dir.mkdir(parents=True, exist_ok=True)
                copied = []
                for file_obj in folder_data.get("files", []):
                    src = Path(file_obj.get("path", ""))
                    if not src.exists():
                        summary["skipped_files"] += 1
                        continue
                    try:
                        dst = variant_dir / src.name
                        if src.resolve() != dst.resolve():
                            shutil.copy2(src, dst)
                        rec = dict(file_obj)
                        rec["path"] = str(dst)
                        copied.append(rec)
                        all_files_for_info.append(rec)
                        summary["processed_files"] += 1
                    except Exception as exc:
                        summary["errors"].append(f"{material_name}/{src.name}: {exc}")
                variants_payload[variant_name] = {"file_count": len(copied), "files": copied}

            process_description = material_data.get("process_description", "")
            process_payload = self._build_process_payload(
                material_name=material_name,
                provider=provider,
                asset_type=asset_type,
                process_description=process_description,
                relationships=relationships,
                files=all_files_for_info,
            )
            material_info_payload = {
                "identity": {
                    "material_name": material_name,
                    "provider": provider,
                    "asset_type": asset_type,
                    "source": "GUI_IMPORT",
                    "url": material_data.get("url", ""),
                    "technique": material_data.get("technique", ""),
                },
                "description": material_data.get("desc", ""),
                "tags": material_data.get("tags", []),
                "variants": variants_payload,
            }

            self._atomic_save_json(dest_dir / "process.json", process_payload)
            self._atomic_save_json(dest_dir / "material_info.json", material_info_payload)
            self._learn_from_import(provider, material_name, list(variants_payload.keys()), all_files_for_info)
            summary["processed_materials"] += 1
            logger.info("Imported material %s to %s", material_name, dest_dir)

        if summary["errors"]:
            summary["status"] = "partial_success"
        return summary

    def _build_process_payload(
        self,
        material_name: str,
        provider: str,
        asset_type: str,
        process_description: str,
        relationships: List[Dict[str, Any]],
        files: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "material_name": material_name,
            "provider": provider,
            "asset_type": asset_type,
            "pipeline": [],
            "relationships": [],
        }
        if asset_type == "RAW":
            payload["pipeline"].append({"process": "raw_import", "tool": "filesystem", "generated_from": [], "confidence": 1.0})
            return payload

        by_name = {f["name"]: f for f in files}
        if relationships:
            for rel in relationships:
                # expected: output, derived_from[], process, tool
                entry = {
                    "output": rel.get("output", ""),
                    "derived_from": rel.get("derived_from", []),
                    "process": rel.get("process", "custom_transform"),
                    "tool": rel.get("tool", "unknown"),
                    "confidence": rel.get("confidence", 0.9),
                }
                payload["relationships"].append(entry)
                payload["pipeline"].append(entry)
                out_name = entry["output"]
                if out_name in by_name:
                    by_name[out_name]["derived_from"] = entry["derived_from"]
                    by_name[out_name]["process"] = entry["process"]
                    by_name[out_name]["tool"] = entry["tool"]
        elif process_description:
            for f in files:
                parsed = self.process_parser.parse(process_description, output_name=f.get("name", ""))
                payload["pipeline"].append(parsed)
        else:
            payload["pipeline"].append({"process": "custom_import", "tool": "manual", "generated_from": [], "confidence": 0.5})
        return payload

    # ----------------------- Legacy helpers -----------------------
    def load_existing_vault(self) -> Dict[str, Any]:
        vault = {}
        self.vault_file_index.clear()
        if not self.manifest_dir.exists():
            return vault
        for man_file in self.manifest_dir.glob("*_manifest.json"):
            try:
                with open(man_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                mat_name = d.get("identity", {}).get("material_name")
                if not mat_name:
                    continue
                vault[mat_name] = {
                    "provider": d.get("identity", {}).get("provider", "Unknown"),
                    "tags": d.get("tags", []),
                    "desc": d.get("description", ""),
                    "url": d.get("identity", {}).get("url", ""),
                    "technique": d.get("identity", {}).get("technique", ""),
                    "folders": {},
                }
                for cat in ["RAW", "CUSTOM"]:
                    for fldr, f_data in d.get("hierarchy", {}).get(cat, {}).items():
                        vault[mat_name]["folders"][fldr] = {"is_custom": cat == "CUSTOM", "files": f_data.get("files", [])}
                        for f_obj in f_data.get("files", []):
                            self.vault_file_index.add(f"{f_obj.get('name', '').lower()}_{f_obj.get('tech_res', '')}")
            except Exception:
                logger.exception("Error loading vault manifest %s", man_file)
        return vault

    def normalize_raw_to_custom(self, source_dir: Optional[Path] = None, target_provider: str = "Normalized") -> Dict[str, Any]:
        src_root = source_dir or self.raw_dir
        out_root = self.custom_dir / target_provider
        out_root.mkdir(parents=True, exist_ok=True)
        stats = {"normalized": 0, "skipped": 0, "errors": []}

        for provider_dir in src_root.iterdir():
            if not provider_dir.is_dir():
                continue
            for material_dir in provider_dir.iterdir():
                if not material_dir.is_dir():
                    continue
                dest_mat = out_root / material_dir.name / "variants" / "SOURCE"
                dest_mat.mkdir(parents=True, exist_ok=True)
                for img_path in material_dir.rglob("*"):
                    if not img_path.is_file() or img_path.suffix.lower() not in self.VALID_TEXTURE_EXT:
                        continue
                    try:
                        map_type = self.naming.classify_filename(img_path.name).map_type
                        normalized_name = f"{material_dir.name}_{map_type}.png"
                        out_path = dest_mat / normalized_name
                        with Image.open(img_path) as img:
                            img.convert("RGB").save(out_path, format="PNG")
                        stats["normalized"] += 1
                    except Exception as exc:
                        stats["errors"].append(f"{img_path}: {exc}")
                        stats["skipped"] += 1
        return stats

    # ----------------------- JSON + KB persistence -----------------------
    def _load_json(self, path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return default

    def _atomic_save_json(self, path: Path, data: Dict[str, Any]):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp, path)

    def _learn_from_import(self, provider: str, material_name: str, variants: List[str], files: List[Dict[str, Any]]):
        learning = self._load_json(self.learning_path, {"providers": {}, "variant_patterns": {}, "map_suffixes": {}})
        provider_info = learning["providers"].setdefault(provider, {"materials": 0})
        provider_info["materials"] += 1

        for variant in variants:
            learning["variant_patterns"][variant] = learning["variant_patterns"].get(variant, 0) + 1

        for f in files:
            name = f.get("name", "")
            map_type = str(f.get("map_type", "unknown")).lower()
            suffix = Path(name).stem.split("_")[-1].lower() if name else ""
            if map_type != "unknown" and suffix:
                learning["map_suffixes"].setdefault(map_type, {})
                learning["map_suffixes"][map_type][suffix] = learning["map_suffixes"][map_type].get(suffix, 0) + 1

        self._atomic_save_json(self.learning_path, learning)


class _NoopContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False