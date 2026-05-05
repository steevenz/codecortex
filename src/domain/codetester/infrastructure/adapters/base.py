"""
/**
 * @project   CodeCortex
 * @package   Domain/CodeTester
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Interface BaseQAAdapter - Abstract contract for different testing/linting tools.
 */
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseQAAdapter(ABC):
    @abstractmethod
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        """Execute the tool and return standardized results."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return tool name (e.g., 'pytest', 'flake8')."""
        pass
