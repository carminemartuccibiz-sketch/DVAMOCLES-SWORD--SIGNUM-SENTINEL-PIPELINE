import re
import json
from pathlib import Path

class NamingIntelligence:
    """Identifica mappe leggendo la Knowledge Base (Single Source of Truth)."""
    
    def __init__(self, kb_path: str = "06_KNOWLEDGE_BASE/mappings/naming_map.json"):
        self.kb_path = Path(kb_path)
        self.map_patterns = {}
        self._load_kb()

    def _load_kb(self):
        if self.kb_path.exists():
            with open(self.kb_path, 'r') as f:
                data = json.load(f)
                self.map_patterns = data.get("map_patterns", {})

    def classify_filename(self, filename: str):
        filename = filename.lower()
        best_match = "Unknown"
        for mtype, suffixes in self.map_patterns.items():
            for s in suffixes:
                if s.lower() in filename:
                    best_match = mtype.upper()
                    break
        return best_match