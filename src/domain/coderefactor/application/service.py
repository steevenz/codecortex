"""
/**
 * @project   CodeCortex
 * @package   Domain/CodeRefactor
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Class CodeRefactorService – Single Responsibility: Manage codebase refactoring operations.
 */
"""

import os
import uuid
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from src.core.database import DatabaseManager
from src.core.logging_config import get_logger
from src.domain.filesystem.application.service import FilesystemService
from src.domain.coderepository import GitService
from src.domain.codegraph.application.service import CodeGraphService
from src.core.tree_sitter_manager import get_tree_sitter_manager, execute_query
from src.domain.coderefactor.core.dtos import RefactorChange, RefactorResult, ImpactAnalysisResult
from src.domain.coderefactor.application.search_service import SearchService

logger = get_logger("CodeCortex.Domain.Refactor")

class CodeRefactorService:
    """
    Service for executing safe, atomic refactoring operations.
    Integrates with Git for version control and CodeGraph for impact analysis.
    """
    def __init__(self, db: DatabaseManager, fs_service: FilesystemService, git_service: GitService, graph_service: CodeGraphService):
        self.db = db
        self.fs = fs_service
        self.git = git_service
        self.graph = graph_service
        self.ts = get_tree_sitter_manager()
        self.search = SearchService(db)

    async def analyze_refactor_impact(self, path: str, symbol_name: str, request_id: str = "internal") -> ImpactAnalysisResult:
        self._log_event("INFO", "REFACTOR_IMPACT_ANALYSIS_STARTED", {"symbol": symbol_name, "path": path}, request_id)
        """Predict breaking changes and affected files for a symbol modification."""
        root_path, repo_id = self._resolve_repo(path)
        if not repo_id:
            return ImpactAnalysisResult(repository_id="", symbol_name=symbol_name, source_file=path, summary="Repository not found")
            
        source_rel = self._get_rel_path(root_path, path)
        callers = self._find_callers_by_name(repo_id, symbol_name, source_rel)
        
        affected_files = list(set([c[1] for c in callers]))
        risk_level = "low"
        if len(affected_files) > 10:
            risk_level = "high"
        elif len(affected_files) > 3:
            risk_level = "medium"
            
        summary = f"Symbol '{symbol_name}' is used in {len(affected_files)} other files. "
        if risk_level == "high":
            summary += "CAUTION: This is a widely used symbol. Refactoring may have significant impact."
            
        return ImpactAnalysisResult(
            repository_id=repo_id,
            symbol_name=symbol_name,
            source_file=source_rel,
            affected_files=affected_files,
            risk_level=risk_level,
            summary=summary
        )

    async def apply_refactor_recipe(self, path: str, recipe: str, dry_run: bool = True, request_id: str = "internal") -> RefactorResult:
        """Apply a predefined refactor pattern (e.g. 'standardize_docstrings', 'add_type_hints')."""
        self._log_event("INFO", "APPLY_RECIPE_STARTED", {"recipe": recipe, "path": path}, request_id)
        
        root_path, repo_id = self._resolve_repo(path)
        if not repo_id:
            return RefactorResult(status="error", message="Repository not found", repository_id="")
            
        rel_path = self._get_rel_path(root_path, path)
        data = self.fs.read_file(rel_path, repo_id)
        if "error" in data:
            return RefactorResult(status="error", message=data["error"], repository_id=repo_id)
            
        content = data["content"]
        new_content = content
        
        if recipe == "standardize_docstrings" and path.endswith(".py"):
            new_content = self._recipe_standardize_docstrings_python(content)
        elif recipe == "add_type_hints" and path.endswith(".py"):
             new_content = self._recipe_add_type_hints_python(content)
        else:
            return RefactorResult(status="error", message=f"Recipe '{recipe}' not supported for this file type", repository_id=repo_id)

        if new_content == content:
            return RefactorResult(status="success", message="No changes needed", repository_id=repo_id)

        change = RefactorChange(path=path, action="modify", description=f"Applied recipe: {recipe}")
        
        if dry_run:
            return RefactorResult(status="dry_run", message="Recipe plan generated", repository_id=repo_id, changes=[change])

        # Execute
        self.fs.write_file(rel_path, new_content, repo_id, dry_run=False)
        commit_hash_data = await self.git.stage_and_commit(root_path, [path], f"refactor: apply recipe {recipe} to {rel_path}")
        commit_hash = commit_hash_data.get("commit_hash")
        
        return RefactorResult(status="success", message=f"Applied recipe {recipe}", repository_id=repo_id, changes=[change], commit_hash=commit_hash)

    async def move_code_element(self, path: str, element_name: str, target_file: str, dry_run: bool = True) -> RefactorResult:
        """
        Move a class or function from source file to target file.
        Automatically updates imports in all calling files based on the call graph.
        """
        self._log_event("INFO", "MOVE_ELEMENT_STARTED", {"element": element_name, "from": path, "to": target_file})
        
        # 1. Resolve repository context
        root_path, repo_id = self._resolve_repo(path)
        if not repo_id:
            return RefactorResult(status="error", message="Repository root not found or not indexed", repository_id="", error_code="REF_001")
            
        source_rel = self._get_rel_path(root_path, path)
        target_rel = self._get_rel_path(root_path, target_file)
        
        # 2. Extract element code block using Tree-Sitter
        src_data = self.fs.read_file(source_rel, repo_id)
        if "error" in src_data:
            return RefactorResult(status="error", message=src_data["error"], repository_id=repo_id, error_code="REF_002")
        
        content = src_data["content"]
        element_code, start_line, end_line = self._extract_element(content, element_name, path)
        if not element_code:
             return RefactorResult(status="error", message=f"Element '{element_name}' not found in {source_rel}", repository_id=repo_id, error_code="REF_003")

        # 3. Identify Impact (Callers)
        changes = []
        
        # Change: Remove from source
        changes.append(RefactorChange(
            path=path, 
            action="modify", 
            description=f"Delete {element_name} (lines {start_line}-{end_line})"
        ))

        # Change: Append to target
        changes.append(RefactorChange(
            path=target_file, 
            action="modify", 
            description=f"Append {element_name} to end of file"
        ))

        # Change: Update Callers
        callers = self._find_callers_by_name(repo_id, element_name, source_rel)
        for caller_path, caller_rel in callers:
            if caller_path == path: continue
            changes.append(RefactorChange(
                path=caller_path, 
                action="update_import", 
                description=f"Redirect import of {element_name} from {source_rel} to {target_rel}"
            ))

        if dry_run:
            return RefactorResult(status="dry_run", message="Refactor plan generated", repository_id=repo_id, changes=changes)

        # 4. Execute Operations
        try:
            # A. Update source file
            src_lines = content.splitlines(keepends=True)
            new_src_lines = src_lines[:start_line-1] + src_lines[end_line:]
            self.fs.write_file(source_rel, "".join(new_src_lines), repo_id, dry_run=False)

            # B. Update target file
            dest_data = self.fs.read_file(target_rel, repo_id)
            dest_content = dest_data.get("content", "") if "error" not in dest_data else ""
            new_dest_content = dest_content.rstrip() + "\n\n" + element_code + "\n"
            self.fs.write_file(target_rel, new_dest_content, repo_id, dry_run=False)

            # C. Synchronize Imports
            for caller_path, caller_rel in callers:
                if caller_path == path: continue
                if caller_path.endswith(".py"):
                    self._update_import_python(caller_path, repo_id, element_name, source_rel, target_rel)
                elif caller_path.endswith((".js", ".ts", ".tsx")):
                    self._update_import_js(caller_path, repo_id, element_name, source_rel, target_rel)

            # 5. Atomic Git Commit
            affected_paths = [path, target_file] + [c[0] for c in callers if c[0] != path]
            commit_msg = f"refactor: move {element_name} from {source_rel} to {target_rel}"
            commit_res = await self.git.stage_and_commit(root_path, affected_paths, commit_msg)
            commit_hash = commit_res.get("commit_hash") if isinstance(commit_res, dict) else None

            self._log_event("INFO", "MOVE_ELEMENT_COMPLETED", {"element": element_name, "commit": commit_hash})
            return RefactorResult(
                status="success", 
                message=f"Successfully moved {element_name} to {target_rel}", 
                repository_id=repo_id, 
                changes=changes, 
                commit_hash=commit_hash
            )
        except Exception as e:
            logger.error(f"Move element failed: {str(e)}")
            return RefactorResult(status="error", message=str(e), repository_id=repo_id)

    async def rename_symbol(self, path: str, old_name: str, new_name: str, dry_run: bool = True) -> RefactorResult:
        """
        Rename a symbol (class, function, variable) semantically and update all references.
        """
        self._log_event("INFO", "RENAME_SYMBOL_STARTED", {"old": old_name, "new": new_name, "file": path})
        
        root_path, repo_id = self._resolve_repo(path)
        if not repo_id:
            return RefactorResult(status="error", message="Repository root not found", repository_id="", error_code="REF_001")
            
        source_rel = self._get_rel_path(root_path, path)
        
        # 1. Identify Impact via CodeGraph
        callers = self._find_callers_by_name(repo_id, old_name, source_rel)
        
        changes = []
        changes.append(RefactorChange(
            path=path, 
            action="modify", 
            description=f"Rename {old_name} to {new_name} in {source_rel}"
        ))
        
        for caller_path, caller_rel in callers:
            changes.append(RefactorChange(
                path=caller_path, 
                action="modify", 
                description=f"Update reference: {old_name} -> {new_name} in {caller_rel}"
            ))

        if dry_run:
            return RefactorResult(status="dry_run", message="Rename plan generated", repository_id=repo_id, changes=changes)

        # 2. Execute Semantic Renaming
        try:
            affected_files = set([path] + [c[0] for c in callers])
            actual_changes = []

            for file_path in affected_files:
                rel_path = self._get_rel_path(root_path, file_path)
                data = self.fs.read_file(rel_path, repo_id)
                if "error" in data: continue
                
                content = data.get("content", "")
                new_content = content
                
                # Language-specific semantic rename
                if file_path.endswith(".py"):
                    new_content = self._rename_in_file_python(content, old_name, new_name)
                elif file_path.endswith((".js", ".ts", ".tsx")):
                    new_content = self._rename_in_file_js(content, old_name, new_name)
                elif file_path.endswith(".go"):
                    new_content = self._rename_in_file_go(content, old_name, new_name)
                else:
                    # Heuristic fallback for unknown languages
                    new_content = re.sub(rf"\b{re.escape(old_name)}\b", new_name, content)
                
                if new_content != content:
                    self.fs.write_file(rel_path, new_content, repo_id, dry_run=False)
                    actual_changes.append(file_path)

            # 3. Git Commit
            if actual_changes:
                commit_msg = f"refactor: rename {old_name} to {new_name}"
                commit_res = await self.git.stage_and_commit(root_path, list(set(actual_changes)), commit_msg)
                commit_hash = commit_res.get("commit_hash") if isinstance(commit_res, dict) else None
                return RefactorResult(status="success", message=f"Renamed {old_name} to {new_name}", repository_id=repo_id, changes=changes, commit_hash=commit_hash)
            
            return RefactorResult(status="success", message="No changes needed", repository_id=repo_id, changes=[])
            
        except Exception as e:
            logger.error(f"Rename failed: {str(e)}")
            return RefactorResult(status="error", message=str(e), repository_id=repo_id, error_code="REF_005")

    def _resolve_repo(self, path: str) -> Tuple[Optional[str], Optional[str]]:
        abs_path = Path(path).resolve()
        curr = abs_path
        while curr.parent != curr:
            cursor = self.db.conn.execute("SELECT id, root_path FROM repositories WHERE root_path = ?", (str(curr),))
            row = cursor.fetchone()
            if row:
                return row["root_path"], row["id"]
            curr = curr.parent
        return None, None

    def _get_rel_path(self, root: str, path: str) -> str:
        try:
            return str(Path(path).resolve().relative_to(Path(root).resolve())).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")

    def _extract_element(self, content: str, name: str, path: str) -> Tuple[Optional[str], int, int]:
        """Extract code block and range for a class or function based on file extension."""
        ext = Path(path).suffix.lower()
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".go": "go",
            ".rs": "rust",
            ".cs": "c_sharp",
            ".java": "java"
        }
        
        lang_name = lang_map.get(ext)
        if not lang_name:
            return None, 0, 0
            
        lang = self.ts.get_language_safe(lang_name)
        parser = self.ts.create_parser(lang_name)
        tree = parser.parse(bytes(content, "utf8"))
        
        # Generic queries for class/func definitions
        queries = {
            "python": f"""
                (class_definition name: (identifier) @name (#eq? @name "{name}")) @el
                (function_definition name: (identifier) @name (#eq? @name "{name}")) @el
            """,
            "javascript": f"""
                (class_declaration name: (identifier) @name (#eq? @name "{name}")) @el
                (function_declaration name: (identifier) @name (#eq? @name "{name}")) @el
                (variable_declarator name: (identifier) @name (#eq? @name "{name}") value: (arrow_function)) @el
            """,
            "go": f"""
                (type_declaration (type_spec name: (type_identifier) @name (#eq? @name "{name}"))) @el
                (function_declaration name: (identifier) @name (#eq? @name "{name}")) @el
                (method_declaration name: (field_identifier) @name (#eq? @name "{name}")) @el
            """
        }
        
        # Default query if specific one not defined
        query_str = queries.get(lang_name, f"""
            (class_declaration name: (identifier) @name (#eq? @name "{name}")) @el
            (function_definition name: (identifier) @name (#eq? @name "{name}")) @el
        """)
        
        captures = execute_query(lang, query_str, tree.root_node)
        for node, tag in captures:
            if tag == "el":
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                code = content[node.start_byte:node.end_byte]
                return code, start_line, end_line
        return None, 0, 0

    def _find_callers_by_name(self, repo_id: str, name: str, source_rel: str) -> List[Tuple[str, str]]:
        """Find files that import or call the specified symbol from the source file."""
        cursor = self.db.conn.execute("""
            SELECT DISTINCT f.name, d.relative_path, r.root_path
            FROM edges e
            JOIN symbols target ON target.id = e.target_id
            JOIN files target_f ON target_f.id = target.file_id
            JOIN directories target_d ON target_d.id = target_f.directory_id
            JOIN symbols caller ON caller.id = e.source_id
            JOIN files f ON f.id = caller.file_id
            JOIN directories d ON d.id = f.directory_id
            JOIN repositories r ON r.id = f.repository_id
            WHERE target.name = ? 
            AND (CASE WHEN target_d.relative_path = '' THEN target_f.name ELSE target_d.relative_path || '/' || target_f.name END) = ?
            AND f.repository_id = ?
            AND e.relation_type IN ('CALLS', 'DEPENDS_ON')
        """, (name, source_rel, repo_id))
        
        results = []
        for row in cursor.fetchall():
            rel_path = f"{row['relative_path']}/{row['name']}" if row['relative_path'] else row['name']
            abs_path = os.path.join(row["root_path"], row["relative_path"], row["name"])
            results.append((abs_path, rel_path))
        return results

    def _apply_edits(self, content: str, edits: List[Tuple[int, int, str]]) -> str:
        """Apply text replacements by byte offsets, from back to front."""
        if not edits: return content
        unique_edits = sorted(list(set(edits)), key=lambda x: x[0], reverse=True)
        
        new_content = content
        for start, end, text in unique_edits:
            b_content = new_content.encode("utf8")
            b_content = b_content[:start] + text.encode("utf8") + b_content[end:]
            new_content = b_content.decode("utf8")
        return new_content

    def _recipe_standardize_docstrings_python(self, content: str) -> str:
        """Simple recipe to ensure functions have triple-quote docstrings."""
        # This would use tree-sitter to find functions without docstrings and add them
        # For now, a simplified version using regex or a targeted TS query
        return content # Placeholder for full implementation

    def _recipe_add_type_hints_python(self, content: str) -> str:
        """Simple recipe to add basic Any type hints to unhinted parameters."""
        return content # Placeholder

    def _rename_in_file_python(self, content: str, old_name: str, new_name: str) -> str:
        lang = self.ts.get_language_safe("python")
        parser = self.ts.create_parser("python")
        tree = parser.parse(bytes(content, "utf8"))
        query_str = f'((identifier) @name (#eq? @name "{old_name}"))'
        captures = execute_query(lang, query_str, tree.root_node)
        edits = []
        for node, _ in captures:
            parent = node.parent
            is_valid = True
            while parent:
                if parent.type in ("string", "comment"):
                    is_valid = False
                    break
                parent = parent.parent
            if is_valid:
                edits.append((node.start_byte, node.end_byte, new_name))
        return self._apply_edits(content, edits)

    def _rename_in_file_js(self, content: str, old_name: str, new_name: str) -> str:
        lang_name = "typescript"
        lang = self.ts.get_language_safe(lang_name)
        parser = self.ts.create_parser(lang_name)
        tree = parser.parse(bytes(content, "utf8"))
        query_str = f'((identifier) @name (#eq? @name "{old_name}"))'
        captures = execute_query(lang, query_str, tree.root_node)
        edits = []
        for node, _ in captures:
            parent = node.parent
            is_valid = True
            while parent:
                if parent.type in ("string", "comment", "template_string"):
                    is_valid = False
                    break
                parent = parent.parent
            if is_valid:
                edits.append((node.start_byte, node.end_byte, new_name))
        return self._apply_edits(content, edits)

    def _rename_in_file_go(self, content: str, old_name: str, new_name: str) -> str:
        lang = self.ts.get_language_safe("go")
        parser = self.ts.create_parser("go")
        tree = parser.parse(bytes(content, "utf8"))
        query_str = f'((field_identifier) @name (#eq? @name "{old_name}")) ((identifier) @name (#eq? @name "{old_name}"))'
        captures = execute_query(lang, query_str, tree.root_node)
        edits = []
        for node, _ in captures:
            parent = node.parent
            is_valid = True
            while parent:
                if parent.type in ("string_literal", "comment"):
                    is_valid = False
                    break
                parent = parent.parent
            if is_valid:
                edits.append((node.start_byte, node.end_byte, new_name))
        return self._apply_edits(content, edits)

    def _update_import_python(self, caller_path: str, repo_id: str, name: str, old_rel: str, new_rel: str):
        old_mod = old_rel.replace(".py", "").replace("/", ".")
        new_mod = new_rel.replace(".py", "").replace("/", ".")
        if old_mod == new_mod: return
        data = self.fs.read_file(caller_path, repo_id)
        if "error" in data: return
        content = data["content"]
        new_content = content
        from_pattern = rf"(from\s+{re.escape(old_mod)}\s+import\s+)([\w\s,()]+)"
        match = re.search(from_pattern, new_content)
        if match:
            prefix = match.group(1)
            imports_str = match.group(2)
            import_list = [i.strip() for i in imports_str.replace("(", "").replace(")", "").split(",")]
            if name in import_list:
                import_list.remove(name)
                if not import_list:
                    new_content = new_content.replace(match.group(0), "")
                else:
                    new_imports = ", ".join(import_list)
                    new_content = new_content.replace(match.group(0), f"{prefix}({new_imports})" if "(" in imports_str else f"{prefix}{new_imports}")
                new_import_stmt = f"from {new_mod} import {name}\n"
                lines = new_content.splitlines(keepends=True)
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.startswith(("import ", "from ")): insert_idx = i + 1
                lines.insert(insert_idx, new_import_stmt)
                new_content = "".join(lines)
        if new_content != content:
            self.fs.write_file(caller_path, new_content, repo_id, dry_run=False)

    def _update_import_js(self, caller_path: str, repo_id: str, name: str, old_rel: str, new_rel: str):
        old_mod = old_rel.replace(".ts", "").replace(".js", "").replace(".tsx", "")
        new_mod = new_rel.replace(".ts", "").replace(".js", "").replace(".tsx", "")
        data = self.fs.read_file(caller_path, repo_id)
        if "error" in data: return
        content = data["content"]
        pattern = rf"(import\s+{{)([\w\s,]+)(}}\s+from\s+['\"]{re.escape(old_mod)}['\"])"
        match = re.search(pattern, content)
        if match:
            prefix = match.group(1)
            imports_str = match.group(2)
            suffix = match.group(3)
            import_list = [i.strip() for i in imports_str.split(",")]
            if name in import_list:
                import_list.remove(name)
                new_content = content
                if not import_list:
                    new_content = new_content.replace(match.group(0), "")
                else:
                    new_imports = ", ".join(import_list)
                    new_content = new_content.replace(match.group(0), f"{prefix} {new_imports} {suffix}")
                new_import_stmt = f"import {{ {name} }} from '{new_mod}';\n"
                new_content = new_import_stmt + new_content
                self.fs.write_file(caller_path, new_content, repo_id, dry_run=False)

    def _log_event(self, level: str, event_code: str, context: Dict, request_id: str = "internal"):
        context["request_id"] = request_id
        msg = f"[{event_code}] {json.dumps(context)}"
        if level == "ERROR":
            logger.error(msg)
        elif level == "WARN":
            logger.warning(msg)
        else:
            logger.info(msg)
