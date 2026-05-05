"""
/**
 * @project   CodeCortex
 * @package   Domain/Repository
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Data Transfer Objects for Repository Analysis.
 */
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Summary:
    """
    Aggregated statistics for a directory.
    
    Single Responsibility: Carry directory statistics data.
    """
    file_count: int = 0
    dir_count: int = 0
    total_size: int = 0

@dataclass
class FileStructure:
    """
    Node in the repository file tree.
    
    Single Responsibility: Represent a file or directory node in the tree.
    """
    path: str
    type: str  # "file" or "directory"
    size: Optional[int] = None
    children: Optional[List[FileStructure]] = field(default_factory=list)
    summary: Optional[Summary] = None
