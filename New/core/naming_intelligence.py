import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any


@dataclass
class NamingResult:
    map_type: str
    confidence: float
    source: str
    convention: str | None = None


class NamingIntelligence:
    """Map type classifier guidato dalla KB JSON."""

    def __init__(self, kb_path: str = "06_KNOWLEDGE_BASE/mappings/naming_map.json"):
        self.kb_path = Path(kb_path)
        self.map_patterns: Dict[str, List[str]] = {}
        self.role_aliases: Dict[str, str] = {}
        self.normal_conventions: Dict[str, List[str]] = {}
        self._load_kb()

    def _load_kb(self):
        if not self.kb_path.exists():
            self.map_patterns = {}
            self.role_aliases = {}
            return
        with open(self.kb_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.map_patterns = data.get("map_patterns", {})
        self.role_aliases = data.get("role_aliases", {})
        self.normal_conventions = data.get("normal_convention_patterns", {})

    def reload_kb(self):
        """Ricarica la KB da disco (es. dopo aggiornamento da MTLX / UniversalParser)."""
        self._load_kb()

    def classify_filename(self, filename: str) -> NamingResult:
        clean = Path(filename).stem.lower()
        tokens = re.split(r"[_\-. ]+", clean)
        best_match = "unknown"
        best_conf = 0.0
        source = "none"

        for map_type, suffixes in self.map_patterns.items():
            for suffix in suffixes:
                s = suffix.lower().lstrip("_")
                if not s:
                    continue
                token_match = s in tokens
                contains = s in clean
                if token_match:
                    conf = 0.99
                elif contains:
                    conf = 0.9
                else:
                    continue
                if conf > best_conf:
                    best_match = map_type.lower()
                    best_conf = conf
                    source = "kb_pattern"

        convention = None
        if best_match == "normal":
            convention = self._detect_normal_convention(clean, tokens)
        return NamingResult(map_type=best_match, confidence=best_conf, source=source, convention=convention)

    def remap_role(self, role_name: str) -> str:
        role = (role_name or "").strip().lower()
        return self.role_aliases.get(role, "unknown")

    def _detect_normal_convention(self, clean_name: str, tokens: List[str]) -> str | None:
        token_set = set(tokens)
        dx_patterns = [str(p).lower().strip("_") for p in self.normal_conventions.get("dx", [])]
        gl_patterns = [str(p).lower().strip("_") for p in self.normal_conventions.get("gl", [])]

        for pattern in dx_patterns:
            if not pattern:
                continue
            if pattern in token_set or pattern in clean_name:
                return "DX"
        for pattern in gl_patterns:
            if not pattern:
                continue
            if pattern in token_set or pattern in clean_name:
                return "GL"
        return None