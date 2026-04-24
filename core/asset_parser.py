import xml.etree.ElementTree as ET
import json
from pathlib import Path
import logging

class UniversalParser:
    """Traduttore di setup file (MaterialX, Godot) e motore di apprendimento."""
    
    def __init__(self, kb_path: str = "06_KNOWLEDGE_BASE/mappings/naming_map.json"):
        self.kb_path = Path(kb_path)
        self.logger = logging.getLogger("SENTINEL.PARSER")

    def parse_file(self, file_path: Path) -> dict:
        """Rileva l'estensione e avvia il parser corretto."""
        if file_path.suffix.lower() == ".mtlx":
            return self._parse_mtlx(file_path)
        elif file_path.suffix.lower() == ".tres":
            return self._parse_godot_tres(file_path)
        return {}

    def _parse_mtlx(self, path: Path) -> dict:
        try:
            tree = ET.parse(path)
            mappings = {}
            for img in tree.getroot().findall('.//tiledimage'):
                role = img.get('name')
                f_node = img.find(".//input[@name='file']")
                if f_node is not None:
                    mappings[Path(f_node.get('value')).name] = self._remap(role)
            self._update_kb(mappings)
            return mappings
        except: return {}

    def _parse_godot_tres(self, path: Path) -> dict:
        """Parsa file .tres di Godot per trovare texture_albedo, texture_normal, etc."""
        mappings = {}
        try:
            with open(path, "r") as f:
                content = f.read()
                # Esempio regex semplificato per Godot resources
                import re
                matches = re.findall(r'texture_(\w+)\s*=\s*ExtResource\("?(.+?)"?\)', content)
                for role, res_id in matches:
                    mappings[res_id] = role.upper()
            return mappings
        except: return {}

    def _remap(self, role: str) -> str:
        table = {"base_color": "ALBEDO", "normal": "NORMAL", "specular_roughness": "ROUGHNESS", "ambient_occlusion": "AO"}
        return table.get(role.lower(), "UNKNOWN")

    def _update_kb(self, mappings: dict):
        """Impara i suffissi dai file di setup e aggiorna la Knowledge Base."""
        if not self.kb_path.exists(): return
        try:
            with open(self.kb_path, 'r') as f: kb = json.load(f)
            for fname, mtype in mappings.items():
                suffix = "_" + fname.split("_")[-1].split(".")[0]
                if mtype != "UNKNOWN" and suffix not in kb["map_patterns"].get(mtype.lower(), []):
                    kb["map_patterns"][mtype.lower()].append(suffix)
            with open(self.kb_path, 'w') as f: json.dump(kb, f, indent=4)
        except: pass