import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import requests


class PhysicallyBasedKnowledgeFetcher:
    """
    Fetches and parses physicallybased.info reference knowledge
    (IOR/material properties) into machine-readable JSON.
    """

    SOURCE_URL = "https://physicallybased.info/"
    API_BASE_URL = "https://api.physicallybased.info/v2"
    GITHUB_RAW_BASE = "https://raw.githubusercontent.com/AntonPalmqvist/physically-based-api/main/data"
    GITHUB_REPO_DEFAULT = "https://github.com/AntonPalmqvist/physically-based-api.git"

    def __init__(self, root_dir: Path):
        self.root = Path(root_dir).resolve()
        self.kb_sources = self.root / "06_KNOWLEDGE_BASE" / "sources" / "md"
        self.kb_rules = self.root / "06_KNOWLEDGE_BASE" / "rules"
        self.kb_sources.mkdir(parents=True, exist_ok=True)
        self.kb_rules.mkdir(parents=True, exist_ok=True)

    def ingest_official_dataset(self, blob_urls: List[str] | None = None) -> Dict[str, Any]:
        """
        Preferred ingestion path:
        1) Official API (api.physicallybased.info/v2)
        2) GitHub raw backup from physically-based-api repository
        """
        materials = self._fetch_dataset("materials")
        lights = self._fetch_dataset("lightsources")
        cameras = self._fetch_dataset("cameras")
        lenses = self._fetch_dataset("lenses")

        blob_notes = self._normalize_blob_notes(blob_urls or [])
        source_meta = {
            "api_base_url": self.API_BASE_URL,
            "github_raw_base": self.GITHUB_RAW_BASE,
            "datasets": {
                "materials": len(materials),
                "lightsources": len(lights),
                "cameras": len(cameras),
                "lenses": len(lenses),
            },
        }

        out_payload = {
            "source": self.SOURCE_URL,
            "source_meta": source_meta,
            "materials": materials,
            "light_sources": lights,
            "cameras": cameras,
            "lenses": lenses,
            "blob_references": blob_notes,
        }
        out_path = self.kb_rules / "physicallybased_knowledge.json"
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(out_payload, fh, indent=2, ensure_ascii=False)

        return {
            "materials": len(materials),
            "light_sources": len(lights),
            "cameras": len(cameras),
            "lenses": len(lenses),
            "output_path": str(out_path),
            "source": "official_api_or_github_backup",
        }

    def ingest_from_github_repository(self, repo_url: str = "") -> Dict[str, Any]:
        """
        Ingest directly from physically-based-api GitHub repository structure.
        Extracts:
        - physical material values (materials)
        - MaterialX references associated to materials when available
        """
        resolved_repo = (repo_url or self.GITHUB_REPO_DEFAULT).strip()
        raw_data_base = self._github_raw_data_base(resolved_repo)

        materials_payload = self._fetch_raw_json(f"{raw_data_base}/materials.json")
        lights_payload = self._fetch_raw_json(f"{raw_data_base}/lightsources.json")
        cameras_payload = self._fetch_raw_json(f"{raw_data_base}/cameras.json")
        lenses_payload = self._fetch_raw_json(f"{raw_data_base}/lenses.json")

        materials = self._extract_data_list(materials_payload)
        lights = self._extract_data_list(lights_payload)
        cameras = self._extract_data_list(cameras_payload)
        lenses = self._extract_data_list(lenses_payload)

        materialx_links = self._extract_materialx_associations(materials)
        material_types = self._extract_material_types(materials)

        out_payload = {
            "source": "github_repository",
            "repository_url": resolved_repo,
            "raw_data_base": raw_data_base,
            "materials": materials,
            "light_sources": lights,
            "cameras": cameras,
            "lenses": lenses,
            "material_types": material_types,
            "materialx_associations": materialx_links,
        }
        out_path = self.kb_rules / "physicallybased_repository_knowledge.json"
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(out_payload, fh, indent=2, ensure_ascii=False)

        self._cache_provider_json("materials_repository", materials_payload, source="github_repo")
        self._cache_provider_json("lightsources_repository", lights_payload, source="github_repo")
        self._cache_provider_json("cameras_repository", cameras_payload, source="github_repo")
        self._cache_provider_json("lenses_repository", lenses_payload, source="github_repo")
        self._cache_provider_json(
            "materialx_associations",
            {"data": materialx_links, "repository_url": resolved_repo},
            source="github_repo",
        )

        return {
            "materials": len(materials),
            "light_sources": len(lights),
            "cameras": len(cameras),
            "lenses": len(lenses),
            "materialx_links": len(materialx_links),
            "material_types": len(material_types),
            "output_path": str(out_path),
            "source": "github_repository",
        }

    def fetch_markdown(self, source_url: str = "") -> str:
        url = (source_url or self.SOURCE_URL).strip()
        try:
            res = requests.get(url, timeout=20)
            res.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Failed fetching PhysicallyBased source: {exc}") from exc
        return res.text

    def ingest_from_markdown(self, markdown_text: str, blob_urls: List[str] | None = None) -> Dict[str, Any]:
        materials = self._parse_materials_table(markdown_text)
        lights = self._parse_table(markdown_text, "## Light Sources")
        cameras = self._parse_table(markdown_text, "## Cameras")

        blob_notes = self._normalize_blob_notes(blob_urls or [])

        md_path = self.kb_sources / "physicallybased.info.md"
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(markdown_text)

        out_payload = {
            "source": self.SOURCE_URL,
            "materials": materials,
            "light_sources": lights,
            "cameras": cameras,
            "blob_references": blob_notes,
        }
        out_path = self.kb_rules / "physicallybased_knowledge.json"
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(out_payload, fh, indent=2, ensure_ascii=False)
        return {"materials": len(materials), "light_sources": len(lights), "cameras": len(cameras), "output_path": str(out_path)}

    def _fetch_dataset(self, dataset_name: str) -> List[Dict[str, Any]]:
        api_url = f"{self.API_BASE_URL}/{dataset_name}"
        try:
            res = requests.get(api_url, timeout=20)
            res.raise_for_status()
            payload = res.json()
            entries = payload.get("data", []) if isinstance(payload, dict) else []
            if isinstance(entries, list):
                self._cache_provider_json(dataset_name, payload, source="api")
                return entries
        except requests.exceptions.RequestException:
            pass

        gh_url = f"{self.GITHUB_RAW_BASE}/{dataset_name}.json"
        try:
            res = requests.get(gh_url, timeout=20)
            res.raise_for_status()
            payload = res.json()
            entries = payload.get("data", []) if isinstance(payload, dict) else []
            if isinstance(entries, list):
                self._cache_provider_json(dataset_name, payload, source="github_raw")
                return entries
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Failed fetching dataset '{dataset_name}' from API and GitHub: {exc}") from exc

        return []

    def _cache_provider_json(self, dataset_name: str, payload: Dict[str, Any], source: str) -> None:
        out_dir = self.root / "06_KNOWLEDGE_BASE" / "sources" / "api"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"physicallybased_{dataset_name}_{source}.json"
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

    @staticmethod
    def _extract_data_list(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        data = payload.get("data", [])
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        return []

    def _fetch_raw_json(self, raw_url: str) -> Dict[str, Any]:
        try:
            res = requests.get(raw_url, timeout=20)
            res.raise_for_status()
            payload = res.json()
            return payload if isinstance(payload, dict) else {}
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Failed fetching repository JSON: {raw_url} ({exc})") from exc

    @staticmethod
    def _github_raw_data_base(repo_url: str) -> str:
        cleaned = repo_url.strip().replace(".git", "")
        parsed = urlparse(cleaned)
        path = parsed.path.strip("/")
        chunks = [c for c in path.split("/") if c]
        if len(chunks) < 2:
            return PhysicallyBasedKnowledgeFetcher.GITHUB_RAW_BASE
        owner, repo = chunks[0], chunks[1]
        return f"https://raw.githubusercontent.com/{owner}/{repo}/main/data"

    def _extract_materialx_associations(self, materials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        links: List[Dict[str, Any]] = []
        for mat in materials:
            name = str(mat.get("name", mat.get("id", "UnknownMaterial")))
            refs = self._collect_materialx_refs(mat)
            if refs:
                links.append({"material": name, "materialx_refs": sorted(list(refs))})
        return links

    def _collect_materialx_refs(self, obj: Any) -> set[str]:
        found: set[str] = set()
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_l = str(key).lower()
                if "materialx" in key_l or "mtlx" in key_l:
                    if isinstance(value, str) and value.strip():
                        found.add(value.strip())
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str) and item.strip():
                                found.add(item.strip())
                found.update(self._collect_materialx_refs(value))
        elif isinstance(obj, list):
            for item in obj:
                found.update(self._collect_materialx_refs(item))
        elif isinstance(obj, str):
            raw = obj.strip()
            if raw.lower().endswith((".mtlx", ".materialx")) or "materialx" in raw.lower():
                found.add(raw)
        return found

    @staticmethod
    def _extract_material_types(materials: List[Dict[str, Any]]) -> List[str]:
        types: set[str] = set()
        for mat in materials:
            for key in ("type", "category", "material_type", "group"):
                val = mat.get(key)
                if isinstance(val, str) and val.strip():
                    types.add(val.strip())
                elif isinstance(val, list):
                    for item in val:
                        if isinstance(item, str) and item.strip():
                            types.add(item.strip())
        return sorted(types)

    @staticmethod
    def _normalize_blob_notes(blob_urls: List[str]) -> List[Dict[str, Any]]:
        blob_notes = []
        for raw in blob_urls:
            u = (raw or "").strip()
            if not u:
                continue
            if u.startswith("blob:"):
                blob_notes.append({"url": u, "status": "unsupported_direct_fetch", "note": "Blob URLs are browser-local."})
            else:
                blob_notes.append({"url": u, "status": "queued_external_fetch"})
        return blob_notes

    def _parse_materials_table(self, markdown_text: str) -> List[Dict[str, Any]]:
        table = self._extract_table(markdown_text, "## Materials")
        rows = self._table_to_rows(table)
        out: List[Dict[str, Any]] = []
        for row in rows:
            if len(row) < 4:
                continue
            name = row[0].strip()
            color_raw = row[1].strip()
            ior_raw = row[2].strip()
            density = row[3].strip()
            rgb = self._parse_rgb_triplet(color_raw)
            ior = self._parse_first_float(ior_raw)
            out.append({"name": name, "color_rgb": rgb, "ior": ior, "density": density})
        return out

    def _parse_table(self, markdown_text: str, section_header: str) -> List[Dict[str, Any]]:
        table = self._extract_table(markdown_text, section_header)
        rows = self._table_to_rows(table)
        if not rows:
            return []
        headers = [h.strip().lower().replace(" ", "_") for h in rows[0]]
        out: List[Dict[str, Any]] = []
        for row in rows[1:]:
            if not any(c.strip() for c in row):
                continue
            rec = {}
            for idx, h in enumerate(headers):
                rec[h or f"col_{idx}"] = row[idx].strip() if idx < len(row) else ""
            out.append(rec)
        return out

    @staticmethod
    def _extract_table(markdown_text: str, section_header: str) -> str:
        start = markdown_text.find(section_header)
        if start < 0:
            return ""
        tail = markdown_text[start:]
        # next section header or eof
        next_match = re.search(r"\n##\s+", tail[1:])
        end = (next_match.start() + 1) if next_match else len(tail)
        return tail[:end]

    @staticmethod
    def _table_to_rows(table_text: str) -> List[List[str]]:
        lines = [ln.strip() for ln in table_text.splitlines() if ln.strip().startswith("|")]
        rows: List[List[str]] = []
        for ln in lines:
            cells = [c.strip() for c in ln.strip("|").split("|")]
            # skip markdown separator rows
            if all(set(c) <= {"-", " "} for c in cells):
                continue
            rows.append(cells)
        return rows

    @staticmethod
    def _parse_rgb_triplet(color_raw: str) -> Tuple[float, float, float] | None:
        nums = re.findall(r"\d+\.\d+|\d+", color_raw)
        if len(nums) < 3:
            return None
        try:
            return float(nums[0]), float(nums[1]), float(nums[2])
        except ValueError:
            return None

    @staticmethod
    def _parse_first_float(raw: str) -> float | None:
        m = re.search(r"\d+\.\d+|\d+", raw)
        if not m:
            return None
        try:
            return float(m.group(0))
        except ValueError:
            return None
