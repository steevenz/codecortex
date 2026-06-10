"""
Interface BaseQA - Abstract contract for different testing/linting tools.
Extended with discover, run_with_coverage, parse_results methods.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Base
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeTester-v1.0
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseQA(ABC):
    @abstractmethod
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        """Execute the tool and return standardized results."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return tool name (e.g., 'pytest', 'jest')."""
        pass

    def discover(self, repo_path: str, target_path: Optional[str] = None) -> Dict[str, Any]:
        """Discover available tests without running them.

        Returns structured test list with names, files, markers, and categories.
        Default implementation returns empty discovery. Override for structured discovery.
        """
        return {"tests": [], "test_files": [], "markers": [], "categories": {}}

    def run_with_coverage(self, repo_path: str, target_path: Optional[str] = None) -> Dict[str, Any]:
        """Run tests with coverage enabled.

        Returns test results + coverage data (overall %, per-file breakdown, uncovered lines).
        Default falls back to regular run. Override for coverage support.
        """
        return self.run(repo_path, target_path, extra_args="--coverage")

    def parse_results(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw adapter output into structured format.

        Returns normalized result with summary, individual test results,
        and failure details. Default returns raw output as-is.
        """
        return raw_output
