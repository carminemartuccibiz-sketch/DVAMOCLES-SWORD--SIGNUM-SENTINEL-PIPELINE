import csv
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, List
from utils.runtime_paths import get_app_root

logger = logging.getLogger("SIGNUM_SENTINEL.KNOWLEDGE_INGESTOR")


class KnowledgeIngestor:
    """
    Ingestione di conoscenza non strutturata (CSV/MD/PDF/TXT)
    in 06_KNOWLEDGE_BASE/sources e index JSON per uso operativo.
    """

    def __init__(self, root_dir: str | None = None):
        self.root = Path(root_dir).resolve() if root_dir else get_app_root()
        self.kb_sources = self.root / "06_KNOWLEDGE_BASE" / "sources"
        self.kb_index = self.root / "06_KNOWLEDGE_BASE" / "kb_index.json"
        self.kb_sources.mkdir(parents=True, exist_ok=True)

    def ingest_files(self, file_paths: List[str]) -> Dict[str, Any]:
        index = self._load_index()
        added = 0
        skipped = 0
        errors: List[str] = []

        for raw in file_paths:
            fp = Path(raw)
            if not fp.exists() or not fp.is_file():
                skipped += 1
                continue
            try:
                kb_rel_path = self._copy_to_kb_sources(fp)
                text = self._extract_text(fp)
                if not text.strip():
                    skipped += 1
                    continue
                if self._doc_exists(index, fp):
                    skipped += 1
                    continue
                rec = {
                    "name": fp.name,
                    "source_path": str(fp),
                    "kb_path": kb_rel_path,
                    "type": fp.suffix.lower().lstrip("."),
                    "size_bytes": fp.stat().st_size,
                    "tokens": self._tokenize(text),
                    "preview": text[:500],
                }
                index["documents"].append(rec)
                added += 1
            except Exception as exc:
                errors.append(f"{fp}: {exc}")

        self._save_index(index)
        return {"added": added, "skipped": skipped, "errors": errors}

    def _copy_to_kb_sources(self, source: Path) -> str:
        ext = source.suffix.lower().lstrip(".") or "misc"
        target_dir = self.kb_sources / ext
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name
        if not target.exists():
            shutil.copy2(source, target)
        return str(target.relative_to(self.root))

    def _extract_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".csv":
            return self._csv_to_text(path)
        if suffix == ".pdf":
            return self._pdf_to_text(path)
        return ""

    @staticmethod
    def _csv_to_text(path: Path) -> str:
        lines: List[str] = []
        with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                lines.append(" | ".join([c.strip() for c in row if c.strip()]))
        return "\n".join(lines)

    @staticmethod
    def _pdf_to_text(path: Path) -> str:
        try:
            from pypdf import PdfReader  # optional dependency
        except Exception:
            logger.warning("pypdf non installato: salto PDF %s", path)
            return ""
        reader = PdfReader(str(path))
        chunks: List[str] = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
        return "\n".join(chunks)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        keep = []
        for token in text.lower().replace("/", " ").replace("_", " ").split():
            clean = "".join(ch for ch in token if ch.isalnum())
            if len(clean) >= 3:
                keep.append(clean)
        return sorted(list(set(keep)))

    def _load_index(self) -> Dict[str, Any]:
        if not self.kb_index.exists():
            return {"documents": []}
        with open(self.kb_index, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_index(self, data: Dict[str, Any]):
        self.kb_index.parent.mkdir(parents=True, exist_ok=True)
        with open(self.kb_index, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def _doc_exists(index: Dict[str, Any], source_path: Path) -> bool:
        src = str(source_path)
        for rec in index.get("documents", []):
            if rec.get("source_path") == src:
                return True
        return False
