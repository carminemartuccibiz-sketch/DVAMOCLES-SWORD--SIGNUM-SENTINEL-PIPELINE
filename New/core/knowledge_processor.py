"""
Structured extracts from KB sources into 06_KNOWLEDGE_BASE/parsed/
(read-only on sources; writes parsed JSON summaries).
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("SIGNUM_SENTINEL.KNOWLEDGE_PROCESSOR")


class KnowledgeProcessor:
    def __init__(self, root_dir: Path) -> None:
        self.root = Path(root_dir).resolve()
        self.sources = self.root / "06_KNOWLEDGE_BASE" / "sources"
        self.parsed = self.root / "06_KNOWLEDGE_BASE" / "parsed"
        self.parsed.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, Any]:
        summaries: List[Dict[str, Any]] = []
        for p in sorted(self.sources.rglob("*")):
            if not p.is_file():
                continue
            if p.suffix.lower() not in {".md", ".csv", ".txt"}:
                continue
            try:
                raw = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            h = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]
            summaries.append(
                {
                    "path": str(p.relative_to(self.root)),
                    "bytes": p.stat().st_size,
                    "sha256_16": h,
                    "head": raw[:400].replace("\n", " "),
                }
            )
        out = self.parsed / "source_summaries.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"sources": summaries}, f, indent=2, ensure_ascii=False)
        logger.info("KnowledgeProcessor wrote %s (%d files)", out, len(summaries))
        return {"status": "ok", "count": len(summaries), "path": str(out)}
