"""P-ID / segmentation facade (SPEC name) over SegmentationEngine."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from core.segmentation_engine import SegmentationEngine


class PIDMaskEngine:
    def __init__(self, root_dir: Path) -> None:
        self._engine = SegmentationEngine(root_dir)

    def run(self) -> Dict[str, Any]:
        return self._engine.run()
