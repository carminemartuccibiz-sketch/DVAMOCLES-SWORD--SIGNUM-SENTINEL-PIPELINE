import json
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

logger = logging.getLogger("SIGNUM_SENTINEL.METADATA_EXTRACTOR")

class MetadataExtractor:
    """Analizzatore forense texture (ExifTool + OpenCV fallback)."""

    def __init__(self):
        self.exiftool_path = shutil.which("exiftool")
        if not self.exiftool_path:
            logger.warning("ExifTool non trovato nel PATH. Fallback OpenCV in uso.")

    def extract_all(self, file_path: Path) -> Dict[str, Any]:
        if not file_path.exists(): return {}

        raw_metadata = self._get_exiftool_data(file_path)
        
        return {
            "file_info": {
                "name": file_path.name,
                "extension": file_path.suffix.lower(),
                "size_bytes": file_path.stat().st_size
            },
            "image_specs": self._parse_technical_specs(file_path, raw_metadata),
            "software_origin": self._detect_software(raw_metadata),
            "metadata_raw": raw_metadata or {},
        }

    def _get_exiftool_data(self, file_path: Path) -> Optional[Dict]:
        if not self.exiftool_path: return None
        try:
            res = subprocess.run([self.exiftool_path, "-j", "-G", str(file_path)], capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            return data[0] if data else None
        except Exception:
            return None

    def _parse_technical_specs(self, file_path: Path, raw: Optional[Dict]) -> Dict[str, Any]:
        specs = {"width": 0, "height": 0, "bit_depth": "Unknown", "color_space": "Unknown", "channels": 0}

        # Dati da EXIF
        if raw:
            specs["width"] = raw.get("File:ImageWidth", 0)
            specs["height"] = raw.get("File:ImageHeight", 0)
            bd = raw.get("EXIF:BitsPerSample") or raw.get("PNG:BitDepth")
            if bd: specs["bit_depth"] = f"{bd}-bit"
            profile = raw.get("ICC_Profile:ProfileDescription") or raw.get("EXIF:ColorSpace")
            if profile: specs["color_space"] = str(profile)
            chan = raw.get("Composite:ImageSize")
            if chan and isinstance(chan, str) and "x" in chan:
                specs["channels"] = 3

        # Fallback Fisico con OpenCV
        if specs["width"] == 0 and HAS_CV2:
            try:
                img = cv2.imread(str(file_path), cv2.IMREAD_UNCHANGED)
                if img is not None:
                    h, w = img.shape[:2]
                    specs["width"], specs["height"] = w, h
                    specs["channels"] = img.shape[2] if len(img.shape) > 2 else 1
                    dtype = str(img.dtype)
                    specs["bit_depth"] = "8-bit" if "uint8" in dtype else "16-bit" if "uint16" in dtype else "32-bit float"
                    if specs["color_space"] == "Unknown":
                        specs["color_space"] = "sRGB" if specs["channels"] >= 3 else "Linear"
            except Exception: pass

        return specs

    def _detect_software(self, raw: Optional[Dict]) -> str:
        if not raw: return "Unknown"
        
        fields = [raw.get("EXIF:Software"), raw.get("PNG:Software"), raw.get("XMP:CreatorTool")]
        full_string = " ".join([str(f) for f in fields if f]).lower()

        if "substance designer" in full_string: return "Substance Designer"
        if "substance painter" in full_string: return "Substance Painter"
        if "adobe photoshop" in full_string: return "Adobe Photoshop"
        if "blender" in full_string: return "Blender / Cycles"
        if "zbrush" in full_string: return "ZBrush"
        if "materialize" in full_string: return "Materialize"
        
        return "Generic / Unknown"

    def enrich_material_sets(self, material_sets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Applica metadata extraction all'output dell'ingestor:
        MaterialSet -> variants -> files[*].specs
        """
        for material in material_sets:
            for variant in material.get("variants", []):
                for file_record in variant.get("files", []):
                    fp = Path(file_record.get("path", ""))
                    if not fp.exists():
                        continue
                    meta = self.extract_all(fp)
                    file_record["specs"] = meta.get("image_specs", {})
                    file_record["software_origin"] = meta.get("software_origin", "Unknown")
                    file_record["size_bytes"] = meta.get("file_info", {}).get("size_bytes", 0)
        return material_sets