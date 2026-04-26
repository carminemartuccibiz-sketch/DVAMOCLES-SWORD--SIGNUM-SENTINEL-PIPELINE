"""Unified local LLM client via Ollama HTTP API (optional; SPEC)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from utils.runtime_paths import get_app_root

logger = logging.getLogger("SIGNUM_SENTINEL.OLLAMA")


def _load_hw_config() -> Dict[str, Any]:
    p = get_app_root() / "config" / "hardware_limits.json"
    if not p.exists():
        return {"ollama_model": "mistral", "ollama_host": "http://127.0.0.1:11434"}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"ollama_model": "mistral", "ollama_host": "http://127.0.0.1:11434"}


class OllamaClient:
    def __init__(self, host: Optional[str] = None, model: Optional[str] = None) -> None:
        cfg = _load_hw_config()
        self.host = (host or cfg.get("ollama_host", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or cfg.get("ollama_model", "mistral")

    def generate(self, prompt: str, system: str = "") -> str:
        url = f"{self.host}/api/generate"
        payload: Dict[str, Any] = {"model": self.model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return str(body.get("response", "")).strip()
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            logger.warning("Ollama unavailable: %s", e)
            return ""
