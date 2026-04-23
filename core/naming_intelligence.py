import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("SIGNUM_SENTINEL.NAMING_INTELLIGENCE")
logger.setLevel(logging.INFO)

@dataclass
class TextureIdentity:
    filename: str
    map_type: str = "unknown"
    confidence: float = 0.0
    convention: Optional[str] = None
    is_packed: bool = False
    packed_channels: Dict[str, str] = field(default_factory=dict)
    method: str = "regex"

class NamingIntelligence:
    # Pattern aggiornati per conformità stretta a Python 3.11+
    MAP_PATTERNS = {
        "albedo": [r"(?i)(_albedo|_basecolor|_bc|_color|_diffuse|_diff|_col)"],
        "normal": [r"(?i)(_normal|_nrm|_nor|_ndx|_nogl|_n)"],
        "roughness": [r"(?i)(_roughness|_rough|_rgh|_r)"],
        "metallic": [r"(?i)(_metallic|_metal|_metalness|_met|_m)"],
        "ambient_occlusion": [r"(?i)(_ambientocclusion|_ao|_occlusion)"],
        "height": [r"(?i)(_height|_displacement|_disp|_h)"],
        "opacity": [r"(?i)(_opacity|_alpha|_mask|_op)"],
        "specular": [r"(?i)(_specular|_spec|_spc)"],
        "glossiness": [r"(?i)(_glossiness|_gloss|_gls)"]
    }

    PACKED_PATTERNS = {
        "orm": {"regex": r"(?i)_orm", "channels": {"R": "ambient_occlusion", "G": "roughness", "B": "metallic"}},
        "arm": {"regex": r"(?i)_arm", "channels": {"R": "ambient_occlusion", "G": "roughness", "B": "metallic"}},
        "rma": {"regex": r"(?i)_rma", "channels": {"R": "roughness", "G": "metallic", "B": "ambient_occlusion"}}
    }

    @classmethod
    def classify_filename(cls, filename: str) -> TextureIdentity:
        identity = TextureIdentity(filename=filename)
        
        for pack_name, pack_data in cls.PACKED_PATTERNS.items():
            if re.search(pack_data["regex"], filename):
                identity.map_type = f"packed_{pack_name}"
                identity.confidence = 0.95
                identity.is_packed = True
                identity.packed_channels = pack_data["channels"]
                return identity

        best_match = "unknown"
        highest_conf = 0.0

        for map_type, patterns in cls.MAP_PATTERNS.items():
            for i, pattern in enumerate(patterns):
                if re.search(pattern, filename):
                    conf = 0.9 - (i * 0.05)
                    if conf > highest_conf:
                        highest_conf = conf
                        best_match = map_type
        
        identity.map_type = best_match
        identity.confidence = max(highest_conf, 0.0)

        # FIX DEL CRASH: I flag globali (?i) devono stare all'inizio assoluto
        if identity.map_type == "normal":
            if re.search(r"(?i)(_dx|_directx)", filename):
                identity.convention = "DirectX"
            elif re.search(r"(?i)(_gl|_opengl)", filename):
                identity.convention = "OpenGL"

        return identity

    @classmethod
    def classify_batch(cls, filenames: List[str]) -> Dict[str, TextureIdentity]:
        return {fname: cls.classify_filename(fname) for fname in filenames}

    @classmethod
    def summarize_set(cls, results: Dict[str, TextureIdentity]) -> Dict[str, Any]:
        found_maps = set()
        packed_maps = []
        unknown_files = []
        conventions = {"DirectX": False, "OpenGL": False}

        for fname, identity in results.items():
            if identity.map_type == "unknown":
                unknown_files.append(fname)
            else:
                if identity.is_packed:
                    packed_maps.append(identity.map_type)
                    for map_ch in identity.packed_channels.values():
                        found_maps.add(map_ch)
                else:
                    found_maps.add(identity.map_type)
                
                if identity.convention in ["DirectX", "OpenGL"]:
                    conventions[identity.convention] = True

        return {
            "covered": list(found_maps),
            "missing_core": list({"albedo", "normal", "roughness"} - found_maps),
            "packed_maps": packed_maps,
            "unknown_files": unknown_files,
            "normal_conventions": conventions
        }