# core/naming_intelligence.py

import re
from dataclasses import dataclass
from typing import Optional

MAP_RULES = {
    "albedo": ["albedo", "basecolor", "color", "diffuse"],
    "normal": ["normal", "nrm"],
    "roughness": ["roughness", "rough"],
    "metallic": ["metallic", "metal"],
    "ao": ["ao", "occlusion"],
    "height": ["height", "displacement", "disp"],
}

@dataclass
class NamingResult:
    map_type: str
    confidence: float
    convention: Optional[str] = None

class NamingIntelligence:

    def classify(self, filename: str) -> NamingResult:
        name = filename.lower()

        # Normal DX/GL
        if "normaldx" in name:
            return NamingResult("normal", 0.95, "DX")
        if "normalgl" in name:
            return NamingResult("normal", 0.95, "GL")

        for map_type, keywords in MAP_RULES.items():
            for kw in keywords:
                if kw in name:
                    return NamingResult(map_type, 0.85)

        return NamingResult("unknown", 0.0)