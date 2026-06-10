"""
CodeAnalysis core domain — data transfer objects.

:project: CodeCortex
:package: Modules.Codeanalysis.Core
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeAnalysis-v1.0
"""

from .dtos import (
    AnalyzedSymbol,
    AnalyzedEdge,
    AnalyzeRequest,
    AnalyzeResult,
    SearchRequest,
    SearchMatch,
    SearchResult,
    AuditFinding,
    AuditRequest,
    AuditResult,
    MetricsInfo,
    VcsInfo,
    GraphStatsInfo,
    StatusRequest,
    StatusResult,
)

__all__ = [
    "AnalyzedSymbol",
    "AnalyzedEdge",
    "AnalyzeRequest",
    "AnalyzeResult",
    "SearchRequest",
    "SearchMatch",
    "SearchResult",
    "AuditFinding",
    "AuditRequest",
    "AuditResult",
    "MetricsInfo",
    "VcsInfo",
    "GraphStatsInfo",
    "StatusRequest",
    "StatusResult",
]
