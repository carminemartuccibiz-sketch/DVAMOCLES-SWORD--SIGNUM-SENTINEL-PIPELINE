import json
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List


class ExternalGeneratorHook:
    """Optional external generator bridge (Materialize or custom scripts)."""

    DEFAULT_CONFIG = {
        "enabled": False,
        "materialize_dir": "C:/Users/Carmine/Desktop/materialize",
        "materialize_executable": "",
        "command_template": "",
    }

    def __init__(self, root_dir: Path):
        self.root = Path(root_dir).resolve()
        self.config_path = self.root / "config" / "external_generator.json"
        self.config = self._load_config()

    def generate(
        self,
        input_path: Path,
        output_path: Path,
        map_type: str,
        material_name: str,
        variant_name: str,
    ) -> Dict[str, Any]:
        if not self.config.get("enabled", False):
            return {"status": "disabled", "used": False}

        command = self._build_command(
            input_path=input_path,
            output_path=output_path,
            map_type=map_type,
            material_name=material_name,
            variant_name=variant_name,
        )
        if not command:
            return {"status": "unavailable", "used": False, "reason": "No external command resolved"}

        try:
            proc = subprocess.run(command, check=False, capture_output=True, text=True, shell=False)
            ok = proc.returncode == 0 and output_path.exists()
            return {
                "status": "ok" if ok else "failed",
                "used": ok,
                "command": command,
                "return_code": proc.returncode,
                "stdout": proc.stdout[-1000:],
                "stderr": proc.stderr[-1000:],
            }
        except Exception as exc:
            return {"status": "error", "used": False, "reason": str(exc)}

    def _build_command(
        self,
        input_path: Path,
        output_path: Path,
        map_type: str,
        material_name: str,
        variant_name: str,
    ) -> List[str]:
        template = str(self.config.get("command_template", "") or "").strip()
        values = {
            "input": str(input_path),
            "output": str(output_path),
            "map_type": map_type.lower(),
            "material": material_name,
            "variant": variant_name,
            "root": str(self.root),
        }
        if template:
            rendered = template.format(**values).strip()
            return shlex.split(rendered, posix=False)

        executable = self._resolve_materialize_executable()
        if not executable:
            return []
        # Materialize has no documented stable CLI for full map generation.
        # We still allow launching external toolchain with a generic argument convention.
        return [str(executable), str(input_path), str(output_path), map_type.lower()]

    def _resolve_materialize_executable(self) -> Path | None:
        explicit = str(self.config.get("materialize_executable", "") or "").strip()
        if explicit:
            candidate = Path(explicit)
            if candidate.exists():
                return candidate

        materialize_dir = Path(str(self.config.get("materialize_dir", ""))).resolve()
        names = ("Materialize.exe", "materialize.exe", "Materialize.x86_64", "Materialize")
        for name in names:
            candidate = materialize_dir / name
            if candidate.exists():
                return candidate
        return None

    def _load_config(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                if isinstance(loaded, dict):
                    cfg = dict(self.DEFAULT_CONFIG)
                    cfg.update(loaded)
                    return cfg
            except Exception:
                pass
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as fh:
            json.dump(self.DEFAULT_CONFIG, fh, indent=2, ensure_ascii=False)
        return dict(self.DEFAULT_CONFIG)
