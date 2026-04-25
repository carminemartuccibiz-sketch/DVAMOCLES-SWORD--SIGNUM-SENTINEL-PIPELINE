import json
import re
import subprocess
from typing import Dict, List, Any


class ProcessDescriptionParser:
    """
    Converte testo libero in un payload strutturato per process.json.
    Se disponibile, usa Ollama; altrimenti fallback deterministico a regole.
    """

    def __init__(self, ollama_model: str = "mistral"):
        self.ollama_model = ollama_model

    def parse(self, description: str, output_name: str = "", derived_from: List[str] | None = None) -> Dict[str, Any]:
        text = (description or "").strip()
        sources = derived_from or self._infer_sources(text)
        if not text:
            return {
                "process": "manual_unspecified",
                "tool": "unknown",
                "generated_from": sources,
                "confidence": 0.45,
            }

        ai_payload = self._parse_with_ollama(text)
        if ai_payload:
            ai_payload.setdefault("generated_from", sources)
            ai_payload.setdefault("confidence", 0.8)
            return ai_payload
        return self._parse_rule_based(text, output_name=output_name, generated_from=sources)

    def _parse_with_ollama(self, text: str) -> Dict[str, Any] | None:
        prompt = f"""
Convert this description to strict JSON with keys:
process, tool, generated_from, confidence.
Description: {text}
Respond ONLY JSON.
"""
        try:
            result = subprocess.run(
                ["ollama", "run", self.ollama_model, prompt],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            raw = (result.stdout or "").strip()
            if not raw:
                return None
            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1 or end == -1:
                return None
            parsed = json.loads(raw[start : end + 1])
            if not isinstance(parsed, dict):
                return None
            return parsed
        except Exception:
            return None

    def _parse_rule_based(self, text: str, output_name: str, generated_from: List[str]) -> Dict[str, Any]:
        lower = text.lower()
        tool = "unknown"
        if "materialize" in lower:
            tool = "Materialize"
        elif "substance" in lower:
            tool = "Substance Designer"
        elif "photoshop" in lower:
            tool = "Adobe Photoshop"
        elif "blender" in lower:
            tool = "Blender"
        elif "opencv" in lower:
            tool = "OpenCV"

        process = "custom_transform"
        if "normal" in lower and "albedo" in lower:
            process = "normal_from_albedo"
        elif "height" in lower and ("normal" in lower or "displacement" in lower):
            process = "height_from_normal"
        elif "roughness" in lower and "albedo" in lower:
            process = "roughness_from_albedo"
        elif "convert" in lower or "conversion" in lower:
            process = "format_conversion"
        elif "upscale" in lower:
            process = "upscale"

        return {
            "process": process,
            "tool": tool,
            "generated_from": generated_from,
            "confidence": 0.7,
            "output": output_name,
        }

    @staticmethod
    def _infer_sources(text: str) -> List[str]:
        aliases = {
            "albedo": r"\balbedo\b|\bbase ?color\b|\bcolor\b|\bdiffuse\b",
            "normal": r"\bnormal\b",
            "roughness": r"\broughness\b|\brough\b",
            "ao": r"\bao\b|\bambient ?occlusion\b|\bocclusion\b",
            "height": r"\bheight\b|\bdisplacement\b|\bdisp\b",
            "metallic": r"\bmetallic\b|\bmetalness\b|\bmetal\b",
        }
        found: List[str] = []
        lower = (text or "").lower()
        for canonical, pattern in aliases.items():
            if re.search(pattern, lower):
                found.append(canonical)
        return found
