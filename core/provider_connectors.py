import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass
class ProviderAssetRecord:
    provider: str
    material_name: str
    variant: str
    file_name: str
    file_url: str
    map_type: str
    format: str
    resolution: str
    tech_res: str
    color_space: str = "Unknown"
    bit_depth: str = "Unknown"
    endpoint: str = ""
    source_raw: str = ""
    tags: List[str] | None = None
    description: str = ""
    asset_kind: str = "material"

    def to_file_record(self) -> Dict[str, Any]:
        source_raw = self.source_raw or self.file_url or self.file_name
        checksum = hashlib.sha256(source_raw.encode("utf-8")).hexdigest()
        return {
            "name": self.file_name,
            "path": self.file_url,
            "provider_hint": self.provider,
            "format": self.format.upper(),
            "map_type": self.map_type.upper(),
            "naming_confidence": 1.0,
            "resolution": self.resolution,
            "tech_res": self.tech_res,
            "bit_depth": self.bit_depth,
            "color_space": self.color_space,
            "is_duplicate": False,
            "derived_from": [],
            "source_raw": source_raw,
            "process": "api_ingest",
            "tool": f"{self.provider.lower()}_api",
            "ai_description": "",
            "visual_validation": "Unknown",
            "visual_confidence": 0.0,
            "metadata_confidence": 1.0,
            "provenance": {
                "provider": self.provider,
                "endpoint": self.endpoint,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "checksum_sha256": checksum,
            },
        }


class ProviderConnector(ABC):
    provider_name: str = "UnknownProvider"

    @abstractmethod
    def fetch_assets(self, query: str = "", limit: int = 25) -> List[ProviderAssetRecord]:
        raise NotImplementedError


class MockProviderConnector(ProviderConnector):
    provider_name = "MockProvider"

    def __init__(self, root_dir: Path):
        self.root = Path(root_dir).resolve()
        self.mock_path = self.root / "config" / "providers_mock_assets.json"

    def fetch_assets(self, query: str = "", limit: int = 25) -> List[ProviderAssetRecord]:
        data = self._load_source()
        raw_assets = data.get("assets", [])
        query_l = query.strip().lower()
        rows = []
        for item in raw_assets:
            material_name = str(item.get("material_name", "UnknownMaterial")).strip() or "UnknownMaterial"
            if query_l and query_l not in material_name.lower():
                continue
            rows.append(
                ProviderAssetRecord(
                    provider=str(item.get("provider", self.provider_name)),
                    material_name=material_name,
                    variant=str(item.get("variant", "SOURCE")),
                    file_name=str(item.get("file_name", "")),
                    file_url=str(item.get("file_url", "")),
                    map_type=str(item.get("map_type", "UNKNOWN")),
                    format=str(item.get("format", "PNG")),
                    resolution=str(item.get("resolution", "UNKNOWN")),
                    tech_res=str(item.get("tech_res", "Unknown")),
                    color_space=str(item.get("color_space", "Unknown")),
                    bit_depth=str(item.get("bit_depth", "Unknown")),
                    endpoint=str(item.get("endpoint", "mock://assets")),
                    source_raw=str(item.get("source_raw", "")),
                    tags=item.get("tags", []),
                    description=str(item.get("description", "")),
                    asset_kind=str(item.get("asset_kind", "material")),
                )
            )
            if len(rows) >= max(1, limit):
                break
        return rows

    def _load_source(self) -> Dict[str, Any]:
        if self.mock_path.exists():
            with open(self.mock_path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            return loaded if isinstance(loaded, dict) else {"assets": []}
        return {"assets": []}


class HttpJsonProviderConnector(ProviderConnector):
    provider_name = "HttpJsonProvider"

    def __init__(self, provider_name: str, base_url: str, endpoint: str = "/assets"):
        self.provider_name = provider_name
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint

    def fetch_assets(self, query: str = "", limit: int = 25) -> List[ProviderAssetRecord]:
        params = urlencode({"q": query, "limit": max(1, limit)})
        url = f"{self.base_url}{self.endpoint}?{params}"
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        items = payload.get("assets", []) if isinstance(payload, dict) else []
        out: List[ProviderAssetRecord] = []
        for item in items[:limit]:
            out.append(
                ProviderAssetRecord(
                    provider=self.provider_name,
                    material_name=str(item.get("material_name", "UnknownMaterial")),
                    variant=str(item.get("variant", "SOURCE")),
                    file_name=str(item.get("file_name", "")),
                    file_url=str(item.get("file_url", "")),
                    map_type=str(item.get("map_type", "UNKNOWN")),
                    format=str(item.get("format", "PNG")),
                    resolution=str(item.get("resolution", "UNKNOWN")),
                    tech_res=str(item.get("tech_res", "Unknown")),
                    color_space=str(item.get("color_space", "Unknown")),
                    bit_depth=str(item.get("bit_depth", "Unknown")),
                    endpoint=url,
                    source_raw=str(item.get("source_raw", "")),
                    tags=item.get("tags", []),
                    description=str(item.get("description", "")),
                    asset_kind=str(item.get("asset_kind", "material")),
                )
            )
        return out
