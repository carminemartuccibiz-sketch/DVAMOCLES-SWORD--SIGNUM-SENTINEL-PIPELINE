"""
ingestor.py — DVAMOCLES SWORD™: SIGNUM SENTINEL
Version 2.1 — Fixed Variant Detection

Scans 01_RAW_ARCHIVE and produces one MaterialSet per material,
with variants correctly grouped (1K-JPG, 2K-PNG, etc.) as sub-units.

ARCHITECTURE (per REGOLE_GLOBALI):
  READ  → 01_RAW_ARCHIVE (never modified)
  WRITE → 03_PROCESSED/manifests/

SUPPORTED STRUCTURES:
  /Provider/Material/                  (flat: images directly in folder)
  /Provider/Material/Resolution/       (1-level: 4K/, 2K/, etc.)
  /Provider/Material/Resolution/Format (2-level: 4K/PNG/, 4K/JPG/)
  /Provider/Material/MatName_4K-PNG/   (AmbientCG style: variant in folder name)
"""

import re
import json
import uuid
import hashlib
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ── Configuration ─────────────────────────────────────────────────────────────

MIN_FILE_SIZE: int = 512

VALID_EXTENSIONS: set = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr"}

ASSET_EXTENSIONS: set = {".blend", ".sbsar", ".uasset", ".usdc", ".usdz",
                          ".tres", ".mtlx", ".glb", ".gltf"}

IGNORE_PATTERNS: list = [
    "thumb", "thumbnail", "preview", "icon", "_t.", "ds_store",
    "desktop.ini", "readme", "license",
]

_VARIANT_FOLDER_RE = re.compile(
    r'^.+[_\-](\d{1,2}[kK])[-_](JPG|PNG|TIFF?|EXR|WEBP)$',
    re.IGNORECASE,
)

_RES_ONLY_RE = re.compile(r'^\d{1,2}[kK]$')

_FORMAT_NAMES: set = {"jpg", "jpeg", "png", "tif", "tiff", "exr", "webp"}

_KNOWN_PROVIDERS: dict = {
    "quixel":     ("Quixel",      "QXL"),
    "megascans":  ("Quixel",      "QXL"),
    "poliigon":   ("Poliigon",    "POL"),
    "ambientcg":  ("AmbientCG",   "ACG"),
    "ambient_cg": ("AmbientCG",   "ACG"),
    "ambient cg": ("AmbientCG",   "ACG"),
    "cc0":        ("AmbientCG",   "ACG"),
    "cgtrader":   ("CGTrader",    "CGT"),
    "textures":   ("Textures.com","TCM"),
    "custom":     ("Custom",      "CUS"),
}

logger = logging.getLogger("sentinel.ingestor")


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class FileRecord:
    filename: str
    path: str
    extension: str
    file_size_bytes: int
    file_hash: str
    format_class: str = "unknown"
    source_type: str = "original"
    generated_from: list = field(default_factory=list)
    tool: str = ""
    process: str = ""
    lineage_confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "filename":           self.filename,
            "path":               self.path,
            "extension":          self.extension,
            "file_size_bytes":    self.file_size_bytes,
            "file_hash":          self.file_hash,
            "format_class":       self.format_class,
            "source_type":        self.source_type,
            "generated_from":     self.generated_from,
            "tool":               self.tool,
            "process":            self.process,
            "lineage_confidence": self.lineage_confidence,
        }


@dataclass
class Variant:
    variant_id: str
    resolution: str
    format: str
    files: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "variant_id": self.variant_id,
            "resolution": self.resolution,
            "format":     self.format,
            "files":      [f.to_dict() for f in self.files],
            "metadata":   self.metadata,
        }


