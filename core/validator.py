import json
import logging
from pathlib import Path
from core.map_generator import MapGenerator

logger = logging.getLogger("SIGNUM_SENTINEL.VALIDATOR")

class PBRValidator:
    """Valida il set PBR e ordina la generazione delle mappe mancanti."""

    def __init__(self, root_dir=None):
        self.root = Path(root_dir) if root_dir else Path(__file__).parent.parent
        self.processed_dir = self.root / "03_PROCESSED"
        self.generator = MapGenerator()

    def process_all(self):
        """Scansiona 03_PROCESSED e ripara i materiali incompleti."""
        for provider_dir in self.processed_dir.iterdir():
            if provider_dir.is_dir():
                for mat_dir in provider_dir.iterdir():
                    if mat_dir.is_dir():
                        self._check_and_fix(mat_dir)

    def _check_and_fix(self, mat_dir: Path):
        manifest_path = mat_dir / "manifest.json"
        if not manifest_path.exists(): return

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        found = set(data["coverage"]["maps_found"])
        albedo_file = next((f["original_name"] for f in data["files"] if f["map_type"] == "albedo"), None)

        if not albedo_file: return

        # Generazione automatica se mancano mappe core
        if "normal" not in found:
            out = mat_dir / f"{mat_dir.name}_Normal_GEN.png"
            if self.generator.generate_normal(mat_dir / albedo_file, out):
                found.add("normal")
                data["files"].append({"original_name": out.name, "map_type": "normal", "is_generated": True})

        if "roughness" not in found:
            out = mat_dir / f"{mat_dir.name}_Roughness_GEN.png"
            if self.generator.generate_roughness(mat_dir / albedo_file, out):
                found.add("roughness")
                data["files"].append({"original_name": out.name, "map_type": "roughness", "is_generated": True})

        data["coverage"]["maps_found"] = list(found)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)