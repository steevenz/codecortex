"""
Codelogs Module — Log management, search, discovery, visualization, and maintenance.

Provides:
  - LogService: scan, search, cleanup, rotate, validate log files
  - LogPathCollector: systematic log path discovery (language, OS, server, database)
  - LogGraphService: comprehensive visualization (error frequency, time trends,
    anomaly detection, file correlation, health assessment, summary stats)
  - Integration with unified_search as 10th provider: codecortex-codelogs
  - MCP tool: codecortex:loggraph (enhanced with search_paths, discover, anomalies)
  - CLI domain: codecortex log <command>
  - HTTP API: /v1/codelogs/* endpoints

:project: CodeCortex
:package: Modules.Codelogs
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Codelogs-v2.0
"""

from src.modules.codelogs.services.log_service import LogService, LogPathCollector
from src.modules.codelogs.services.loggraph_service import LogGraphService

__all__ = [
    "LogService",
    "LogPathCollector",
    "LogGraphService",
]
