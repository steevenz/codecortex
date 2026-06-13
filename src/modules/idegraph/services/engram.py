"""
@project   CodeCortex
@package   modules.idegraph.services
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.services
:standard: CODDY-IdeGraph-v1.0

Engram — Deduplication and processing of raw Engrams.
"""

from typing import List, Set
from src.modules.idegraph.domain.engram import Engram as EngramModel
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)


class Engram:
    def deduplicate(self, engrams: List[EngramModel]) -> List[EngramModel]:
        seen_ids: Set[str] = set()
        unique: List[EngramModel] = []
        for engram in engrams:
            if engram.id not in seen_ids:
                unique.append(engram)
                seen_ids.add(engram.id)
        logger.info(f"Deduplication: {len(unique)} unique from {len(engrams)} total")
        return unique
