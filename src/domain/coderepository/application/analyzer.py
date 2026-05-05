"""
/**
 * @project   CodeCortex
 * @package   Domain/Repository
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Class RepoStructureAnalyzer – Single Responsibility: Analyze repository structure and respect gitignore.
 */
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import List, Optional, Tuple
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from ..core.dto import FileStructure, Summary

class RepoStructureAnalyzer:
    """
    Handles repository structure traversal and filtering.
    """
    def __init__(self, repo_path: Path):
        """
        Initialize with repository path and gitignore patterns.
        
        @param repo_path: Absolute path to the repository
        """
        self.repo_path = repo_path
        self.gitignore_spec: Optional[PathSpec] = self._load_gitignore()

    def _load_gitignore(self) -> Optional[PathSpec]:
        """
        Load .gitignore patterns from the repository root.
        
        @return: PathSpec object if .gitignore exists, else None
        """
        gitignore_path = self.repo_path / '.gitignore'
        if gitignore_path.exists():
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    return PathSpec.from_lines(GitWildMatchPattern, f)
            except Exception:
                return None
        return None

    def should_ignore(self, path: Path) -> bool:
        """
        Check if a path should be ignored based on .gitignore or default rules.
        
        @param path: Absolute or relative path to check
        @return: True if ignored, False otherwise
        """
        try:
            rel_path = path.relative_to(self.repo_path)
        except ValueError:
            rel_path = path

        # Always ignore .git directory
        if '.git' in rel_path.parts:
            return True

        if self.gitignore_spec:
            return self.gitignore_spec.match_file(str(rel_path))
        
        return False

    def get_structure(self, sub_path: Optional[str] = None, max_depth: int = 3) -> FileStructure:
        """
        Recursively traverse the repository to build a file structure tree.
        
        @param sub_path: Optional subdirectory path relative to repository root
        @param max_depth: Maximum depth for traversal
        @return: FileStructure object representing the root of the (sub)tree
        """
        current_path = self.repo_path
        if sub_path:
            current_path = (self.repo_path / sub_path).resolve()
            if not str(current_path).startswith(str(self.repo_path)):
                raise ValueError("Access denied: path is outside repository root")

        return self._build_structure(current_path, max_depth)

    def _build_structure(self, current_path: Path, max_depth: int, current_depth: int = 0) -> FileStructure:
        """
        Internal recursive method to build the file structure.
        
        @param current_path: Current path being analyzed
        @param max_depth: Maximum depth allowed
        @param current_depth: Current depth in the recursion
        @return: FileStructure node
        """
        rel_path = current_path.relative_to(self.repo_path)
        path_str = str(rel_path) if str(rel_path) != '.' else ''

        if current_path.is_file():
            return FileStructure(
                path=path_str,
                type="file",
                size=current_path.stat().st_size
            )

        # It's a directory
        node = FileStructure(
            path=path_str,
            type="directory",
            summary=Summary()
        )

        if current_depth >= max_depth:
            return node

        try:
            for item in sorted(current_path.iterdir()):
                if self.should_ignore(item):
                    continue

                child_node = self._build_structure(item, max_depth, current_depth + 1)
                node.children.append(child_node)

                # Update summary
                if child_node.type == "file":
                    node.summary.file_count += 1
                    node.summary.total_size += child_node.size or 0
                else:
                    node.summary.dir_count += 1
                    node.summary.file_count += child_node.summary.file_count
                    node.summary.dir_count += child_node.summary.dir_count
                    node.summary.total_size += child_node.summary.total_size
        except PermissionError:
            pass

        return node
