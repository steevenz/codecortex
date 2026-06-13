"""
Auto-Update Module — background version checking, update signals, and AI-triggered upgrades.

:project: CodeCortex
:package: Core.Update
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Core-v1.0
"""

from .updater import (
    CodeCortexUpdater,
    UpdateStatus,
    UpdateSignal,
    VersionCheckResult,
)

__all__ = [
    "CodeCortexUpdater",
    "UpdateStatus",
    "UpdateSignal",
    "VersionCheckResult",
]
