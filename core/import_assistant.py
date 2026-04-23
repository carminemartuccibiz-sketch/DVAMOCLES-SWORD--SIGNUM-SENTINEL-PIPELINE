import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Union
from PIL import Image
import re

try:
    from core.naming_intelligence import NamingIntelligence
    HAS_NAMING = True
except ImportError:
    HAS_NAMING = False

try:
    import exiftool
    HAS_EXIFTOOL = True
except ImportError:
    HAS_EXIFTOOL = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SIGNUM_SENTINEL.IMPORTER")

class AdvancedImporter:
    def __init__(self, root_dir: Union[str, Path] = None):
        self.root = Path(root_dir) if root_dir else Path(__file__).parent.parent
        self.raw_dir = self.root / "01_RAW_ARCHIVE"
        self.custom_dir = self.root / "02_CUSTOM"
        self.manifest_dir = self.root / "06_KNOWLEDGE_BASE" / "Manifests"
        self.config_dir = self.root / "config"
        self.temp_dir = self.root / "temp" / "thumbnails"
        
        for d in [self.raw_dir, self.custom_dir, self.manifest_dir, self.config_dir, self.temp_dir]:
            d.mkdir(parents=True, exist_ok=True)
            
        self.naming_ai = NamingIntelligence() if HAS_NAMING else None
        self.learning_db_path = self.config_dir / "learned_naming.json"
        self.ui_prefs_path = self.config_dir / "ui_prefs.json"
        
        self.learned_rules = self._load_json(self.learning_db_path)
        self.ui_prefs = self._load_ui_prefs()
        self.vault_file_index = set() 

    def _load_ui_prefs(self) -> Dict:
        default_prefs = {
            "providers": ["AmbientCG", "Quixel", "Poliigon", "Personal"],
            "formats": ["Auto", "PNG", "JPG", "EXR", "TIF", "TGA"],
            "resolutions": ["Auto", "1K", "2K", "4K", "8K"],
            "map_types": ["ALBEDO", "NORMAL", "ROUGHNESS", "METALLIC", "AO", "HEIGHT", "OPACITY"]
        }
        saved = self._load_json(self.ui_prefs_path)
        for k, v in default_prefs.items():
            if k not in saved: saved[k] = v
        return saved

    def add_ui_pref(self, category: str, value: str):
        if not value or value.upper() == "UNKNOWN": return
        clean_val = value.strip()
        if category in ["formats", "map_types", "resolutions"]: clean_val = clean_val.upper()
        if clean_val not in self.ui_prefs[category]:
            self.ui_prefs[category].append(clean_val)
            self._save_json(self.ui_prefs_path, self.ui_prefs)

    def _load_json(self, path: Path) -> Dict:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f: return json.load(f)
            except: pass
        return {}

    def _save_json(self, path: Path, data: Dict):
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)

    def _sanitize_name(self, name: str) -> str:
        return name.strip().replace(" ", "_").replace("/", "-").replace("\\", "-")

    def extract_suffix(self, filename: str) -> str:
        name = Path(filename).stem
        parts = name.replace("-", "_").split("_")
        return f"_{parts[-1].lower()}" if len(parts) > 1 else name.lower()

    def learn_rule(self, provider: str, filename: str, map_type: str):
        if not provider: provider = "Generic"
        suffix = self.extract_suffix(filename)
        if provider not in self.learned_rules: self.learned_rules[provider] = {}
        self.learned_rules[provider][suffix] = map_type.upper()
        self._save_json(self.learning_db_path, self.learned_rules)

    def load_existing_vault(self) -> Dict[str, Any]:
        vault = {}
        self.vault_file_index.clear()
        
        for man_file in self.manifest_dir.glob("*_manifest.json"):
            try:
                with open(man_file, "r", encoding="utf-8") as f: data = json.load(f)
                mat_name = data.get("identity", {}).get("material_name")
                prov_name = data.get("identity", {}).get("provider", "Unknown")
                if not mat_name: continue
                
                vault[mat_name] = {
                    "provider": prov_name, "url": data["identity"].get("url", ""),
                    "technique": data["identity"].get("technique", ""),
                    "tags": data.get("tags", []), "desc": data.get("description", ""),
                    "extra_docs": [], "folders": {}
                }
                
                mat_raw_path = self.raw_dir / prov_name / mat_name
                mat_custom_path = self.custom_dir / prov_name / mat_name
                
                for cat in ["RAW", "CUSTOM"]:
                    for folder_name, folder_data in data.get("hierarchy", {}).get(cat, {}).items():
                        if folder_name not in vault[mat_name]["folders"]:
                            vault[mat_name]["folders"][folder_name] = {"is_custom": (cat=="CUSTOM"), "files": []}
                        
                        base_path = mat_custom_path if cat == "CUSTOM" else mat_raw_path
                        for f_obj in folder_data.get("files", []):
                            f_obj["is_existing"] = True
                            actual_path = base_path / folder_name / f_obj["name"] if folder_name != "Root" else base_path / f_obj["name"]
                            f_obj["path"] = str(actual_path) 
                            
                            vault[mat_name]["folders"][folder_name]["files"].append(f_obj)
                            self.vault_file_index.add(f"{f_obj['name'].lower()}_{f_obj.get('tech_res','')}")
            except Exception as e:
                logger.error(f"Errore caricamento vault: {e}")
        return vault

    def _extract_metadata_safe(self, path: Path) -> Dict:
        res = {"tech_res": "Unknown", "bit_depth": "Unknown", "color_space": "Unknown"}
        try:
            with Image.open(path) as img:
                res["tech_res"] = f"{img.width}x{img.height}"
                res["color_space"] = img.mode
        except: pass

        if HAS_EXIFTOOL:
            try:
                with exiftool.ExifToolHelper() as et:
                    meta = et.get_metadata(str(path))
                    if meta:
                        m = meta[0]
                        w = m.get("File:ImageWidth", m.get("EXIF:ExifImageWidth"))
                        h = m.get("File:ImageHeight", m.get("EXIF:ExifImageHeight"))
                        if w and h: res["tech_res"] = f"{w}x{h}"
                        bd = m.get("EXIF:BitsPerSample", m.get("PNG:BitDepth", "Unknown"))
                        if bd != "Unknown": res["bit_depth"] = f"{bd}-bit"
            except: pass
        return res

    def auto_detect_file(self, file_path: str, provider: str = "Generic") -> Dict[str, Any]:
        p = Path(file_path)
        data = {
            "name": p.name, "path": str(p), "format": p.suffix.lower().replace(".", "").upper(),
            "map_type": "Unknown", "resolution": "Unknown", "is_custom": False,
            "process": "", "derived_from": "", 
            "tech_res": "Unknown", "bit_depth": "Unknown", "color_space": "Unknown",
            "is_duplicate": False, "auto_organized": False
        }
        
        exif_data = self._extract_metadata_safe(p)
        data.update(exif_data)
        
        dupe_key = f"{p.name.lower()}_{data['tech_res']}"
        if dupe_key in self.vault_file_index:
            data["is_duplicate"] = True
        
        if data["tech_res"] != "Unknown":
            try:
                w = int(data["tech_res"].split("x")[0])
                if w >= 7500: data["resolution"] = "8K"
                elif w >= 3800: data["resolution"] = "4K"
                elif w >= 1900: data["resolution"] = "2K"
                elif w >= 900: data["resolution"] = "1K"
            except: pass

        suffix = self.extract_suffix(p.name)
        if provider in self.learned_rules and suffix in self.learned_rules[provider]:
            data["map_type"] = self.learned_rules[provider][suffix]
        elif "Generic" in self.learned_rules and suffix in self.learned_rules["Generic"]:
            data["map_type"] = self.learned_rules["Generic"][suffix]
        elif self.naming_ai:
            identity = self.naming_ai.classify_filename(p.name)
            base_type = identity.map_type.upper()
            
            # FUSIONE NORMAL + CONVENTION (Se l'AI base lo individua)
            if base_type == "NORMAL":
                if identity.convention:
                    conv_short = "DX" if identity.convention.upper() == "DIRECTX" else "GL"
                    data["map_type"] = f"NORMAL_{conv_short}"
                else:
                    data["map_type"] = "NORMAL"
            else:
                data["map_type"] = base_type
            
        if data["resolution"] == "Unknown":
            res_match = re.search(r'(?i)(1k|2k|3k|4k|8k|1024|2048|4096|8192)', p.name)
            if res_match: data["resolution"] = res_match.group(1).upper()
            
        if "custom" in p.name.lower() or "generated" in p.name.lower(): data["is_custom"] = True
        return data

    def generate_thumbnail(self, img_path: str, size=(64, 64)) -> str:
        try:
            path_obj = Path(img_path)
            if path_obj.suffix.lower() not in ['.png', '.jpg', '.jpeg', '.tga', '.tif']: return ""
            thumb_path = self.temp_dir / f"thumb_{path_obj.name}.png"
            if thumb_path.exists(): return str(thumb_path)
            with Image.open(img_path) as img:
                img.thumbnail(size)
                img.save(thumb_path, "PNG")
            return str(thumb_path)
        except: return ""

    def run_import(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        if not project_data.get("materials"): return {"status": "error", "message": "Nessun materiale da importare."}
        logs = []
        for mat_name, mat_data in project_data["materials"].items():
            safe_mat_name = self._sanitize_name(mat_name)
            prov_name = self._sanitize_name(mat_data.get("provider", "Unknown"))
            
            mat_raw_path = self.raw_dir / prov_name / safe_mat_name
            mat_custom_path = self.custom_dir / prov_name / safe_mat_name
            structure_log = {"RAW": {}, "CUSTOM": {}}
            has_new_files = False

            for folder_name, folder_data in mat_data.get("folders", {}).items():
                if not folder_data["files"]: continue
                is_folder_custom = folder_data.get("is_custom", False)
                safe_folder_name = self._sanitize_name(folder_name)
                
                for file_obj in folder_data["files"]:
                    file_is_custom = file_obj.get("is_custom", is_folder_custom)
                    log_cat = "CUSTOM" if file_is_custom else "RAW"
                    if safe_folder_name not in structure_log[log_cat]: structure_log[log_cat][safe_folder_name] = {"files": []}
                    
                    structure_log[log_cat][safe_folder_name]["files"].append({
                        "name": file_obj.get("name", ""), "map_type": file_obj.get("map_type", "Unknown"),
                        "resolution": file_obj.get("resolution", "Unknown"), "format": file_obj.get("format", "Unknown"),
                        "process": file_obj.get("process", ""), "derived_from": file_obj.get("derived_from", ""),
                        "tech_res": file_obj.get("tech_res", "Unknown"), "bit_depth": file_obj.get("bit_depth", "Unknown"),
                        "color_space": file_obj.get("color_space", "Unknown")
                    })

                    if file_obj.get("is_existing"): continue

                    f_path = Path(file_obj["path"])
                    if not f_path.exists(): continue
                    has_new_files = True

                    target_base = mat_custom_path if file_is_custom else mat_raw_path
                    target_dir = target_base if safe_folder_name == "Root" else target_base / safe_folder_name
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    try:
                        shutil.copy2(f_path, target_dir / f_path.name)
                        self.learn_rule(prov_name, f_path.name, file_obj.get("map_type", "Unknown"))
                    except Exception as e: logger.error(f"Copy failed: {e}")

            manifest_data = {
                "identity": {"material_name": safe_mat_name, "provider": prov_name, "url": mat_data.get("url", ""), "technique": mat_data.get("technique", ""), "import_date": datetime.now().isoformat()},
                "tags": mat_data.get("tags", []), "description": mat_data.get("desc", ""), "hierarchy": structure_log
            }
            manifest_file = self.manifest_dir / f"{prov_name}_{safe_mat_name}_manifest.json"
            self._save_json(manifest_file, manifest_data)
            logs.append(f"✅ Forgiato: {safe_mat_name} (New Data: {has_new_files})")
        return {"status": "success", "message": "\n".join(logs)}