"""
Texture generation + packed/unpacked variants (SPEC + user notes).
Composes MapGenerator + ExternalGeneratorHook; supports ORM/ARM/RMA style packing study.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.external_generator_hook import ExternalGeneratorHook
from core.map_generator import MapGenerator

logger = logging.getLogger("SIGNUM_SENTINEL.GENERATOR_PIPELINE")


class GeneratorPipeline:
    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root = Path(root_dir).resolve() if root_dir else Path.cwd().resolve()
        self.maps = MapGenerator(self.root)
        self.external = ExternalGeneratorHook(self.root)

    def run_external(
        self,
        input_path: Path,
        output_path: Path,
        map_type: str,
        material_name: str,
        variant_name: str,
    ) -> Dict[str, Any]:
        return self.external.generate(input_path, output_path, map_type, material_name, variant_name)

    def packed_channel_plan(self) -> List[str]:
        """Schemes to correlate (single files + packed)."""
        return ["ORM", "ARM", "RMA", "unpacked"]
