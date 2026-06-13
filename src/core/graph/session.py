"""
NoOp graph backend session for graceful degradation.

:project: CodeCortex
:package: Core.Graph.Session
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

class _NoOpResult:
    def single(self) -> Optional[Dict[str, Any]]:
        return None

    def data(self) -> List[Dict[str, Any]]:
        return []

    def consume(self) -> Any:
        return None

    def __iter__(self):
        return iter([])

class _NoOpSession:
    def run(self, query: str, **parameters) -> _NoOpResult:
        return _NoOpResult()

    def __enter__(self) -> _NoOpSession:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return None

class NoOpBackend:
    def get_session(self) -> _NoOpSession:
        return _NoOpSession()

    def create_schema(self) -> None:
        return None

    def is_connected(self) -> bool:
        return True

    def get_backend_type(self) -> str:
        return "none"

    def close(self) -> None:
        return None

    @staticmethod
    def validate_config():
        return True, None

    @staticmethod
    def test_connection():
        return True, None
