"""
Data Transfer Objects for CodeTester Domain.
Supports run, coverage, discover, generate, diagnose actions.

:project: CodeCortex
:package: Modules.Codetester.Core.Dtos
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeTester-v1.0
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# ═══════════════════════════════════════════════════════════════════
# GENERIC RESULT TYPES
# ═══════════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    name: str
    file: str
    line: int
    status: str
    duration_ms: float = 0.0
    failure: Optional[Dict[str, Any]] = None

@dataclass
class CoverageFile:
    file: str
    coverage: float = 0.0
    total_lines: int = 0
    covered_lines: int = 0
    uncovered_lines: List[int] = field(default_factory=list)
    uncovered_functions: List[str] = field(default_factory=list)

@dataclass
class TestDiscovery:
    name: str
    file: str
    line: int = 0
    markers: List[str] = field(default_factory=list)
    category: str = ""

# ═══════════════════════════════════════════════════════════════════
# FRAMEWORK DETECTION
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FrameworkDetection:
    framework: str
    adapter_key: str
    config_file: Optional[str] = None
    version: Optional[str] = None
    project_dir: str = "."

# ═══════════════════════════════════════════════════════════════════
# REQUEST DTO
# ═══════════════════════════════════════════════════════════════════

@dataclass
class CodeTesterRequest:
    action: str
    target_path: str
    test_framework: str = "auto"
    test_filter: Optional[str] = None
    test_names: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    coverage_format: str = "summary"
    target_symbol: Optional[str] = None
    max_duration: int = 300
    async_mode: bool = False
    follow: bool = False

# ═══════════════════════════════════════════════════════════════════
# ACTION RESULT DTOS
# ═══════════════════════════════════════════════════════════════════

@dataclass
class TestRunData:
    action: str = "run"
    target_path: str = ""
    framework: str = ""
    duration_seconds: float = 0.0
    summary: Dict[str, int] = field(default_factory=lambda: {
        "total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0
    })
    results: List[Dict[str, Any]] = field(default_factory=list)
    test_run_id: str = ""

@dataclass
class CoverageData:
    action: str = "coverage"
    target_path: str = ""
    overall_coverage: float = 0.0
    files: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class DiscoveryData:
    action: str = "discover"
    target_path: str = ""
    framework: str = ""
    test_files: List[Dict[str, Any]] = field(default_factory=list)
    tests: List[Dict[str, Any]] = field(default_factory=list)
    markers: List[str] = field(default_factory=list)
    categories: Dict[str, List[str]] = field(default_factory=dict)

@dataclass
class GenerateData:
    action: str = "generate"
    target_file: str = ""
    target_symbol: str = ""
    test_file: str = ""
    test_line_start: int = 0
    test_code: str = ""
    recommendations: List[str] = field(default_factory=list)

@dataclass
class DiagnoseData:
    action: str = "diagnose"
    target_path: str = ""
    failure: Dict[str, Any] = field(default_factory=dict)
    root_cause: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    related_source: Optional[Dict[str, Any]] = None
