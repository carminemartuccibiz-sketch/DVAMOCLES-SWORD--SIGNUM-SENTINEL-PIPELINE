import logging
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests


logger = logging.getLogger("SIGNUM_SENTINEL.API_FETCHER")


class AmbientCGFetcher:
    BASE_URL = "https://ambientcg.com/api/v3/assets"
    CATEGORIES_URL = "https://ambientcg.com/api/v3/categories"
    COLLECTIONS_URL = "https://ambientcg.com/api/v3/collections"
    RSS_URL = "https://ambientcg.com/api/v3/rss"

    def __init__(self, root_dir: Path):
        self.root = Path(root_dir).resolve()
        self.cache_dir = self.root / "temp" / "cache" / "ambientcg"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.bulk_state_path = self.cache_dir / "bulk_resume_state.json"

    def search_assets(self, query: str, limit: int = 25) -> List[Dict[str, Any]]:
        params = {
            "q": query,
            "type": "material",
            "include": "title,downloads",
            "limit": max(1, int(limit)),
        }
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"AmbientCG search failed: {exc}") from exc

        found = data.get("assets") if isinstance(data, dict) else None
        if isinstance(found, list):
            return found
        return []

    def list_assets_page(self, query: str = "", page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        offset = (page - 1) * page_size
        params = {
            "q": query,
            "type": "material",
            "include": "title,downloads,tags",
            "limit": page_size,
            "offset": offset,
            "sort": "popular",
        }
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"AmbientCG catalog page fetch failed: {exc}") from exc

        assets = data.get("assets", []) if isinstance(data, dict) else []
        total = int(data.get("totalResults", len(assets))) if isinstance(data, dict) else len(assets)
        return {"page": page, "page_size": page_size, "total_results": total, "assets": assets}

    def list_assets_offset(self, query: str = "", limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        limit = max(1, min(100, int(limit)))
        offset = max(0, int(offset))
        params = {
            "q": query,
            "type": "material",
            "include": "title,downloads,tags,dataType,description",
            "limit": limit,
            "offset": offset,
            "sort": "popular",
        }
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"AmbientCG catalog offset fetch failed: {exc}") from exc

        assets = data.get("assets", []) if isinstance(data, dict) else []
        total = int(data.get("totalResults", len(assets))) if isinstance(data, dict) else len(assets)
        return {"offset": offset, "limit": limit, "total_results": total, "assets": assets}

    def fetch_categories(self) -> List[Dict[str, Any]]:
        try:
            response = requests.get(self.CATEGORIES_URL, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"AmbientCG categories fetch failed: {exc}") from exc
        return payload if isinstance(payload, list) else []

    def fetch_collections(self) -> List[Dict[str, Any]]:
        try:
            response = requests.get(self.COLLECTIONS_URL, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"AmbientCG collections fetch failed: {exc}") from exc
        return payload if isinstance(payload, list) else []

    def fetch_rss(self) -> str:
        try:
            response = requests.get(self.RSS_URL, timeout=20)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"AmbientCG RSS fetch failed: {exc}") from exc
        return response.text

    def export_catalog_page(self, query: str, page: int, page_size: int = 20) -> Path:
        payload = self.list_assets_page(query=query, page=page, page_size=page_size)
        out_dir = self.root / "06_KNOWLEDGE_BASE" / "sources" / "api"
        out_dir.mkdir(parents=True, exist_ok=True)
        q = (query or "all").strip().replace(" ", "_")
        out_path = out_dir / f"ambientcg_catalog_{q}_p{payload['page']}_n{payload['page_size']}.json"
        with open(out_path, "w", encoding="utf-8") as fh:
            import json

            json.dump(payload, fh, indent=2, ensure_ascii=False)
        return out_path

    def get_asset_metadata(self, asset_id: str) -> Dict[str, Any]:
        asset = self._resolve_asset(asset_id)
        return {
            "provider": "AmbientCG",
            "asset_id": asset.get("id", asset_id),
            "title": asset.get("title", ""),
            "downloads": asset.get("downloads", []),
            "tags": asset.get("tags", []),
            "data_type": asset.get("dataType", ""),
            "description": asset.get("description", ""),
        }

    def download_all_variants(
        self,
        asset_id: str,
        dest_folder: Optional[Path] = None,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        asset_id = asset_id.strip()
        if not asset_id:
            raise ValueError("asset_id is required")
        asset = self._resolve_asset(asset_id)
        downloads = asset.get("downloads", []) if isinstance(asset, dict) else []
        zip_items = [item for item in downloads if str(item.get("extension", "")).lower() == "zip"]
        if not zip_items:
            raise RuntimeError(f"No zip variants found for {asset_id}")

        out_root = Path(dest_folder).resolve() if dest_folder else (self.root / "temp" / "staging_web" / asset_id)
        out_root.mkdir(parents=True, exist_ok=True)
        extracted_paths: List[str] = []
        variants_info: List[Dict[str, Any]] = []
        total = len(zip_items)
        done = 0

        for item in zip_items:
            attr = str(item.get("attributes", "SOURCE")).strip() or "SOURCE"
            variant_name = self._sanitize_variant_name(attr)
            url = str(item.get("url", "")).strip()
            if not url:
                continue
            cache_zip = self.cache_dir / f"{asset_id}_{variant_name}.zip"
            self._download_zip(url, cache_zip, progress_cb=None)
            variant_dir = out_root / variant_name
            variant_dir.mkdir(parents=True, exist_ok=True)
            self._extract_zip(cache_zip, variant_dir)
            extracted_paths.append(str(variant_dir))
            variants_info.append(
                {
                    "variant": variant_name,
                    "attributes": attr,
                    "attribute_parsed": self._parse_variant_attributes(attr),
                    "url": url,
                    "files": self._list_variant_files(variant_dir),
                }
            )
            done += 1
            if progress_cb is not None:
                progress_cb(done, total)

        context = {
            "provider": "AmbientCG",
            "asset_id": asset.get("id", asset_id),
            "title": asset.get("title", ""),
            "description": asset.get("description", ""),
            "tags": asset.get("tags", []),
            "data_type": asset.get("dataType", ""),
            "download_variants": variants_info,
        }
        context_path = out_root / "asset_context.json"
        with open(context_path, "w", encoding="utf-8") as fh:
            json.dump(context, fh, indent=2, ensure_ascii=False)

        logger.info("AmbientCG all variants extracted: %s -> %s", asset_id, out_root)
        return {"asset_id": asset_id, "root_path": str(out_root), "context_path": str(context_path), "variants": extracted_paths}

    def load_bulk_resume_state(self) -> Dict[str, Any]:
        if not self.bulk_state_path.exists():
            return {}
        try:
            with open(self.bulk_state_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def save_bulk_resume_state(self, payload: Dict[str, Any]) -> None:
        with open(self.bulk_state_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

    def clear_bulk_resume_state(self) -> None:
        if self.bulk_state_path.exists():
            self.bulk_state_path.unlink(missing_ok=True)

    def download_material(
        self,
        asset_id: str,
        resolution: str = "2K",
        format: str = "PNG",
        dest_folder: Optional[Path] = None,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """
        Download an ambientCG asset zip into cache and extract into dest_folder.
        Returns extraction directory path.
        """
        asset_id = asset_id.strip()
        if not asset_id:
            raise ValueError("asset_id is required")

        asset = self._resolve_asset(asset_id)
        download_url = self._select_download_url(asset, resolution=resolution, fmt=format)
        if not download_url:
            raise RuntimeError(f"No downloadable zip found for {asset_id} ({resolution}, {format})")

        cache_zip = self.cache_dir / f"{asset_id}_{resolution.upper()}_{format.upper()}.zip"
        self._download_zip(download_url, cache_zip, progress_cb=progress_cb)

        out_dir = Path(dest_folder).resolve() if dest_folder else (self.root / "temp" / "staging_web" / asset_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        self._extract_zip(cache_zip, out_dir)

        logger.info("AmbientCG asset extracted: %s -> %s", asset_id, out_dir)
        return out_dir

    def _download_zip(
        self,
        url: str,
        cache_zip: Path,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        if not cache_zip.exists():
            try:
                with requests.get(url, stream=True, timeout=45) as resp:
                    resp.raise_for_status()
                    total = int(resp.headers.get("Content-Length", "0") or 0)
                    downloaded = 0
                    with open(cache_zip, "wb") as fh:
                        for chunk in resp.iter_content(chunk_size=1024 * 128):
                            if chunk:
                                fh.write(chunk)
                                downloaded += len(chunk)
                                if progress_cb is not None:
                                    progress_cb(downloaded, total)
            except requests.exceptions.RequestException as exc:
                raise RuntimeError(f"AmbientCG download failed: {exc}") from exc
        elif progress_cb is not None:
            cached_size = cache_zip.stat().st_size
            progress_cb(cached_size, cached_size)

    @staticmethod
    def _extract_zip(cache_zip: Path, out_dir: Path) -> None:
        try:
            with zipfile.ZipFile(cache_zip, "r") as zf:
                zf.extractall(out_dir)
        except zipfile.BadZipFile as exc:
            raise RuntimeError(f"Invalid zip downloaded: {cache_zip}") from exc

    @staticmethod
    def _sanitize_variant_name(attr: str) -> str:
        out = attr.upper().replace("-", "_")
        out = re.sub(r"[^A-Z0-9_]+", "_", out).strip("_")
        return out or "SOURCE"

    @staticmethod
    def _list_variant_files(variant_dir: Path) -> List[Dict[str, Any]]:
        texture_ext = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".tga", ".mtlx", ".materialx"}
        rows: List[Dict[str, Any]] = []
        for fp in sorted(variant_dir.rglob("*"), key=lambda p: str(p).lower()):
            if not fp.is_file() or fp.suffix.lower() not in texture_ext:
                continue
            rows.append({"name": fp.name, "relative_path": str(fp.relative_to(variant_dir))})
        return rows

    @staticmethod
    def _parse_variant_attributes(attr: str) -> Dict[str, str]:
        cleaned = str(attr or "").strip().upper().replace("_", "-")
        tokens = [tok for tok in cleaned.split("-") if tok]
        resolution = next((tok for tok in tokens if re.match(r"^\d+K$", tok)), "")
        fmt_map = {"JPEG": "JPG", "TIFF": "TIF"}
        fmt = next((fmt_map.get(tok, tok) for tok in tokens if tok in {"PNG", "JPG", "JPEG", "TIF", "TIFF", "EXR"}), "")
        return {"resolution": resolution, "format": fmt}

    def _resolve_asset(self, asset_id: str) -> Dict[str, Any]:
        direct_params = {
            "id": asset_id,
            "type": "material",
            "include": "title,downloads",
            "limit": 1,
        }
        try:
            response = requests.get(self.BASE_URL, params=direct_params, timeout=15)
            response.raise_for_status()
            data = response.json()
            direct_assets = data.get("assets", []) if isinstance(data, dict) else []
            if direct_assets:
                return direct_assets[0]
        except requests.exceptions.RequestException:
            pass

        candidates = self.search_assets(asset_id, limit=20)
        asset_id_l = asset_id.lower()
        exact = next((a for a in candidates if str(a.get("id", "")).lower() == asset_id_l), None)
        if exact:
            return exact
        if candidates:
            return candidates[0]
        raise RuntimeError(f"Asset not found on ambientCG: {asset_id}")

    @staticmethod
    def _select_download_url(asset: Dict[str, Any], resolution: str, fmt: str) -> str:
        wanted = f"{resolution.upper()}-{fmt.upper()}"
        downloads = asset.get("downloads", [])
        if not isinstance(downloads, list):
            return ""
        exact = next(
            (
                str(item.get("url", "")).strip()
                for item in downloads
                if str(item.get("extension", "")).lower() == "zip" and str(item.get("attributes", "")).upper() == wanted
            ),
            "",
        )
        if exact:
            return exact
        fallback = next(
            (
                str(item.get("url", "")).strip()
                for item in downloads
                if str(item.get("extension", "")).lower() == "zip"
            ),
            "",
        )
        return fallback