@dataclass
class MaterialSet:
    id: str
    dva_id: str
    provider: str
    provider_code: str
    material_name: str
    folder_path: str
    variants: list = field(default_factory=list)
    asset_files: list = field(default_factory=list)
    extra_files: list = field(default_factory=list)
    category: str = ""
    scale: str = ""
    source: str = "unknown"
    custom_variants: list = field(default_factory=list)
    notes: str = ""
    has_process_data: bool = False
    process_pipeline: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "dva_id":           self.dva_id,
            "provider":         self.provider,
            "provider_code":    self.provider_code,
            "material_name":    self.material_name,
            "folder_path":      self.folder_path,
            "variants":         [v.to_dict() for v in self.variants],
            "asset_files":      self.asset_files,
            "extra_files":      self.extra_files,
            "category":         self.category,
            "scale":            self.scale,
            "source":           self.source,
            "custom_variants":  self.custom_variants,
            "notes":            self.notes,
            "has_process_data": self.has_process_data,
            "process_pipeline": self.process_pipeline,
        }


# ── Folder Classification ─────────────────────────────────────────────────────

def _classify_subfolder(name: str):
    """
    Returns (kind, resolution, format).
    kind = "variant_named" | "resolution" | "format" | "unknown"
    """
    m = _VARIANT_FOLDER_RE.match(name)
    if m:
        return "variant_named", m.group(1).upper(), m.group(2).upper()
    if _RES_ONLY_RE.match(name):
        return "resolution", name.upper(), ""
    if name.lower() in _FORMAT_NAMES:
        return "format", "", name.upper()
    return "unknown", "", ""


def _is_material_folder(folder: Path) -> bool:
    """True if folder contains PBR content (images or variant subfolders)."""
    for child in folder.iterdir():
        if child.is_file():
            if child.suffix.lower() in VALID_EXTENSIONS:
                if child.stat().st_size >= MIN_FILE_SIZE:
                    if not _is_ignored(child.name):
                        return True
        elif child.is_dir():
            kind, _, _ = _classify_subfolder(child.name)
            if kind in ("variant_named", "resolution"):
                return True
    return False


def _is_provider_folder(folder: Path, root: Path) -> bool:
    """True if folder is a depth-1 provider wrapper with no direct images."""
    try:
        depth = len(folder.relative_to(root).parts)
    except ValueError:
        return False
    if depth != 1:
        return False
    name_lower = folder.name.lower()
    for key in _KNOWN_PROVIDERS:
        if key in name_lower:
            return True
    # Unknown name at depth 1 with only subdirs and no images → wrapper
    has_images = any(
        c.is_file() and c.suffix.lower() in VALID_EXTENSIONS
        for c in folder.iterdir()
    )
    if has_images:
        return False
    all_dirs = all(c.is_dir() for c in folder.iterdir() if not c.name.startswith("."))
    return all_dirs


def _is_ignored(filename: str) -> bool:
    lower = filename.lower()
    return any(p in lower for p in IGNORE_PATTERNS)


# ── Provider Detection ────────────────────────────────────────────────────────

def _detect_provider(folder: Path, root: Path):
    try:
        parts = folder.relative_to(root).parts
    except ValueError:
        return "Unknown", "UNK"
    for part in parts[:-1]:
        lower = part.lower()
        for key, (name, code) in _KNOWN_PROVIDERS.items():
            if key in lower:
                return name, code
    if len(parts) >= 2:
        ancestor = parts[0]
        code = re.sub(r'[^A-Za-z]', '', ancestor)[:3].upper() or "GEN"
        return ancestor.title(), code
    return "Unknown", "UNK"


# ── File Helpers ──────────────────────────────────────────────────────────────

def _collect_image_files(folder: Path) -> list:
    result = []
    for f in folder.iterdir():
        if (f.is_file()
                and f.suffix.lower() in VALID_EXTENSIONS
                and f.stat().st_size >= MIN_FILE_SIZE
                and not _is_ignored(f.name)):
            result.append(f)
    return sorted(result)


