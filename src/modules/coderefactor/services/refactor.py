"""
Class Refactor – Single Responsibility: Manage safe, semantic code
transformations using AST (Tree-Sitter) + Knowledge Graph + Filesystem + Git.
Removed: Search (moved to fs_search), duplicate rename_symbol.
Added: change_signature, extract_function, inline_function.

:project: CodeCortex
:package: Modules.Coderefactor.Services.Refactor
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeRefactor-v1.0
"""

import os
import json
import re
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from src.core.database import DatabaseManager
from src.core.logging import get_logger
from src.modules.filesystem.core.service import Filesystem
from src.modules.coderepository import Git
from src.modules.codegraph.services.graph import Graph
from src.core.parser.tree_sitter_manager import get_tree_sitter_manager, execute_query
from src.modules.coderefactor.core.dtos import (
    RefactorChange, RefactorResult, ImpactResult, BlastRadius, RefactorErrorCode,
)
from src.core.utils.diff import generate_unified_diff

logger = get_logger("CodeCortex.Domain.Refactor")

class Refactor:
    """
    Service for executing safe, atomic refactoring operations.
    Depends on: repo_index (AST + graph), filesystem (read/write), git (commit).
    Single unified entry point: code_refactor(repo_id, action, target_symbol, ...).
    """

    def __init__(self, db: DatabaseManager, fs_service: Filesystem,
                 git_service: Git, graph_service: Graph):
        self.db = db
        self.fs = fs_service
        self.git = git_service
        self.graph = graph_service
        self.ts = get_tree_sitter_manager()

    # ═══════════════════════════════════════════════════════════════════
    # PUBLIC ACTIONS
    # ═══════════════════════════════════════════════════════════════════

    async def analyze_impact(self, repo_id: str, symbol_name: str,
                              source_file: str) -> ImpactResult:
        """Blast radius analysis using the Knowledge Graph."""
        try:
            root_path = self._get_repo_root(repo_id)
            if not root_path:
                return ImpactResult(repository_id=repo_id, symbol_name=symbol_name,
                                    source_file=source_file,
                                    summary=f"[{RefactorErrorCode.MISSING_REPO}] Repository not found: {repo_id}")

            callers = self._find_callers_by_name(repo_id, symbol_name, source_file)
            affected = list(set(c[0] for c in callers))
            direct = len(affected)

            transitive = self._find_transitive_callers(repo_id, affected)
            total = len(set(affected + transitive))
            test_files = sum(1 for f in affected if "/test/" in f or "/tests/" in f or f.startswith("test_"))
            core = total - test_files

            risk = "low"
            if total > 10:
                risk = "high"
            elif total > 3:
                risk = "medium"

            br = BlastRadius(
                total_files=total,
                direct_dependents=direct,
                transitive_dependents=len(transitive),
                test_files=test_files,
                core_modules=core,
                affected_symbols=self._count_symbols_in_files(repo_id, affected),
                confidence_score=85 if total > 0 else 100,
            )

            summary = f"Symbol '{symbol_name}' affects {total} file(s) ({direct} direct, {len(transitive)} transitive). "
            rec = ""
            if risk == "high":
                summary += "CAUTION: Widely used symbol."
                rec = "Run integration tests after changes. Consider incremental refactoring."
            elif risk == "medium":
                rec = "Review each affected file before applying."

            return ImpactResult(
                repository_id=repo_id, symbol_name=symbol_name,
                source_file=source_file, blast_radius=br,
                affected_files=affected, risk_level=risk,
                summary=summary, recommendation=rec,
            )
        except Exception as e:
            logger.error(f"Impact analysis failed: {e}")
            return ImpactResult(repository_id=repo_id, symbol_name=symbol_name,
                                source_file=source_file,
                                summary=f"[{RefactorErrorCode.INTERNAL}] {e}")

    async def rename_symbol(self, repo_id: str, symbol_name: str,
                             source_file: str, new_name: str,
                             dry_run: bool = True) -> RefactorResult:
        """Rename a symbol across the codebase using AST-aware replacements."""
        try:
            root_path = self._get_repo_root(repo_id)
            if not root_path:
                return RefactorResult(status="error",
                                      message=f"[{RefactorErrorCode.MISSING_REPO}] Repository not found: {repo_id}",
                                      repository_id=repo_id, action="rename",
                                      error_code=RefactorErrorCode.MISSING_REPO)

            callers = self._find_callers_by_name(repo_id, symbol_name, source_file)
            affected = sorted(list(set([source_file] + [c[0] for c in callers])))
            changes = []

            for file_path in affected:
                abs_path = self._resolve_abs(root_path, file_path)
                if not abs_path or not abs_path.exists():
                    continue
                content = abs_path.read_text(encoding="utf-8", errors="ignore")
                lang = self._detect_lang(str(abs_path))
                new_content = self._rename_in_file(content, symbol_name, new_name, lang)
                if new_content != content:
                    rel = self._get_rel_path(root_path, str(abs_path))
                    diff = generate_unified_diff(content, new_content, rel)
                    changes.append(RefactorChange(
                        path=rel, action="modify",
                        description=f"Rename '{symbol_name}' → '{new_name}'",
                        diff=diff,
                    ))

            if dry_run:
                return RefactorResult(status="preview", message=f"Rename plan: {len(changes)} file(s)",
                                      repository_id=repo_id, action="rename", changes=changes)

            for ch in changes:
                ap = root_path / ch.path
                if ap.exists():
                    content = ap.read_text(encoding="utf-8", errors="ignore")
                    new_content = self._rename_in_file(content, symbol_name, new_name,
                                                       self._detect_lang(str(ap)))
                    ap.write_text(new_content, encoding="utf-8")

            paths = [c.path for c in changes]
            commit = await self.git.stage_and_commit(root_path, paths,
                     f"refactor: rename {symbol_name} -> {new_name}")

            reindex = self._reindex_affected_files(repo_id, root_path, paths)
            logger.info(f"Reindexed {reindex['files_reindexed']} files after rename")

            return RefactorResult(status="applied", message=f"Renamed in {len(changes)} file(s)",
                                  repository_id=repo_id, action="rename", changes=changes,
                                  commit_hash=commit.get("commit_hash"),
                                  validation_result=json.dumps(reindex))
        except Exception as e:
            logger.error(f"Rename failed: {e}")
            return RefactorResult(status="error", message=str(e), repository_id=repo_id, action="rename",
                                  error_code=RefactorErrorCode.INTERNAL)

    async def move_code_element(self, repo_id: str, element_name: str,
                                 source_file: str, target_file: str,
                                 dry_run: bool = True) -> RefactorResult:
        """Move a class or function from source to target, updating imports."""
        try:
            root_path = self._get_repo_root(repo_id)
            if not root_path:
                return RefactorResult(status="error",
                                      message=f"[{RefactorErrorCode.MISSING_REPO}] Repository not found: {repo_id}",
                                      repository_id=repo_id, action="move",
                                      error_code=RefactorErrorCode.MISSING_REPO)

            src_abs = self._resolve_abs(root_path, source_file)
            tgt_abs = self._resolve_abs(root_path, target_file)
            if not src_abs or not src_abs.exists():
                return RefactorResult(status="error",
                                      message=f"[{RefactorErrorCode.MISSING_SOURCE_FILE}] Source not found: {source_file}",
                                      repository_id=repo_id, action="move",
                                      error_code=RefactorErrorCode.MISSING_SOURCE_FILE)

            content = src_abs.read_text(encoding="utf-8", errors="ignore")
            element_code, start_line, end_line = self._extract_element(content, element_name, str(src_abs))
            if not element_code:
                return RefactorResult(status="error",
                                      message=f"[{RefactorErrorCode.MISSING_SYMBOL}] Element '{element_name}' not found in {source_file}",
                                      repository_id=repo_id, action="move",
                                      error_code=RefactorErrorCode.MISSING_SYMBOL)

            # ── Blast Radius Analysis ──────────────────────────────────────
            callers = self._find_callers_by_name(repo_id, element_name, source_file)
            affected = list(set(c[0] for c in callers))
            direct = len(affected)
            transitive = self._find_transitive_callers(repo_id, affected)
            test_files = sum(1 for f in affected if "/test/" in f or "/tests/" in f or f.startswith("test_"))
            core = len(affected) - test_files

            br = BlastRadius(
                total_files=len(set(affected + transitive)),
                direct_dependents=direct,
                transitive_dependents=len(transitive),
                test_files=test_files,
                core_modules=core,
                affected_symbols=self._count_symbols_in_files(repo_id, affected),
                confidence_score=85 if affected else 100,
            )

            risk = "low"
            if direct > 10:
                risk = "high"
            elif direct > 3:
                risk = "medium"

            changes = []
            src_lines = content.splitlines(keepends=True)
            new_src = "".join(src_lines[:start_line - 1] + src_lines[end_line:])
            src_diff = generate_unified_diff(content, new_src, source_file)
            changes.append(RefactorChange(path=source_file, action="modify",
                         description=f"Delete {element_name} (L{start_line}-{end_line})", diff=src_diff))

            # ── Smart Placement Detection ─────────────────────────────────
            dest_content = tgt_abs.read_text(encoding="utf-8", errors="ignore") if tgt_abs and tgt_abs.exists() else ""
            lang = self._detect_lang(target_file)
            insert_line = self._detect_smart_placement(dest_content, element_name, lang)

            # Insert at smart position instead of just appending
            dest_lines = dest_content.splitlines(keepends=True) if dest_content else []
            if insert_line < len(dest_lines):
                dest_lines.insert(insert_line, element_code + "\n")
            else:
                # Fallback: append with newline padding
                dest_lines = (dest_lines + ["\n", element_code + "\n"])
            new_dest = "".join(dest_lines)

            dest_diff = generate_unified_diff(dest_content, new_dest, target_file)
            changes.append(RefactorChange(path=target_file, action="modify",
                         description=f"Insert {element_name} at line {insert_line} (smart placement)", diff=dest_diff))

            for caller_abs, caller_rel in callers:
                if caller_abs == source_file:
                    continue
                changes.append(RefactorChange(path=caller_abs, action="update_import",
                             description=f"Redirect import of {element_name}"))

            if dry_run:
                return RefactorResult(
                    status="preview",
                    message=f"Move plan: {len(changes)} change(s), risk={risk}, {direct} direct dependents",
                    repository_id=repo_id, action="move", changes=changes,
                    blast_radius=br,
                )

            src_abs.write_text(new_src, encoding="utf-8")
            (tgt_abs or root_path / target_file).parent.mkdir(parents=True, exist_ok=True)
            (tgt_abs or root_path / target_file).write_text(new_dest, encoding="utf-8")

            # ── Multi-language Import Updates ─────────────────────────────
            updated_count = 0
            for caller_abs, caller_rel in callers:
                if caller_abs == source_file:
                    continue
                updated = await self._update_import_generic(caller_abs, element_name, source_file, target_file)
                if updated:
                    updated_count += 1

            affected = [source_file, target_file] + [c[0] for c in callers]
            commit = await self.git.stage_and_commit(root_path, list(set(affected)),
                     f"refactor: move {element_name} from {source_file} to {target_file}")

            reindex = self._reindex_affected_files(repo_id, root_path, list(set(affected)))
            logger.info(f"Reindexed {reindex['files_reindexed']} files after move, updated {updated_count} imports")

            return RefactorResult(
                status="applied",
                message=f"Moved {element_name} to {target_file}, updated {updated_count} imports",
                repository_id=repo_id, action="move", changes=changes,
                blast_radius=br,
                commit_hash=commit.get("commit_hash"),
                validation_result=json.dumps(reindex)
            )
        except Exception as e:
            logger.error(f"move_code_element failed: {e}")
            return RefactorResult(
                status="error", message=str(e), repository_id=repo_id, action="move",
                error_code=RefactorErrorCode.INTERNAL
            )

    async def change_signature(self, repo_id: str, target_symbol: str,
                                changes: Dict[str, Any], dry_run: bool = True) -> RefactorResult:
        """Change function signature — add/remove/reorder parameters.

        changes:
          add_params:    [{"name": "debug", "default_value": "False"}]
          remove_params: ["old_param"]
          reorder:       ["c", "a", "b"]  (new parameter name order)
        """
        try:
            source_file, symbol_name = self._parse_target(target_symbol)
            root_path = self._get_repo_root(repo_id)
            if not root_path:
                return RefactorResult(status="error", message="Repository not found",
                                      repository_id=repo_id, action="change_signature")

            abs_path = self._resolve_abs(root_path, source_file)
            if not abs_path or not abs_path.exists():
                return RefactorResult(status="error", message=f"File not found: {source_file}",
                                      repository_id=repo_id, action="change_signature")

            content = abs_path.read_text(encoding="utf-8", errors="ignore")
            lang_name = self._detect_lang(str(abs_path))
            lang = self.ts.get_language_safe(lang_name)
            parser = self.ts.create_parser(lang_name)
            tree = parser.parse(bytes(content, "utf8"))

            query_str = f'((function_definition name: (identifier) @name (#eq? @name "{symbol_name}")) @func)'
            captures = execute_query(lang, query_str, tree.root_node)
            func_node = None
            for node, tag in captures:
                if tag == "func":
                    func_node = node
                    break
            if not func_node:
                return RefactorResult(status="error", message=f"Function '{symbol_name}' not found",
                                      repository_id=repo_id, action="change_signature")

            params_node = func_node.child_by_field_name("parameters")
            if not params_node:
                return RefactorResult(status="error", message="Function has no parameters node",
                                      repository_id=repo_id, action="change_signature")

            # Build current param list from AST
            current_params = []
            def _walk_params(node):
                for i in range(node.child_count):
                    c = node.child(i)
                    if c is None:
                        continue
                    if c.type in ("identifier", "keyword_identifier"):
                        current_params.append({"name": c.text.decode(), "start": c.start_byte, "end": c.end_byte})
                    elif c.type == "typed_parameter":
                        nc = c.child_by_field_name("name")
                        if nc:
                            current_params.append({"name": nc.text.decode(), "start": nc.start_byte, "end": nc.end_byte})
                    elif c.type in ("default_parameter", "keyword_argument"):
                        nc = c.child_by_field_name("name")
                        if nc:
                            current_params.append({"name": nc.text.decode(), "start": nc.start_byte, "end": nc.end_byte})
                    _walk_params(c)
            _walk_params(params_node)

            param_names = [p["name"] for p in current_params]
            add_list = changes.get("add_params", [])
            remove_list = changes.get("remove_params", [])
            reorder_list = changes.get("reorder") or param_names[:]

            # Remove params
            keep_params = [p for p in current_params if p["name"] not in remove_list]
            # Add params (default to end)
            existing_names = {p["name"] for p in keep_params}
            for ap in add_list:
                if ap["name"] not in existing_names:
                    keep_params.append(ap)
            # Reorder
            name_order = {n: i for i, n in enumerate(reorder_list)}
            keep_params.sort(key=lambda p: name_order.get(p["name"], 999))

            # Build new signature string
            parts = []
            for p in keep_params:
                if isinstance(p, dict) and "default_value" in p:
                    parts.append(f"{p['name']}={p['default_value']}")
                else:
                    parts.append(p["name"])
            new_params_str = ", ".join(parts)

            # Replace params node text
            params_text = content[params_node.start_byte:params_node.end_byte]
            new_params_text = f"({new_params_str})"
            content = content[:params_node.start_byte] + new_params_text + content[params_node.end_byte:]

            # Fix byte offsets: recalculate end of replacement
            shift = len(new_params_text) - len(params_text)

            # ── Blast Radius Analysis ──────────────────────────────────────
            callers = self._find_callers_by_name(repo_id, symbol_name, source_file)
            affected = list(set(c[0] for c in callers))
            direct = len(affected)
            transitive = self._find_transitive_callers(repo_id, affected)
            test_files = sum(1 for f in affected if "/test/" in f or "/tests/" in f or f.startswith("test_"))
            core = len(affected) - test_files

            br = BlastRadius(
                total_files=len(set(affected + transitive)),
                direct_dependents=direct,
                transitive_dependents=len(transitive),
                test_files=test_files,
                core_modules=core,
                affected_symbols=self._count_symbols_in_files(repo_id, affected),
                confidence_score=85 if affected else 100,
            )

            risk = "low"
            if direct > 10:
                risk = "high"
            elif direct > 3:
                risk = "medium"

            # ── Multi-language Call Site Updates ─────────────────────────
            caller_changes = []
            updated_call_sites = 0
            for caller_abs, _ in callers:
                if not Path(caller_abs).exists():
                    continue
                cc = Path(caller_abs).read_text(encoding="utf-8", errors="ignore")
                lang2 = self._detect_lang(caller_abs)

                # Support Python, JS, TS, Go for call site updates
                if lang2 not in ("python", "javascript", "typescript", "go"):
                    continue

                l2 = self.ts.get_language_safe(lang2)
                p2 = self.ts.create_parser(lang2)
                t2 = p2.parse(bytes(cc, "utf8"))

                # Language-specific call patterns
                if lang2 == "python":
                    q2 = f'((call function: (identifier) @name (#eq? @name "{symbol_name}")) @call)'
                elif lang2 in ("javascript", "typescript"):
                    q2 = f'((call_expression function: (identifier) @name (#eq? @name "{symbol_name}")) @call)'
                elif lang2 == "go":
                    q2 = f'((call_expression function: (identifier) @name (#eq? @name "{symbol_name}")) @call)'
                else:
                    continue

                cap2 = execute_query(l2, q2, t2.root_node)
                c_edits = []
                for cn, ct in cap2:
                    if ct != "call":
                        continue
                    args_node = cn.child_by_field_name("arguments")
                    if not args_node:
                        continue
                    # Replace arguments with new pattern
                    old_args_text = cc[args_node.start_byte:args_node.end_byte]
                    new_args = new_params_str
                    if old_args_text != "()":
                        new_args_text = f"({new_args})"
                    else:
                        new_args_text = "()"
                    c_edits.append((args_node.start_byte, args_node.end_byte, new_args_text))

                if c_edits:
                    nc2 = self._apply_edits(cc, c_edits)
                    rel = self._get_rel_path(root_path, caller_abs)
                    diff = generate_unified_diff(cc, nc2, rel)
                    caller_changes.append(RefactorChange(path=rel, action="modify",
                                       description=f"Update call to {symbol_name}", diff=diff))
                    updated_call_sites += 1
                    if not dry_run:
                        Path(caller_abs).write_text(nc2, encoding="utf-8")

            rel_src = self._get_rel_path(root_path, str(abs_path))
            src_diff = generate_unified_diff(content, content, rel_src)
            main_change = RefactorChange(path=rel_src, action="modify",
                        description=f"Change signature of {symbol_name}", diff=src_diff)

            changes_list = [main_change] + caller_changes

            if dry_run:
                return RefactorResult(
                    status="preview",
                    message=f"Signature change plan: {len(changes_list)} changes, risk={risk}, {updated_call_sites} call sites",
                    repository_id=repo_id, action="change_signature", changes=changes_list,
                    blast_radius=br,
                )

            abs_path.write_text(content, encoding="utf-8")
            all_paths = [rel_src] + [c.path for c in caller_changes]
            commit = await self.git.stage_and_commit(root_path, all_paths,
                     f"refactor: change signature of {symbol_name}")

            reindex = self._reindex_affected_files(repo_id, root_path, all_paths)
            logger.info(f"Reindexed {reindex['files_reindexed']} files after change_signature, updated {updated_call_sites} call sites")

            return RefactorResult(
                status="applied",
                message=f"Signature of {symbol_name} changed, updated {updated_call_sites} call sites",
                repository_id=repo_id, action="change_signature",
                changes=changes_list, blast_radius=br,
                commit_hash=commit.get("commit_hash"),
                validation_result=json.dumps(reindex)
            )
        except Exception as e:
            logger.error(f"change_signature failed: {e}")
            return RefactorResult(
                status="error", message=str(e), repository_id=repo_id,
                action="change_signature", error_code=RefactorErrorCode.INTERNAL
            )

    async def extract_function(self, repo_id: str, target_symbol: str,
                                changes: Dict[str, Any], dry_run: bool = True) -> RefactorResult:
        """Extract selected code lines into a new function.

        changes:
          new_name:    "helper_func"     (name of new function)
          start_line:  10                (1-indexed, inclusive)
          end_line:    20                (1-indexed, inclusive)
        """
        try:
            source_file = target_symbol.split("::")[0] if "::" in target_symbol else target_symbol
            root_path = self._get_repo_root(repo_id)
            if not root_path:
                return RefactorResult(status="error", message="Repository not found",
                                      repository_id=repo_id, action="extract_function")

            abs_path = self._resolve_abs(root_path, source_file)
            if not abs_path or not abs_path.exists():
                return RefactorResult(status="error", message=f"File not found: {source_file}",
                                      repository_id=repo_id, action="extract_function")

            content = abs_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines(keepends=True)

            new_name = changes.get("new_name", "extracted_function")
            start_line = changes.get("start_line", 1)
            end_line = changes.get("end_line", len(lines))

            si, ei = max(0, start_line - 1), min(len(lines), end_line)
            extracted_lines = lines[si:ei]
            extracted_text = "".join(extracted_lines)
            extracted_stripped = extracted_text.strip()
            if not extracted_stripped:
                return RefactorResult(status="error", message="No code to extract",
                                      repository_id=repo_id, action="extract_function")

            # Simple variable analysis: find which names are used but not defined locally
            used_names = set()
            defined_names = set()
            for ln in extracted_lines:
                for word in ln.replace("(", " ").replace(")", " ").replace(",", " ").replace("=", " = ").split():
                    w = word.strip()
                    if w and w[0].isalpha() and not w.startswith(("#", '"', "'")):
                        used_names.add(w)
            # Python-specific: detect function defs and assignments inside extracted block
            for ln in extracted_lines:
                m = re.match(r"^\s+(?:def|class)\s+(\w+)", ln)
                if m:
                    defined_names.add(m.group(1))
                m = re.match(r"^\s+(\w+)\s*=", ln)
                if m:
                    defined_names.add(m.group(1))
                m = re.match(r"^\s+for\s+(\w+)", ln)
                if m:
                    defined_names.add(m.group(1))

            params = sorted(used_names - defined_names - {"self", "cls", "None", "True", "False"})
            indent = "    "
            body_indent = indent
            # Detect existing indentation
            for ln in extracted_lines:
                stripped = ln.lstrip()
                if stripped and not stripped.startswith("#"):
                    body_indent = ln[:len(ln) - len(stripped)]
                    break

            new_func = f"def {new_name}({', '.join(params)}):\n"
            for ln in extracted_lines:
                stripped = ln.strip()
                if stripped:
                    new_func += f"{body_indent}{stripped}\n"
                else:
                    new_func += "\n"

            call_str = f"{new_name}({', '.join(params)})"
            new_lines = lines[:si] + [f"{body_indent}{call_str}\n"] + lines[ei:]
            new_content = "".join(new_lines)

            # Prepend function definition before the class/method containing the lines
            # Find containing function/class
            lang_name = self._detect_lang(str(abs_path))
            lang = self.ts.get_language_safe(lang_name)
            parser = self.ts.create_parser(lang_name)
            tree = parser.parse(bytes(content, "utf8"))

            containing_node = None
            def _find_containing(node, line):
                if node.start_point[0] <= line <= node.end_point[0]:
                    for i in range(node.child_count):
                        child = node.child(i)
                        if child and _find_containing(child, line):
                            return _find_containing(child, line)
                    return node
                return None

            target_node = _find_containing(tree.root_node, si)
            if target_node and target_node.type in ("function_definition", "class_definition", "module"):
                # Insert new function before the containing block
                insert_line = target_node.start_point[0]
                if target_node.type == "module":
                    insert_line = si  # insert before extracted lines

                # Build full new function with proper module-level indent
                module_func = f"\n\ndef {new_name}({', '.join(params)}):\n"
                for ln in extracted_lines:
                    stripped = ln.strip()
                    if stripped:
                        module_func += f"    {stripped}\n"
                    else:
                        module_func += "\n"

                new_lines2 = lines[:insert_line] + [module_func] + lines[insert_line:]
            else:
                new_lines2 = [new_func + "\n"] + new_lines

            new_content2 = "".join(new_lines2)
            rel = self._get_rel_path(root_path, str(abs_path))
            diff = generate_unified_diff(content, new_content2, rel)
            change = RefactorChange(path=rel, action="modify",
                                    description=f"Extract {new_name} (L{start_line}-{end_line})", diff=diff)

            if dry_run:
                return RefactorResult(status="preview", message=f"Extract function plan: {new_name}",
                                      repository_id=repo_id, action="extract_function", changes=[change])

            abs_path.write_text(new_content2, encoding="utf-8")
            commit = await self.git.stage_and_commit(root_path, [source_file],
                     f"refactor: extract {new_name} from {source_file}")

            reindex = self._reindex_affected_files(repo_id, root_path, [source_file])
            logger.info(f"Reindexed {reindex['files_reindexed']} files after extract_function")

            return RefactorResult(status="applied", message=f"Extracted {new_name}",
                                  repository_id=repo_id, action="extract_function",
                                  changes=[change], commit_hash=commit.get("commit_hash"),
                                  validation_result=json.dumps(reindex))
        except Exception as e:
            logger.error(f"extract_function failed: {e}")
            return RefactorResult(status="error", message=str(e), repository_id=repo_id,
                                  action="extract_function")

    async def inline_function(self, repo_id: str, target_symbol: str,
                               changes: Dict[str, Any], dry_run: bool = True) -> RefactorResult:
        """Inline a function at all call sites, then remove the function definition.

        target_symbol: "file_path::function_name"
        """
        try:
            source_file, symbol_name = self._parse_target(target_symbol)
            root_path = self._get_repo_root(repo_id)
            if not root_path:
                return RefactorResult(status="error", message="Repository not found",
                                      repository_id=repo_id, action="inline_function")

            abs_path = self._resolve_abs(root_path, source_file)
            if not abs_path or not abs_path.exists():
                return RefactorResult(status="error", message=f"File not found: {source_file}",
                                      repository_id=repo_id, action="inline_function")

            content = abs_path.read_text(encoding="utf-8", errors="ignore")
            lang_name = self._detect_lang(str(abs_path))

            # Parse function body via Tree-Sitter
            lang = self.ts.get_language_safe(lang_name)
            parser = self.ts.create_parser(lang_name)
            tree = parser.parse(bytes(content, "utf8"))

            q = f'((function_definition name: (identifier) @name (#eq? @name "{symbol_name}")) @func)'
            captures = execute_query(lang, q, tree.root_node)
            func_node = None
            for node, tag in captures:
                if tag == "func":
                    func_node = node
                    break
            if not func_node:
                return RefactorResult(status="error", message=f"Function '{symbol_name}' not found",
                                      repository_id=repo_id, action="inline_function")

            # Get function body
            body_node = func_node.child_by_field_name("body")
            params_node = func_node.child_by_field_name("parameters")
            if not body_node or not params_node:
                return RefactorResult(status="error", message="Cannot parse function body or parameters",
                                      repository_id=repo_id, action="inline_function")

            body_text = content[body_node.start_byte:body_node.end_byte]
            # Strip outer braces/colon/newline for Python
            body_lines = body_text.split("\n")
            # Remove first line (the colon line or opening brace)
            if body_lines and body_lines[0].strip() in (":", "{", ""):
                body_lines = body_lines[1:]
            body_lines = [ln for ln in body_lines if ln.strip()]
            # Dedent
            if body_lines:
                base_indent = len(body_lines[0]) - len(body_lines[0].lstrip())
                body_lines = [ln[base_indent:] if len(ln) > base_indent else ln for ln in body_lines]

            # Get parameter names
            param_names = []
            def _wp(node):
                for i in range(node.child_count):
                    c = node.child(i)
                    if c is None:
                        continue
                    if c.type in ("identifier", "keyword_identifier"):
                        param_names.append(c.text.decode())
                    _wp(c)
            _wp(params_node)

            # Find call sites
            callers = self._find_callers_by_name(repo_id, symbol_name, source_file)
            all_changes = []

            for caller_abs, _ in callers:
                if not Path(caller_abs).exists():
                    continue
                cc = Path(caller_abs).read_text(encoding="utf-8", errors="ignore")
                l2 = self._detect_lang(caller_abs)
                if l2 == "unknown":
                    continue
                lang2 = self.ts.get_language_safe(l2)
                p2 = self.ts.create_parser(l2)
                t2 = p2.parse(bytes(cc, "utf8"))
                q2 = f'((call function: (identifier) @name (#eq? @name "{symbol_name}")) @call)'
                cap2 = execute_query(lang2, q2, t2.root_node)

                edits = []
                for cn, ct in cap2:
                    if ct != "call":
                        continue
                    args_node = cn.child_by_field_name("arguments")
                    if not args_node:
                        continue

                    # Extract argument values
                    args_text = cc[args_node.start_byte:args_node.end_byte].lstrip("(").rstrip(")")
                    arg_values = [a.strip() for a in args_text.split(",")] if args_text else []

                    # Build substitution map
                    subs = {}
                    for i, pn in enumerate(param_names):
                        if i < len(arg_values):
                            subs[pn] = arg_values[i]
                        else:
                            subs[pn] = "None"

                    # Replace params in body with args
                    inlined = "\n".join(body_lines)
                    for pn, av in subs.items():
                        inlined = inlined.replace(pn, av)

                    # Replace the entire call with inlined body
                    call_text = cc[cn.start_byte:cn.end_byte]

                    # Create a versioned replacement
                    # Indent inlined body to match current line's indentation
                    line_start = cc.rfind("\n", 0, cn.start_byte) + 1
                    line_indent = cc[line_start:cn.start_byte]
                    inlined_indented = inlined.replace("\n", "\n" + line_indent)

                    edits.append((cn.start_byte, cn.end_byte, inlined_indented))

                if edits:
                    nc2 = self._apply_edits(cc, edits)
                    rel = self._get_rel_path(root_path, caller_abs)
                    diff = generate_unified_diff(cc, nc2, rel)
                    all_changes.append(RefactorChange(path=rel, action="modify",
                                    description=f"Inline {symbol_name} call", diff=diff))
                    if not dry_run:
                        Path(caller_abs).write_text(nc2, encoding="utf-8")

            # Remove function definition from source file
            func_text = content[func_node.start_byte:func_node.end_byte]
            content_no_func = content.replace(func_text, "", 1)
            # Clean up extra blank lines
            content_no_func = re.sub(r"\n{3,}", "\n\n", content_no_func)
            rel_src = self._get_rel_path(root_path, str(abs_path))
            src_diff = generate_unified_diff(content, content_no_func, rel_src)
            all_changes.append(RefactorChange(path=rel_src, action="modify",
                            description=f"Remove definition of {symbol_name}", diff=src_diff))

            if dry_run:
                return RefactorResult(status="preview", message=f"Inline plan: {symbol_name} → {len([c for c in all_changes if c.action == 'modify'])} site(s)",
                                      repository_id=repo_id, action="inline_function", changes=all_changes)

            abs_path.write_text(content_no_func, encoding="utf-8")
            all_paths = [rel_src] + [c.path for c in all_changes if c.path != rel_src]
            commit = await self.git.stage_and_commit(root_path, list(set(all_paths)),
                     f"refactor: inline {symbol_name}")

            reindex = self._reindex_affected_files(repo_id, root_path, list(set(all_paths)))
            logger.info(f"Reindexed {reindex['files_reindexed']} files after inline_function")

            return RefactorResult(status="applied", message=f"Inlined {symbol_name}",
                                  repository_id=repo_id, action="inline_function",
                                  changes=all_changes, commit_hash=commit.get("commit_hash"),
                                  validation_result=json.dumps(reindex))
        except Exception as e:
            logger.error(f"inline_function failed: {e}")
            return RefactorResult(status="error", message=str(e), repository_id=repo_id,
                                  action="inline_function")

    # ═══════════════════════════════════════════════════════════════════
    # VCS-LEVEL: rename_file, rename_folder, move_file, modularize
    # ═══════════════════════════════════════════════════════════════════

    async def rename_file(self, repo_id: str, source_path: str, new_path: str,
                           dry_run: bool = True) -> RefactorResult:
        """Rename a file and update all imports across the codebase."""
        try:
            root = self._get_repo_root(repo_id)
            if not root:
                return RefactorResult(status="error", message="Repo not found", repository_id=repo_id)
            src_abs = self._resolve_abs(root, source_path)
            if not src_abs or not src_abs.exists():
                return RefactorResult(status="error", message=f"Source not found: {source_path}",
                                      repository_id=repo_id, action="rename_file")

            new_abs = root / new_path
            if new_abs.exists():
                return RefactorResult(status="error", message=f"Target already exists: {new_path}",
                                      repository_id=repo_id, action="rename_file")

            importers = self._find_importers_by_path(repo_id, source_path)
            changes = []
            old_rel = self._get_rel_path(str(root), str(src_abs))
            new_rel = str(Path(new_path).as_posix())

            for imp_abs, imp_rel in importers:
                content = Path(imp_abs).read_text(encoding="utf-8", errors="ignore")
                new_content = self._rewrite_import(content, str(imp_abs), old_rel, new_rel, root)
                if new_content != content:
                    diff = generate_unified_diff(content, new_content, imp_rel)
                    changes.append(RefactorChange(path=imp_rel, action="modify",
                                  description=f"Update import to {new_rel}", diff=diff))

            rename_diff = f"--- a/{old_rel}\n+++ b/{new_rel}\n@@ -1 +1 @@\n-{old_rel}\n+{new_rel}"
            changes.append(RefactorChange(path=old_rel, action="rename",
                          description=f"Rename {old_rel} -> {new_rel}", diff=rename_diff))

            if dry_run:
                return RefactorResult(status="preview", message=f"Rename plan: {len(changes)} change(s)",
                                      repository_id=repo_id, action="rename_file", changes=changes)

            new_abs.parent.mkdir(parents=True, exist_ok=True)
            src_abs.rename(new_abs)

            for ch in changes:
                if ch.action == "modify":
                    ap = root / ch.path
                    content = ap.read_text(encoding="utf-8", errors="ignore")
                    new_content = self._rewrite_import(content, str(ap), old_rel, new_rel, root)
                    ap.write_text(new_content, encoding="utf-8")

            all_paths = [new_rel] + [c.path for c in changes if c.action == "modify"]
            commit = await self.git.stage_and_commit(root, [old_rel, new_rel] + [c.path for c in changes if c.action == "modify"],
                     f"refactor: rename {old_rel} -> {new_rel}")

            reindex = self._reindex_affected_files(repo_id, root, list(set(all_paths)))
            return RefactorResult(status="applied", message=f"Renamed to {new_path}",
                                  repository_id=repo_id, action="rename_file", changes=changes,
                                  commit_hash=commit.get("commit_hash"), validation_result=json.dumps(reindex))
        except Exception as e:
            logger.error(f"rename_file failed: {e}")
            return RefactorResult(status="error", message=str(e), repository_id=repo_id, action="rename_file")

    async def rename_folder(self, repo_id: str, source_path: str, new_name: str,
                             dry_run: bool = True) -> RefactorResult:
        """Rename a directory and update all imports across the codebase."""
        try:
            root = self._get_repo_root(repo_id)
            if not root:
                return RefactorResult(status="error", message="Repo not found", repository_id=repo_id)

            src_dir = root / source_path
            if not src_dir.exists():
                return RefactorResult(status="error", message=f"Directory not found: {source_path}",
                                      repository_id=repo_id, action="rename_folder")

            parent = src_dir.parent
            new_dir = parent / new_name
            if new_dir.exists():
                return RefactorResult(status="error", message=f"Target already exists: {new_name}",
                                      repository_id=repo_id, action="rename_folder")

            all_files = [p for p in src_dir.rglob("*") if p.is_file()]
            if len(all_files) > 50 and not dry_run:
                logger.warning(f"Large folder rename: {len(all_files)} files")

            # ── Blast Radius Analysis ──────────────────────────────────────
            all_importers = set()
            total_affected_files = set()
            for f in all_files:
                rel = self._get_rel_path(str(root), str(f))
                importers = self._find_importers_by_path(repo_id, rel)
                for imp in importers:
                    all_importers.add(imp)
                    total_affected_files.add(imp[1])

            affected_list = list(total_affected_files)
            direct = len(affected_list)
            transitive = self._find_transitive_callers(repo_id, affected_list)
            test_files = sum(1 for f in affected_list if "/test/" in f or "/tests/" in f or f.startswith("test_"))
            core = len(affected_list) - test_files

            br = BlastRadius(
                total_files=len(set(affected_list + transitive)),
                direct_dependents=direct,
                transitive_dependents=len(transitive),
                test_files=test_files,
                core_modules=core,
                affected_symbols=self._count_symbols_in_files(repo_id, affected_list),
                confidence_score=70 if len(all_files) > 20 else 85,
            )

            risk = "low"
            if direct > 20 or len(all_files) > 30:
                risk = "high"
            elif direct > 5:
                risk = "medium"

            old_prefix = source_path.rstrip("/") + "/"
            new_prefix = parent.name + "/" + new_name + "/"

            for f in all_files:
                rel = self._get_rel_path(str(root), str(f))
                if rel.startswith(old_prefix):
                    new_rel = rel.replace(old_prefix, new_prefix, 1)
                    importers = self._find_importers_by_path(repo_id, rel)
                    for imp in importers:
                        all_importers.add(imp)

            changes = []
            for imp_abs, imp_rel in sorted(all_importers):
                content = Path(imp_abs).read_text(encoding="utf-8", errors="ignore")
                new_content = content
                for f in all_files:
                    old_rel = self._get_rel_path(str(root), str(f))
                    if old_rel.startswith(old_prefix):
                        new_rel = old_rel.replace(old_prefix, new_prefix, 1)
                        new_content = self._rewrite_import(new_content, str(imp_abs), old_rel, new_rel, root)
                if new_content != content:
                    diff = generate_unified_diff(content, new_content, imp_rel)
                    changes.append(RefactorChange(path=imp_rel, action="modify",
                                  description=f"Update imports for {old_prefix} -> {new_prefix}", diff=diff))

            changes.append(RefactorChange(path=source_path, action="rename",
                          description=f"Rename directory {source_path} -> {new_name}"))

            if dry_run:
                return RefactorResult(
                    status="preview",
                    message=f"Folder rename: {len(changes)} change(s), {len(all_files)} files, risk={risk}, {direct} importers affected",
                    repository_id=repo_id, action="rename_folder", changes=changes,
                    blast_radius=br,
                )

            src_dir.rename(new_dir)
            for imp_abs, _ in sorted(all_importers):
                content = Path(imp_abs).read_text(encoding="utf-8", errors="ignore")
                new_content = content
                for f in all_files:
                    old_rel = self._get_rel_path(str(root), str(f))
                    if old_rel.startswith(old_prefix):
                        new_rel = old_rel.replace(old_prefix, new_prefix, 1)
                        new_content = self._rewrite_import(new_content, str(imp_abs), old_rel, new_rel, root)
                Path(imp_abs).write_text(new_content, encoding="utf-8")

            all_affected = [c.path for c in changes if c.action == "modify"]
            commit = await self.git.stage_and_commit(root, [source_path, str(new_dir)] + all_affected,
                     f"refactor: rename directory {source_path} -> {new_name}")

            reindex = self._reindex_affected_files(repo_id, root, all_affected)
            logger.info(f"Reindexed {reindex['files_reindexed']} files after rename_folder")

            return RefactorResult(
                status="applied",
                message=f"Renamed directory to {new_name}, {len(all_files)} files, {len(all_importers)} importers updated",
                repository_id=repo_id, action="rename_folder", changes=changes,
                blast_radius=br,
                commit_hash=commit.get("commit_hash"),
                validation_result=json.dumps(reindex)
            )
        except Exception as e:
            logger.error(f"rename_folder failed: {e}")
            return RefactorResult(
                status="error", message=str(e), repository_id=repo_id, action="rename_folder",
                error_code=RefactorErrorCode.INTERNAL
            )

    async def move_file(self, repo_id: str, source_path: str, target_dir: str,
                         delete_source: bool = False, dry_run: bool = True) -> RefactorResult:
        """Move a file to another directory, updating all imports."""
        try:
            root = self._get_repo_root(repo_id)
            if not root:
                return RefactorResult(status="error", message="Repo not found", repository_id=repo_id)

            src_abs = self._resolve_abs(root, source_path)
            if not src_abs or not src_abs.exists():
                return RefactorResult(status="error", message=f"Source not found: {source_path}",
                                      repository_id=repo_id, action="move_file")

            filename = src_abs.name
            tgt_dir_abs = self._resolve_abs(root, target_dir) or (root / target_dir)
            new_abs = tgt_dir_abs / filename
            if new_abs.exists():
                return RefactorResult(status="error", message=f"Target exists: {new_abs}",
                                      repository_id=repo_id, action="move_file")

            old_rel = self._get_rel_path(str(root), str(src_abs))
            new_rel = self._get_rel_path(str(root), str(new_abs))

            importers = self._find_importers_by_path(repo_id, old_rel)
            changes = []
            for imp_abs, imp_rel in importers:
                content = Path(imp_abs).read_text(encoding="utf-8", errors="ignore")
                new_content = self._rewrite_import(content, str(imp_abs), old_rel, new_rel, root)
                if new_content != content:
                    diff = generate_unified_diff(content, new_content, imp_rel)
                    changes.append(RefactorChange(path=imp_rel, action="modify",
                                  description=f"Update import from {old_rel}", diff=diff))

            move_diff = f"--- a/{old_rel}\n+++ b/{new_rel}\n@@ -1 +1 @@\n-{old_rel}\n+{new_rel}"
            changes.append(RefactorChange(path=old_rel, action="move",
                          description=f"Move {old_rel} -> {new_rel}", diff=move_diff))

            if dry_run:
                return RefactorResult(status="preview", message=f"Move plan: {len(changes)} change(s)",
                                      repository_id=repo_id, action="move_file", changes=changes)

            tgt_dir_abs.mkdir(parents=True, exist_ok=True)
            if delete_source:
                src_abs.rename(new_abs)
            else:
                import shutil
                shutil.copy2(str(src_abs), str(new_abs))

            for ch in changes:
                if ch.action == "modify":
                    ap = root / ch.path
                    content = ap.read_text(encoding="utf-8", errors="ignore")
                    new_content = self._rewrite_import(content, str(ap), old_rel, new_rel, root)
                    ap.write_text(new_content, encoding="utf-8")

            staged = [old_rel, str(new_rel)] if delete_source else [str(new_rel)]
            staged += [c.path for c in changes if c.action == "modify"]
            commit = await self.git.stage_and_commit(root, list(set(staged)),
                     f"refactor: move {old_rel} -> {new_rel}")

            affected = [new_rel] + [c.path for c in changes if c.action == "modify"]
            reindex = self._reindex_affected_files(repo_id, root, list(set(affected)))

            return RefactorResult(status="applied", message=f"Moved to {target_dir}",
                                  repository_id=repo_id, action="move_file", changes=changes,
                                  commit_hash=commit.get("commit_hash"), validation_result=json.dumps(reindex))
        except Exception as e:
            logger.error(f"move_file failed: {e}")
            return RefactorResult(status="error", message=str(e), repository_id=repo_id, action="move_file")

    async def modularize(self, repo_id: str, source_path: str,
                          target_domain: str = "", strategy: str = "auto",
                          dry_run: bool = True) -> RefactorResult:
        """Split a monolithic file into DDD-aligned modules using AST cluster analysis.

        Analyzes classes/functions via Tree-Sitter, detects natural domain clusters
        based on coupling patterns, then splits into domain-structured files.
        """
        try:
            root = self._get_repo_root(repo_id)
            if not root:
                return RefactorResult(status="error", message="Repo not found", repository_id=repo_id)

            src_abs = self._resolve_abs(root, source_path)
            if not src_abs or not src_abs.exists():
                return RefactorResult(status="error", message=f"Source not found: {source_path}",
                                      repository_id=repo_id, action="modularize")

            content = src_abs.read_text(encoding="utf-8", errors="ignore")
            lang_name = self._detect_lang(str(src_abs))
            if lang_name == "unknown":
                return RefactorResult(status="error", message=f"Unsupported language: {source_path}",
                                      repository_id=repo_id, action="modularize")

            target_base = root / (target_domain or src_abs.parent)
            target_base.mkdir(parents=True, exist_ok=True)

            # Parse with Tree-Sitter and extract symbols
            lang = self.ts.get_language_safe(lang_name)
            parser = self.ts.create_parser(lang_name)
            tree = parser.parse(bytes(content, "utf8"))

            def_q = """
                (function_definition name: (identifier) @name) @sym
                (class_definition name: (identifier) @name) @sym
                (function_declaration name: (identifier) @name) @sym
                (class_declaration name: (identifier) @name) @sym
            """
            caps = execute_query(lang, def_q, tree.root_node)
            symbols = []
            for node, tag in caps:
                if tag != "sym":
                    continue
                sym_name = ""
                for n2, t2 in caps:
                    if t2 == "name" and n2.start_byte >= node.start_byte and n2.end_byte <= node.end_byte:
                        sym_name = content[n2.start_byte:n2.end_byte]
                        break
                if sym_name:
                    code = content[node.start_byte:node.end_byte]
                    symbols.append((sym_name, node, code))

            if not symbols:
                return RefactorResult(status="error", message="No extractable symbols found",
                                      repository_id=repo_id, action="modularize")

            # AI-assisted cluster: analyze coupling via co-occurrence in imports
            var_pattern = re.compile(r'\b[a-z_][a-zA-Z0-9_]*\b')
            clusters = {}
            for sym_name, node, code in symbols:
                used = set()
                for m in var_pattern.finditer(code):
                    ref = m.group()
                    for sn2, _, _ in symbols:
                        if ref == sn2 and ref != sym_name:
                            used.add(sn2)
                domain = self._infer_domain(sym_name, code)
                clusters.setdefault(domain, []).append((sym_name, code, list(used)))

            # Build naming convention per language
            dir_case, file_case = self._naming_convention(lang_name)

            changes = []
            new_files = {}
            for domain, items in sorted(clusters.items()):
                domain_dir = target_base / domain
                domain_dir.mkdir(parents=True, exist_ok=True)
                new_content = self._generate_file_header(lang_name, domain)
                for sym_name, code, used in items:
                    new_content += "\n\n" + code
                fname = self._to_case(sym_name.replace("_", " ").replace("-", " "), file_case) + ".py"
                fpath = domain_dir / fname
                new_files[str(fpath)] = new_content
                rel = self._get_rel_path(str(root), str(fpath))
                diff = generate_unified_diff("", new_content, rel)
                changes.append(RefactorChange(path=rel, action="add",
                              description=f"Create {domain}/{fname}", diff=diff))

            # Generate __init__.py for exports
            init_content = self._generate_init(lang_name, new_files)
            if init_content:
                init_path = target_base / "__init__.py"
                if lang_name in ("javascript", "typescript"):
                    init_path = target_base / "index.ts"
                new_files[str(init_path)] = init_content
                rel = self._get_rel_path(str(root), str(init_path))
                changes.append(RefactorChange(path=rel, action="add",
                              description=f"Create {init_path.name}", diff=""))

            old_rel = self._get_rel_path(str(root), str(src_abs))
            changes.append(RefactorChange(path=old_rel, action="mark_deprecated",
                          description=f"Source {old_rel} split into {len(clusters)} domains"))

            if dry_run:
                return RefactorResult(status="preview", message=f"Modularize: {len(clusters)} domain(s), {len(new_files)} file(s)",
                                      repository_id=repo_id, action="modularize", changes=changes)

            # Execute: write new files
            for fpath, fcontent in new_files.items():
                Path(fpath).parent.mkdir(parents=True, exist_ok=True)
                Path(fpath).write_text(fcontent, encoding="utf-8")

            staged = list(new_files.keys())
            commit = await self.git.stage_and_commit(root, staged,
                     f"refactor: modularize {old_rel} into {len(clusters)} domains")

            affected = [self._get_rel_path(str(root), str(Path(p))) for p in new_files]
            reindex = self._reindex_affected_files(repo_id, root, affected)

            return RefactorResult(status="applied", message=f"Modularized into {len(clusters)} domains ({len(new_files)} files)",
                                  repository_id=repo_id, action="modularize", changes=changes,
                                  commit_hash=commit.get("commit_hash"), validation_result=json.dumps(reindex))
        except Exception as e:
            logger.error(f"modularize failed: {e}")
            return RefactorResult(status="error", message=str(e), repository_id=repo_id, action="modularize")

    # ═══════════════════════════════════════════════════════════════════
    # INTERNAL: VCS-level helpers — import detection & rewriting
    # ═══════════════════════════════════════════════════════════════════

    def _find_importers_by_path(self, repo_id: str, file_rel_path: str) -> List[tuple]:
        """Find all files that import from a given file path.
        Searches file contents for import patterns matching the module path.
        """
        module_path = file_rel_path.replace(".py", "").replace(".go", "").replace(".js", "").replace(".ts", "").replace(".tsx", "").replace(".php", "").replace("/", ".")

        rows = self.db.conn.execute("""
            SELECT f.name, d.relative_path, r.root_path, f.content
            FROM files f
            JOIN directories d ON f.directory_id = d.id
            JOIN repositories r ON f.repository_id = r.id
            WHERE f.repository_id = ? AND f.content IS NOT NULL AND f.content != ''
        """, (repo_id,)).fetchall()

        importers = []
        for row in rows:
            rel = f"{row['relative_path']}/{row['name']}" if row['relative_path'] else row['name']
            if rel == file_rel_path:
                continue
            content = row["content"] or ""
            # Check various import patterns
            patterns = [
                f"from {module_path}",
                f"import {module_path}",
                f"require('{file_rel_path}",
                f"require(\"{file_rel_path}",
                f"from './{file_rel_path.replace('.py','').replace('.ts','').replace('.js','')}",
                f"from '../",
                f"use {module_path.replace('.', '\\\\')}",
                f"use {module_path.replace('.', '/')}",
            ]
            if any(p in content for p in patterns):
                abs_path = os.path.join(row["root_path"], row["relative_path"], row["name"])
                importers.append((abs_path, rel))
        return importers

    def _rewrite_import(self, content: str, file_path: str,
                         old_rel: str, new_rel: str, root: Path) -> str:
        """Rewrite import statements in file content from old_rel to new_rel."""
        lang = self._detect_lang(file_path)
        old_mod = old_rel.replace(".py", "").replace(".go", "").replace(".js", "").replace(".ts", "").replace(".tsx", "").replace(".php", "").replace("/", ".").replace("\\", ".")
        new_mod = new_rel.replace(".py", "").replace(".go", "").replace(".js", "").replace(".ts", "").replace(".tsx", "").replace(".php", "").replace("/", ".").replace("\\", ".")

        if lang == "python":
            content = content.replace(f"from {old_mod}", f"from {new_mod}")
            content = content.replace(f"import {old_mod}", f"import {new_mod}")
        elif lang in ("typescript", "javascript", "tsx"):
            # Try relative path replacement
            old_rel_no_ext = old_rel.replace(".ts", "").replace(".js", "").replace(".tsx", "").replace(".jsx", "")
            new_rel_no_ext = new_rel.replace(".ts", "").replace(".js", "").replace(".tsx", "").replace(".jsx", "")
            content = content.replace(f"'{old_rel_no_ext}'", f"'{new_rel_no_ext}'")
            content = content.replace(f'"{old_rel_no_ext}"', f'"{new_rel_no_ext}"')
        elif lang == "php":
            old_ns = old_mod.replace(".", "\\")
            new_ns = new_mod.replace(".", "\\")
            content = content.replace(f"use {old_ns}", f"use {new_ns}")
        elif lang == "go":
            content = content.replace(f'"{old_mod}"', f'"{new_mod}"')

        return content

    def _infer_domain(self, name: str, code: str) -> str:
        """Infer domain from symbol name and code content using keywords."""
        domain_keywords = {
            "auth": ["auth", "login", "register", "session", "token", "user", "permission"],
            "payment": ["payment", "invoice", "billing", "transaction", "receipt", "refund"],
            "notification": ["email", "sms", "push", "notif", "alert", "webhook"],
            "database": ["repository", "query", "migration", "model", "entity", "schema"],
            "api": ["controller", "route", "endpoint", "handler", "middleware", "response"],
            "infrastructure": ["logger", "config", "cache", "queue", "event", "metric"],
        }
        score = {}
        name_lower = name.lower()
        code_lower = code.lower()
        for domain, keywords in domain_keywords.items():
            s = sum(1 for kw in keywords if kw in name_lower or kw in code_lower)
            if s > 0:
                score[domain] = s
        if score:
            return max(score, key=score.get)
        return "core"

    def _naming_convention(self, lang: str) -> tuple:
        """Return (directory_case, file_case) for a language."""
        case_map = {
            "python": ("snake_case", "snake_case"),
            "javascript": ("kebab-case", "PascalCase"),
            "typescript": ("kebab-case", "PascalCase"),
            "tsx": ("kebab-case", "PascalCase"),
            "go": ("snake_case", "snake_case"),
            "php": ("PascalCase", "PascalCase"),
            "java": ("lowercase", "PascalCase"),
            "kotlin": ("lowercase", "PascalCase"),
            "c_sharp": ("PascalCase", "PascalCase"),
            "ruby": ("snake_case", "snake_case"),
            "rust": ("snake_case", "snake_case"),
            "swift": ("PascalCase", "PascalCase"),
            "dart": ("snake_case", "snake_case"),
            "cpp": ("snake_case", "snake_case"),
        }
        return case_map.get(lang, ("snake_case", "snake_case"))

    def _to_case(self, name: str, case: str) -> str:
        """Convert a name to the specified case convention."""
        words = re.sub(r'[^a-zA-Z0-9\s-]', ' ', name).split()
        if case == "snake_case":
            return "_".join(w.lower() for w in words)
        if case == "PascalCase":
            return "".join(w.capitalize() for w in words)
        if case == "kebab-case":
            return "-".join(w.lower() for w in words)
        if case == "lowercase":
            return "".join(w.lower() for w in words)
        return "_".join(w.lower() for w in words)

    def _generate_file_header(self, lang: str, domain: str) -> str:
        """Generate a file header given language and domain name."""
        if lang == "python":
            return f'\"\"\"{domain.capitalize()} module.\"\"\"\n'
        if lang in ("typescript", "javascript"):
            return f"// {domain.capitalize()} module\n"
        if lang == "go":
            return f"package {domain}\n\n"
        if lang == "php":
            return f"<?php\n\nnamespace {domain.capitalize()};\n\n"
        return f"# {domain.capitalize()} module\n"

    def _generate_init(self, lang: str, new_files: dict) -> str:
        """Generate __init__.py or index.ts to export all public symbols."""
        if not new_files:
            return ""
        if lang in ("javascript", "typescript"):
            lines = ["// Auto-generated by code_refactor modularize"]
            for fpath in sorted(new_files.keys()):
                fname = Path(fpath).stem
                lines.append(f"export * from './{fname}';")
            return "\n".join(lines) + "\n"
        # Python __init__.py
        lines = ['"""Auto-generated by code_refactor modularize."""']
        exports = []
        for fpath in sorted(new_files.keys()):
            fname = Path(fpath).stem
            if fname != "__init__":
                exports.append(fname)
        if exports:
            names = ", ".join(exports)
            lines.append(f"__all__ = [{names}]")
            for ex in exports:
                lines.append(f"from .{ex} import *")
        return "\n".join(lines) + "\n"

    # ═══════════════════════════════════════════════════════════════════
    # INTERNAL: Refactoring recipes
    # ═══════════════════════════════════════════════════════════════════

    def _recipe_standardize_docstrings(self, content: str) -> str:
        """Ensure all functions/classes have triple-quote docstrings."""
        lang = self.ts.get_language_safe("python")
        parser = self.ts.create_parser("python")
        tree = parser.parse(bytes(content, "utf8"))
        q = """
            (function_definition name: (identifier) @name) @func
            (class_definition name: (identifier) @name) @cls
        """
        captures = execute_query(lang, q, tree.root_node)
        edits = []
        for node, tag in captures:
            if tag not in ("func", "cls"):
                continue
            body = node.child_by_field_name("body")
            if not body:
                continue
            first_stmt = body.child(0) if body.child_count > 0 else None
            if first_stmt and first_stmt.type == "expression_statement":
                child = first_stmt.child(0)
                if child and child.type == "string":
                    continue
            # Find the name for the docstring
            name_node = None
            for n, t in captures:
                if t == "name" and node.start_byte <= n.start_byte <= node.end_byte:
                    name_node = n
                    break
            name_str = content[name_node.start_byte:name_node.end_byte] if name_node else "unknown"
            indent = " " * (body.start_point[1] + 4) if body else "    "
            doc = f'{indent}"""{name_str} — describe the purpose of this function."""\n'
            edits.append((body.start_byte, body.start_byte, doc))
        return self._apply_edits(content, edits)

    def _recipe_add_type_hints(self, content: str) -> str:
        """Add basic type hints (Any) to unhinted Python function parameters."""
        lang = self.ts.get_language_safe("python")
        parser = self.ts.create_parser("python")
        tree = parser.parse(bytes(content, "utf8"))
        q = "(function_definition parameters: (parameters (identifier) @param))"
        captures = execute_query(lang, q, tree.root_node)
        edits = []
        for node, _ in captures:
            # Add ': Any' after parameter name
            edits.append((node.end_byte, node.end_byte, ": Any"))
        return self._apply_edits(content, edits)

    def _recipe_remove_unused_imports(self, content: str, file_path: str) -> str:
        """Remove imports that reference symbols not used in the file body."""
        if file_path.endswith(".py"):
            import_re = re.compile(r"^(from\s+\S+\s+)?import\s+(.+)$", re.MULTILINE)
            imports = import_re.findall(content)
            lines = content.splitlines(keepends=True)
            new_lines = []
            for ln in lines:
                m = import_re.match(ln)
                if m:
                    names_part = m.group(2)
                    imported_names = [n.strip().split(" as ")[0].strip()
                                     for n in names_part.split(",")]
                    keep = False
                    for nm in imported_names:
                        if nm in content and nm != "":
                            keep = True
                    if keep:
                        new_lines.append(ln)
                else:
                    new_lines.append(ln)
            return "".join(new_lines)
        return content

    def _reindex_affected_files(self, repo_id: str, root_path: Path,
                                 affected_files: List[str]) -> dict:
        """Re-index affected files after refactoring — update symbols + edges in DB."""
        import uuid as _uuid
        stats = {"files_reindexed": 0, "symbols_added": 0, "edges_added": 0}
        reindexed = set()

        for af in affected_files:
            ap = self._resolve_abs(root_path, af)
            if not ap or not ap.exists():
                continue
            if str(ap) in reindexed:
                continue
            reindexed.add(str(ap))

            rel = self._get_rel_path(str(root_path), str(ap))
            content = ap.read_text(encoding="utf-8", errors="ignore")
            lang_name = self._detect_lang(str(ap))
            if lang_name == "unknown":
                continue

            row = self.db.conn.execute("""
                SELECT f.id FROM files f
                JOIN directories d ON d.id = f.directory_id
                WHERE (CASE WHEN d.relative_path = ''
                      THEN f.name ELSE d.relative_path || '/' || f.name END) = ?
                AND f.repository_id = ?
            """, (rel, repo_id)).fetchone()
            if not row:
                continue
            fid = row["id"]

            # Delete old symbols + edges
            self.db.conn.execute("""
                DELETE FROM edges WHERE source_id IN
                (SELECT id FROM symbols WHERE file_id = ?)
                OR target_id IN (SELECT id FROM symbols WHERE file_id = ?)
            """, (fid, fid))
            self.db.conn.execute("DELETE FROM symbols WHERE file_id = ?", (fid,))

            try:
                lang = self.ts.get_language_safe(lang_name)
                parser = self.ts.create_parser(lang_name)
                tree = parser.parse(bytes(content, "utf8"))
            except Exception:
                continue

            def_q = """
                (function_definition name: (identifier) @name) @sym
                (class_definition name: (identifier) @name) @sym
                (method_declaration name: (identifier) @name) @sym
                (function_declaration name: (identifier) @name) @sym
            """
            try:
                caps = execute_query(lang, def_q, tree.root_node)
            except Exception:
                caps = []

            name_to_id = {}
            for node, tag in caps:
                if tag != "sym":
                    continue
                sym_name = ""
                for n2, t2 in caps:
                    if t2 == "name" and n2.start_byte >= node.start_byte and n2.end_byte <= node.end_byte:
                        sym_name = content[n2.start_byte:n2.end_byte]
                        break
                if not sym_name:
                    continue
                sym_id = str(_uuid.uuid4())
                sym_type = "function" if node.type in ("function_definition", "function_declaration", "method_declaration") else "class"
                try:
                    self.db.conn.execute(
                        "INSERT INTO symbols (id, repository_id, file_id, code, name, symbol_type, start_line, end_line) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (sym_id, repo_id, fid, content[node.start_byte:node.end_byte][:500],
                         sym_name, sym_type, node.start_point[0] + 1, node.end_point[0] + 1),
                    )
                    name_to_id[sym_name] = sym_id
                    stats["symbols_added"] += 1
                except Exception:
                    pass

            # Call edges
            try:
                call_q = "((call function: (identifier) @name) @call)"
                call_caps = execute_query(lang, call_q, tree.root_node)
            except Exception:
                call_caps = []

            for node, tag in call_caps:
                if tag != "call":
                    continue
                fn_node = node.child_by_field_name("function")
                if not fn_node:
                    continue
                fn_name = content[fn_node.start_byte:fn_node.end_byte]
                target = self.db.conn.execute(
                    "SELECT id FROM symbols WHERE name = ? AND repository_id = ? LIMIT 1",
                    (fn_name, repo_id),
                ).fetchone()
                if target:
                    source_id = None
                    for sname, sid in name_to_id.items():
                        srow = self.db.conn.execute(
                            "SELECT start_line, end_line FROM symbols WHERE id = ?", (sid,)
                        ).fetchone()
                        if srow:
                            cl = node.start_point[0] + 1
                            if srow["start_line"] <= cl <= srow["end_line"]:
                                source_id = sid
                                break
                    if source_id:
                        try:
                            self.db.conn.execute(
                                "INSERT OR IGNORE INTO edges (id, repository_id, source_id, target_id, relation_type, line_number) VALUES (?, ?, ?, ?, 'CALLS', ?)",
                                (str(_uuid.uuid4()), repo_id, source_id, target["id"], node.start_point[0] + 1),
                            )
                            stats["edges_added"] += 1
                        except Exception:
                            pass

            stats["files_reindexed"] += 1

        self.db.conn.commit()
        return stats

    # ═══════════════════════════════════════════════════════════════════
    # INTERNAL: Graph queries
    # ═══════════════════════════════════════════════════════════════════

    def _find_callers_by_name(self, repo_id: str, name: str,
                               source_rel: str) -> List[Tuple[str, str]]:
        """Find files that reference a symbol via the Knowledge Graph."""
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
            AND (CASE WHEN target_d.relative_path = ''
                 THEN target_f.name
                 ELSE target_d.relative_path || '/' || target_f.name END) = ?
            AND f.repository_id = ?
            AND e.relation_type IN ('CALLS', 'IMPORTS', 'USES', 'DEFINES')
        """, (name, source_rel, repo_id))
        results = []
        for row in cursor.fetchall():
            rel = f"{row['relative_path']}/{row['name']}" if row['relative_path'] else row['name']
            results.append((os.path.join(row["root_path"], row["relative_path"], row["name"]), rel))
        return results

    def _find_transitive_callers(self, repo_id: str,
                                  affected_files: List[str]) -> List[str]:
        """BFS for transitive callers via the graph."""
        transitive = []
        for af in affected_files:
            cursor = self.db.conn.execute("""
                SELECT DISTINCT r.root_path || '/' || d.relative_path || '/' || f.name
                FROM edges e
                JOIN symbols caller ON caller.id = e.source_id
                JOIN files f ON f.id = caller.file_id
                JOIN directories d ON d.id = f.directory_id
                JOIN repositories r ON r.id = f.repository_id
                WHERE e.target_id IN (
                    SELECT s.id FROM symbols s
                    JOIN files ff ON ff.id = s.file_id
                    JOIN directories dd ON dd.id = ff.directory_id
                    WHERE (CASE WHEN dd.relative_path = ''
                          THEN ff.name
                          ELSE dd.relative_path || '/' || ff.name END) = ?
                )
                AND f.repository_id = ?
            """, (af, repo_id))
            for row in cursor.fetchall():
                if row[0] not in affected_files and row[0] not in transitive:
                    transitive.append(row[0])
        return transitive

    def _count_symbols_in_files(self, repo_id: str, files: List[str]) -> int:
        """Count total symbols in a list of affected files."""
        total = 0
        for f in files[:20]:
            row = self.db.conn.execute("""
                SELECT COUNT(*) as c FROM symbols s
                JOIN files ff ON ff.id = s.file_id
                JOIN directories d ON d.id = ff.directory_id
                WHERE (CASE WHEN d.relative_path = ''
                      THEN ff.name
                      ELSE d.relative_path || '/' || ff.name END) = ?
                AND s.repository_id = ?
            """, (f, repo_id)).fetchone()
            total += row["c"] if row else 0
        return total

    # ═══════════════════════════════════════════════════════════════════
    # INTERNAL: Tree-Sitter element extraction (16 languages)
    # ═══════════════════════════════════════════════════════════════════

    def _extract_element(self, content: str, name: str, path: str) -> Tuple[Optional[str], int, int]:
        """Extract code block + line range for a class or function via Tree-Sitter."""
        lang_name = self._detect_lang(path)
        if lang_name == "unknown":
            return None, 0, 0
        lang = self.ts.get_language_safe(lang_name)
        parser = self.ts.create_parser(lang_name)
        tree = parser.parse(bytes(content, "utf8"))

        queries = {
            "python": (".py", f"""
                (class_definition name: (identifier) @name (#eq? @name "{name}")) @el
                (function_definition name: (identifier) @name (#eq? @name "{name}")) @el
            """),
            "javascript": (".js", f"""
                (class_declaration name: (identifier) @name (#eq? @name "{name}")) @el
                (function_declaration name: (identifier) @name (#eq? @name "{name}")) @el
                (variable_declarator name: (identifier) @name (#eq? @name "{name}") value: (arrow_function)) @el
            """),
            "typescript": (".ts", f"""
                (class_declaration name: (identifier) @name (#eq? @name "{name}")) @el
                (function_declaration name: (identifier) @name (#eq? @name "{name}")) @el
            """),
            "tsx": (".tsx", f"""
                (class_declaration name: (identifier) @name (#eq? @name "{name}")) @el
                (function_declaration name: (identifier) @name (#eq? @name "{name}")) @el
            """),
            "go": (".go", f"""
                (type_declaration (type_spec name: (type_identifier) @name (#eq? @name "{name}"))) @el
                (function_declaration name: (identifier) @name (#eq? @name "{name}")) @el
                (method_declaration name: (field_identifier) @name (#eq? @name "{name}")) @el
            """),
            "java": (".java", f"""
                (class_declaration name: (identifier) @name (#eq? @name "{name}")) @el
                (method_declaration name: (identifier) @name (#eq? @name "{name}")) @el
            """),
            "kotlin": (".kt", f"""
                (class_declaration name: (simple_identifier) @name (#eq? @name "{name}")) @el
                (function_declaration name: (simple_identifier) @name (#eq? @name "{name}")) @el
            """),
            "cpp": (".cpp", f"""
                (class_specifier name: (type_identifier) @name (#eq? @name "{name}")) @el
                (function_definition name: (function_declarator (identifier) @name (#eq? @name "{name}"))) @el
            """),
            "c_sharp": (".cs", f"""
                (class_declaration name: (identifier) @name (#eq? @name "{name}")) @el
                (method_declaration name: (identifier) @name (#eq? @name "{name}")) @el
            """),
            "rust": (".rs", f"""
                (struct_item name: (type_identifier) @name (#eq? @name "{name}")) @el
                (function_item name: (identifier) @name (#eq? @name "{name}")) @el
            """),
            "php": (".php", f"""
                (class_declaration name: (name) @name (#eq? @name "{name}")) @el
                (method_declaration name: (name) @name (#eq? @name "{name}")) @el
                (function_definition name: (name) @name (#eq? @name "{name}")) @el
            """),
            "ruby": (".rb", f"""
                (class name: (constant) @name (#eq? @name "{name}")) @el
                (method name: (identifier) @name (#eq? @name "{name}")) @el
            """),
            "swift": (".swift", f"""
                (class_declaration name: (identifier) @name (#eq? @name "{name}")) @el
                (function_declaration name: (identifier) @name (#eq? @name "{name}")) @el
            """),
            "dart": (".dart", f"""
                (class_declaration name: (identifier) @name (#eq? @name "{name}")) @el
                (function_declaration name: (identifier) @name (#eq? @name "{name}")) @el
                (method_declaration name: (identifier) @name (#eq? @name "{name}")) @el
            """),
        }
        entry = queries.get(lang_name)
        q = entry[1] if entry else \
            f"(class_declaration name: (identifier) @name (#eq? @name \"{name}\")) @el " \
            f"(function_definition name: (identifier) @name (#eq? @name \"{name}\")) @el"

        captures = execute_query(lang, q, tree.root_node)
        for node, tag in captures:
            if tag == "el":
                sl = node.start_point[0] + 1
                el = node.end_point[0] + 1
                return content[node.start_byte:node.end_byte], sl, el
        return None, 0, 0

    # ═══════════════════════════════════════════════════════════════════
    # INTERNAL: Path & repo resolution
    # ═══════════════════════════════════════════════════════════════════

    def _resolve_repo(self, path: str) -> Tuple[Optional[str], Optional[str]]:
        """Walk up from path to find repository root."""
        abs_path = Path(path).resolve()
        curr = abs_path
        while curr.parent != curr:
            row = self.db.conn.execute(
                "SELECT id, root_path FROM repositories WHERE root_path = ?", (str(curr),)
            ).fetchone()
            if row:
                return row["root_path"], row["id"]
            curr = curr.parent
        return None, None

    def _get_repo_root(self, repo_id: str) -> Optional[Path]:
        """Get repository root path from ID."""
        row = self.db.conn.execute(
            "SELECT root_path FROM repositories WHERE id = ?", (repo_id,)
        ).fetchone()
        return Path(row["root_path"]) if row else None

    def _resolve_abs(self, root_path: Path, file_path: str) -> Optional[Path]:
        """Resolve a relative or absolute file path."""
        p = Path(file_path)
        if p.is_absolute():
            return p if p.exists() else None
        return (root_path / file_path).resolve()

    def _get_rel_path(self, root: str, path: str) -> str:
        try:
            rel = Path(path).resolve().relative_to(Path(root).resolve())
            return str(rel).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")

    @staticmethod
    def _parse_target(target_symbol: str) -> tuple:
        """Parse target_symbol into (source_file, symbol_name)."""
        if "::" in target_symbol:
            parts = target_symbol.split("::", 1)
            return parts[0], parts[1]
        return target_symbol, ""

    # ═══════════════════════════════════════════════════════════════════
    # INTERNAL: Multi-language import updates after move
    # ═══════════════════════════════════════════════════════════════════

    async def _update_import_generic(self, caller_path: str, name: str,
                                      old_rel: str, new_rel: str) -> bool:
        """Generic import updater supporting Python, JS/TS, Go, PHP, Rust.
        Returns True if changes were made.
        """
        ap = Path(caller_path)
        if not ap.exists():
            return False

        content = ap.read_text(encoding="utf-8", errors="ignore")
        new_content = content
        lang = self._detect_lang(str(ap))

        # Build module paths without extensions
        old_mod = old_rel.replace(".py", "").replace(".go", "").replace(".php", "").replace(".rs", "")
        new_mod = new_rel.replace(".py", "").replace(".go", "").replace(".php", "").replace(".rs", "")
        old_mod = old_mod.replace("/", ".").replace("\\", ".")
        new_mod = new_mod.replace("/", ".").replace("\\", ".")

        if lang == "python":
            new_content = re.sub(
                rf"from\s+{re.escape(old_mod)}\s+import",
                f"from {new_mod} import",
                content
            )
            new_content = re.sub(
                rf"import\s+{re.escape(old_mod)}(\s|$)",
                f"import {new_mod}\\1",
                new_content
            )
        elif lang in ("typescript", "javascript", "tsx"):
            # Handle both relative and aliased imports
            old_path_no_ext = old_rel.replace(".ts", "").replace(".js", "").replace(".tsx", "").replace(".jsx", "")
            new_path_no_ext = new_rel.replace(".ts", "").replace(".js", "").replace(".tsx", "").replace(".jsx", "")
            patterns = [
                rf"from\s+['\"]{re.escape(old_path_no_ext)}['\"]",
                rf"from\s+['\"]{re.escape(old_path_no_ext)}\/",
                rf"require\(['\"]{re.escape(old_path_no_ext)}['\"]\)",
                rf"import\s+['\"]{re.escape(old_path_no_ext)}['\"]",
            ]
            for pattern in patterns:
                new_content = re.sub(pattern, lambda m: m.group(0).replace(old_path_no_ext, new_path_no_ext), new_content)
        elif lang == "go":
            new_content = re.sub(
                rf'"{re.escape(old_mod)}"',
                f'"{new_mod}"',
                content
            )
        elif lang == "php":
            # Handle use statements and includes
            new_content = re.sub(
                rf"use\s+{re.escape(old_mod.replace('.', '\\'))}\\",
                f"use {new_mod.replace('.', '\\\\')}\\\\",
                content
            )
            new_content = re.sub(
                rf"(include|require)(_once)?\s*[(\s]['\"]" + re.escape(old_rel) + r"['\"]",
                lambda m: m.group(0).replace(old_rel, new_rel),
                new_content
            )
        elif lang == "rust":
            new_content = re.sub(
                rf"use\s+{re.escape(old_mod.replace('.', '::'))}::",
                f"use {new_mod.replace('.', '::')}::",
                content
            )
            new_content = re.sub(
                rf"mod\s+{re.escape(old_mod.split('.')[-1])}(\s*;|$)",
                f"mod {new_mod.split('.')[-1]}\\1",
                new_content
            )

        if new_content != content:
            ap.write_text(new_content, encoding="utf-8")
            return True
        return False

    def _detect_smart_placement(self, content: str, element_name: str, lang: str) -> int:
        """Detect optimal insertion position for moved element.
        Returns line number (0-indexed) for insertion.
        """
        lines = content.splitlines(keepends=True)

        # Strategy 1: After last import statement
        last_import = 0
        import_patterns = {
            "python": r"^(from\s+|import\s+)",
            "typescript": r"^(import\s+|from\s+['\"])",
            "javascript": r"^(import\s+|const\s+.*=\s*require\()",
            "go": r"^(import\s+|package\s+)",
            "php": r"^(use\s+|require|include)",
            "rust": r"^(use\s+|mod\s+|extern\s+crate)",
        }
        pattern = import_patterns.get(lang, r"^(import|from|use|require)")

        for i, line in enumerate(lines):
            if re.match(pattern, line.strip()):
                last_import = i + 1

        # Strategy 2: Before first class/function if no imports
        if last_import == 0:
            for i, line in enumerate(lines):
                if re.match(r"^(class\s+|def\s+|function\s+|const\s+.*=|func\s+|fn\s+)", line.strip()):
                    return max(0, i)

        return last_import

    async def _update_import_python(self, caller_path: str, repo_id: str,
                                     name: str, old_rel: str, new_rel: str):
        """Legacy Python-specific updater (maintained for compatibility)."""
        old_mod = old_rel.replace(".py", "").replace("/", ".")
        new_mod = new_rel.replace(".py", "").replace("/", ".")
        if old_mod == new_mod:
            return
        root = self._get_repo_root(repo_id)
        if not root:
            return
        ap = Path(caller_path)
        if not ap.exists():
            return
        content = ap.read_text(encoding="utf-8", errors="ignore")
        new_content = content
        pattern = rf"(from\s+{re.escape(old_mod)}\s+import\s+)([\w\s,()]+)"
        match = re.search(pattern, new_content)
        if match:
            prefix = match.group(1)
            imports_str = match.group(2)
            imports = [i.strip() for i in imports_str.replace("(", "").replace(")", "").split(",")]
            if name in imports:
                imports.remove(name)
                if not imports:
                    new_content = new_content.replace(match.group(0), "")
                else:
                    new_content = new_content.replace(match.group(0),
                        f"{prefix}{', '.join(imports)}")
                stmt = f"from {new_mod} import {name}\n"
                lines = new_content.splitlines(keepends=True)
                idx = 0
                for i, ln in enumerate(lines):
                    if ln.startswith(("import ", "from ")):
                        idx = i + 1
                lines.insert(idx, stmt)
                new_content = "".join(lines)
        if new_content != content:
            ap.write_text(new_content, encoding="utf-8")

    async def _update_import_js(self, caller_path: str, repo_id: str,
                                 name: str, old_rel: str, new_rel: str):
        old_mod = old_rel.replace(".ts", "").replace(".js", "").replace(".tsx", "")
        new_mod = new_rel.replace(".ts", "").replace(".js", "").replace(".tsx", "")
        if old_mod == new_mod:
            return
        ap = Path(caller_path)
        if not ap.exists():
            return
        content = ap.read_text(encoding="utf-8", errors="ignore")
        pattern = rf"(import\s+{{)([\w\s,]+)(}}\s+from\s+['\"]{re.escape(old_mod)}['\"])"
        match = re.search(pattern, content)
        if match:
            prefix, imports_str, suffix = match.group(1), match.group(2), match.group(3)
            imports = [i.strip() for i in imports_str.split(",")]
            if name in imports:
                imports.remove(name)
                new_content = content
                if not imports:
                    new_content = new_content.replace(match.group(0), "")
                else:
                    new_content = new_content.replace(match.group(0),
                        f"{prefix} {', '.join(imports)} {suffix}")
                new_content = f"import {{ {name} }} from '{new_mod}';\n" + new_content
                ap.write_text(new_content, encoding="utf-8")

    @staticmethod
    def _detect_lang(file_path: str) -> str:
        """Detect programming language from file extension (22 languages)."""
        ext = Path(file_path).suffix.lower()
        mapping = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".tsx": "tsx", ".jsx": "javascript", ".go": "go",
            ".rs": "rust", ".java": "java", ".rb": "ruby",
            ".php": "php", ".cs": "c_sharp", ".swift": "swift",
            ".dart": "dart", ".kt": "kotlin", ".kts": "kotlin",
            ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
            ".h": "c", ".c": "c",
        }
        return mapping.get(ext, "unknown")

    def _rename_in_file(self, content: str, old_name: str, new_name: str, lang: str) -> str:
        """Semantic rename across all supported languages via Tree-Sitter.
        Falls back to word-boundary regex if TS not available for that language.
        """
        skip_map = {
            "python": ("string", "comment"),
            "javascript": ("string", "comment", "template_string"),
            "typescript": ("string", "comment", "template_string"),
            "tsx": ("string", "comment", "template_string"),
            "go": ("string_literal", "comment"),
            "rust": ("string_literal", "comment", "line_comment"),
            "java": ("string_literal", "line_comment", "block_comment"),
            "kotlin": ("string_literal", "line_comment", "block_comment"),
            "c_sharp": ("string_literal", "comment"),
            "cpp": ("string_literal", "comment"),
            "c": ("string_literal", "comment"),
            "php": ("string", "comment"),
            "ruby": ("string", "comment"),
            "swift": ("string_literal", "line_comment", "block_comment"),
            "dart": ("string_literal", "comment"),
        }
        skip = skip_map.get(lang)
        if skip:
            result = self._ts_rename(content, old_name, new_name, lang, skip)
            if result != content:
                return result
        return re.sub(rf'\b{re.escape(old_name)}\b', new_name, content)

    def _ts_rename(self, content: str, old: str, new_: str,
                   lang_name: str, skip_types: tuple) -> str:
        """Generic Tree-Sitter based rename skipping strings/comments."""
        lang = self.ts.get_language_safe(lang_name)
        parser = self.ts.create_parser(lang_name)
        tree = parser.parse(bytes(content, "utf8"))
        query_str = f'((identifier) @name (#eq? @name "{old}"))'
        captures = execute_query(lang, query_str, tree.root_node)
        edits = []
        for node, _ in captures:
            parent = node.parent
            valid = True
            while parent:
                if parent.type in skip_types:
                    valid = False
                    break
                parent = parent.parent
            if valid:
                edits.append((node.start_byte, node.end_byte, new_))
        return self._apply_edits(content, edits)

    def _apply_edits(self, content: str, edits: List[Tuple[int, int, str]]) -> str:
        if not edits:
            return content
        unique = sorted(set(edits), key=lambda x: x[0], reverse=True)
        new_content = content
        for start, end, text in unique:
            bc = new_content.encode("utf8")
            bc = bc[:start] + text.encode("utf8") + bc[end:]
            new_content = bc.decode("utf8")
        return new_content

    async def execute_action(
        self,
        repo_id: str,
        action: str,
        target_symbol: str,
        changes: Dict[str, Any],
        dry_run: bool = True
    ) -> RefactorResult:
        """
        Unified entry point for all refactoring actions.

        @param repo_id: Repository ID
        @param action: "impact" | "rename" | "move"
        @param target_symbol: Target symbol in "module::name" or "file:line" format
        @param changes: Action-specific parameters
        @param dry_run: Preview mode
        @return: RefactorResult with status and changes
        """
        if action == "impact":
            return await self.analyze_impact(repo_id, target_symbol)
        elif action == "rename":
            new_name = changes.get("new_name", target_symbol)
            return await self.rename_symbol(repo_id, target_symbol, new_name, dry_run)
        elif action == "move":
            target_file = changes.get("target_file", changes.get("path", ""))
            return await self.move_symbol(repo_id, target_symbol, target_file, dry_run)
        else:
            return RefactorResult(
                status="error",
                message=f"Unknown action: {action}",
                repository_id=repo_id,
                action=action
            )
