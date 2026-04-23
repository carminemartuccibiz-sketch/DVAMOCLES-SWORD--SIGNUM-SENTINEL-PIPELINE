import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re

# Integrazioni opzionali per l'analisi tecnica (Regole di Integrazione)
try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from PIL import Image, ImageCms
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Configurazione Logging (Production Standard)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SIGNUM_SENTINEL.IMPORT_ASSISTANT")


class ImageAnalyzer:
    """Responsabile dell'estrazione delle specifiche fisiche (DNA Tecnico)."""

    @staticmethod
    def get_specs(file_path: Path) -> Dict[str, Any]:
        """Estrae resolution, bit_depth, color_space e format."""
        specs = {
            "format": file_path.suffix.lower().replace('.', ''),
            "resolution": [0, 0],
            "bit_depth": "Unknown",
            "color_space": "Unknown"
        }

        if not file_path.exists():
            return specs

        logger.debug(f"Analisi file: {file_path.name}")

        # Try OpenCV (Ottimale per EXR/TIFF 16-32bit)
        if HAS_CV2:
            try:
                img = cv2.imread(str(file_path), cv2.IMREAD_UNCHANGED)
                if img is not None:
                    h, w = img.shape[:2]
                    specs["resolution"] = [w, h]
                    dtype = str(img.dtype)
                    specs["bit_depth"] = "8-bit" if "uint8" in dtype else "16-bit" if "uint16" in dtype else "32-bit float"
                    
                    if len(img.shape) == 2: specs["color_space"] = "Grayscale"
                    else: specs["color_space"] = "RGB" if img.shape[2] == 3 else "RGBA"
                    return specs
            except Exception as e:
                logger.warning(f"OpenCV fallito su {file_path.name}: {e}")

        # Fallback Pillow
        if HAS_PIL:
            try:
                with Image.open(file_path) as img:
                    specs["resolution"] = list(img.size)
                    mode_map = {"L": "Grayscale", "RGB": "RGB", "RGBA": "RGBA", "I;16": "16-bit", "F": "32-bit float"}
                    specs["color_space"] = mode_map.get(img.mode, "Unknown")
                    return specs
            except Exception as e:
                logger.warning(f"Pillow fallito su {file_path.name}: {e}")

        return specs


class ProcessParser:
    """Converte descrizioni testuali in pipeline strutturate (NLP-lite)."""

    TOOLS_DB = ["Substance Designer", "Substance Painter", "Photoshop", "Materialize", "ZBrush", "Blender", "RealityCapture"]

    @classmethod
    def parse(cls, text: str) -> Dict[str, Any]:
        """Analizza il testo per definire il workflow."""
        if not text:
            return {"process": "legacy_import", "tool": "manual", "generated_from": "archive", "output_type": "pbr_material"}

        low_text = text.lower()
        found_tools = [t for t in cls.TOOLS_DB if t.lower() in low_text]
        
        # Logica di classificazione processo
        process = "custom_creation"
        gen_from = "scratch"
        
        if any(x in low_text for x in ["scan", "photogrammetry", "foto"]):
            process, gen_from = "photogrammetry", "real_world"
        elif any(x in low_text for x in ["ai", "midjourney", "stable"]):
            process, gen_from = "ai_generation", "text_prompt"
        elif "bake" in low_text:
            process, gen_from = "baking", "high_poly_mesh"

        return {
            "process": process,
            "tool": ", ".join(found_tools) if found_tools else "Unknown",
            "generated_from": gen_from,
            "output_type": "pbr_material",
            "description": text
        }


class ImportAssistant:
    """Orchestratore della Fase 1 (The Gatekeeper)."""

    def __init__(self):
        self.root = Path(__file__).parent.parent
        self.raw_dir = self.root / "01_RAW_ARCHIVE"
        self.custom_dir = self.root / "02_CUSTOM"

    def run_import(self, source_folder: str, is_custom: bool = False, overrides: Dict[str, Any] = None):
        """Esegue l'importazione completa."""
        src = Path(source_folder)
        if not src.exists():
            logger.error(f"Sorgente non trovata: {source_folder}")
            return

        # Setup metadati base
        ovr = overrides or {}
        provider = ovr.get("provider_name", "Unknown")
        material = ovr.get("material_name", src.name)
        
        # Destinazione (Regola 01 vs 02)
        base_dest = self.custom_dir if is_custom else self.raw_dir
        dest_path = base_dest / provider / material
        dest_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Importazione in corso: {material} -> {dest_path}")

        files_meta = []
        for f in src.iterdir():
            if f.is_file() and not f.name.startswith('.'):
                target_file = dest_path / f.name
                shutil.copy2(f, target_file)
                
                # Analisi tecnica file per file
                if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.tif', '.exr', '.tga']:
                    specs = ImageAnalyzer.get_specs(target_file)
                    files_meta.append({"file": f.name, "specs": specs})
                logger.debug(f"File copiato: {f.name}")

        # Generazione SIDECARES
        self._write_material_info(dest_path, material, provider, ovr, files_meta)
        self._write_process_json(dest_path, ovr.get("process_description", ""))

        logger.info(f"✅ Import Completato per {material}")

    def _write_material_info(self, path: Path, name: str, provider: str, ovr: Dict, files: List):
        data = {
            "identity": {
                "material_name": name,
                "provider": provider,
                "asset_id": ovr.get("asset_id", "N/A"),
                "source_url": ovr.get("source_url", ""),
                "license": ovr.get("license", "Standard"),
                "import_date": datetime.now().isoformat()
            },
            "tags": ovr.get("tags", []),
            "technical_summary": files
        }
        with open(path / "material_info.json", "w") as f:
            json.dump(data, f, indent=4)

    def _write_process_json(self, path: Path, desc: str):
        process_data = ProcessParser.parse(desc)
        with open(path / "process.json", "w") as f:
            json.dump(process_data, f, indent=4)


if __name__ == "__main__":
    # Esempio di utilizzo CLI rapido
    assistant = ImportAssistant()
    
    # Esempio configurazione utente (Override)
    my_overrides = {
        "provider_name": "AmbientCG",
        "material_name": "Rough_Bricks_01",
        "tags": ["bricks", "red", "outdoor"],
        "process_description": "Downloaded from AmbientCG, processed in Photoshop for seamless tiling.",
        "license": "CC0"
    }
    
    # Esegui (Cambia il path con uno reale per testare)
    # assistant.run_import("path/to/your/textures", is_custom=True, overrides=my_overrides)