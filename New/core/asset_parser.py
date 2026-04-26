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
            return self.parse_mtlx(file_path)
        if suffix == ".tres":
            return self.parse_tres(file_path)
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

    def parse_mtlx(self, path: Path) -> dict:
        try:
            tree = ET.parse(path)
            mappings = {}
            for img in tree.getroot().findall(".//tiledimage"):
                role = img.get("name", "")
                f_node = img.find(".//input[@name='file']")
                if f_node is not None:
                    value = f_node.get("value", "")
                    if not value:
                        continue
                    mappings[Path(value).name] = self._remap(role)
            # Fallback generic image nodes for broader MaterialX compatibility.
            for node in tree.getroot().findall(".//image"):
                role = node.get("name", "")
                f_node = node.find(".//input[@name='file']")
                if f_node is None:
                    continue
                value = f_node.get("value", "")
                if not value:
                    continue
                mappings.setdefault(Path(value).name, self._remap(role))
            self._update_kb(mappings)
            return mappings
        except Exception:
            self.logger.exception("Parse MTLX fallito.")
            return {}

    def parse_tres(self, path: Path) -> dict:
        """
        Parse Godot .tres:
        - map ExtResource id -> texture file path
        - map resource slots (albedo_texture, normal_texture, ...) -> ExtResource ids
        """
        mappings = {}
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            ext_resources = {}
            ext_pattern = re.compile(r'\[ext_resource[^\]]*path="([^"]+)"[^\]]*id="([^"]+)"[^\]]*\]', re.IGNORECASE)
            for tex_path, res_id in ext_pattern.findall(content):
                ext_resources[res_id] = Path(tex_path).name

            slot_pattern = re.compile(r"([a-zA-Z0-9_]+)\s*=\s*ExtResource\(\"([^\"]+)\"\)")
            for slot, res_id in slot_pattern.findall(content):
                role = self._slot_to_role(slot)
                mapped = self._remap(role)
                if mapped == "UNKNOWN":
                    continue
                file_name = ext_resources.get(res_id)
                if file_name:
                    mappings[file_name] = mapped

            self._update_kb(mappings)
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

    @staticmethod
    def _slot_to_role(slot: str) -> str:
        s = (slot or "").strip().lower()
        if "albedo" in s or "base_color" in s or "basecolor" in s:
            return "albedo"
        if "normal" in s:
            return "normal"
        if "roughness" in s or "rough" in s:
            return "roughness"
        if "metal" in s:
            return "metallic"
        if "ao" in s or "occlusion" in s:
            return "ao"
        if "height" in s or "displacement" in s:
            return "height"
        return s

    def _update_kb(self, mappings: dict):
        """Impara i suffissi dai file di setup e aggiorna la Knowledge Base."""
        if not self.kb_path.exists():
            return
        try:
            with open(self.kb_path, "r", encoding="utf-8") as f:
                kb = json.load(f)
            for fname, mtype in mappings.items():
                if fname.startswith("__"):
                    continue
                suffix = "_" + fname.split("_")[-1].split(".")[0]
                if mtype != "UNKNOWN":
                    kb["map_patterns"].setdefault(mtype.lower(), [])
                    if suffix not in kb["map_patterns"][mtype.lower()]:
                        kb["map_patterns"][mtype.lower()].append(suffix)
            with open(self.kb_path, "w", encoding="utf-8") as f:
                json.dump(kb, f, indent=4, ensure_ascii=False)
            self.kb = kb
        except Exception:
            self.logger.exception("Aggiornamento KB da parser fallito.")