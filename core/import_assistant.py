import os, json, shutil, logging, re, gc
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Union
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

# Import opzionali per gestire il mancato caricamento di Torch su Python 3.14
try:
    import torch
    import cv2
    from transformers import BlipProcessor, BlipForConditionalGeneration
    HAS_AI_LIBS = True
except ImportError:
    HAS_AI_LIBS = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SIGNUM_SENTINEL.ADV_IMPORTER")

class AdvancedImporter:
    def __init__(self, root_dir: Union[str, Path] = None):
        self.root = Path(root_dir) if root_dir else Path.cwd()
        self.manifest_dir = self.root / "06_KNOWLEDGE_BASE" / "Manifests"
        self.kb_path = self.root / "06_KNOWLEDGE_BASE" / "mappings" / "naming_map.json"
        self.ui_prefs_path = self.root / "config" / "ui_prefs.json"
        
        # Stato AI
        self.ai_model = None
        self.ai_processor = None
        self.device = "cuda" if HAS_AI_LIBS and torch.cuda.is_available() else "cpu"
        
        # Carica preferenze e indici
        self.ui_prefs = self._load_json(self.ui_prefs_path, {"providers":[], "formats":[], "resolutions":[], "map_types":[]})
        self.learned_naming = self._load_json(self.kb_path, {"map_patterns": {}})
        self.vault_file_index = set()

    def _load_json(self, path, default):
        if Path(path).exists():
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
        return default

    def _save_json(self, path, data):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)

    # --- GESTIONE CICLO DI VITA AI ---
    def load_ai(self):
        """Carica i modelli pesanti in memoria solo se richiesto."""
        if not HAS_AI_LIBS or self.ai_model is not None: return
        try:
            logger.info(f"Caricamento AI Vision (BLIP) su {self.device}...")
            self.ai_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            self.ai_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
            logger.info("AI Vision pronta.")
        except Exception as e:
            logger.error(f"Errore caricamento AI: {e}")

    def unload_ai(self):
        """Svuota la VRAM e libera la memoria."""
        if self.ai_model is None: return
        logger.info("Spegnimento AI e svuotamento VRAM...")
        try:
            del self.ai_model
            del self.ai_processor
            self.ai_model = None
            self.ai_processor = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except: pass

    # --- SENSORI (Visual & Parser) ---
    def visual_check(self, path: Path) -> str:
        if not HAS_AI_LIBS: return "Unknown"
        try:
            img = cv2.imread(str(path))
            if img is None: return "Unknown"
            b, g, r = cv2.split(img)
            if np.allclose(r, g, atol=10) and np.allclose(g, b, atol=10): return "GRAYSCALE"
            mean_bgr = cv2.mean(img)[:3]
            if 110 < mean_bgr[2] < 150 and 110 < mean_bgr[1] < 150 and mean_bgr[0] > 180: return "NORMAL"
            return "COLOR"
        except: return "Unknown"

    def ai_describe(self, path: Path) -> str:
        if self.ai_model is None: return ""
        try:
            raw_image = Image.open(path).convert('RGB')
            inputs = self.ai_processor(raw_image, "a PBR material texture showing", return_tensors="pt").to(self.device)
            out = self.ai_model.generate(**inputs)
            return self.ai_processor.decode(out[0], skip_special_tokens=True).capitalize()
        except: return ""

    def parse_mtlx(self, folder_path: Path) -> Dict[str, str]:
        mappings = {}
        for mtlx in folder_path.glob("*.mtlx"):
            try:
                tree = ET.parse(mtlx)
                for img in tree.getroot().findall('.//tiledimage'):
                    role = img.get('name', '').lower()
                    f_node = img.find(".//input[@name='file']")
                    if f_node is not None:
                        fname = Path(f_node.get('value')).name
                        mtype = "ALBEDO" if "color" in role else "NORMAL" if "normal" in role else "ROUGHNESS" if "rough" in role else "Unknown"
                        mappings[fname] = mtype
                        if mtype != "Unknown":
                            suffix = "_" + fname.split("_")[-1].split(".")[0]
                            self._learn_suffix(mtype, suffix)
            except: pass
        return mappings

    def _learn_suffix(self, mtype, suffix):
        patterns = self.learned_naming["map_patterns"].setdefault(mtype.lower(), [])
        if suffix not in patterns:
            patterns.append(suffix)
            self._save_json(self.kb_path, self.learned_naming)

    def auto_detect_file(self, file_path: str, provider: str = "Generic") -> Dict[str, Any]:
        p = Path(file_path)
        data = {
            "name": p.name, "path": str(p), "format": p.suffix.lower().replace(".", "").upper(),
            "map_type": "Unknown", "resolution": "Unknown", "is_custom": False,
            "tech_res": "Unknown", "ai_description": "", "visual_validation": "",
            "is_duplicate": False, "auto_organized": False
        }

        # 1. Pixel Spec
        try:
            with Image.open(p) as img:
                data["tech_res"] = f"{img.width}x{img.height}"
                if img.width >= 3800: data["resolution"] = "4K"
                elif img.width >= 1900: data["resolution"] = "2K"
        except: pass

        # 2. OpenCV & AI
        data["visual_validation"] = self.visual_check(p)
        if self.ai_model and data["visual_validation"] == "COLOR":
            data["ai_description"] = self.ai_describe(p)

        # 3. Naming
        fname_lower = p.name.lower()
        for mtype, suffixes in self.learned_naming.get("map_patterns", {}).items():
            for s in suffixes:
                if s.lower() in fname_lower:
                    data["map_type"] = mtype.upper()
                    break
        
        # 4. Duplicate check
        if f"{p.name.lower()}_{data['tech_res']}" in self.vault_file_index:
            data["is_duplicate"] = True

        return data

    def load_existing_vault(self) -> Dict[str, Any]:
        vault = {}
        self.vault_file_index.clear()
        for man_file in self.manifest_dir.glob("*_manifest.json"):
            try:
                with open(man_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    mat_name = d["identity"]["material_name"]
                    vault[mat_name] = {
                        "provider": d["identity"]["provider"], "tags": d.get("tags", []),
                        "desc": d.get("description", ""), "url": d["identity"].get("url",""),
                        "technique": d["identity"].get("technique",""), "extra_docs":[], "folders": {}
                    }
                    # Popola indice duplicati
                    for cat in ["RAW", "CUSTOM"]:
                        for fldr, f_data in d.get("hierarchy", {}).get(cat, {}).items():
                            vault[mat_name]["folders"][fldr] = {"is_custom": (cat=="CUSTOM"), "files": f_data["files"]}
                            for f_obj in f_data["files"]:
                                f_obj["is_existing"] = True
                                self.vault_file_index.add(f"{f_obj['name'].lower()}_{f_obj.get('tech_res','')}")
            except: pass
        return vault

    def run_import(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        # Implementazione della copia fisica e scrittura manifest (omessa qui per brevità, ma è quella dei turni precedenti)
        return {"status": "success", "message": "Importazione completata."}