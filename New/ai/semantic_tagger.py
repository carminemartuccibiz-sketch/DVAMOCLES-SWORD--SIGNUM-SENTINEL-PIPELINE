"""Derive material tags from text descriptions (provider + AI + optional Ollama)."""

from __future__ import annotations

import re
from typing import Iterable, List, Set

from ai.ollama_client import OllamaClient


def tags_from_description(description: str, max_tags: int = 12) -> List[str]:
    """Lightweight heuristic tags from free text."""
    if not description:
        return []
    words = re.findall(r"[a-zA-Z]{3,}", description.lower())
    stop = {"the", "and", "with", "from", "this", "that", "texture", "material", "showing", "photo", "image"}
    seen: Set[str] = set()
    out: List[str] = []
    for w in words:
        if w in stop or w in seen:
            continue
        seen.add(w)
        out.append(w)
        if len(out) >= max_tags:
            break
    return out


def tags_with_ollama(description: str, client: OllamaClient | None = None) -> List[str]:
    """Ask Ollama for comma-separated PBR tags; fallback to heuristic."""
    c = client or OllamaClient()
    prompt = (
        "List 8 short lowercase tags for this PBR material description, comma separated, no prose:\n\n"
        f"{description[:2000]}"
    )
    raw = c.generate(prompt)
    if not raw:
        return tags_from_description(description)
    parts = [p.strip().lower() for p in raw.replace("\n", ",").split(",") if p.strip()]
    return parts[:12]


def merge_tags(*buckets: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for b in buckets:
        for t in b:
            t = t.strip().lower()
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(t)
    return out