def _build_file_record(path: Path, process_pipeline: list) -> FileRecord:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            h.update(fh.read(16384))
    except Exception:
        pass
    fr = FileRecord(
        filename=path.name,
        path=str(path),
        extension=path.suffix.lower(),
        file_size_bytes=path.stat().st_size,
        file_hash=h.hexdigest()[:16],
        format_class=path.suffix.lower().lstrip("."),
    )
    for entry in process_pipeline:
        if entry.get("output") == path.name:
            fr.source_type         = "generated"
            fr.generated_from      = entry.get("generated_from", [])
            fr.tool                = entry.get("tool", "")
            fr.process             = entry.get("process", "")
            fr.lineage_confidence  = entry.get("confidence", 0.9)
            break
    return fr


def _infer_format(files: list) -> str:
    exts = {f.suffix.lower() for f in files}
    if ".png"  in exts: return "PNG"
    if ".jpg"  in exts: return "JPG"
    if ".jpeg" in exts: return "JPG"
    if ".tif"  in exts: return "TIFF"
    if ".tiff" in exts: return "TIFF"
    if ".exr"  in exts: return "EXR"
    return "MIX"


def _infer_resolution(files: list, folder: Path) -> str:
    for f in files:
        m = re.search(r'[_\-](\d{1,2}[kK])[_\-\.]', f.stem + ".", re.IGNORECASE)
        if m:
            return m.group(1).upper()
        m = re.search(r'[_\-](4096|8192|2048|1024|512)[_\-\.]', f.stem + ".")
        if m:
            px = int(m.group(1))
            for thr, lbl in ((7681,"8K"),(3841,"4K"),(2049,"2K"),(1025,"1K")):
                if px >= thr: return lbl
    try:
        from PIL import Image
        with Image.open(files[0]) as img:
            px = max(img.size)
            for thr, lbl in ((7681,"8K"),(3841,"4K"),(2049,"2K"),(1025,"1K")):
                if px >= thr: return lbl
    except Exception:
        pass
    return "UNKNOWN"


# ── Variant Building ──────────────────────────────────────────────────────────

def _build_variants(folder: Path, dva_id: str, process_pipeline: list) -> list:
    """
    Detect and build Variant objects for a material folder.
    Priority: named variants > resolution subfolders > flat.
    """
    variants = []
    named_variants = []
    resolution_folders = []

    for child in sorted(folder.iterdir()):
        if not child.is_dir():
            continue
        kind, res, fmt = _classify_subfolder(child.name)
        if kind == "variant_named":
            named_variants.append((child, res, fmt))
        elif kind == "resolution":
            resolution_folders.append((child, res))

    # ── Case 1: AmbientCG named variants ─────────────────────────────────────
    if named_variants:
        for vfolder, res, fmt in named_variants:
            files = _collect_image_files(vfolder)
            if not files:
                continue
            v = Variant(
                variant_id=f"{dva_id}_{res}_{fmt}",
                resolution=res,
                format=fmt,
            )
            for fp in files:
                v.files.append(_build_file_record(fp, process_pipeline))
            variants.append(v)
        return variants

    # ── Case 2: Resolution subfolders ────────────────────────────────────────
    if resolution_folders:
        for res_folder, res in resolution_folders:
            fmt_subfolders = [
                c for c in res_folder.iterdir()
                if c.is_dir() and _classify_subfolder(c.name)[0] == "format"
            ]
            if fmt_subfolders:
                for fmt_folder in sorted(fmt_subfolders):
                    _, _, fmt = _classify_subfolder(fmt_folder.name)
                    files = _collect_image_files(fmt_folder)
                    if not files:
                        continue
                    v = Variant(
                        variant_id=f"{dva_id}_{res}_{fmt or 'UNK'}",
                        resolution=res,
                        format=fmt,
                    )
                    for fp in files:
                        v.files.append(_build_file_record(fp, process_pipeline))
                    variants.append(v)
            else:
                files = _collect_image_files(res_folder)
                if not files:
                    continue
                fmt = _infer_format(files)
                v = Variant(
                    variant_id=f"{dva_id}_{res}_{fmt}",
                    resolution=res,
                    format=fmt,
                )
                for fp in files:
                    v.files.append(_build_file_record(fp, process_pipeline))
                variants.append(v)
        return variants

    # ── Case 3: Flat structure ────────────────────────────────────────────────
    direct = _collect_image_files(folder)
    if direct:
        res = _infer_resolution(direct, folder)
        fmt = _infer_format(direct)
        v = Variant(
            variant_id=f"{dva_id}_{res}_{fmt}",
            resolution=res,
            format=fmt,
        )
        for fp in direct:
            v.files.append(_build_file_record(fp, process_pipeline))
        variants.append(v)

    return variants


