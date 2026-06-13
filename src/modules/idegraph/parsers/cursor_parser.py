"""
@project   CodeCortex
@package   modules.idegraph.parsers
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.parsers
:standard: CODDY-IdeGraph-v1.0
@fileoverview CursorParser - Parser for Cursor IDE AI interaction data.
"""

import json
import uuid
import platform
import os
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from src.modules.idegraph.core.base_parser import BaseIDEParser
from src.modules.idegraph.domain.engram import Engram, Message, IDEInfo
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

class CursorParser(BaseIDEParser):
    @property
    def ide_name(self) -> str:
        return "cursor"

    def find_installations(self) -> List[Path]:
        """
        Cross-platform Cursor IDE installation detection.
        Searches application data directories AND ~/.cursor project configs.
        Respects CURSOR_PATHS env var for custom locations.
        Windows priority: %APPDATA%, %LOCALAPPDATA%, %USERPROFILE%\\.cursor
        """
        system = platform.system()
        home = Path.home()
        locations = []

        # Priority 1: Application data directories (where state.vscdb lives)
        if system == "Darwin":
            app_dirs = [home / "Library/Application Support", home / ".config"]
        elif system == "Linux":
            app_dirs = [home / ".config", home / ".local/share"]
        elif system == "Windows":
            app_dirs = [
                Path(os.environ.get('APPDATA', home / 'AppData/Roaming')),
                Path(os.environ.get('LOCALAPPDATA', home / 'AppData/Local'))
            ]
        else:
            app_dirs = [home / ".config"]

        for base_dir in app_dirs:
            cursor_dir = base_dir / 'Cursor'
            if cursor_dir.exists():
                locations.append(cursor_dir)

        # Priority 2: ~/.cursor project configs (cursorRules, project metadata)
        # On Windows: %USERPROFILE%\.cursor, cross-platform: ~/.cursor
        dot_cursor = home / '.cursor'
        if dot_cursor.exists():
            locations.append(dot_cursor)

        return list(set(locations))

    def parse_all(self) -> List[Engram]:
        installations = self.find_installations()
        all_engrams = []
        for inst in installations:
            engrams = self._parse_installation(inst)
            # Filter out aiservice entries with no meaningful assistant content
            # (these are old-format metadata-only records; actual conversations are in global-composers)
            for e in engrams:
                if e.metadata.get('cursor_type') == 'aiservice':
                    has_assistant_content = any(
                        m.role == 'assistant' and m.content and m.content.strip()
                        for m in e.messages
                    )
                    if not has_assistant_content:
                        continue  # Skip empty aiservice records
                all_engrams.append(e)
        return all_engrams

    def _parse_installation(self, installation: Path) -> List[Engram]:
        engrams = []

        # Check if this is the ~/.cursor project configs directory (not app data)
        if installation.name == '.cursor' and installation.parent == Path.home():
            # ~/.cursor contains project-level cursorRules and metadata
            engrams.extend(self._extract_cursorrules_from_dot_cursor(installation))
            return engrams

        # 1. Extract from ALL workspace databases (AppData style)
        workspace_storage = installation / 'User/workspaceStorage'
        if workspace_storage.exists():
            for workspace in workspace_storage.iterdir():
                if workspace.is_dir() and workspace.name != 'ext-dev':
                    db_file = workspace / 'state.vscdb'
                    if db_file.exists():
                        ws_engrams: List[Engram] = []
                        ws_engrams.extend(self._extract_aiservice_conversations(db_file, workspace.name, installation))
                        ws_engrams.extend(self._extract_workspace_composers(db_file, workspace.name, installation))
                        ws_engrams.extend(self._extract_chat_mode(db_file, workspace.name, installation))
                        ws_engrams.extend(self._extract_cursorrules_from_workspace_db(db_file, workspace.name, installation))
                        if not ws_engrams:
                            ws_engrams.extend(self._artifact_db_summary(db_file=db_file, installation=installation, workspace_id=workspace.name))
                        engrams.extend(ws_engrams)

                    for extra in workspace.glob("*.db"):
                        if extra.name == "state.vscdb":
                            continue
                        engrams.extend(self._artifact_any_db_file(db_file=extra, installation=installation, workspace_id=workspace.name))

                    for extra in workspace.glob("*.vscdb"):
                        if extra.name == "state.vscdb":
                            continue
                        engrams.extend(self._artifact_any_db_file(db_file=extra, installation=installation, workspace_id=workspace.name))

        # 2. Extract global composers + plans + todos
        global_storage = installation / 'User/globalStorage/state.vscdb'
        if global_storage.exists():
            global_engrams = self._extract_global_composers(global_storage, installation)
            if not global_engrams:
                global_engrams.extend(self._artifact_db_summary(db_file=global_storage, installation=installation, workspace_id="global"))
            engrams.extend(global_engrams)

        return engrams

    def _extract_aiservice_conversations(self, db_path: Path, workspace_id: str, installation: Path) -> List[Engram]:
        """Extract OLD Cursor format (pre-v0.43) aiService prompts and generations"""
        engrams = []
        prompts_raw = self._read_sqlite(db_path, "SELECT value FROM ItemTable WHERE key = 'aiService.prompts'")
        gens_raw = self._read_sqlite(db_path, "SELECT value FROM ItemTable WHERE key = 'aiService.generations'")

        # Resolve workspace path once per workspace
        ws_path = self._extract_workspace_path(db_path, workspace_id)

        if prompts_raw or gens_raw:
            prompts = self._safe_json_loads(prompts_raw[0][0]) if prompts_raw else []
            generations = self._safe_json_loads(gens_raw[0][0]) if gens_raw else []

            max_len = max(len(prompts), len(generations))
            for i in range(max_len):
                messages = []
                model = None
                if i < len(prompts):
                    p = prompts[i]
                    messages.append(Message(role='user', content=self._extract_bubble_content(p), metadata={'command_type': p.get('commandType')}))
                if i < len(generations):
                    g = generations[i]
                    model = g.get('model') or g.get('modelId') or g.get('modelName')
                    messages.append(Message(role='assistant', content=self._extract_bubble_content(g), metadata={'model': model}))

                if messages:
                    engrams.append(Engram(
                        id=str(uuid.uuid4()), source=self.ide_name, source_file=str(db_path),
                        messages=messages, workspace_id=workspace_id, model=model,
                        project_path=ws_path,
                        metadata={'cursor_type': 'aiservice'},
                        ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation)
                    ))
        return engrams

    def _extract_workspace_composers(self, db_path: Path, workspace_id: str, installation: Path) -> List[Engram]:
        engrams = []
        results = self._read_sqlite(db_path, "SELECT value FROM ItemTable WHERE key = 'composer.composerData'")
        ws_path = self._extract_workspace_path(db_path, workspace_id)
        if results:
            data = self._safe_json_loads(results[0][0])
            if isinstance(data, dict) and 'allComposers' in data:
                for comp in data['allComposers']:
                    if not isinstance(comp, dict): continue
                    messages = self._parse_composer_conversation(comp.get('conversation', []))
                    if messages:
                        model = comp.get('modelConfig', {}).get('modelName')
                        comp_path = ws_path or self._extract_composer_project_path(comp)
                        engrams.append(Engram(
                            id=str(uuid.uuid4()), source=self.ide_name, source_file=str(db_path),
                            messages=messages, workspace_id=workspace_id, model=model,
                            project_path=comp_path,
                            title=comp.get('name', 'Untitled'),
                            metadata={'cursor_type': 'workspace-composer', 'composer_id': comp.get('composerId')},
                            ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation)
                        ))
                        # Extract plans and todos as separate engrams
                        engrams.extend(self._extract_plans_and_todos(
                            comp, db_path, installation, workspace_id=workspace_id
                        ))
        return engrams

    def _extract_chat_mode(self, db_path: Path, workspace_id: str, installation: Path) -> List[Engram]:
        engrams = []
        results = self._read_sqlite(db_path, "SELECT value FROM ItemTable WHERE key = 'workbench.panel.aichat.view.aichat.chatdata'")
        ws_path = self._extract_workspace_path(db_path, workspace_id)
        if results:
            data = self._safe_json_loads(results[0][0])
            if isinstance(data, dict) and 'tabs' in data:
                for tab in data['tabs']:
                    bubbles = tab.get('bubbles', [])
                    messages = []
                    for b in bubbles:
                        role = 'user' if b.get('type') == 'user' else 'assistant'
                        msg = Message(
                            role=role,
                            content=self._extract_bubble_content(b),
                            code_context=self._parse_selections(b.get('selections', [])),
                            diffs=b.get('suggestedDiffs', [])
                        )
                        messages.append(msg)

                    if messages:
                        engrams.append(Engram(
                            id=str(uuid.uuid4()), source=self.ide_name, source_file=str(db_path),
                            messages=messages, workspace_id=workspace_id,
                            project_path=ws_path,
                            title=tab.get('chatTitle'),
                            metadata={'cursor_type': 'chat', 'tab_id': tab.get('tabId')},
                            ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation)
                        ))
        return engrams

    def _extract_global_composers(self, db_path: Path, installation: Path) -> List[Engram]:
        engrams = []
        results = self._read_sqlite(db_path, "SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%'")
        for key, value in results:
            data = self._safe_json_loads(value)
            if not data: continue
            composer_id = data.get('composerId', key.split(':')[1])

            # Global composers can be inline or in separate bubbleId keys
            messages = self._parse_composer_conversation(data.get('conversation', []))
            if not messages:
                # Try separate bubbleId keys
                messages = self._extract_bubbles_for_composer(db_path, composer_id)

            if messages:
                model = data.get('modelConfig', {}).get('modelName')
                inferred_path = self._extract_composer_project_path(data)
                engrams.append(Engram(
                    id=str(uuid.uuid4()), source=self.ide_name, source_file=str(db_path),
                    messages=messages, model=model,
                    project_path=inferred_path,
                    title=data.get('name', 'Untitled'),
                    metadata={
                        'cursor_type': 'global-composer',
                        'composer_id': composer_id,
                        'status': data.get('status'),
                        'created_at': data.get('createdAt'),
                        'plan': data.get('plan'),
                        'steps': data.get('steps')
                    },
                    ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation)
                ))
                # Extract plans and todos as separate engrams
                engrams.extend(self._extract_plans_and_todos(
                    data, db_path, installation, workspace_id='global'
                ))
        return engrams

    def _extract_bubbles_for_composer(self, db_path: Path, composer_id: str) -> List[Message]:
        bubbles_raw = self._read_sqlite(db_path, "SELECT key, value FROM cursorDiskKV WHERE key LIKE ?", (f'bubbleId:{composer_id}:%',))
        messages = []
        for key, value in bubbles_raw:
            b = self._safe_json_loads(value)
            if not b: continue
            role = 'user' if b.get('type') == 1 else 'assistant'
            msg = Message(
                role=role,
                content=self._extract_bubble_content(b),
                code_context=self._parse_selections(b.get('selections', [])),
                tool_use=b.get('toolResults', []),
                diffs=b.get('suggestedCodeBlocks', []) + b.get('diffHistories', []),
                metadata={'bubble_id': key.split(':')[2]}
            )
            messages.append(msg)
        return messages

    def _parse_composer_conversation(self, conversation: List[Dict]) -> List[Message]:
        messages = []
        for b in conversation:
            bubble_type = b.get('type')
            if bubble_type not in [1, 2]: continue
            role = 'user' if bubble_type == 1 else 'assistant'
            msg = Message(
                role=role,
                content=self._extract_bubble_content(b),
                code_context=self._parse_selections(b.get('context', {}).get('selections', [])),
                tool_use=b.get('toolResults', []),
                diffs=b.get('suggestedCodeBlocks', []) + b.get('diffHistories', []),
                metadata={'model': b.get('modelId')}
            )
            messages.append(msg)
        return messages

    def _parse_selections(self, selections: List[Dict]) -> List[Dict]:
        ctx = []
        for sel in selections:
            if 'uri' in sel and 'fsPath' in sel['uri']:
                ctx.append({
                    'file': sel['uri']['fsPath'],
                    'code': sel.get('text', sel.get('rawText', '')),
                    'range': sel.get('range')
                })
        return ctx

    def _extract_bubble_content(self, bubble: Dict) -> str:
        """Extract message content trying multiple known Cursor field names."""
        # Ordered by likelihood for modern Cursor versions
        candidates = [
            'rawText', 'text', 'response', 'result', 'aiOutput',
            'markdownText', 'content', 'answer', 'output', 'generation',
            'message', 'body', 'value', 'data', 'thinking'
        ]
        for key in candidates:
            val = bubble.get(key)
            if val and isinstance(val, str) and val.strip():
                return val
            # Handle nested objects like {"text": "..."} inside result/aiOutput/thinking
            if val and isinstance(val, dict):
                for sub_key in ['text', 'content', 'markdown', 'value', 'response']:
                    sub_val = val.get(sub_key)
                    if sub_val and isinstance(sub_val, str) and sub_val.strip():
                        return sub_val
        # Fallback: extract from diffs/code changes if no text content
        diffs = bubble.get('assistantSuggestedDiffs') or bubble.get('gitDiffs') or []
        if diffs and isinstance(diffs, list) and len(diffs) > 0:
            parts = []
            for d in diffs:
                if isinstance(d, dict):
                    fpath = d.get('filePath') or d.get('uri') or d.get('path', 'unknown')
                    parts.append(f"[Code change: {fpath}]")
                    patch = d.get('diff') or d.get('patch') or d.get('code') or d.get('text', '')
                    if patch:
                        parts.append(patch[:500])
            return '\n'.join(parts) if parts else ''
        # Fallback: tool call info
        tool_data = bubble.get('toolFormerData')
        if tool_data and isinstance(tool_data, dict):
            tool_name = tool_data.get('toolName') or tool_data.get('toolCallId', 'unknown')
            return f"[Tool call: {tool_name}]"
        return ''

    def _extract_composer_project_path(self, comp: Dict) -> Optional[str]:
        """Infer project path from composer data (context, files, diffs)."""
        ctx = comp.get('context', {})
        # Attempt 1: fileSelections URIs
        for sel in ctx.get('fileSelections', []) or []:
            if isinstance(sel, dict) and 'uri' in sel:
                uri = sel['uri']
                if isinstance(uri, dict) and 'fsPath' in uri:
                    p = Path(uri['fsPath'])
                    if p.exists() or str(p.parent) != '.':
                        return self._normalize_project_path(p.parent)
                elif isinstance(uri, str) and uri.startswith('file:///'):
                    p = Path(uri[8:].replace('/', '\\') if platform.system() == 'Windows' else uri[7:])
                    return self._normalize_project_path(p.parent)
        # Attempt 2: originalFileStates keys
        ofs = comp.get('originalFileStates')
        if ofs and isinstance(ofs, dict):
            for key in list(ofs.keys())[:3]:
                p = Path(key)
                if p.parent != Path('.'):
                    return self._normalize_project_path(p.parent)
        # Attempt 3: newlyCreatedFiles / addedFiles
        for field in ['newlyCreatedFiles', 'addedFiles']:
            val = comp.get(field)
            if val and isinstance(val, list) and len(val) > 0:
                p = Path(str(val[0]))
                if p.parent != Path('.'):
                    return self._normalize_project_path(p.parent)
        # Attempt 4: conversation bubbles with file paths
        cmap = comp.get('conversationMap', {})
        for bubble in list(cmap.values()) if isinstance(cmap, dict) else []:
            # attachedCodeChunks
            for chunk in bubble.get('attachedCodeChunks', []) or []:
                if isinstance(chunk, dict):
                    uri = chunk.get('uri') or chunk.get('filePath')
                    if uri:
                        p = Path(uri)
                        if p.parent != Path('.'):
                            return self._normalize_project_path(p.parent)
            # diffs
            for d in bubble.get('assistantSuggestedDiffs', []) or []:
                if isinstance(d, dict):
                    fp = d.get('filePath') or d.get('uri')
                    if fp:
                        p = Path(fp)
                        if p.parent != Path('.'):
                            return self._normalize_project_path(p.parent)
        return None

    def _extract_workspace_path(self, db_path: Path, workspace_id: str) -> Optional[str]:
        """Try to resolve the actual folder path for a workspace from state.vscdb."""
        # Attempt 1: folderUri from workspace configuration
        results = self._read_sqlite(db_path, "SELECT value FROM ItemTable WHERE key = 'history.recentlyOpenedPathsList'")
        if results:
            data = self._safe_json_loads(results[0][0])
            if isinstance(data, dict) and 'entries' in data:
                for entry in data['entries']:
                    if isinstance(entry, dict):
                        folder_uri = entry.get('folderUri') or entry.get('workspace', {}).get('configPath')
                        if folder_uri and isinstance(folder_uri, str):
                            # Convert file:///C:/... to C:/...
                            if folder_uri.startswith('file:///'):
                                return self._normalize_project_path(
                                    Path(folder_uri[8:].replace('/', '\\') if platform.system() == 'Windows' else folder_uri[7:])
                                )
                            elif folder_uri.startswith('file://'):
                                return self._normalize_project_path(
                                    Path(folder_uri[7:].replace('/', '\\') if platform.system() == 'Windows' else folder_uri[7:])
                                )
                            return self._normalize_project_path(Path(folder_uri))

        # Attempt 2: Look for workspaceStorage folder parent that looks like a project path
        ws_dir = db_path.parent
        if ws_dir.name == workspace_id:
            # Check if there's a workspace.json or similar
            ws_json = ws_dir / 'workspace.json'
            if ws_json.exists():
                try:
                    with open(ws_json, 'r', encoding='utf-8') as f:
                        ws_data = json.load(f)
                    if isinstance(ws_data, dict):
                        folder = ws_data.get('folder') or ws_data.get('folderUri') or ws_data.get('configPath')
                        if folder and isinstance(folder, str):
                            return self._normalize_project_path(Path(folder))
                except Exception as e:
                    logger.debug(f"Cursor parse warning: {e}")
        return None

    def _artifact_db_summary(self, *, db_file: Path, installation: Path, workspace_id: str) -> List[Engram]:
        return self._artifact_any_db_file(db_file=db_file, installation=installation, workspace_id=workspace_id, artifact_type="cursor_sqlite_unparsed")

    def _artifact_any_db_file(
        self,
        *,
        db_file: Path,
        installation: Path,
        workspace_id: str,
        artifact_type: Optional[str] = None,
    ) -> List[Engram]:
        header = b""
        try:
            header = db_file.read_bytes()[:16]
        except Exception:
            header = b""

        is_sqlite = header == b"SQLite format 3\x00"
        details: Dict[str, Any] = {
            "file_name": db_file.name,
            "suffix": db_file.suffix,
            "size_bytes": self._safe_stat_size(db_file),
            "header_hex": header.hex() if header else None,
            "tables": self._sqlite_list_tables(db_file) if is_sqlite else [],
        }

        stable_seed = f"cursor|artifact|{db_file}|{artifact_type or ('cursor_sqlite' if is_sqlite else 'cursor_db_unknown_format')}".encode("utf-8", errors="ignore")
        engram_id = hashlib.sha256(stable_seed).hexdigest()
        created_at = datetime.fromtimestamp(db_file.stat().st_mtime) if db_file.exists() else datetime.now()
        msg = Message(
            role="assistant",
            content="artifact_captured",
            timestamp=created_at.isoformat(),
            metadata={"artifact_type": artifact_type or ("cursor_sqlite" if is_sqlite else "cursor_db_unknown_format")},
        )

        return [
            Engram(
                id=engram_id,
                source=self.ide_name,
                source_file=str(db_file),
                messages=[msg],
                created_at=created_at,
                workspace_id=workspace_id,
                metadata={"artifact_type": artifact_type or ("cursor_sqlite" if is_sqlite else "cursor_db_unknown_format"), "details": details},
                ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation),
            )
        ]

    # --- Digital Artifacts: Plans, Tasks, Rules, Walkthroughs ---

    def _extract_plans_and_todos(self, comp: Dict, db_path: Path, installation: Path,
                                  workspace_id: str = 'global') -> List[Engram]:
        """Extract composer plans (plan, todos, subtasks) as separate engrams."""
        engrams = []

        # Extract plan
        plan = comp.get('plan')
        if plan and isinstance(plan, dict):
            plan_text = plan.get('text') or plan.get('markdownText') or plan.get('content')
            if plan_text and isinstance(plan_text, str) and plan_text.strip():
                model = comp.get('modelConfig', {}).get('modelName')
                engrams.append(Engram(
                    id=str(uuid.uuid4()), source=self.ide_name, source_file=str(db_path),
                    messages=[Message(role='assistant', content=plan_text)],
                    workspace_id=workspace_id, model=model,
                    title=f"Plan: {comp.get('name', 'Untitled')}",
                    metadata={'cursor_type': 'composer-plan', 'composer_id': comp.get('composerId')},
                    ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation)
                ))

        # Extract todos / subtasks
        todos = comp.get('todos')
        if todos and isinstance(todos, list) and len(todos) > 0:
            todo_lines = []
            for t in todos:
                if isinstance(t, dict):
                    status = t.get('status', '')
                    text = t.get('text') or t.get('description') or t.get('title')
                    if text:
                        status_icon = '✅' if status == 'done' else '⏳'
                        todo_lines.append(f"{status_icon} [{status}] {text}")
                elif isinstance(t, str):
                    todo_lines.append(f"- {t}")

            if todo_lines:
                model = comp.get('modelConfig', {}).get('modelName')
                engrams.append(Engram(
                    id=str(uuid.uuid4()), source=self.ide_name, source_file=str(db_path),
                    messages=[Message(role='assistant', content='\n'.join(todo_lines))],
                    workspace_id=workspace_id, model=model,
                    title=f"Tasks: {comp.get('name', 'Untitled')}",
                    metadata={'cursor_type': 'composer-tasks', 'composer_id': comp.get('composerId')},
                    ide_info=self._build_ide_info(ide_type="vscode-extension", installation_path=installation)
                ))

        return engrams

    def _extract_cursorrules_from_dot_cursor(self, dot_cursor_dir: Path) -> List[Engram]:
        """Extract .cursorrules files from ~/.cursor directory (project-level rules)."""
        engrams = []

        # ~/.cursor structure: ~/.cursor/projects/{project-slug}/.cursorrules
        projects_dir = dot_cursor_dir / 'projects'
        if not projects_dir.exists():
            return engrams

        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            # Find .cursorrules file
            cursorrules_file = project_dir / '.cursorrules'
            if not cursorrules_file.exists():
                continue

            try:
                content = cursorrules_file.read_text(encoding='utf-8')
                if content.strip():
                    engrams.append(Engram(
                        id=str(uuid.uuid4()), source=self.ide_name,
                        source_file=str(cursorrules_file),
                        messages=[Message(
                            role='system',
                            content=content,
                            metadata={'file': '.cursorrules'}
                        )],
                        title=f"Cursor Rules: {project_dir.name}",
                        project_path=str(project_dir),
                        metadata={
                            'cursor_type': 'cursorrules',
                            'project_slug': project_dir.name,
                            'rules_file': str(cursorrules_file)
                        },
                        ide_info=self._build_ide_info(
                            ide_type="vscode-extension",
                            installation_path=dot_cursor_dir
                        )
                    ))
            except Exception as e:
                    logger.debug(f"Cursor parse warning: {e}")

        # Also look for terminal data
        for project_dir in projects_dir.iterdir():
            terminals_dir = project_dir / 'terminals'
            if terminals_dir.exists():
                for term_file in terminals_dir.iterdir():
                    if term_file.suffix == '.txt':
                        try:
                            content = term_file.read_text(encoding='utf-8')
                            if content.strip():
                                engrams.append(Engram(
                                    id=str(uuid.uuid4()), source=self.ide_name,
                                    source_file=str(term_file),
                                    messages=[Message(
                                        role='system',
                                        content=content,
                                        metadata={'file': str(term_file.name)}
                                    )],
                                    title=f"Terminal: {project_dir.name}/{term_file.name}",
                                    project_path=str(project_dir),
                                    metadata={
                                        'cursor_type': 'terminal-history',
                                        'project_slug': project_dir.name
                                    },
                                    ide_info=self._build_ide_info(
                                        ide_type="vscode-extension",
                                        installation_path=dot_cursor_dir
                                    )
                                ))
                        except Exception as e:
                            logger.debug(f"Cursor parse warning: {e}")

        return engrams

    def _extract_cursorrules_from_workspace_db(self, db_path: Path, workspace_id: str,
                                                installation: Path) -> List[Engram]:
        """Extract cursorRules from workspace state.vscdb (newer Cursor versions)."""
        engrams = []

        # Check for 'cursor.rules' or 'cursorRules' key
        for key in ['cursor.rules', 'cursorRules', 'cursor.rulesContent']:
            results = self._read_sqlite(db_path, "SELECT value FROM ItemTable WHERE key = ?", (key,))
            if results:
                content = results[0][0]
                if content and isinstance(content, str) and content.strip():
                    engrams.append(Engram(
                        id=str(uuid.uuid4()), source=self.ide_name,
                        source_file=str(db_path),
                        messages=[Message(role='system', content=content)],
                        workspace_id=workspace_id,
                        title=f"Cursor Rules: {workspace_id}",
                        metadata={'cursor_type': 'cursorrules-db', 'db_key': key},
                        ide_info=self._build_ide_info(
                            ide_type="vscode-extension", installation_path=installation
                        )
                    ))
        return engrams
