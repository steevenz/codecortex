"""
@project   CodeCortex
@package   modules.idegraph.services
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.services
:standard: Aegis-IdeGraph-v1.0

Resolver — Group diverse IDE data into logical projects.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from src.modules.idegraph.domain.engram import Engram
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)


class Resolver:
    def group_by_project(self, engrams: List[Engram]) -> Dict[str, List[Engram]]:
        projects: Dict[str, List[Engram]] = {}
        for engram in engrams:
            project_name = self.resolve_project_name(engram)
            if project_name not in projects:
                projects[project_name] = []
            projects[project_name].append(engram)
        logger.info(f"Resolved {len(projects)} distinct projects from {len(engrams)} engrams")
        return projects

    def resolve_project_name(self, engram: Engram) -> str:
        path_to_check: Optional[str] = (
            engram.project_path or engram.workspace_id
            or engram.metadata.get('workspace') or engram.metadata.get('project_path')
            or engram.metadata.get('workspaceDirectory')
        )
        if path_to_check and isinstance(path_to_check, str) and (os.path.isabs(path_to_check) or '/' in path_to_check or '\\' in path_to_check):
            if '\x00' in path_to_check:
                path_to_check = None
            else:
                p = Path(path_to_check)
                try:
                    current = p
                    for _ in range(5):
                        if (current / ".aicoders").exists():
                            return current.name
                        if current.parent == current:
                            break
                        current = current.parent
                except Exception:
                    pass
                return p.name
        workspace = engram.metadata.get('workspace') or engram.metadata.get('workspace_id')
        if workspace:
            if isinstance(workspace, str):
                if os.path.isabs(workspace) or '/' in workspace or '\\' in workspace:
                    return Path(workspace).name
                return workspace
        source_path = Path(engram.source_file)
        if 'projects' in source_path.parts:
            idx = source_path.parts.index('projects')
            if len(source_path.parts) > idx + 1:
                return source_path.parts[idx + 1]
        meta_source_path = engram.metadata.get('source_path') or engram.metadata.get('source_file')
        if meta_source_path and isinstance(meta_source_path, str):
            p = Path(meta_source_path)
            if 'projects' in p.parts:
                idx = p.parts.index('projects')
                if len(p.parts) > idx + 1:
                    return p.parts[idx + 1]
        return f"Unknown-{engram.source.capitalize()}"
