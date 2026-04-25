import xml.etree.ElementTree as ET
import json
from pathlib import Path
import logging
import re

class UniversalParser:
    """Traduttore di setup file (MaterialX, Godot) e motore di apprendimento."""
    
    def __init__(self, kb_path: str = "06_KNOWLEDGE_BASE/mappings/naming_map.json"):
        self.kb_path = Path(kb_path)
        self.logger = logging.getLogger("SENTINEL.PARSER")
        self.kb = self._load_kb()

    def parse_file(self, file_path: Path) -> dict:
        """Rileva l'estensione e avvia il parser corretto."""
        suffix = file_path.suffix.lower()
        if suffix == ".mtlx":
            return self._parse_mtlx(file_path)
        if suffix == ".tres":
            return self._parse_godot_tres(file_path)
        if suffix == ".usdc":
            return self._parse_usdc_stub(file_path)
        return {}

    def _load_kb(self) -> dict:
        if not self.kb_path.exists():
            return {"map_patterns": {}, "role_aliases": {}}
        try:
            with open(self.kb_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            self.logger.exception("Errore lettura KB naming map.")
            return {"map_patterns": {}, "role_aliases": {}}

    def _parse_mtlx(self, path: Path) -> dict:
        try:
            tree = ET.parse(path)
            mappings = {}
            for img in tree.getroot().findall('.//tiledimage'):
                role = img.get('name', '')
                f_node = img.find(".//input[@name='file']")
                if f_node is not None:
                    value = f_node.get('value', '')
                    if not value:
                        continue
                    mappings[Path(value).name] = self._remap(role)
            self._update_kb(mappings)
            return mappings
        except Exception:
            self.logger.exception("Parse MTLX fallito.")
            return {}

    def _parse_godot_tres(self, path: Path) -> dict:
        """Parsa file .tres di Godot per trovare texture_albedo, texture_normal, etc."""
        mappings = {}
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                matches = re.findall(r'texture_(\w+)\s*=\s*ExtResource\("?(.+?)"?\)', content)
                for role, res_id in matches:
                    mappings[res_id] = self._remap(role)
            return mappings
        except Exception:
            self.logger.exception("Parse Godot .tres fallito.")
            return {}

    def _parse_usdc_stub(self, path: Path) -> dict:
        """
        Stub iniziale USDC:
        - USDC è binario, quindi qui registriamo solo metadati e lasciamo il mapping vuoto.
        - Preparato per futura integrazione usd-core/usdcat.
        """
        self.logger.info("USDC rilevato: %s (stub parser attivo).", path.name)
        return {"__usdc_stub__": path.name}

    def _remap(self, role: str) -> str:
        role_key = (role or "").strip().lower()
        aliases = self.kb.get("role_aliases", {})
        mapped = aliases.get(role_key, "unknown")
        return mapped.upper()

    def _update_kb(self, mappings: dict):
        """Impara i suffissi dai file di setup e aggiorna la Knowledge Base."""
        if not self.kb_path.exists():
            return
        try:
            with open(self.kb_path, 'r', encoding="utf-8") as f:
                kb = json.load(f)
            for fname, mtype in mappings.items():
                if fname.startswith("__"):
                    continue
                suffix = "_" + fname.split("_")[-1].split(".")[0]
                if mtype != "UNKNOWN":
                    kb["map_patterns"].setdefault(mtype.lower(), [])
                    if suffix not in kb["map_patterns"][mtype.lower()]:
                        kb["map_patterns"][mtype.lower()].append(suffix)
            with open(self.kb_path, 'w', encoding="utf-8") as f:
                json.dump(kb, f, indent=4)
        except Exception:
            self.logger.exception("Aggiornamento KB da parser fallito.")