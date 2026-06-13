"""
Base contract for AST parsing strategies.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Strategies.Base
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class RawSymbol:
    """Intermediate DTO for extracted symbols. Aligned with legacy SymbolInfo."""
    name: str
    symbol_type: str
    start_line: int
    end_line: int
    parent_id: Optional[str] = None
    docstring: Optional[str] = None
    signature: Optional[str] = None
    code_ref: Optional[str] = None
    called_by: List[str] = field(default_factory=list)
    pending_calls: List[tuple] = field(default_factory=list)
    variables: List[Dict[str, Any]] = field(default_factory=list)
    function_calls: List[Dict[str, Any]] = field(default_factory=list)
    imports: List[Dict[str, Any]] = field(default_factory=list)
    language: Optional[str] = None

class BaseStrategy(ABC):
    """
    Abstract base for language-specific parsing.
    """
    @abstractmethod
    def parse(self, content: str, file_rel_path: str) -> List[RawSymbol]:
        """Parse content and return raw symbols."""
        pass