# ── Sidecar Loaders ───────────────────────────────────────────────────────────

def _load_material_info(folder: Path, mat: MaterialSet):
    p = folder / "material_info.json"
    if not p.exists():
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if "material" in data:
            mat.material_name = re.sub(r'\s+', '_', data["material"].strip())
        mat.category        = data.get("category", mat.category)
        mat.scale           = data.get("scale", "")
        mat.source          = data.get("source", mat.source)
        mat.custom_variants = data.get("variants", [])
        mat.notes           = data.get("notes", "")
    except Exception as e:
        logger.warning(f"material_info.json error ({folder.name}): {e}")


def _load_process_json(folder: Path, mat: MaterialSet):
    p = folder / "process.json"
    if not p.exists():
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        mat.has_process_data = True
        mat.process_pipeline = data.get("pipeline", [])
        if "source" in data:
            mat.source = data["source"]
    except Exception as e:
        logger.warning(f"process.json error ({folder.name}): {e}")


# ── Ingestor ──────────────────────────────────────────────────────────────────

class Ingestor:
    """
    Scans 01_RAW_ARCHIVE.
    Returns one MaterialSet per physical material, variants properly grouped.

    Usage:
        result = Ingestor("./01_RAW_ARCHIVE").scan()
    """

    def __init__(self, root_path: str, min_file_size: int = MIN_FILE_SIZE):
        self.root = Path(root_path)
        self.min_file_size = min_file_size
        self._materials: list = []

    def scan(self) -> dict:
        if not self.root.exists():
            raise FileNotFoundError(f"Root not found: {self.root}")
        logger.info(f"Ingestor v2.1 scanning: {self.root}")
        self._materials = []

        material_folders = self._discover_material_folders()
        logger.info(f"Ingestor: {len(material_folders)} material folder(s)")

        for folder in sorted(material_folders):
            mat = self._process_folder(folder)
            if mat:
                self._materials.append(mat)
                logger.info(f"  [{mat.provider_code}] {mat.material_name} → {len(mat.variants)} variant(s)")

        logger.info(f"Ingestor: {len(self._materials)} MaterialSet(s) built")
        return self._build_output()

    def get_materials(self) -> list:
        return self._materials

    def save_manifest(self, output_path: str) -> str:
        out = self._build_output()
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, indent=2, ensure_ascii=False))
        logger.info(f"Manifest saved → {output_path}")
        return output_path

    def summary(self) -> dict:
        return self._build_output()["summary"]

    # ── Discovery ─────────────────────────────────────────────────────────────

    def _discover_material_folders(self) -> list:
        """
        Walk root BFS. Identify material folders.
        Claim variant subfolders so they are not treated as separate materials.
        """
        candidates = []
        claimed: set = set()

        queue = [self.root]
        while queue:
            current = queue.pop(0)

            # Skip claimed folders (they are variants owned by a parent)
            if current in claimed:
                continue

            # Skip provider wrappers at depth 1
            if current != self.root and _is_provider_folder(current, self.root):
                # Enqueue children (material folders inside provider)
                for child in sorted(current.iterdir()):
                    if child.is_dir():
                        queue.append(child)
                continue

            # Skip folders that look like variants themselves
            kind, _, _ = _classify_subfolder(current.name)
            if kind in ("variant_named", "resolution", "format") and current != self.root:
                continue

            # Check if this is a material
            if current != self.root and _is_material_folder(current):
                candidates.append(current)
                # Claim all direct and grandchild dirs (variant subfolders)
                for child in current.iterdir():
                    if child.is_dir():
                        claimed.add(child)
                        for grandchild in child.iterdir():
                            if grandchild.is_dir():
                                claimed.add(grandchild)
                continue

            # Not a material yet — keep walking
            for child in sorted(current.iterdir()):
                if child.is_dir() and child not in claimed:
                    queue.append(child)

        return candidates

    # ── Material Processing ───────────────────────────────────────────────────

    def _process_folder(self, folder: Path) -> Optional[MaterialSet]:
        provider, provider_code = _detect_provider(folder, self.root)
        raw_name  = folder.name.strip()
        mat_name  = re.sub(r'\s+', '_', raw_name)

        uid    = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(folder.resolve())))
        dva_id = f"DVA_{provider_code}_{mat_name}"

        mat = MaterialSet(
            id=uid,
            dva_id=dva_id,
            provider=provider,
            provider_code=provider_code,
            material_name=mat_name,
            folder_path=str(folder),
            source=provider.lower(),
        )

        _load_material_info(folder, mat)
        _load_process_json(folder, mat)

        mat.variants = _build_variants(folder, dva_id, mat.process_pipeline)

        if not mat.variants:
            return None

        # Collect non-image files
        for child in folder.rglob("*"):
            if child.is_file():
                ext = child.suffix.lower()
                if ext in ASSET_EXTENSIONS:
                    mat.asset_files.append(str(child))
                elif ext not in VALID_EXTENSIONS and not _is_ignored(child.name):
                    mat.extra_files.append(str(child))

        return mat

    # ── Output ────────────────────────────────────────────────────────────────

    def _build_output(self) -> dict:
        mats = [m.to_dict() for m in self._materials]
        total_files = sum(len(v["files"]) for m in mats for v in m["variants"])
        return {
            "materials": mats,
            "summary": {
                "total_materials":   len(mats),
                "total_files":       total_files,
                "providers":         sorted({m["provider"] for m in mats}),
                "resolutions_found": sorted({v["resolution"] for m in mats for v in m["variants"]}),
            },
        }


