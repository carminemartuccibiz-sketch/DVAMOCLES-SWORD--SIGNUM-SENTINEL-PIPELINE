"""
Layer 0 reference: profiles from KB JSON + optional PhysicallyBased API dumps.
Does not mutate KB; returns validation hints and physics_validated flags (Protocol v3).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("SIGNUM_SENTINEL.ORACLE")


class PhysicsOracle:
    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root = Path(root_dir).resolve() if root_dir else Path.cwd().resolve()
        self.rules_path = self.root / "06_KNOWLEDGE_BASE" / "rules" / "pbr_rules.json"
        self.pb_materials = self.root / "06_KNOWLEDGE_BASE" / "sources" / "api" / "physicallybased_materials_api.json"
        self._rules = self._load_json(self.rules_path) or {}
        self._pb = self._load_json(self.pb_materials)

    @staticmethod
    def _load_json(p: Path) -> Optional[Dict[str, Any]]:
        if not p.exists():
            return None
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.exception("Oracle failed loading %s", p)
            return None

    def list_profiles(self) -> List[str]:
        prof = (self._rules or {}).get("profiles") or {}
        return sorted(prof.keys())

    def profile(self, name: str) -> Dict[str, Any]:
        prof = (self._rules or {}).get("profiles") or {}
        return dict(prof.get(name, {}))

    def suggest_profile_for_material(self, category_hint: str) -> str:
        h = (category_hint or "").lower()
        for key in self.list_profiles():
            if key.lower() in h or h in key.lower():
                return key
        return "dielectric"

    def validate_record_hints(self, map_types_found: List[str], profile_name: str) -> Dict[str, Any]:
        """Non-destructive check: map presence vs generic PBR expectation."""
        prof = self.profile(profile_name)
        expected = {"albedo", "normal", "roughness", "metallic", "ao", "height"}
        found = {m.lower() for m in map_types_found}
        missing = sorted(expected - found)
        return {
            "profile": profile_name,
            "profile_snippet": prof,
            "missing_core_maps": missing,
            "physics_validated": len(missing) == 0,
            "physics_ref_source": str(self.rules_path),
        }
