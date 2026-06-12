"""
ActionRouter — Maps top-level MCP tool actions to underlying domain service calls.

4 tools → 39 actions → 38 domain tools via lazy import dispatch.

:project: CodeCortex
:package: Api.Orchestration
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-API-v1.0
"""
from __future__ import annotations
import time
import logging
from typing import Any, Callable, Dict, Optional

from ..core import api_response, new_request_id

logger = logging.getLogger("CodeCortex.API.Router")

# ────────────────────────────────────────────────────────────
# Action → module resolution map
# ────────────────────────────────────────────────────────────
REPO_ACTIONS = {
    "init", "inspect", "analyze", "sync", "audit", "staleness",
    "list", "compact", "cleanup", "dump", "restore", "git", "svn",
}
FS_ACTIONS = {
    "read", "write", "delete", "copy", "move", "mkdir", "list",
    "search", "watch", "usage", "audit", "read_lines", "write_lines",
}
CODEBASE_ACTIONS = {
    "analyze", "search", "audit", "graph", "status", "index", "test", "refactor",
}
SCAFFOLDER_ACTIONS = {
    "list_stacks", "get_stack", "validate_name", "list_licenses",
    "generate_content", "generate_class", "create_project",
}

class ActionRouter:
    """Routes action→domain→tool function with lazy import and uniform response."""

    def __init__(self, orchestrator_factory: Callable[[], Any]):
        self._factory = orchestrator_factory
        self._orch = None

    @property
    def orchestrator(self):
        if self._orch is None:
            self._orch = self._factory()
        return self._orch

    def _ok(self, message: str, data: Any, meta: Optional[Dict] = None,
            request_id: Optional[str] = None, insight: Any = None,
            duration_ms: Optional[int] = None) -> Dict[str, Any]:
        result = api_response(success=True, status_code=200, message=message,
                              data=data, request_id=request_id or new_request_id(),
                              insight=insight, duration_ms=duration_ms)
        if meta:
            result.setdefault("meta", {}).update(meta)
        return result

    def _err(self, message: str, error_code: str, request_id: Optional[str] = None,
             status_code: int = 400) -> Dict[str, Any]:
        return api_response(success=False, status_code=status_code, message=message,
                            data=None, request_id=request_id or new_request_id(),
                            error_code=error_code)

    def _resolve_id(self, repo_id: Optional[str], repo_path: Optional[str]) -> Optional[str]:
        if repo_id:
            return repo_id
        if repo_path:
            import os
            from pathlib import Path
            resolved = str(Path(repo_path).resolve())
            if self._orch:
                return self.orchestrator.get_repo_id(resolved)
        return None

    async def dispatch(self, tool: str, action: str, args: Dict) -> Dict:
        """Unified dispatch method for all tools."""
        tool_lower = tool.lower()
        action_lower = action.lower()

        if tool_lower == "codecortex_repository":
            return await self.dispatch_repository(action, args.get("repo_path"), args.get("repo_id"), args)
        elif tool_lower == "codecortex_filesystem":
            return await self.dispatch_filesystem(action, args.get("path"), args.get("repo_id"), args)
        elif tool_lower == "codecortex_codebase":
            return await self.dispatch_codebase(action, args.get("repo_id"), args.get("repo_path"), args)
        elif tool_lower == "codecortex_scaffolder":
            return await self.dispatch_scaffolder(action, args)
        else:
            return self._err(f"Unknown tool: {tool}", "API_400")

    async def dispatch_repository(self, action: str, repo_path: Optional[str],
                            repo_id: Optional[str], args: Dict) -> Dict:
        action_lower = action.lower()
        if action_lower == "init": return await self._repo_init(repo_path, args)
        elif action_lower == "inspect": return await self._repo_inspect(repo_path, repo_id, args)
        elif action_lower == "analyze": return await self._repo_analyze(repo_path, repo_id, args)
        elif action_lower == "sync": return await self._repo_sync(repo_path, repo_id, args)
        elif action_lower == "audit": return await self._repo_audit(repo_path, repo_id, args)
        elif action_lower == "staleness": return await self._repo_staleness(repo_path, repo_id, args)
        elif action_lower == "list": return await self._repo_list(args)
        elif action_lower == "compact": return await self._repo_compact(repo_path, repo_id, args)
        elif action_lower == "cleanup": return await self._repo_cleanup(repo_path, repo_id, args)
        elif action_lower == "dump": return await self._repo_dump(repo_path, repo_id, args)
        elif action_lower == "restore": return await self._repo_restore(args)
        elif action_lower == "git": return await self._repo_git(repo_path, args)
        elif action_lower == "svn": return await self._repo_svn(args)
        else: return self._err(f"Unknown repository action: {action}", "API_400")

    # ── (Removed duplicate dispatch_filesystem) ──

    async def _repo_init(self, repo_path: str, args: Dict) -> Dict:
        import os
        from pathlib import Path
        from ..core.database import cleanup_project
        from ..modules.codeanalysis.analyzers.audit import CodeAuditor
        from ..modules.coderepository.core.utils import extract_vcs_metadata

        if not repo_path:
            return self._err("repo_path required for init", "API_400")
        resolved = str(Path(repo_path).resolve())
        remote_url = args.get("remote_url")
        force = args.get("force", False)
        run_audit = args.get("run_audit", True)
        audit_categories = args.get("audit_categories")
        max_depth = args.get("max_depth")
        request_id = new_request_id()

        try:
            existing_id = self.orchestrator.get_repo_id(resolved)
            if existing_id:
                if not force:
                    return self._ok("Repository already initialized", {"repo_id": existing_id},
                                    request_id=request_id)
                cleanup_project(self.orchestrator.db.conn, existing_id)

            repo_id = await self.orchestrator.repo_service.initialize(
                resolved, max_depth=max_depth, remote_url=remote_url,
            )
            tree = self.orchestrator.fs_service.get_codebase_tree(path=resolved)

            audit_result = None
            if run_audit:
                auditor = CodeAuditor(db=self.orchestrator.db)
                audit_result = auditor.audit({
                    "target": resolved, "scan_categories": audit_categories,
                    "output_format": "json",
                })

            vcs_meta = extract_vcs_metadata(resolved)
            if vcs_meta:
                self.orchestrator.repo_store.update_vcs_metadata(repo_id, vcs_meta)

            return self._ok("Repository initialized", {
                "repo_id": repo_id, "tree": tree, "audit": audit_result,
            }, request_id=request_id)
        except Exception as e:
            return self._err(f"Init failed: {e}", "API_500", status_code=500)

    async def _repo_inspect(self, repo_path: Optional[str], repo_id: Optional[str],
                            args: Dict) -> Dict:
        import os
        import subprocess
        from pathlib import Path
        from datetime import datetime, timezone

        rp = repo_path
        if not rp:
            return self._err("repo_path required for inspect", "API_400")
        resolved = str(Path(rp).resolve())
        request_id = new_request_id()
        diag = args.get("include_git_diagnostics", True)
        include_index = args.get("include_index_metadata", True)
        include_vcs = args.get("include_vcs_status", True)
        include_files = args.get("include_file_stats", True)
        include_deps = args.get("include_dependency_summary", False)
        period = args.get("diagnostic_period", "1_year")
        timeout = args.get("timeout", 30)
        rid = repo_id or self.orchestrator.get_repo_id(resolved)

        data = {"target": resolved, "repo_id": rid, "exists": os.path.exists(resolved)}

        try:
            if diag and os.path.exists(os.path.join(resolved, ".git")):
                data["git"] = self._run_git_diagnostics(resolved, period, timeout)
        except Exception:
            pass
        try:
            if include_files:
                nfiles = self.orchestrator.db.conn.execute(
                    "SELECT COUNT(*) FROM files WHERE repository_id=? AND deleted_at IS NULL",
                    (rid,)
                ).fetchone()[0] if rid else 0
                nsym = self.orchestrator.db.conn.execute(
                    "SELECT COUNT(*) FROM symbols WHERE repository_id=?",
                    (rid,)
                ).fetchone()[0] if rid else 0
                data["stats"] = {"files": nfiles, "symbols": nsym}
        except Exception:
            pass
        try:
            if include_deps and rid:
                deps = self.orchestrator.db.conn.execute(
                    "SELECT COUNT(*) FROM edges WHERE repository_id=?",
                    (rid,)
                ).fetchone()[0] if rid else 0
                data["dependencies"] = deps
        except Exception:
            pass

        return self._ok("Inspection complete", data, request_id=request_id)

    async def _repo_analyze(self, repo_path: Optional[str], repo_id: Optional[str],
                            args: Dict) -> Dict:
        if not repo_path:
            return self._err("repo_path required for analyze", "API_400")
        from pathlib import Path
        resolved = str(Path(repo_path).resolve())
        request_id = new_request_id()
        force = args.get("force", False)
        incremental = args.get("incremental", True)
        build_graph = args.get("build_graph", True)
        extract_symbols = args.get("extract_symbols", True)
        store_embeddings = args.get("store_embeddings", False)
        embedding_model = args.get("embedding_model", "codebert")
        timeout = args.get("timeout", 300)
        dry_run = args.get("dry_run", False)

        try:
            result = await self.orchestrator.analyze(
                resolved, request_id=request_id, dry_run=dry_run,
                max_depth=None, include_codemap=True,
            )
            if store_embeddings and result.get("repository_id"):
                rid = result["repository_id"]
                await self.orchestrator.index_service.generate_embeddings(
                    rid, model=embedding_model, request_id=request_id,
                )
            return self._ok("Analysis complete", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Analysis failed: {e}", "API_500", status_code=500)

    async def _repo_sync(self, repo_path: Optional[str], repo_id: Optional[str],
                         args: Dict) -> Dict:
        import os
        from pathlib import Path
        if not repo_path:
            return self._err("repo_path required for sync", "API_400")
        resolved = str(Path(repo_path).resolve())
        request_id = new_request_id()
        mode = args.get("mode", "auto")
        scope = args.get("scope", {})
        reindex = args.get("reindex_updated", True)
        remove_deleted = args.get("remove_deleted", True)
        dry_run = args.get("dry_run", False)

        try:
            repo = self.orchestrator.repo_store.get_repository_by_path(resolved)
            if not repo:
                return self._err(f"Repository not found at {resolved}", "API_404", status_code=404)
            rid = repo.get("id") or repo_id
            if dry_run:
                changed = self.orchestrator.db.conn.execute(
                    "SELECT COUNT(*) FROM files WHERE repository_id=? AND updated_at > COALESCE(indexed_at, '1970-01-01')",
                    (rid,)
                ).fetchone()[0] if rid else 0
                return self._ok("Dry run — would sync", {"changed_files": changed, "repo_id": rid},
                                request_id=request_id)
            if mode in ("full", "auto"):
                rid = await self.orchestrator.repo_service.sync_repository(
                    resolved, request_id=request_id,
                )
                await self.orchestrator.index_service.index_repository(
                    rid, request_id=request_id,
                )
            elif mode == "incremental":
                inc_result = await self.orchestrator.repo_service.sync_repository_incremental(rid)
                rid = inc_result[0] if isinstance(inc_result, tuple) else inc_result
            return self._ok("Sync complete", {"repo_id": rid, "mode": mode},
                            request_id=request_id)
        except Exception as e:
            return self._err(f"Sync failed: {e}", "API_500", status_code=500)

    async def _repo_audit(self, repo_path: Optional[str], repo_id: Optional[str],
                          args: Dict) -> Dict:
        import os, re, json
        from pathlib import Path
        if not repo_path:
            return self._err("repo_path required for audit", "API_400")
        resolved = str(Path(repo_path).resolve())
        request_id = new_request_id()
        secrets = args.get("secrets", True)
        scan_cats = args.get("scan_categories")

        try:
            findings = []
            if secrets and os.path.exists(resolved):
                from ..modules.coderepository.core.utils import scan_secrets
                findings = scan_secrets(resolved,
                    exclude_paths=args.get("scope", {}).get("exclude"),
                )
            return self._ok("Audit complete", {
                "target": resolved, "findings": findings,
                "count": len(findings) if isinstance(findings, list) else 0,
            }, request_id=request_id)
        except Exception as e:
            return self._err(f"Audit failed: {e}", "API_500", status_code=500)

    async def _repo_staleness(self, repo_path: Optional[str], repo_id: Optional[str],
                              args: Dict) -> Dict:
        from pathlib import Path
        if not repo_path:
            return self._err("repo_path required for staleness", "API_400")
        resolved = str(Path(repo_path).resolve())
        request_id = new_request_id()

        try:
            repo = self.orchestrator.repo_store.get_repository_by_path(resolved)
            if not repo:
                return self._err("Repository not found", "API_404", status_code=404)
            rid = repo.get("id")
            last_sync = repo.get("sync_at")
            return self._ok("Staleness check", {
                "repo_id": rid, "sync_at": last_sync, "is_stale": True,
            }, request_id=request_id)
        except Exception as e:
            return self._err(f"Staleness check failed: {e}", "API_500", status_code=500)

    async def _repo_list(self, args: Dict) -> Dict:
        request_id = new_request_id()
        try:
            repos = self.orchestrator.repo_store.list_repositories()
            return self._ok("Repositories listed", {"repos": repos, "total": len(repos)},
                            request_id=request_id)
        except Exception as e:
            return self._err(f"List failed: {e}", "API_500", status_code=500)

    async def _repo_compact(self, repo_path: Optional[str], repo_id: Optional[str],
                            args: Dict) -> Dict:
        import json, yaml
        from pathlib import Path
        from ..core.database import compact_database

        request_id = new_request_id()
        output_format = args.get("output_format", "yaml")
        output_path = args.get("output_path")
        compact_db = args.get("compact_db", True)
        dry_run = args.get("dry_run", False)
        rid = self._resolve_id(repo_id, repo_path)

        try:
            if compact_db and not dry_run:
                compact_database(self.orchestrator.db.conn)
            snapshot = {}
            if rid:
                rows = self.orchestrator.db.conn.execute(
                    "SELECT * FROM files WHERE repository_id=? LIMIT 10", (rid,)
                ).fetchall()
                snapshot = {"repo_id": rid, "sample_files": [dict(r) for r in rows]}
            return self._ok("Compact complete", snapshot, request_id=request_id)
        except Exception as e:
            return self._err(f"Compact failed: {e}", "API_500", status_code=500)

    async def _repo_cleanup(self, repo_path: Optional[str], repo_id: Optional[str],
                            args: Dict) -> Dict:
        from pathlib import Path
        from ..modules.coderepository.core.registry import RegistryManager

        request_id = new_request_id()
        force = args.get("force", False)
        dry_run = args.get("dry_run", False)
        rid = self._resolve_id(repo_id, repo_path)

        if not rid:
            return self._err("No repository found to clean up", "API_404", status_code=404)
        if dry_run:
            return self._ok("Dry run — would delete", {"repo_id": rid}, request_id=request_id)

        try:
            for table in ("files", "directories", "symbols", "edges", "audit_findings",
                          "test_results", "execution_tasks", "file_tree",
                          "disk_usage", "repo_sync_state", "index_stats",
                          "index_query_cache", "embeddings", "edge_hashes"):
                try:
                    self.orchestrator.db.conn.execute(
                        f"DELETE FROM {table} WHERE repository_id=?", (rid,)
                    )
                except Exception:
                    pass
            self.orchestrator.db.conn.execute(
                "DELETE FROM repositories WHERE id=?", (rid,)
            )
            self.orchestrator.db.conn.commit()
            return self._ok("Repository cleaned up", {"repo_id": rid}, request_id=request_id)
        except Exception as e:
            return self._err(f"Cleanup failed: {e}", "API_500", status_code=500)

    async def _repo_dump(self, repo_path: Optional[str], repo_id: Optional[str],
                         args: Dict) -> Dict:
        import json, os
        from pathlib import Path

        request_id = new_request_id()
        rp = repo_path
        if not rp:
            return self._err("repo_path required for dump", "API_400")
        resolved = str(Path(rp).resolve())
        output_dir = args.get("output_dir", os.path.join(os.getcwd(), "codecortex_dumps"))
        fmt = args.get("format", "yaml")
        dry_run = args.get("dry_run", False)

        try:
            repo = self.orchestrator.repo_store.get_repository_by_path(resolved)
            if not repo:
                return self._err("Repository not found", "API_404", status_code=404)
            rid = repo.get("id")

            if dry_run:
                nfiles = self.orchestrator.db.conn.execute(
                    "SELECT COUNT(*) FROM files WHERE repository_id=?", (rid,)
                ).fetchone()[0]
                return self._ok("Dry run", {"estimated_files": nfiles, "output_dir": output_dir},
                                request_id=request_id)

            # export all tables
            tables = ["files", "directories", "symbols", "edges"]
            dump_data = {"repo_id": rid, "tables": {}}
            for table in tables:
                try:
                    rows = self.orchestrator.db.conn.execute(
                        f"SELECT * FROM {table} WHERE repository_id=?", (rid,)
                    ).fetchall()
                    dump_data["tables"][table] = [dict(r) for r in rows]
                except Exception:
                    pass

            os.makedirs(output_dir, exist_ok=True)
            out = os.path.join(output_dir, f"{rid}.json")
            with open(out, "w", encoding="utf-8") as f:
                json.dump(dump_data, f, indent=2, default=str)

            return self._ok("Dump complete", {"output": out, "repo_id": rid, "tables": list(dump_data["tables"].keys())},
                            request_id=request_id)
        except Exception as e:
            return self._err(f"Dump failed: {e}", "API_500", status_code=500)

    async def _repo_restore(self, args: Dict) -> Dict:
        import json, os
        from pathlib import Path
        from ..modules.coderepository.core.registry import RegistryManager

        request_id = new_request_id()
        source = args.get("source")
        repo_path = args.get("repo_path")
        overwrite = args.get("overwrite", False)
        dry_run = args.get("dry_run", False)

        if not source:
            return self._err("source is required for restore", "API_400")

        final_rp = repo_path or source
        try:
            if dry_run:
                return self._ok("Dry run — would restore from", {"source": source},
                                request_id=request_id)

            if os.path.isdir(source):
                for f in os.listdir(source):
                    if f.endswith(".json"):
                        with open(os.path.join(source, f), encoding="utf-8") as fh:
                            dump = json.load(fh)
                        rid = dump.get("repo_id", "restored_0")
                        for table, rows in dump.get("tables", {}).items():
                            for row in rows:
                                cols = list(row.keys())
                                vals = [row[c] for c in cols]
                                placeholders = ",".join(["?"] * len(vals))
                                try:
                                    self.orchestrator.db.conn.execute(
                                        f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({placeholders})",
                                        vals,
                                    )
                                except Exception:
                                    pass
                        self.orchestrator.db.conn.commit()
                        RegistryManager.register(final_rp, rid)
                        return self._ok("Restore complete", {"repo_id": rid}, request_id=request_id)

            with open(source, encoding="utf-8") as fh:
                dump = json.load(fh)
            rid = dump.get("repo_id", "restored_0")
            for table, rows in dump.get("tables", {}).items():
                for row in rows:
                    cols = list(row.keys())
                    vals = [row[c] for c in cols]
                    try:
                        self.orchestrator.db.conn.execute(
                            f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({','.join(['?']*len(vals))})",
                            vals,
                        )
                    except Exception:
                        pass
            self.orchestrator.db.conn.commit()
            RegistryManager.register(final_rp, rid)
            return self._ok("Restore complete", {"repo_id": rid}, request_id=request_id)
        except Exception as e:
            return self._err(f"Restore failed: {e}", "API_500", status_code=500)

    async def _repo_git(self, repo_path: Optional[str], args: Dict) -> Dict:
        from pathlib import Path
        from ..modules.filesystem.adapters.git import DiskGit

        if not repo_path:
            return self._err("repo_path required for git", "API_400")
        resolved = str(Path(repo_path).resolve())
        request_id = new_request_id()
        dry_run = args.get("dry_run", False)

        try:
            params = {
                "subcommand": args.get("subcommand", "status"),
                "args": args.get("args", []),
                "flags": args.get("flags", {}),
                "repo_root": resolved,
            }
            if dry_run:
                return self._ok("Dry run", {"command": params}, request_id=request_id)
            result = DiskGit().execute(params)
            return self._ok("Git executed", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Git failed: {e}", "API_500", status_code=500)

    async def _repo_svn(self, args: Dict) -> Dict:
        from ..modules.filesystem.adapters.svn import DiskSvn

        request_id = new_request_id()
        dry_run = args.get("dry_run", False)
        try:
            params = {
                "subcommand": args.get("subcommand", "info"),
                "args": args.get("args", []),
                "flags": args.get("flags", {}),
                "target": args.get("target", "."),
            }
            if dry_run:
                return self._ok("Dry run", {"command": params}, request_id=request_id)
            result = DiskSvn().execute(params)
            return self._ok("SVN executed", result, request_id=request_id)
        except Exception as e:
            return self._err(f"SVN failed: {e}", "API_500", status_code=500)

    # ══════════════════════════════════════════════════════════
    # FILESYSTEM DISPATCH (13 actions)
    # ══════════════════════════════════════════════════════════
    async def dispatch_filesystem(self, action: str, path: str, repo_id: Optional[str],
                            args: Dict) -> Dict:
        """Dispatch filesystem actions to internal async methods."""
        action_lower = action.lower()
        if action_lower == "read": return await self._fs_read(path, repo_id, args)
        elif action_lower == "write": return await self._fs_write(path, repo_id, args)
        elif action_lower == "delete": return await self._fs_delete(path, args)
        elif action_lower == "copy": return await self._fs_copy(path, args)
        elif action_lower == "move": return await self._fs_move(path, args)
        elif action_lower == "mkdir": return await self._fs_mkdir(path, args)
        elif action_lower in ("list", "ls"): return await self._fs_list(path, repo_id, args)
        elif action_lower == "search": return await self._fs_search(args)
        elif action_lower == "watch": return await self._fs_watch(args)
        elif action_lower == "usage": return await self._fs_usage(args)
        elif action_lower == "audit": return await self._fs_audit(args)
        elif action_lower == "read_lines": return await self._fs_read_lines(path, repo_id, args)
        elif action_lower == "write_lines": return await self._fs_write_lines(path, repo_id, args)
        else: return self._err(f"Unknown filesystem action: {action}", "API_400")

    async def _fs_read(self, path: Optional[str], repo_id: Optional[str], args: Dict) -> Dict:
        import os
        from pathlib import Path
        from ..core.database.integrity import FileIntegrity

        if not path:
            return self._err("path required for read", "API_400")

        resolved = str(Path(path).resolve()) if os.path.isabs(path) else (
            self.orchestrator.fs_service.resolve_repo_path(repo_id, path) if repo_id else str(Path(path).resolve())
        )
        encoding = args.get("encoding", "utf-8")
        offset = args.get("offset", 0)
        limit = args.get("limit")
        request_id = new_request_id()

        try:
            with open(resolved, "r", encoding=encoding, errors="replace") as f:
                content = f.read()
            if offset:
                content = content[offset:]
            if limit:
                content = content[:int(limit)]
            rid = self._resolve_id(repo_id, None) or repo_id
            if rid:
                try:
                    FileIntegrity(self.orchestrator.db).update_file(
                        rid, Path(resolved), os.stat(resolved).st_mtime,
                    )
                except Exception:
                    pass
            return self._ok("File read", {"path": resolved, "content": content, "size": len(content)},
                            request_id=request_id)
        except FileNotFoundError:
            return self._err(f"File not found: {resolved}", "API_404", status_code=404)

    async def _fs_write(self, path: Optional[str], repo_id: Optional[str], args: Dict) -> Dict:
        import os
        from pathlib import Path

        if not path:
            return self._err("path required for write", "API_400")
        content = args.get("content", "")
        encoding = args.get("encoding", "utf-8")
        atomic = args.get("atomic", True)
        backup = args.get("backup", False)
        create_parents = args.get("create_parents", True)
        overwrite = args.get("overwrite", False)
        request_id = new_request_id()

        resolved = str(Path(path).resolve()) if os.path.isabs(path) else (
            self.orchestrator.fs_service.resolve_repo_path(repo_id, path) if repo_id else str(Path(path).resolve())
        )

        try:
            if os.path.exists(resolved) and not overwrite:
                return self._err(f"File exists: {resolved}", "API_409", status_code=409)
            if create_parents:
                os.makedirs(os.path.dirname(resolved), exist_ok=True)
            if backup and os.path.exists(resolved):
                import shutil
                shutil.copy2(resolved, resolved + ".bak")
            if atomic:
                tmp = resolved + ".tmp"
                with open(tmp, "w", encoding=encoding) as f:
                    f.write(content)
                os.replace(tmp, resolved)
            else:
                with open(resolved, "w", encoding=encoding) as f:
                    f.write(content)
            return self._ok("File written", {"path": resolved, "size": len(content)},
                            request_id=request_id)
        except Exception as e:
            return self._err(f"Write failed: {e}", "API_500", status_code=500)

    async def _fs_delete(self, path: Optional[str], args: Dict) -> Dict:
        import os, shutil
        from pathlib import Path

        if not path:
            return self._err("path required for delete", "API_400")
        resolved = str(Path(path).resolve())
        recursive = args.get("recursive", False)
        dry_run = args.get("dry_run", False)
        request_id = new_request_id()

        try:
            if dry_run:
                return self._ok("Dry run — would delete", {"path": resolved},
                                request_id=request_id)
            if os.path.isdir(resolved):
                if recursive:
                    shutil.rmtree(resolved)
                else:
                    os.rmdir(resolved)
            else:
                os.remove(resolved)
            return self._ok("Deleted", {"path": resolved}, request_id=request_id)
        except FileNotFoundError:
            return self._err(f"Not found: {resolved}", "API_404", status_code=404)

    async def _fs_copy(self, path: Optional[str], args: Dict) -> Dict:
        import os, shutil
        from pathlib import Path

        if not path:
            return self._err("path required for copy", "API_400")
        dest = args.get("dest")
        if not dest:
            return self._err("dest required for copy", "API_400")
        src = str(Path(path).resolve())
        dst = str(Path(dest).resolve())
        overwrite = args.get("overwrite", False)
        create_parents = args.get("create_dest_parents", True)
        dry_run = args.get("dry_run", False)
        request_id = new_request_id()

        try:
            if dry_run:
                return self._ok("Dry run — would copy", {"from": src, "to": dst},
                                request_id=request_id)
            if os.path.exists(dst) and not overwrite:
                return self._err(f"Destination exists: {dst}", "API_409", status_code=409)
            if create_parents:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=overwrite)
            else:
                shutil.copy2(src, dst)
            return self._ok("Copied", {"from": src, "to": dst}, request_id=request_id)
        except FileNotFoundError:
            return self._err(f"Source not found: {src}", "API_404", status_code=404)

    async def _fs_move(self, path: Optional[str], args: Dict) -> Dict:
        import os, shutil
        from pathlib import Path

        if not path:
            return self._err("path required for move", "API_400")
        dest = args.get("dest")
        if not dest:
            return self._err("dest required for move", "API_400")
        src = str(Path(path).resolve())
        dst = str(Path(dest).resolve())
        overwrite = args.get("overwrite", False)
        create_parents = args.get("create_dest_parents", True)
        dry_run = args.get("dry_run", False)
        request_id = new_request_id()

        try:
            if dry_run:
                return self._ok("Dry run — would move", {"from": src, "to": dst},
                                request_id=request_id)
            if os.path.exists(dst) and not overwrite:
                return self._err(f"Destination exists: {dst}", "API_409", status_code=409)
            if create_parents:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            return self._ok("Moved", {"from": src, "to": dst}, request_id=request_id)
        except FileNotFoundError:
            return self._err(f"Source not found: {src}", "API_404", status_code=404)

    async def _fs_mkdir(self, path: Optional[str], args: Dict) -> Dict:
        import os
        from pathlib import Path

        if not path:
            return self._err("path required for mkdir", "API_400")
        resolved = str(Path(path).resolve())
        create_parents = args.get("create_parents", True)
        dry_run = args.get("dry_run", False)
        request_id = new_request_id()

        try:
            if dry_run:
                return self._ok("Dry run — would create", {"path": resolved},
                                request_id=request_id)
            os.makedirs(resolved, exist_ok=create_parents)
            return self._ok("Directory created", {"path": resolved}, request_id=request_id)
        except FileExistsError:
            return self._err(f"Directory exists: {resolved}", "API_409", status_code=409)

    async def _fs_list(self, path: Optional[str], repo_id: Optional[str], args: Dict) -> Dict:
        import os
        from pathlib import Path

        rp = path or "."
        try:
            resolved = str(Path(rp).resolve()) if os.path.isabs(rp) else (
                self.orchestrator.fs_service.resolve_repo_path(repo_id, rp) if repo_id else str(Path(rp).resolve())
            )
        except Exception:
            resolved = str(Path(rp).resolve())
        recursive = args.get("recursive", False)
        max_depth = args.get("max_depth")
        include_hidden = args.get("include_hidden", False)
        file_pattern = args.get("file_pattern", "*")
        request_id = new_request_id()

        try:
            entries = []
            if recursive and max_depth:
                for root, dirs, files in os.walk(resolved):
                    depth = root[len(str(resolved)):].count(os.sep)
                    if depth >= int(max_depth):
                        dirs[:] = []
                    for name in files + dirs:
                        fp = os.path.join(root, name)
                        if not include_hidden and name.startswith("."):
                            continue
                        entries.append({
                            "name": name, "path": fp,
                            "is_dir": os.path.isdir(fp),
                            "size": os.path.getsize(fp) if os.path.isfile(fp) else 0,
                        })
            else:
                for name in os.listdir(resolved):
                    if not include_hidden and name.startswith("."):
                        continue
                    fp = os.path.join(resolved, name)
                    entries.append({
                        "name": name, "path": fp,
                        "is_dir": os.path.isdir(fp),
                        "size": os.path.getsize(fp) if os.path.isfile(fp) else 0,
                    })
            return self._ok("Directory listed", {"path": resolved, "entries": entries, "count": len(entries)},
                            request_id=request_id)
        except FileNotFoundError:
            return self._err(f"Not found: {resolved}", "API_404", status_code=404)

    async def _fs_search(self, args: Dict) -> Dict:
        # pyrefly: ignore [missing-import]
        from ..modules.filesystem.adapters.search import DiskSearch

        request_id = new_request_id()
        try:
            params = {
                "root_path": args.get("root_path"),
                "repo_id": args.get("repo_id"),
                "file_pattern": args.get("file_pattern", "*"),
                "file_regex": args.get("file_regex"),
                "content_regex": args.get("content_regex"),
                "content_regex_flags": args.get("content_regex_flags", ""),
                "recursive": args.get("recursive", True),
                "max_depth": args.get("max_depth"),
                "include_hidden": args.get("include_hidden", False),
                "follow_symlinks": args.get("follow_symlinks", False),
                "max_results": args.get("max_results", 100),
                "include_content_snippet": args.get("include_content_snippet", True),
                "exclude_patterns": args.get("exclude_patterns"),
                "replace_text": args.get("replace_text"),
                "dry_run": args.get("dry_run", True),
            }
            result = DiskSearch().search(params)
            return self._ok("Search complete", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Search failed: {e}", "API_500", status_code=500)

    async def _fs_watch(self, args: Dict) -> Dict:
        from ..modules.filesystem.adapters.watch import DiskWatcher

        request_id = new_request_id()
        try:
            params = {
                "target": args.get("target", "."),
                "recursive": args.get("recursive", True),
                "events": args.get("events"),
                "poll_interval": args.get("poll_interval", 1),
                "max_events": args.get("max_events", 100),
            }
            result = DiskWatcher.watch(params)
            return self._ok("Watch results", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Watch failed: {e}", "API_500", status_code=500)

    async def _fs_usage(self, args: Dict) -> Dict:
        from ..modules.filesystem.adapters.df import DiskUsage

        request_id = new_request_id()
        try:
            params = {
                "target": args.get("target", "."),
                "recursive": args.get("recursive", True),
                "depth": args.get("depth", 10),
                "unit": args.get("unit", "auto"),
                "include_hidden": args.get("include_hidden", False),
                "exclude_patterns": args.get("exclude_patterns"),
                "aggregate_by": args.get("aggregate_by", "file"),
                "max_items": args.get("max_items", 100),
            }
            result = DiskUsage.analyze(params)
            return self._ok("Disk usage", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Usage analysis failed: {e}", "API_500", status_code=500)

    async def _fs_audit(self, args: Dict) -> Dict:
        from ..modules.filesystem.adapters.audit import DiskAudit

        request_id = new_request_id()
        try:
            params = {
                "target": args.get("target", "."),
                "recursive": args.get("recursive", True),
                "severity": args.get("severity"),
                "check_permissions": args.get("check_permissions", True),
                "check_hidden": args.get("check_hidden", True),
                "max_file_size_mb": args.get("max_file_size_mb", 100),
                "exclude_patterns": args.get("exclude_patterns"),
                "limit": args.get("limit", 200),
            }
            result = DiskAudit.audit(params)
            return self._ok("Filesystem audit complete", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Filesystem audit failed: {e}", "API_500", status_code=500)

    async def _fs_read_lines(self, path: Optional[str], repo_id: Optional[str],
                             args: Dict) -> Dict:
        request_id = new_request_id()
        if not path:
            return self._err("path required for read_lines", "API_400")
        try:
            result = self.orchestrator.fs_service.read_lines(
                path=path,
                start_line=args.get("start_line", 1),
                end_line=args.get("end_line"),
                repo_id=repo_id,
                encoding=args.get("encoding", "utf-8"),
            )
            if "error" in result:
                return self._err(result["error"], "API_500", status_code=500)
            return self._ok("Read lines complete", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Read lines failed: {e}", "API_500", status_code=500)

    async def _fs_write_lines(self, path: Optional[str], repo_id: Optional[str],
                              args: Dict) -> Dict:
        request_id = new_request_id()
        if not path:
            return self._err("path required for write_lines", "API_400")
        if "content" not in args:
            return self._err("content required for write_lines", "API_400")
        try:
            result = self.orchestrator.fs_service.write_lines(
                path=path,
                start_line=args.get("start_line", 1),
                end_line=args.get("end_line"),
                content=args["content"],
                repo_id=repo_id,
                encoding=args.get("encoding", "utf-8"),
                dry_run=args.get("dry_run", False),
            )
            if "error" in result:
                return self._err(result["error"], "API_500", status_code=500)
            return self._ok("Write lines complete", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Write lines failed: {e}", "API_500", status_code=500)

    # ══════════════════════════════════════════════════════════
    # CODEBASE DISPATCH (8 actions)
    # Uses shared codebase service
    # ══════════════════════════════════════════════════════════
    async def dispatch_codebase(self, action: str, repo_id: Optional[str],
                                repo_path: Optional[str], args: Dict) -> Dict:
        action_lower = action.lower()
        if action_lower == "search": return await self._cb_search(repo_id, repo_path, args)
        elif action_lower == "audit": return await self._cb_audit(repo_path, repo_id, args)
        elif action_lower == "status": return await self._cb_status(repo_path, repo_id, args)
        elif action_lower == "analyze": return await self._cb_analyze(repo_path, repo_id, args)
        elif action_lower == "index": return await self._cb_index(repo_id, repo_path, args)
        elif action_lower == "test": return await self._cb_test(repo_id, repo_path, args)
        elif action_lower == "refactor": return await self._cb_refactor(repo_id, args)
        elif action_lower == "graph": return await self._cb_graph(repo_id, repo_path, args)
        else: return self._err(f"Unknown codebase action: {action}", "API_400")

    # ══════════════════════════════════════════════════════════
    # SCAFFOLDER DISPATCH (7 actions)
    # Uses shared scaffolder service
    # ══════════════════════════════════════════════════════════
    async def dispatch_scaffolder(self, action: str, args: Dict) -> Dict:
        action_lower = action.lower()
        if action_lower == "list_stacks": return await self._scaffold_list_stacks(args)
        elif action_lower == "get_stack": return await self._scaffold_get_stack(args)
        elif action_lower == "validate_name": return await self._scaffold_validate_name(args)
        elif action_lower == "list_licenses": return await self._scaffold_list_licenses(args)
        elif action_lower == "generate_content": return await self._scaffold_generate_content(args)
        elif action_lower == "generate_class": return await self._scaffold_generate_class(args)
        elif action_lower == "create_project": return await self._scaffold_create_project(args)
        else: return self._err(f"Unknown scaffolder action: {action}", "API_400")

    # ── scaffolder handlers ────────────────────────────────

    async def _scaffold_list_stacks(self, args: Dict) -> Dict:
        # pyrefly: ignore [missing-import]
        from ..core import get_project_root
        # pyrefly: ignore [missing-import]
        from ..modules.scaffolder.adapters.stack import Stack as StackAdapter

        project_root = get_project_root()
        templates_root = project_root / "datasets" / "templates"
        stack_repo = StackAdapter(templates_root)
        stacks = stack_repo.list_stacks()
        data = []
        for s in stacks:
            data.append({
                "name": s.name,
                "display_name": s.display_name,
                "version": s.version,
                "file_conventions": {
                    "directories": s.file_conventions.directories.value if s.file_conventions else "snake_case",
                    "modules": s.file_conventions.modules if s.file_conventions else "snake_case.py",
                    "classes": s.file_conventions.classes if s.file_conventions else "PascalCase",
                },
                "project_types": [pt.id for pt in s.project_types] if s.project_types else [],
            })
        return self._ok(f"Found {len(data)} stacks", {"stacks": data})

    async def _scaffold_get_stack(self, args: Dict) -> Dict:
        from ..core import get_project_root
        from ..modules.scaffolder.adapters.stack import Stack as StackAdapter

        stack_name = (args.get("stack_name") or "").strip().lower()
        if not stack_name:
            return self._err("stack_name required", "STACK_NAME_REQUIRED")
        project_root = get_project_root()
        templates_root = project_root / "datasets" / "templates"
        stack_repo = StackAdapter(templates_root)
        stack = stack_repo.get_stack(stack_name)
        if stack is None:
            available = [s.name for s in stack_repo.list_stacks()] or ["(none)"]
            return self._err(f"Stack '{stack_name}' not found. Available: {', '.join(available)}",
                             "STACK_NOT_FOUND", status_code=404)
        project_types = [
            {"id": pt.id, "display_name": pt.display_name, "description": pt.description}
            for pt in (stack.project_types or [])
        ]
        return self._ok(f"Stack '{stack.display_name}' found", {
            "stack": {
                "name": stack.name,
                "display_name": stack.display_name,
                "version": stack.version,
                "file_conventions": {
                    "directories": stack.file_conventions.directories.value if stack.file_conventions else "snake_case",
                    "modules": stack.file_conventions.modules if stack.file_conventions else "snake_case.py",
                    "classes": stack.file_conventions.classes if stack.file_conventions else "PascalCase",
                },
                "project_types": project_types,
            },
        })

    async def _scaffold_validate_name(self, args: Dict) -> Dict:
        from ..modules.scaffolder.core.name import Name
        from ..modules.scaffolder.core.exceptions import InvalidNameError

        raw = (args.get("name") or "").strip()
        if not raw:
            return self._err("name required for validate_name", "NAME_REQUIRED")
        try:
            validated = Name.create(raw)
            return self._ok(f"Name '{validated.display}' is valid", {
                "display": validated.display,
                "slug": validated.slug,
                "snake": validated.snake,
                "pascal": validated.pascal,
            })
        except InvalidNameError as exc:
            return self._err(str(exc), "INVALID_NAME", status_code=400)

    async def _scaffold_list_licenses(self, args: Dict) -> Dict:
        from ..modules.scaffolder.core.constants import LicenseIdentifier

        licenses = [
            {"id": member.value, "name": member.name.replace("_", " ").title()}
            for member in LicenseIdentifier
        ]
        return self._ok(f"Found {len(licenses)} license types", {"licenses": licenses})

    async def _scaffold_generate_content(self, args: Dict) -> Dict:
        from ..modules.scaffolder.core.generators import (
            ProjectCategory, gitignore, env_boilerplate, pyproject, readme,
            requirements, dockerfile, docker_compose, setup_sh, setup_bat,
            setup_ps1, logger_py, author_file, ai_ignore,
        )

        file_type = (args.get("file_type") or "").strip().lower()
        if not file_type:
            return self._err("file_type required for generate_content", "FILE_TYPE_REQUIRED")

        generator_map = {
            "gitignore": (gitignore, None),
            "env": (env_boilerplate, None),
            "pyproject": (pyproject, None),
            "readme": (readme, None),
            "requirements": (requirements, None),
            "dockerfile": (dockerfile, None),
            "docker_compose": (docker_compose, None),
            "setup_sh": (setup_sh, None),
            "setup_bat": (setup_bat, None),
            "setup_ps1": (setup_ps1, None),
            "logger_py": (logger_py, None),
            "author_file": (author_file, None),
            "ai_ignore": (ai_ignore, None),
        }

        entry = generator_map.get(file_type)
        if entry is None:
            return self._err(f"Unknown file_type '{file_type}'", "UNKNOWN_FILE_TYPE")

        generator, _ = entry
        category_str = (args.get("project_category") or "standard").strip().lower().replace(" ", "_")
        category_map = {
            "standard": ProjectCategory.STANDARD,
            "data_science": ProjectCategory.DATA_SCIENCE,
            "web_api": ProjectCategory.WEB_API,
            "cli_tool": ProjectCategory.CLI_TOOL,
            "automation": ProjectCategory.AUTOMATION,
            "custom": ProjectCategory.CUSTOM,
        }
        category = category_map.get(category_str, ProjectCategory.STANDARD)
        project_name = args.get("project_name", "My Project")
        author = args.get("author", "Author")
        email = args.get("email", "author@example.com")

        if file_type in ("gitignore", "env", "requirements", "dockerfile", "docker_compose"):
            content = generator(category)
        elif file_type == "pyproject":
            content = generator(author, email, project_name, category, project_name.lower().replace(" ", "_"))
        elif file_type == "readme":
            license_name = args.get("license_name", "MIT")
            content = generator(project_name, author, email, category, license_name)
        elif file_type in ("setup_sh", "setup_bat", "setup_ps1"):
            content = generator(project_name, author)
        elif file_type == "logger_py":
            content = generator(author)
        elif file_type == "author_file":
            content = generator(author, email)
        elif file_type == "ai_ignore":
            content = generator()
        else:
            content = generator(category)

        filename_map = {
            "gitignore": ".gitignore", "env": ".env.example",
            "pyproject": "pyproject.toml", "readme": "README.md",
            "requirements": "requirements.txt", "dockerfile": "Dockerfile",
            "docker_compose": "docker-compose.yml",
            "setup_sh": "bin/setup.sh", "setup_bat": "bin/setup.bat",
            "setup_ps1": "bin/setup.ps1", "logger_py": "src/core/logger.py",
            "author_file": ".author", "ai_ignore": ".aiignore",
        }

        return self._ok(f"Generated {file_type}", {
            "filename": filename_map.get(file_type, file_type),
            "content": content,
            "content_length": len(content),
        })

    async def _scaffold_generate_class(self, args: Dict) -> Dict:
        # pyrefly: ignore [missing-import]
        from ..modules.scaffolder.core.maker import make_class

        type_id = (args.get("type") or "").strip().lower().replace("-", "_")
        name = (args.get("name") or "").strip()
        if not type_id:
            return self._err("type required for generate_class", "TYPE_REQUIRED")
        if not name:
            return self._err("name required for generate_class", "NAME_REQUIRED")

        result = make_class(
            type_id=type_id,
            name=name,
            stack=args.get("stack", "python"),
            module=args.get("module"),
            project_name=args.get("project_name", "Project"),
            author=args.get("author", "Author"),
            target_path=args.get("target_path"),
            overwrite=args.get("overwrite", False),
        )
        if not result["success"]:
            return self._err(result["error"], "MAKE_VALIDATION_ERROR", status_code=400)
        return self._ok(f"Generated {result['type_display']} '{result['class_name']}'", {
            "type": result["type"],
            "type_display": result["type_display"],
            "stack": result["stack"],
            "class_name": result["class_name"],
            "file_name": result["file_name"],
            "relative_path": result["relative_path"],
            "absolute_path": result.get("absolute_path"),
            "content": result["content"],
            "content_length": result["content_length"],
            "written": result["written"],
        })

    async def _scaffold_create_project(self, args: Dict) -> Dict:
        import asyncio
        from ..core import get_project_root, Version
        from ..modules.scaffolder.api.tools import _build_scaffold_services
        from ..modules.scaffolder.core.name import Name
        from ..modules.scaffolder.core.license import License
        from ..modules.scaffolder.core.exceptions import InvalidNameError, ProjectAlreadyExistsError, ScaffoldError
        from ..modules.scaffolder.core.dtos import Project as ProjectDTO
        from ..modules.scaffolder.services.scaffold import Scaffold

        name_raw = (args.get("name") or "").strip()
        if not name_raw:
            return self._err("name required for create_project", "NAME_REQUIRED")
        try:
            validated_name = Name.create(name_raw)
        except InvalidNameError as exc:
            return self._err(str(exc), "INVALID_NAME", status_code=400)

        stack_name = (args.get("stack") or "python").strip().lower()
        project_type_id = (args.get("project_type") or "standard").strip().lower()

        stack_repo, template_repo, engine, file_header = _build_scaffold_services()
        resolved_stack = stack_repo.get_stack(stack_name)
        if resolved_stack is None:
            available = [s.name for s in stack_repo.list_stacks()] or ["(none)"]
            return self._err(f"Stack '{stack_name}' not found. Available: {', '.join(available)}",
                             "STACK_NOT_FOUND", status_code=404)

        resolved_pt = resolved_stack.get_project_type(project_type_id)
        if resolved_pt is None:
            available_pts = resolved_stack.project_type_ids or ["standard"]
            return self._err(f"Project type '{project_type_id}' not found. Available: {', '.join(available_pts)}",
                             "PROJECT_TYPE_NOT_FOUND", status_code=404)

        dry_run = args.get("dry_run", True)
        target_path = args.get("target_path")
        final_target = (
            Path(target_path).resolve()
            if target_path
            else (get_project_root() / "outputs" / "projects" / validated_name.slug).resolve()
        )
        author = args.get("author") or "Author"
        email = args.get("email") or "author@example.com"
        version_str = args.get("version") or "0.1.0"
        license_str = args.get("license") or "MIT"
        overwrite = args.get("overwrite", False)
        include_ai = args.get("include_ai", False)
        include_trainer = args.get("include_trainer", False)
        project_code = args.get("project_code")

        from pathlib import Path

        try:
            resolved_version = Version.from_string(version_str)
        except Exception:
            return self._err(f"Invalid version '{version_str}'", "INVALID_VERSION", status_code=400)

        resolved_license = License.from_string(license_str)

        if dry_run:
            file_count = (
                len(template_repo.get_shared_templates())
                + len(template_repo.get_stack_templates(resolved_stack.name, resolved_pt.id))
            )
            return self._ok(f"Dry-run: project '{validated_name.display}' ready", {
                "dry_run": True,
                "name": {
                    "display": validated_name.display,
                    "slug": validated_name.slug,
                    "snake": validated_name.snake,
                    "pascal": validated_name.pascal,
                },
                "stack": resolved_stack.name,
                "stack_display": resolved_stack.display_name,
                "project_type": resolved_pt.id,
                "project_type_display": resolved_pt.display_name,
                "target_path": str(final_target),
                "author": author,
                "email": email,
                "version": version_str,
                "license": resolved_license.identifier.value,
                "include_ai": include_ai,
                "include_trainer": include_trainer,
                "template_count": file_count,
                "directory_count": 33 + len(resolved_pt.extra_directories),
                "template_context_keys": list(ProjectDTO(
                    name=validated_name,
                    target_path=final_target,
                    stack_name=resolved_stack.name,
                    project_type=resolved_pt,
                    author=author,
                    email=email,
                    version=resolved_version,
                    license=resolved_license,
                    include_ai=include_ai,
                    include_trainer=include_trainer,
                    project_code=project_code,
                ).template_context().keys()),
            })

        project = ProjectDTO(
            name=validated_name,
            target_path=final_target,
            stack_name=resolved_stack.name,
            project_type=resolved_pt,
            author=author,
            email=email,
            version=resolved_version,
            license=resolved_license,
            include_ai=include_ai,
            include_trainer=include_trainer,
            project_code=project_code,
        )

        scaffold_service = Scaffold(stack_repo, template_repo, engine, file_header)
        progress_messages = []

        def _progress(msg: str) -> None:
            progress_messages.append(msg)

        try:
            await asyncio.to_thread(
                scaffold_service.scaffold,
                project,
                progress=_progress,
                overwrite=overwrite,
            )
            return self._ok(f"Project '{validated_name.display}' scaffolded", {
                "dry_run": False,
                "target_path": str(final_target),
                "name": validated_name.display,
                "slug": validated_name.slug,
                "stack": resolved_stack.name,
                "project_type": resolved_pt.id,
                "version": version_str,
                "license": resolved_license.identifier.value,
                "progress": progress_messages,
            })
        except ProjectAlreadyExistsError:
            return self._err(f"Project exists at {final_target}. Set overwrite=true.",
                             "PROJECT_EXISTS", status_code=409)
        except ScaffoldError as exc:
            return self._err(str(exc), "SCAFFOLD_ERROR", status_code=500)
        except Exception as exc:
            logger.error("scaffold_create failed: %s", exc, exc_info=True)
            return self._err(f"Unexpected scaffold error: {exc}", "SCAFFOLD_UNEXPECTED", status_code=500)

    # ── codebase handlers ──────────────────────────────────

    async def _cb_analyze(self, repo_path: Optional[str], repo_id: Optional[str],
                          args: Dict) -> Dict:
        from ..modules.codeanalysis.services.analyze import Analyze, AnalyzeRequest

        target = args.get("target")
        if not target:
            return self._err("args.target required for analyze", "API_400")
        request_id = new_request_id()

        try:
            service = Analyze(db=self.orchestrator.db,
                              fs_service=self.orchestrator.fs_service)
            req = AnalyzeRequest(
                target=target,
                repo_id=repo_id,
                mode=args.get("mode", "auto"),
                max_depth=args.get("max_depth", 3),
                focus=args.get("focus"),
                follow_depth=args.get("follow_depth", 1),
                include_docstring=args.get("include_docstring", True),
                include_comments=args.get("include_comments", False),
                page_size=args.get("page_size", 100),
                cursor=args.get("cursor"),
            )
            result = service.analyze(req)
            return self._ok("Analysis complete", {
                "target": result.target,
                "symbols": [{"name": s.name, "kind": s.kind, "file": s.file_path,
                             "line": s.line_start}
                            for s in result.symbols] if hasattr(result, "symbols") else [],
                "call_graph": result.call_graph if hasattr(result, "call_graph") else {},
            }, request_id=request_id)
        except Exception as e:
            return self._err(f"Analyze failed: {e}", "API_500", status_code=500)

    async def _cb_search(self, repo_id: Optional[str], repo_path: Optional[str],
                         args: Dict) -> Dict:
        from ..modules.codeanalysis.services.search import Search, SearchRequest

        query = args.get("query")
        if not query:
            return self._err("args.query required for search", "API_400")
        request_id = new_request_id()

        try:
            service = Search(db=self.orchestrator.db)
            req = SearchRequest(
                query=query,
                repo_id=repo_id,
                limit=args.get("limit", 50),
                file_pattern=args.get("file_pattern", "*"),
                include_content=args.get("include_content", False),
            )
            result = service.search(
                req,
                semantic=args.get("semantic", False),
                graph=args.get("graph_enrichment", False),
                graph_relations=args.get("graph_relations"),
            )
            return self._ok("Search complete", {
                "query": query,
                "results": result.results if hasattr(result, "results") else [],
                "total": result.total if hasattr(result, "total") else 0,
            }, request_id=request_id)
        except Exception as e:
            return self._err(f"Search failed: {e}", "API_500", status_code=500)

    async def _cb_audit(self, repo_path: Optional[str], repo_id: Optional[str],
                        args: Dict) -> Dict:
        from ..modules.codeanalysis.services.audit import Audit, AuditRequest
        from ..core.database.integrity import FileIntegrity

        target = args.get("target") or repo_path or "."
        request_id = new_request_id()

        try:
            service = Audit(db=self.orchestrator.db,
                            fs_service=self.orchestrator.fs_service)
            req = AuditRequest(
                target=target,
                repository_id=repo_id,
                scan_categories=args.get("scan_categories"),
                severity_threshold=args.get("severity_threshold", "medium"),
                entropy_threshold=args.get("entropy_threshold", 4.5),
                include_comments=args.get("include_comments", False),
                max_file_size_kb=args.get("max_file_size_kb", 1024),
                files=args.get("files"),
                use_ast=args.get("use_ast", True),
                use_aiignore=args.get("use_aiignore", True),
                since=args.get("since"),
            )
            result = service.audit(req)
            # Mark sync
            rid = repo_id or self._resolve_id(None, repo_path)
            if rid:
                try:
                    FileIntegrity(self.orchestrator.db).mark_synced(rid, "audit")
                except Exception:
                    pass
            findings = [{"category": f.category, "severity": f.severity,
                         "file": f.file, "line": f.line, "message": f.message,
                         "remediation": f.remediation}
                        for f in result.findings] if hasattr(result, "findings") else []
            return self._ok(f"Audit complete: {len(findings)} findings",
                            {"target": result.target,
                             "scanned_files": result.scanned_files,
                             "compliance_score": result.compliance_score,
                             "findings": findings,
                             "recommendations": result.recommendations},
                            request_id=request_id)
        except Exception as e:
            return self._err(f"Audit failed: {e}", "API_500", status_code=500)

    async def _cb_graph(self, repo_id: Optional[str], repo_path: Optional[str],
                        args: Dict) -> Dict:
        from ..modules.codegraph.services.aegis import AEGIS
        from ..modules.codegraph.services.search import AEGISGraphSearch
        from ..modules.codegraph.services.audit import AEGISGraphAudit
        from ..modules.codegraph.services.trace import AEGISGraphTrace
        from ..modules.codegraph.services.relationship import AEGISGraphRelationship

        sub_action = args.get("sub_action", "build")
        request_id = new_request_id()
        rid = repo_id or self._resolve_id(None, repo_path)
        from pathlib import Path
        rp = str(Path(repo_path).resolve()) if repo_path else None
        if not rp and rid:
            row = self.orchestrator.db.conn.execute("SELECT root_path FROM repositories WHERE id=?", (rid,)).fetchone()
            if row:
                rp = row[0]
        graph_mgr = self.orchestrator.graph_service.graph_manager

        try:
            if sub_action == "build":
                if not rp:
                    return self._err("repo_path required for graph build", "API_400")
                builder = AEGIS(self.orchestrator.db, graph_mgr)
                result = await builder.build(
                    repo_path=rp, repo_id=rid,
                    detect_modular=args.get("detect_modular", True),
                    build_dependency_graph=args.get("build_dependency_graph", True),
                    include_core_contracts=args.get("include_core_contracts", True),
                    scan_hmvc_p=args.get("scan_hmvc_p", True),
                    max_depth=args.get("max_depth", 5),
                    use_cache=args.get("use_cache", True),
                )
                return self._ok("Graph built", result, request_id=request_id)

            elif sub_action == "query":
                query_type = args.get("query_type", "callers")
                target = args.get("target")
                if not target:
                    return self._err("args.target required for graph query", "API_400")

                if query_type == "trace_flow":
                    result = await self.orchestrator.graph_service.trace_execution_flow(
                        target, min(args.get("max_depth", 10), 10),
                    )
                elif query_type == "trace_path":
                    tracer = AEGISGraphTrace(self.orchestrator.db, graph_mgr)
                    result = await tracer.trace(
                        repo_id=rid, query_type="trace_path",
                        target_node=target,
                        max_depth=min(args.get("max_depth", 10), 10),
                        end_node=args.get("end_node"),
                        limit=args.get("limit", 20),
                    )
                else:
                    tracer = AEGISGraphTrace(self.orchestrator.db, graph_mgr)
                    result = await tracer.trace(
                        repo_id=rid,
                        query_type=f"find_{query_type}",
                        target_node=target,
                        max_depth=min(args.get("max_depth", 3), 10),
                        limit=args.get("limit", 20),
                    )
                return self._ok("Graph query complete", result, request_id=request_id)

            elif sub_action == "audit":
                auditor = AEGISGraphAudit(self.orchestrator.db, graph_mgr)
                result = await auditor.audit(
                    repo_id=rid,
                    max_depth=5,
                    include_suggestions=True,
                )
                # Also run graph_service audits
                god_nodes = self.orchestrator.graph_service.find_god_nodes(
                    rid, args.get("degree_threshold", 10),
                ) if rid else []
                dead_code = self.orchestrator.graph_service.find_dead_code(
                    rid, rp, args.get("limit", 50),
                ) if rid and rp else []
                return self._ok("Graph audit complete", {
                    "aegis_audit": result,
                    "god_nodes": god_nodes,
                    "dead_code": dead_code,
                }, request_id=request_id)

            elif sub_action == "relationships":
                target_node = args.get("target_node")
                if not target_node:
                    return self._err("args.target_node required for relationships", "API_400")
                rel = AEGISGraphRelationship(self.orchestrator.db, graph_mgr)
                result = await rel.explore(
                    repo_id=rid, target_node=target_node,
                    relation_type=args.get("relation_type"),
                    direction=args.get("direction", "both"),
                    depth=args.get("depth", 1),
                    modular_type=args.get("modular_type"),
                    include_community=args.get("include_community", False),
                    min_confidence=args.get("min_confidence", "INFERRED"),
                    limit=args.get("limit", 100),
                    cursor=args.get("cursor"),
                )
                return self._ok("Relationships explored", result, request_id=request_id)

            else:
                return self._err(f"Unknown graph sub_action: {sub_action}", "API_400")

        except Exception as e:
            return self._err(f"Graph operation failed: {e}", "API_500", status_code=500)

    async def _cb_status(self, repo_path: Optional[str], repo_id: Optional[str],
                         args: Dict) -> Dict:
        from ..modules.codeanalysis.services.status import Status, StatusRequest
        from ..core.database.index_cache import IndexCache
        from ..core.database.integrity import FileIntegrity

        rp = repo_path or "."
        rid = self._resolve_id(repo_id, repo_path)
        request_id = new_request_id()

        # Try cached path first
        if rid:
            try:
                stats = IndexCache(self.orchestrator.db).get_stats(rid)
                if stats:
                    state = FileIntegrity(self.orchestrator.db).get_sync_state(rid)
                    return self._ok("Status (cached)", {
                        "target": rp, "repo_id": rid,
                        "index_stats": stats,
                        "sync_state": {k: v for k, v in state.items() if k.endswith("_synced_at")},
                        "cached": True,
                    }, request_id=request_id)
            except Exception:
                pass

        try:
            service = Status(db=self.orchestrator.db)
            req = StatusRequest(
                path=rp, repo_id=rid,
                include_metrics=args.get("include_metrics", True),
                include_vcs=args.get("include_vcs", True),
                include_symbols=args.get("include_symbols", True),
                language=args.get("language"),
            )
            result = service.get_status(req)
            data = {
                "target": result.target, "repo_id": result.repo_id,
                "summary": {
                    "files": result.summary.files,
                    "total_lines": result.summary.total_lines,
                    "code_lines": result.summary.code_lines,
                    "comment_ratio": result.summary.comment_ratio,
                } if result.summary else None,
                "symbols": result.symbols,
                "graph_stats": {
                    "nodes": result.graph_stats.nodes,
                    "edges": result.graph_stats.edges,
                } if result.graph_stats else None,
            }
            return self._ok("Status retrieved", data, request_id=request_id)
        except Exception as e:
            return self._err(f"Status failed: {e}", "API_500", status_code=500)

    async def _cb_index(self, repo_id: Optional[str], repo_path: Optional[str],
                        args: Dict) -> Dict:
        sub_action = args.get("sub_action", "build")
        request_id = new_request_id()
        rid = repo_id or self._resolve_id(None, repo_path)

        try:
            if sub_action in ("build", "rebuild"):
                if repo_path:
                    rid = await self.orchestrator.repo_service.sync_repository(
                        repo_path, request_id=request_id,
                    )
                if rid:
                    await self.orchestrator.index_service.index_repository(
                        rid, request_id=request_id,
                    )
                return self._ok("Index built", {"repo_id": rid}, request_id=request_id)

            elif sub_action == "remove":
                if rid:
                    self.orchestrator.db.conn.execute(
                        "DELETE FROM symbols WHERE repository_id=?", (rid,)
                    )
                    self.orchestrator.db.conn.execute(
                        "DELETE FROM edges WHERE repository_id=?", (rid,)
                    )
                    self.orchestrator.db.conn.execute(
                        "DELETE FROM index_stats WHERE repository_id=?", (rid,)
                    )
                    self.orchestrator.db.conn.commit()
                return self._ok("Index removed", {"repo_id": rid}, request_id=request_id)

            elif sub_action == "status":
                if rid:
                    nfiles = self.orchestrator.db.conn.execute(
                        "SELECT COUNT(*) FROM files WHERE repository_id=? AND deleted_at IS NULL",
                        (rid,)
                    ).fetchone()[0]
                    nsym = self.orchestrator.db.conn.execute(
                        "SELECT COUNT(*) FROM symbols WHERE repository_id=?", (rid,)
                    ).fetchone()[0]
                    return self._ok("Index status", {"repo_id": rid, "files": nfiles, "symbols": nsym},
                                    request_id=request_id)
                return self._ok("Index status", {"repo_id": rid, "files": 0, "symbols": 0},
                                request_id=request_id)
            else:
                return self._err(f"Unknown index sub_action: {sub_action}", "API_400")
        except Exception as e:
            return self._err(f"Index operation failed: {e}", "API_500", status_code=500)

    async def _cb_test(self, repo_id: Optional[str], repo_path: Optional[str],
                       args: Dict) -> Dict:
        from ..modules.codetester.services.tester import Tester, CodeTesterRequest
        from ..core.database.integrity import FileIntegrity

        sub_action = args.get("sub_action", "run")
        target = args.get("target_path") or repo_path or "."
        request_id = new_request_id()
        rid = self._resolve_id(repo_id, repo_path)

        try:
            tester = Tester(db=self.orchestrator.db)
            req = CodeTesterRequest(
                target_path=target,
                action=sub_action,
                test_framework=args.get("test_framework", "auto"),
                test_filter=args.get("test_filter"),
                test_names=args.get("test_names"),
                categories=args.get("categories"),
                coverage_format=args.get("coverage_format", "summary"),
                target_symbol=args.get("target_symbol"),
                max_duration=args.get("max_duration", 300),
                async_mode=args.get("async_mode", False),
            )
            result = tester.run_tests(req)
            # Mark synced
            if rid:
                try:
                    FileIntegrity(self.orchestrator.db).mark_synced(rid, "test")
                except Exception:
                    pass
            return self._ok("Test complete", result, request_id=request_id)
        except Exception as e:
            return self._err(f"Test failed: {e}", "API_500", status_code=500)

    async def _cb_refactor(self, repo_id: Optional[str], args: Dict) -> Dict:
        if not repo_id:
            return self._err("repo_id required for refactor", "API_400")

        sub_action = args.get("sub_action", "rename")
        target_symbol = args.get("target_symbol")
        changes = args.get("changes", {})
        dry_run = args.get("dry_run", True)
        request_id = new_request_id()

        try:
            if sub_action == "impact":
                result = await self.orchestrator.refactor_service.analyze_impact(
                    repo_id, target_symbol, changes.get("source_file"),
                )
            elif sub_action == "rename":
                result = await self.orchestrator.refactor_service.rename_symbol(
                    repo_id, target_symbol, changes.get("source_file"),
                    changes.get("new_name"), dry_run=dry_run,
                )
            elif sub_action == "move":
                result = await self.orchestrator.refactor_service.move_code_element(
                    repo_id, target_symbol, changes.get("source_file"),
                    changes.get("target_file"), dry_run=dry_run,
                )
            elif sub_action == "extract":
                result = await self.orchestrator.refactor_service.extract_function(
                    repo_id, target_symbol, changes, dry_run=dry_run,
                )
            elif sub_action == "inline":
                result = await self.orchestrator.refactor_service.inline_function(
                    repo_id, target_symbol, changes, dry_run=dry_run,
                )
            elif sub_action == "signature":
                result = await self.orchestrator.refactor_service.change_signature(
                    repo_id, target_symbol, changes, dry_run=dry_run,
                )
            else:
                return self._err(f"Unknown refactor sub_action: {sub_action}", "API_400")

            return self._ok(f"Refactor {sub_action} {'preview' if dry_run else 'executed'}",
                            result, request_id=request_id)
        except Exception as e:
            return self._err(f"Refactor failed: {e}", "API_500", status_code=500)

    @staticmethod
    def _run_git_diagnostics(resolved: str, period: str, timeout: int) -> Dict:
        import subprocess
        result = {}
        try:
            subprocess.run(["git", "-C", resolved, "fetch", "--dry-run"],
                           capture_output=True, text=True, timeout=min(timeout, 30))
        except Exception:
            pass
        try:
            logs = subprocess.run(["git", "-C", resolved, "log", "--oneline", f"--since={period}"],
                                  capture_output=True, text=True, timeout=timeout)
            result["recent_commits"] = len(logs.stdout.strip().split("\n")) if logs.stdout.strip() else 0
        except Exception:
            pass
        try:
            status = subprocess.run(["git", "-C", resolved, "status", "--short"],
                                    capture_output=True, text=True, timeout=timeout)
            result["uncommitted"] = len(status.stdout.strip().split("\n")) if status.stdout.strip() else 0
        except Exception:
            pass
        return result
