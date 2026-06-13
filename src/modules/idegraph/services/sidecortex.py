"""
@project   CodeCortex
@package   modules.idegraph.services
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.services
:standard: CODDY-IdeGraph-v1.0

SideCortex — Service layer for cross-IDE ingestion operations.
"""

import json
import os
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.modules.idegraph.core.orchestrator import SideCortexOrchestrator
from src.modules.idegraph.domain.engram import Engram, IDEInfo
from src.modules.idegraph.services.engram import Engram as EngramProcessor
from src.modules.idegraph.services.export import Export as Exporter
from src.modules.idegraph.services.resolver import Resolver as ProjectResolver
from src.modules.idegraph.services.storage import Storage
from src.modules.idegraph.services.ide_harvest import IdeHarvest
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)


class SideCortex:
    def __init__(self, output_dir: Optional[Path] = None, db=None):
        self.orchestrator = SideCortexOrchestrator()
        self.engram_processor = EngramProcessor()
        self.exporter = Exporter()
        self.project_resolver = ProjectResolver()
        self.sqlite_storage = Storage(db=db)
        self.ide_harvester = IdeHarvest(self.sqlite_storage)
        self.output_dir = output_dir or Path("outputs")
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self._cached_engrams: Optional[List[Engram]] = None
        self._sqlite_persisted: bool = False
        self._ide_harvested: bool = False
        self.version = self._load_version()

    def _load_version(self) -> str:
        version_file = Path(os.getcwd()) / ".version"
        if version_file.exists():
            return version_file.read_text(encoding="utf-8").strip()
        return "0.1.0"

    def _get_all_engrams(self) -> List[Engram]:
        if self._cached_engrams is not None:
            return self._cached_engrams
        raw_engrams = self.orchestrator.run_all()
        processed = self.engram_processor.deduplicate(raw_engrams)
        for engram in processed:
            engram.project_name = self.project_resolver.resolve_project_name(engram)
        self._cached_engrams = processed
        return self._cached_engrams

    def _persist_cache_to_sqlite(self, request_id: Optional[str] = None) -> None:
        if self._cached_engrams is None or self._sqlite_persisted:
            return
        result = self.sqlite_storage.persist_engrams(self._cached_engrams, request_id=request_id)
        logger.info("SQLite persistence completed", extra={"request_id": request_id, "extra_data": {"sqlite": result}})
        self._sqlite_persisted = True
        self._harvest_ide_configs(request_id=request_id)

    def _harvest_ide_configs(self, *, request_id: Optional[str]) -> None:
        if self._ide_harvested:
            return
        try:
            totals = {"ides": 0, "ide_settings_upserted": 0, "ide_extensions_upserted": 0, "configurations_upserted": 0, "mcp_settings_upserted": 0}
            for parser in self.orchestrator.parsers:
                try:
                    raw_installations = parser.find_installations()
                    installations = []
                    for item in raw_installations:
                        if isinstance(item, tuple) and len(item) == 2:
                            installations.append(item[1])
                        else:
                            installations.append(item)
                    ide_type = "desktop" if parser.ide_name in {"trae", "cursor", "windsurf"} else "cli"
                    counts = self.ide_harvester.harvest_installations(
                        ide_name=parser.ide_name, ide_type=ide_type,
                        installations=installations, request_id=request_id or f"req_{uuid.uuid4()}",
                    )
                    ide_install_path = str(installations[0]) if installations else None
                    ide_id = self.sqlite_storage.ensure_ide(
                        IDEInfo(name=parser.ide_name, type=ide_type, installation_path=ide_install_path),
                        source=parser.ide_name,
                    )
                    ws_counts = self.ide_harvester.harvest_workspace_settings(
                        ide_name=parser.ide_name, ide_id=ide_id, request_id=request_id or f"req_{uuid.uuid4()}",
                    )
                    totals["ides"] += 1
                    for k in ("ide_settings_upserted", "ide_extensions_upserted", "configurations_upserted", "mcp_settings_upserted"):
                        totals[k] += int(counts.get(k, 0) or 0)
                    for k in ("workspace_settings_upserted", "workspace_extensions_upserted"):
                        totals.setdefault(k, 0)
                        totals[k] += int(ws_counts.get(k, 0) or 0)
                except Exception as e:
                    logger.warning("IDE harvest failed", extra={"request_id": request_id, "extra_data": {"ide": parser.ide_name, "error": str(e)}})
            logger.info("IDE harvest summary", extra={"request_id": request_id, "extra_data": totals})
        finally:
            self._ide_harvested = True

    def ingest_all_to_jsonl(self, filename: Optional[str] = None, *, request_id: Optional[str] = None) -> Path:
        from datetime import datetime
        processed_engrams = self._get_all_engrams()
        request_id = request_id or f"req_{uuid.uuid4()}"
        self.last_request_id = request_id
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sidecortex_ingest_{timestamp}.jsonl"
        output_path = self.output_dir / filename
        temp_path = output_path.with_suffix(output_path.suffix + '.tmp')
        try:
            self._persist_cache_to_sqlite(request_id=request_id)
            with open(temp_path, 'w', encoding='utf-8') as f:
                for engram in processed_engrams:
                    f.write(json.dumps(engram.to_export_record(request_id=request_id, version=self.version), ensure_ascii=False) + '\n')
            os.replace(temp_path, output_path)
            logger.info("Ingestion export written", extra={"request_id": request_id, "extra_data": {
                "event": "ingestion_export_written", "output_path": str(output_path),
                "total_engrams": len(processed_engrams), "total_messages": sum(len(e.messages) for e in processed_engrams),
            }})
            return output_path
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def refresh_project(self, *, project_path: str, force: bool = False) -> Dict[str, Any]:
        from datetime import datetime
        if force:
            self._cached_engrams = None
            self._sqlite_persisted = False
        processed_engrams = self._get_all_engrams()
        normalized_target = Engram._normalize_workspace_value(project_path)
        filtered = [e for e in processed_engrams if e.project_path and Engram._normalize_workspace_value(e.project_path) == normalized_target]
        request_id = f"req_{uuid.uuid4()}"
        persist = self.sqlite_storage.persist_engrams(filtered, request_id=request_id)
        return {"request_id": request_id, "project_path": project_path, "matched_engrams": len(filtered), "persist": persist, "timestamp": datetime.now().isoformat(timespec="milliseconds") + "Z"}

    def export_all_by_project(self, format: str = "markdown") -> List[Path]:
        processed_engrams = self._get_all_engrams()
        projects = self.project_resolver.group_by_project(processed_engrams)
        exported_files = []
        project_output_dir = self.output_dir / "projects"
        project_output_dir.mkdir(exist_ok=True, parents=True)
        for project_name, engrams in projects.items():
            safe_name = project_name.replace('\\', '-').replace('/', '-').replace(':', '-')
            if format == "markdown":
                filename = f"{safe_name}.md"
                output_path = project_output_dir / filename
                self.exporter.export_project_report(project_name, engrams, output_path)
                exported_files.append(output_path)
            elif format == "json":
                filename = f"{safe_name}.json"
                output_path = project_output_dir / filename
                self.exporter.save_json(engrams, output_path, request_id=f"req_{uuid.uuid4()}", version=self.version)
                exported_files.append(output_path)
            else:
                raise ValueError(f"Unsupported export format: '{format}'. Use 'markdown' or 'json'.")
        return exported_files

    def export_by_ide(self, format: str = "json", ide_name: Optional[str] = None) -> List[Path]:
        from collections import defaultdict
        from datetime import datetime
        processed_engrams = self._get_all_engrams()
        by_ide = defaultdict(list)
        for e in processed_engrams:
            name = e.ide_info.name if e.ide_info else e.source
            by_ide[name].append(e)
        exported_files = []
        targets = [ide_name] if ide_name else list(by_ide.keys())
        for target_ide in targets:
            if target_ide not in by_ide:
                continue
            engrams = by_ide[target_ide]
            ide_dir = self.output_dir / "results" / target_ide.lower()
            ide_dir.mkdir(exist_ok=True, parents=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            request_id = f"req_{uuid.uuid4()}"
            if format == "json":
                filename = f"{target_ide.lower()}_export_{timestamp}.json"
                self.exporter.save_json(engrams, ide_dir / filename, request_id=request_id, version=self.version)
                exported_files.append(ide_dir / filename)
            elif format == "jsonl":
                filename = f"{target_ide.lower()}_export_{timestamp}.jsonl"
                self.exporter.save_jsonl(engrams, ide_dir / filename, request_id=request_id, version=self.version)
                exported_files.append(ide_dir / filename)
            elif format == "markdown":
                filename = f"{target_ide.lower()}_export_{timestamp}.md"
                self.exporter.export_project_report(target_ide, engrams, ide_dir / filename)
                exported_files.append(ide_dir / filename)
        return exported_files

    def export_combined(self, format: str = "jsonl") -> Path:
        from datetime import datetime
        processed_engrams = self._get_all_engrams()
        combined_dir = self.output_dir / "results" / "combined"
        combined_dir.mkdir(exist_ok=True, parents=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        request_id = f"req_{uuid.uuid4()}"
        filename = f"combined_export_{timestamp}.{format}"
        output_path = combined_dir / filename
        if format == "json":
            self.exporter.save_json(processed_engrams, output_path, request_id=request_id, version=self.version)
        elif format == "jsonl":
            self.exporter.save_jsonl(processed_engrams, output_path, request_id=request_id, version=self.version)
        elif format == "markdown":
            self.exporter.export_project_report("Combined IDE Export", processed_engrams, output_path)
        logger.info(f"Exported {len(processed_engrams)} combined engrams to {output_path}")
        return output_path

    def get_summary(self) -> Dict[str, Any]:
        from collections import Counter
        processed_engrams = self._get_all_engrams()
        stats = self.orchestrator.get_stats(processed_engrams)
        by_ide = Counter()
        by_type = Counter()
        for e in processed_engrams:
            ide_name = e.ide_info.name if e.ide_info else e.source
            ide_type = e.ide_info.type if e.ide_info else 'unknown'
            by_ide[ide_name] += 1
            by_type[ide_type] += 1
        return {"total_engrams": len(processed_engrams), "breakdown": {"by_ide": dict(by_ide), "by_type": dict(by_type), "by_source": stats}, "total_messages": sum(len(e.messages) for e in processed_engrams)}
