"""
@project   CodeCortex
@package   modules.idegraph.services
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.services
:standard: Aegis-IdeGraph-v1.0

Service layer exports — backward-compatible aliases.
"""

from .engram import Engram as EngramService
from .export import Export as ExportService
from .ide_harvest import IdeHarvest as IdeHarvestService
from .resolver import Resolver as ProjectResolver
from .search import Search as SearchService
from .sidecortex import SideCortex as SideCortexService
from .storage import Storage as SqliteStorage
from .compact import Compact as MemoryCompactor
from .artifact import Artifact
from .insight_generator import InsightGenerator

__all__ = [
    "EngramService",
    "ExportService",
    "IdeHarvestService",
    "ProjectResolver",
    "SearchService",
    "SideCortexService",
    "SqliteStorage",
    "MemoryCompactor",
    "Artifact",
    "InsightGenerator",
]
