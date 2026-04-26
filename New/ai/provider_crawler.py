"""Fetch public provider pages for tags/metadata (best-effort; SPEC)."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List
from urllib.parse import urlparse

logger = logging.getLogger("SIGNUM_SENTINEL.CRAWLER")

try:
    import requests
    from bs4 import BeautifulSoup

    HAS_HTTP = True
except ImportError:
    HAS_HTTP = False


def fetch_page_text(url: str, timeout: int = 25) -> str:
    if not HAS_HTTP:
        return ""
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "SignumSentinel/1.0"})
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.warning("fetch_page_text failed %s: %s", url, e)
        return ""


def ambientcg_meta_from_html(html: str) -> Dict[str, Any]:
    """Very loose tag extraction from AmbientCG-like pages."""
    if not html or not HAS_HTTP:
        return {"tags": [], "title": ""}
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string or "").strip() if soup.title else ""
    text = soup.get_text(" ", strip=True).lower()
    tags: List[str] = []
    for m in re.finditer(r"\b(seamless|tileable|pbr|roughness|normal|albedo|stone|wood|metal|concrete)\b", text):
        t = m.group(1)
        if t not in tags:
            tags.append(t)
    return {"tags": tags[:20], "title": title}


def crawl_url(url: str) -> Dict[str, Any]:
    host = urlparse(url).netloc.lower()
    html = fetch_page_text(url)
    if "ambientcg" in host:
        return ambientcg_meta_from_html(html)
    return {"tags": [], "title": "", "raw_len": len(html)}
