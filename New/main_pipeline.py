"""
CLI / headless pipeline (SPEC PART 6).
Run from repository New/: python main_pipeline.py [--reports-only]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from utils.logger_setup import init_session_logging
from utils.runtime_paths import get_app_root


def main() -> int:
    init_session_logging()
    root = get_app_root()

    parser = argparse.ArgumentParser(description="SIGNUM SENTINEL headless pipeline")
    parser.add_argument(
        "--reports-only",
        action="store_true",
        help="Skip import; run ingest through dataset + gates",
    )
    parser.add_argument(
        "--project-json",
        type=Path,
        default=None,
        help="Optional path to staging project JSON for import stage",
    )
    args = parser.parse_args()

    from core.import_assistant import AdvancedImporter
    from core.pipeline_orchestrator import PipelineOrchestrator

    importer = AdvancedImporter(root)
    orch = PipelineOrchestrator(root, importer)
    payload = None
    if args.project_json and args.project_json.exists():
        with open(args.project_json, encoding="utf-8") as f:
            payload = json.load(f)
    if args.reports_only:
        report = orch.run_reports_only()
    else:
        report = orch.run(project_payload=payload, skip_import=payload is None)
    print(json.dumps({"status": report.get("status"), "output_path": report.get("output_path")}, indent=2))
    return 0 if report.get("status") != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