# ── Main Test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, os

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)-22s] %(levelname)s %(message)s",
    )

    root = sys.argv[1] if len(sys.argv) > 1 else "./01_RAW_ARCHIVE"

    if not os.path.exists(root):
        print(f"Path not found: {root}")
        sys.exit(1)

    ingestor = Ingestor(root_path=root)
    result   = ingestor.scan()
    summary  = result["summary"]

    print()
    print("=" * 60)
    print("INGESTOR v2.1 — SCAN SUMMARY")
    print("=" * 60)
    print(f"  Materials found   : {summary['total_materials']}")
    print(f"  Total files       : {summary['total_files']}")
    print(f"  Providers         : {', '.join(summary['providers']) or 'none'}")
    print(f"  Resolutions found : {', '.join(summary['resolutions_found']) or 'none'}")
    print()

    for mat in result["materials"]:
        tag = " (process.json)" if mat["has_process_data"] else ""
        print(f"  [{mat['provider_code']}] {mat['material_name']}{tag}")
        for v in mat["variants"]:
            gen = sum(1 for f in v["files"] if f["source_type"] == "generated")
            g = f"  [{gen} generated]" if gen else ""
            print(f"    {v['resolution']}-{v['format']}: {len(v['files'])} files{g}")
        if mat["asset_files"]:
            print(f"    Asset files: {len(mat['asset_files'])}")
    print("=" * 60)
