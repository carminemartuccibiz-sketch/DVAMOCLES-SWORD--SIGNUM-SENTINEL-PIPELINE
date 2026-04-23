import json
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Any

# Importiamo i moduli "Cervello" della pipeline
try:
    from core.naming_intelligence import NamingIntelligence
    HAS_NAMING = True
except ImportError:
    HAS_NAMING = False

try:
    from core.metadata_extractor import MetadataExtractor
    HAS_METADATA = True
except ImportError:
    HAS_METADATA = False

# Configurazione Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SIGNUM_SENTINEL.INGESTOR")

class Ingestor:
    """
    Orchestratore della Fase 2: Lettura, Estrazione Dati Fisici e Standardizzazione.
    Prende i dati da 01_RAW e 02_CUSTOM e genera i Manifesti in 03_PROCESSED.
    """

    def __init__(self, root_dir: str = None):
        self.root = Path(root_dir) if root_dir else Path(__file__).parent.parent
        self.raw_dir = self.root / "01_RAW_ARCHIVE"
        self.custom_dir = self.root / "02_CUSTOM"
        self.processed_dir = self.root / "03_PROCESSED"
        
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Inizializziamo i sottomoduli se disponibili
        self.naming_engine = NamingIntelligence() if HAS_NAMING else None
        self.meta_engine = MetadataExtractor() if HAS_METADATA else None

    def run_full_ingestion(self) -> Dict[str, Any]:
        """Scansiona interi archivi per trovare materiali da processare."""
        logger.info("Inizio Ingestione Massiva...")
        processed_materials = 0
        errors = 0

        # Scansione RAW
        for provider_dir in self.raw_dir.iterdir():
            if provider_dir.is_dir():
                for material_dir in provider_dir.iterdir():
                    if material_dir.is_dir():
                        if self._process_material_folder(material_dir, "01_RAW"):
                            processed_materials += 1
                        else:
                            errors += 1

        # Scansione CUSTOM
        for provider_dir in self.custom_dir.iterdir():
            if provider_dir.is_dir():
                for material_dir in provider_dir.iterdir():
                    if material_dir.is_dir():
                        if self._process_material_folder(material_dir, "02_CUSTOM"):
                            processed_materials += 1
                        else:
                            errors += 1

        logger.info(f"Ingestione Completata. Successi: {processed_materials} | Errori/Saltati: {errors}")
        return {"status": "success", "processed": processed_materials, "errors": errors}

    def _process_material_folder(self, source_path: Path, source_type: str) -> bool:
        """Elabora una singola cartella materiale, estrae i dati e genera il Master Manifest."""
        logger.info(f"Analisi: {source_path.parent.name} / {source_path.name} [{source_type}]")

        # 1. Leggi i sidecar creati dalla GUI/Importer (Fase 1)
        material_info = self._read_json(source_path / "material_info.json")
        process_info = self._read_json(source_path / "process.json")
        
        # Identità base
        provider = material_info.get("identity", {}).get("provider", source_path.parent.name)
        mat_name = material_info.get("identity", {}).get("material_name", source_path.name)
        tags = material_info.get("tags", [])

        # Destinazione
        target_dir = self.processed_dir / provider / mat_name
        
        # Se esiste già, lo puliamo per evitare conflitti (Pipeline idempotente)
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        files_data = []
        coverage = set()
        
        # Estensioni supportate
        valid_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".tga", ".uasset"}
        
        image_files = [f for f in source_path.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
        if not image_files:
            logger.warning(f"Nessun file valido trovato in {source_path}. Salto.")
            return False

        # 2. Elaborazione File per File (The Brain)
        for f in image_files:
            target_file = target_dir / f.name
            shutil.copy2(f, target_file)

            file_record = {
                "original_name": f.name,
                "map_type": "unknown",
                "confidence": 0.0,
                "specs": {},
                "software_origin": "Unknown"
            }

            # Naming Intelligence (Capisce cos'è dal nome)
            if self.naming_engine:
                ident = self.naming_engine.classify_filename(f.name)
                file_record["map_type"] = ident.map_type
                file_record["confidence"] = ident.confidence
                if ident.map_type != "unknown":
                    coverage.add(ident.map_type)
            
            # Metadata Extractor (Legge i pixel e gli EXIF)
            if self.meta_engine and f.suffix.lower() != ".uasset":
                tech_data = self.meta_engine.extract_all(f)
                file_record["specs"] = tech_data.get("image_specs", {})
                file_record["software_origin"] = tech_data.get("software_origin", "Unknown")

            files_data.append(file_record)

        # 3. Costruzione del Master Manifest (dataset-ready)
        manifest = {
            "metadata": {
                "material_name": mat_name,
                "provider": provider,
                "source_origin": source_type,
                "tags": tags
            },
            "coverage": {
                "maps_found": list(coverage),
                "is_pbr_complete": self._check_pbr_completeness(coverage)
            },
            "derivation": process_info if process_info else {"is_raw": True},
            "files": files_data
        }

        # Salvataggio Manifest
        with open(target_dir / "manifest.json", "w", encoding="utf-8") as mj:
            json.dump(manifest, mj, indent=4, ensure_ascii=False)

        logger.debug(f"Manifest generato per {mat_name}.")
        return True

    def _check_pbr_completeness(self, coverage: set) -> bool:
        """Verifica se il materiale ha le mappe base minime."""
        core_maps = {"albedo", "normal", "roughness"}
        # Se l'intersezione contiene tutti gli elementi di core_maps
        return core_maps.issubset(coverage)

    def _read_json(self, path: Path) -> Dict[str, Any]:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}


# CLI di test rapido
if __name__ == "__main__":
    ingestor = Ingestor()
    ingestor.run_full_ingestion()