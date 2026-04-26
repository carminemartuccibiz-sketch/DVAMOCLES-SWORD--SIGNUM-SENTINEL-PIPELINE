import json
from pathlib import Path
from typing import Any, Dict, List


class KnowledgeBaseQualityGates:
    """
    Lightweight KB consistency gates used by ingestion pipeline.
    Non-destructive checks only: read-only validation of required files
    and minimal schema consistency between KB index and manifests.
    """

    def __init__(self, root_dir: Path):
        self.root = Path(root_dir).resolve()
        self.kb_dir = self.root / "06_KNOWLEDGE_BASE"
        self.naming_map_path = self.kb_dir / "mappings" / "naming_map.json"
        self.pbr_rules_path = self.kb_dir / "rules" / "pbr_rules.json"
        self.kb_index_path = self.kb_dir / "kb_index.json"
        self.manifest_dir = self.kb_dir / "Manifests"

    def run(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []

        self._check_naming_map(errors, warnings)
        self._check_pbr_rules(errors, warnings)
        self._check_kb_index(errors, warnings)
        self._check_manifests(errors, warnings)

        return {
            "status": "ok" if not errors else "error",
            "errors": errors,
            "warnings": warnings,
        }

    def _check_naming_map(self, errors: List[str], warnings: List[str]) -> None:
        data = self._load_json(self.naming_map_path)
        if data is None:
            errors.append(f"Missing or invalid naming map: {self.naming_map_path}")
            return
        map_patterns = data.get("map_patterns", {})
        if not isinstance(map_patterns, dict) or not map_patterns:
            errors.append("naming_map.json: `map_patterns` missing or empty")
        role_aliases = data.get("role_aliases", {})
        if not isinstance(role_aliases, dict) or not role_aliases:
            warnings.append("naming_map.json: `role_aliases` missing or empty")

    def _check_pbr_rules(self, errors: List[str], warnings: List[str]) -> None:
        data = self._load_json(self.pbr_rules_path)
        if data is None:
            errors.append(f"Missing or invalid PBR rules: {self.pbr_rules_path}")
            return
        map_rules = data.get("map_rules", {})
        profiles = data.get("profiles", {})
        if not isinstance(map_rules, dict) or not map_rules:
            errors.append("pbr_rules.json: `map_rules` missing or empty")
        if not isinstance(profiles, dict) or not profiles:
            warnings.append("pbr_rules.json: `profiles` missing or empty")

    def _check_kb_index(self, errors: List[str], warnings: List[str]) -> None:
        data = self._load_json(self.kb_index_path)
        if data is None:
            warnings.append(f"kb_index.json not available or invalid: {self.kb_index_path}")
            return
        docs = data.get("documents", [])
        if not isinstance(docs, list):
            errors.append("kb_index.json: `documents` must be a list")
            return
        if not docs:
            warnings.append("kb_index.json: `documents` is empty")

    def _check_manifests(self, errors: List[str], warnings: List[str]) -> None:
        if not self.manifest_dir.exists():
            warnings.append(f"Manifest directory not found: {self.manifest_dir}")
            return
        manifest_files = sorted(self.manifest_dir.glob("*_manifest.json"))
        if not manifest_files:
            warnings.append("No manifests found in KB")
            return

        for manifest_path in manifest_files:
            data = self._load_json(manifest_path)
            if data is None:
                errors.append(f"Invalid manifest JSON: {manifest_path.name}")
                continue
            identity = data.get("identity", {})
            if not isinstance(identity, dict):
                errors.append(f"{manifest_path.name}: missing `identity` object")
                continue
            material_name = str(identity.get("material_name", "")).strip()
            provider = str(identity.get("provider", "")).strip()
            if not material_name:
                errors.append(f"{manifest_path.name}: `identity.material_name` missing")
            if not provider:
                warnings.append(f"{manifest_path.name}: `identity.provider` missing")
            hierarchy = data.get("hierarchy", {})
            if not isinstance(hierarchy, dict):
                errors.append(f"{manifest_path.name}: `hierarchy` must be an object")

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            return loaded if isinstance(loaded, dict) else None
        except Exception:
            return None
