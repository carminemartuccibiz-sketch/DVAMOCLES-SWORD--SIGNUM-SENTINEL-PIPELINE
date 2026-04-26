"""
Cross-file correlations: RAW vs CUSTOM, variants, packing schemes.
Appends to 04_DATASET/correlations.json (immutable append per SPEC note).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("SIGNUM_SENTINEL.CORRELATION")


class CorrelationEngine:
    def __init__(self, root_dir: Path) -> None:
        self.root = Path(root_dir).resolve()
        self.processed = self.root / "03_PROCESSED"
        self.raw = self.root / "01_RAW_ARCHIVE"
        self.custom = self.root / "02_CUSTOM"
        self.out = self.root / "04_DATASET" / "correlations.json"
        self.out.parent.mkdir(parents=True, exist_ok=True)

    def _load_existing(self) -> List[Dict[str, Any]]:
        if not self.out.exists():
            return []
        try:
            with open(self.out, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else data.get("records", [])
        except Exception:
            logger.exception("correlations read failed")
            return []

    def run(self) -> Dict[str, Any]:
        new_rows: List[Dict[str, Any]] = []
        ts = datetime.now(timezone.utc).isoformat()
        for manifest in sorted(self.processed.glob("*/*/manifest.json")):
            try:
                with open(manifest, encoding="utf-8") as f:
                    payload = json.load(f)
            except Exception:
                continue
            provider = manifest.parent.parent.name
            material = manifest.parent.name
            variants = payload.get("variants") or {}
            for vname, vdata in variants.items():
                files = vdata.get("files") or []
                new_rows.append(
                    {
                        "timestamp_utc": ts,
                        "kind": "variant_file_set",
                        "provider": provider,
                        "material": material,
                        "variant": vname,
                        "file_count": len(files),
                        "map_types": sorted({str(f.get("map_type", "")).lower() for f in files}),
                        "manifest_path": str(manifest),
                    }
                )
        existing = self._load_existing()
        merged = existing + new_rows
        with open(self.out, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        return {"status": "ok", "appended": len(new_rows), "path": str(self.out)}
