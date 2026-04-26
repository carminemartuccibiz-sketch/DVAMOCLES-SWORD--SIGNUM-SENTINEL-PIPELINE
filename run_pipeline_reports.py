import json
from pathlib import Path

from core.import_assistant import AdvancedImporter
from core.pipeline_orchestrator import PipelineOrchestrator


def main() -> int:
    root = Path(__file__).resolve().parent
    importer = AdvancedImporter(root)
    orchestrator = PipelineOrchestrator(root, importer)
    result = orchestrator.run_reports_only()
    print(json.dumps({"status": result.get("status", "unknown"), "output_path": result.get("output_path", "")}, indent=2))
    return 0 if result.get("status") in {"success", "partial_success"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
