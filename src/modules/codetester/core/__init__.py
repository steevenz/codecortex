"""
CodeTester core domain — DTOs and framework detection.

:project: CodeCortex
:package: Modules.Codetester.Core
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeTester-v1.0
"""

from .dtos import (
    TestResult, CoverageFile, TestDiscovery, FrameworkDetection,
    CodeTesterRequest, TestRunData, CoverageData,
    DiscoveryData, GenerateData, DiagnoseData,
)
from .framework import detect_framework, get_run_command

__all__ = [
    "TestResult", "CoverageFile", "TestDiscovery", "FrameworkDetection",
    "CodeTesterRequest", "TestRunData", "CoverageData",
    "DiscoveryData", "GenerateData", "DiagnoseData",
    "detect_framework", "get_run_command",
]
