import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from core.analysis_benchmark import AnalysisBenchmarkEngine
from core.correlation_engine import CorrelationEngine
from core.dataset_builder import DatasetBuilder
from core.ingestor import Ingestor
from core.knowledge_processor import KnowledgeProcessor
from core.pbr_validator import PBRValidator
from core.pid_mask_engine import PIDMaskEngine
from core.quality_gates import KnowledgeBaseQualityGates


class PipelineOrchestrator:
    """Single pipeline entrypoint for import, processing, analysis and dataset export."""

    SCHEMA_VERSION = "1.0.0"

    def __init__(self, root_dir: Path, importer: Any):
        self.root = Path(root_dir).resolve()
        self.importer = importer
        self.ingestor = Ingestor(str(self.root))
        self.validator = PBRValidator(str(self.root))
        self.gates = KnowledgeBaseQualityGates(self.root)
        self.analysis = AnalysisBenchmarkEngine(self.root)
        self.pid_masks = PIDMaskEngine(self.root)
        self.correlations = CorrelationEngine(self.root)
        self.knowledge_processor = KnowledgeProcessor(self.root)
        self.dataset_builder = DatasetBuilder(self.root)
        self.report_dir = self.root / "06_KNOWLEDGE_BASE" / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def run(self, project_payload: Dict[str, Any] | None = None, skip_import: bool = False) -> Dict[str, Any]:
        import_result = {"status": "skipped", "reason": "skip_import"}
        if not skip_import:
            if not self.importer:
                import_result = {"status": "error", "reason": "importer_missing"}
            elif project_payload is None:
                import_result = {"status": "error", "reason": "project_payload_missing"}
            else:
                import_result = self.importer.run_import(project_payload)
        ingest_result = self.ingestor.run_full_ingestion()
        self.validator.process_all()
        analysis_result = self.analysis.run()
        pid_result = self.pid_masks.run()
        correlation_result = self.correlations.run()
        knowledge_result = self.knowledge_processor.run()
        dataset_result = self.dataset_builder.run()
        gates_result = self.gates.run()
        report = {
            "schema_version": self.SCHEMA_VERSION,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "stages": {
                "import": import_result,
                "ingestion": ingest_result,
                "analysis_benchmark": analysis_result,
                "pid_mask_engine": pid_result,
                "correlation_engine": correlation_result,
                "knowledge_processor": knowledge_result,
                "dataset_builder": dataset_result,
                "quality_gates": gates_result,
            },
        }
        report["status"] = self._derive_status(report)
        report_path = self.report_dir / "pipeline_run_report.json"
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
        report["output_path"] = str(report_path)
        return report

    def run_reports_only(self) -> Dict[str, Any]:
        return self.run(project_payload=None, skip_import=True)

    @staticmethod
    def _derive_status(report: Dict[str, Any]) -> str:
        stages = report.get("stages", {})
        okish = {"ok", "success", "partial_success", "skipped"}
        ingest_status = str(stages.get("ingestion", {}).get("status", "ok")).lower()
        if ingest_status not in okish:
            return "error"
        imp = stages.get("import", {})
        imp_status = str(imp.get("status", "ok")).lower()
        if imp_status not in okish:
            return "error"
        gate_status = str(stages.get("quality_gates", {}).get("status", "ok")).lower()
        if gate_status != "ok":
            return "partial_success"
        return "success"
