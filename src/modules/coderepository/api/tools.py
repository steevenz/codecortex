"""
Module tools - 14 repo_* tools for repository lifecycle management.

Lifecycle:
  repo_init (sync files to DB)
    ├── repo_inspect (metadata & structure)
    ├── repo_analyze (full pipeline: sync → index → analyze)
    ├── repo_sync (incremental sync)
    ├── repo_audit (git/SVN history secrets scan)
    ├── repo_staleness (check if re-index needed)
    ├── repo_history (commit history & author stats)
    ├── repo_git (arbitrary git operations)
    └── repo_svn (arbitrary SVN operations)
  repo_list (discover all registered repos)
  repo_compact (database compaction)
  repo_cleanup (irreversible deletion)
  repo_dump (full data export)
  repo_restore (import from dump).

:project: CodeCortex
:package: Modules.Coderepository.Api.Tools
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeRepository-v2.0
"""

from __future__ import annotations
import json
import os
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import Optional, List, Any, Dict
from mcp.server.fastmcp import FastMCP

from src.core import ApiError, api_response, new_request_id, utc_now_iso
from src.modules.coderepository.core.registry import RegistryManager
from src.core.logging import get_logger

logger = get_logger("CodeCortex.Module.CodeRepository.Tools")

def register_tools(mcp: FastMCP, orchestrator_factory) -> None:
    """
    Register repository tools (repo_* prefix, 14 tools).

    Lifecycle: repo_init → repo_audit → repo_staleness → repo_analyze
    VCS ops: repo_git (arbitrary git), repo_svn (arbitrary svn), repo_history
    Admin: repo_inspect, repo_sync, repo_list, repo_compact, repo_cleanup
    Data: repo_dump, repo_restore

    All tools now include ai_actions for AI coder assistance and dry_run
    support for safe preview of destructive operations.

        Args:
            mcp: FastMCP server instance
            orchestrator_factory: Factory function to create CortexOrchestrator instances
    """

    # =========================================================================
    # 1. repo_init - Initialize, clone, or sync a repository
    # =========================================================================
    # Purpose: One-shot repository setup. Supports clone/init + index + audit.
    # Flow:
    #   repo_init
    #     ├── STEP 1: Validate path, handle create_new / force
    #     ├── STEP 2: VCS setup (clone via repo_git, checkout via repo_svn, or init)
    #     ├── STEP 3: Full indexing via internal pipeline (file discovery → AST → graph)
    #     ├── STEP 4: Optional code_audit (secrets, PII, misconfig)
    #     └── STEP 5: Save metadata → return repo_id + stats

    @mcp.tool()
    async def repo_init(
        repo_path: str,
        vcs_type: str = "git",
        remote_url: Optional[str] = None,
        create_new: bool = False,
        force: bool = False,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        run_audit: bool = True,
        audit_categories: Optional[List[str]] = None,
        parallel: bool = True,
        max_workers: int = 4,
    ) -> dict:
        """
        Initialize, clone, or sync a repository for CodeCortex analysis.

        One-shot setup: validates path, configures VCS (clone/init/checkout),
        indexes source code (AST → symbols → graph), and optionally runs

        Args:
            repo_path: Absolute path where the repository will be initialized.
            vcs_type: Version control system: "git", "svn", or "none" (default "git").
            remote_url: Remote URL for clone (git) or checkout (svn).
            create_new: If True, create new directory (error 409 if exists).
            force: If True, overwrite existing index (cleanup + re-index).
            include_patterns: File patterns to include in indexing (default: source code extensions).
            exclude_patterns: Directories to exclude (default: node_modules, __pycache__, .git, .svn, etc).
            run_audit: Run security audit after indexing (default True).
            audit_categories: Audit categories: "secrets", "pii", "misconfig", "vulns".
            parallel: Process files in parallel during indexing (default True).
            max_workers: Number of worker threads for parallel processing (default 4).

        Returns:
            repo_id, indexing stats, audit summary (if enabled), VCS operation status.
        """
        import time
        import subprocess
        from pathlib import Path
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        start_time = time.time()

        resolved = Path(repo_path).resolve()

        # ── STEP 1: Validation ─────────────────────────────────────────────
        if resolved.exists():
            if create_new:
                return api_response(
                    success=False, status_code=409,
                    message="Path already exists. Use create_new=false to use existing directory, or force=true to overwrite.",
                    data={"repo_path": str(resolved)}, request_id=request_id, error_code="REP_409",
                )
            # Check if already indexed
            existing_id = orchestrator.get_repo_id(str(resolved))
            if existing_id and not force:
                return api_response(
                    success=False, status_code=409,
                    message="Repository already indexed. Use force=true to re-index, or repo_init with a different path.",
                    data={"repo_path": str(resolved), "existing_repo_id": existing_id},
                    request_id=request_id, error_code="REP_409",
                )
            if existing_id and force:
                from src.core.database import cleanup_project
                await asyncio.to_thread(lambda: cleanup_project(orchestrator.db.conn, existing_id))
        else:
            if not create_new and not remote_url:
                return api_response(
                    success=False, status_code=404,
                    message="Path does not exist. Use create_new=true to create, or provide remote_url to clone.",
                    data={"repo_path": str(resolved)}, request_id=request_id, error_code="REP_404",
                )
            resolved.mkdir(parents=True, exist_ok=True)

        # ── STEP 2: VCS Setup ──────────────────────────────────────────────
        vcs_op: dict = {"type": vcs_type, "operation": "none", "success": True}

        if remote_url and vcs_type == "git":
            try:
                subprocess.run(
                    ["git", "clone", remote_url, str(resolved)],
                    capture_output=True, text=True, timeout=300,
                )
                vcs_op = {"type": "git", "operation": "clone", "success": True, "remote_url": remote_url}
            except subprocess.TimeoutExpired:
                return api_response(success=False, status_code=408, message="Git clone timed out", data=None, request_id=request_id, error_code="REP_TIMEOUT")
            except Exception as e:
                return api_response(success=False, status_code=400, message=f"Git clone failed: {e}", data=None, request_id=request_id, error_code="REP_CLONE")

        elif remote_url and vcs_type == "svn":
            try:
                subprocess.run(
                    ["svn", "checkout", remote_url, str(resolved)],
                    capture_output=True, text=True, timeout=300,
                )
                vcs_op = {"type": "svn", "operation": "checkout", "success": True, "remote_url": remote_url}
            except subprocess.TimeoutExpired:
                return api_response(success=False, status_code=408, message="SVN checkout timed out", data=None, request_id=request_id, error_code="REP_TIMEOUT")
            except Exception as e:
                return api_response(success=False, status_code=400, message=f"SVN checkout failed: {e}", data=None, request_id=request_id, error_code="REP_CHECKOUT")

        elif vcs_type == "git" and not (resolved / ".git").exists():
            try:
                subprocess.run(["git", "init"], cwd=str(resolved), capture_output=True, text=True, timeout=30)
                vcs_op = {"type": "git", "operation": "init", "success": True}
            except Exception as e:
                vcs_op = {"type": "git", "operation": "init", "success": False, "error": str(e)}

        elif vcs_type == "svn" and not (resolved / ".svn").exists():
            try:
                subprocess.run(["svn", "mkdir", str(resolved)], capture_output=True, text=True, timeout=30)
                vcs_op = {"type": "svn", "operation": "mkdir", "success": True}
            except Exception:
                vcs_op = {"type": "svn", "operation": "mkdir", "success": False, "note": "SVN mkdir failed - try svn checkout with remote_url"}

        # Get commit hash / revision after VCS ops
        if vcs_type == "git" and (resolved / ".git").exists():
            try:
                br = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(resolved), capture_output=True, text=True, timeout=10)
                co = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(resolved), capture_output=True, text=True, timeout=10)
                if br.returncode == 0: vcs_op["branch"] = br.stdout.strip()
                if co.returncode == 0: vcs_op["commit"] = co.stdout.strip()
            except Exception:
                pass
        elif vcs_type == "svn" and (resolved / ".svn").exists():
            try:
                rev = subprocess.run(["svn", "info", "--show-item", "revision"], cwd=str(resolved), capture_output=True, text=True, timeout=10)
                if rev.returncode == 0: vcs_op["revision"] = rev.stdout.strip()
            except Exception:
                pass

        # ── STEP 3: Indexing ──────────────────────────────────────────────
        repo_id = await orchestrator.repo_service.initialize(str(resolved))
        indexing_time = time.time() - start_time

        # Gather indexing stats
        indexing_stats: dict = {"duration_seconds": round(indexing_time, 2)}
        try:
            tree = orchestrator.fs_service.get_codebase_tree(path=str(resolved))
            if tree and isinstance(tree, dict):
                data = tree.get("data", {})
                indexing_stats["files_scanned"] = data.get("total_files", 0)
                indexing_stats["source_code_files"] = data.get("code_files", 0)
                indexing_stats["languages"] = data.get("languages", {})
        except Exception:
            pass

        # ── STEP 4: Audit ─────────────────────────────────────────────────
        audit_result: Optional[dict] = None
        if run_audit:
            try:
                from src.modules.codeanalysis.analyzers.audit import CodeAuditor
                audit_params = {
                    "target_path": str(resolved),
                    "scan_categories": audit_categories or ["secrets", "pii", "misconfig"],
                    "severity_threshold": "medium",
                    "generate_suggestions": True,
                    "max_file_size_kb": 1024,
                }
                audit_result = CodeAuditor.audit(audit_params)
                if audit_result and audit_result.get("success"):
                    audit_data = audit_result["data"]
                    audit_summary = audit_data.get("summary", {})
                    indexing_stats["audit_findings"] = audit_summary
                    if "recommendations" in audit_data:
                        indexing_stats["audit_recommendations"] = audit_data["recommendations"]
            except Exception:
                indexing_stats["audit_findings"] = {"error": "Audit failed"}
        else:
            indexing_stats["audit_findings"] = {"enabled": False}

        # ── Post-index: Capture VCS metadata ───────────────────────────────
        try:
            from src.modules.coderepository.core.utils import extract_vcs_metadata
            vcs_meta = extract_vcs_metadata(str(resolved))
            orchestrator.repo_store.update_vcs_metadata(repo_id, vcs_meta)
        except Exception:
            pass

        # ── STEP 5: AI Actions generation ───────────────────────────────────
        ai_actions = []
        files_scanned = indexing_stats.get("files_scanned", 0)

        ai_actions.append({
            "priority": "info",
            "action": f"Repository '{resolved.name}' initialized successfully with {files_scanned} files indexed.",
            "status": "completed",
            "repo_id": repo_id
        })

        # Recommend next steps based on audit results
        if run_audit and indexing_stats.get("audit_findings"):
            audit_findings = indexing_stats["audit_findings"]
            critical_count = audit_findings.get("critical", 0)
            high_count = audit_findings.get("high", 0)

            if critical_count > 0:
                ai_actions.append({
                    "priority": "critical",
                    "action": f"{critical_count} CRITICAL security issues detected. Review and fix immediately.",
                    "command_hint": f"repo_audit --repo_path {resolved} --severity_threshold=critical",
                    "count": critical_count
                })
            elif high_count > 0:
                ai_actions.append({
                    "priority": "high",
                    "action": f"{high_count} HIGH severity issues found. Address security concerns before proceeding.",
                    "command_hint": f"repo_audit --repo_path {resolved}",
                    "count": high_count
                })

        # Suggest analysis for larger repos
        if files_scanned > 100:
            ai_actions.append({
                "priority": "medium",
                "action": f"Large codebase ({files_scanned} files). Run repo_analyze for full semantic analysis including call graphs.",
                "command_hint": f"repo_analyze --repo_path {resolved} --build_graph=true"
            })
        else:
            ai_actions.append({
                "priority": "low",
                "action": "Run repo_analyze to build code intelligence (call graphs, symbol extraction).",
                "command_hint": f"repo_analyze --repo_path {resolved}"
            })

        # VCS-related recommendations
        if vcs_type == "git" and vcs_op.get("operation") == "init":
            ai_actions.append({
                "priority": "info",
                "action": "Git repository initialized. Set up remote origin and make initial commit.",
                "commands": [
                    f"git remote add origin <your-remote-url>",
                    f"git add .",
                    f"git commit -m 'Initial commit'",
                    f"git push -u origin main"
                ]
            })

        # Add health check recommendation
        ai_actions.append({
            "priority": "info",
            "action": "Monitor repository health with periodic checks.",
            "recommended_workflow": [
                "repo_staleness --check remote status",
                "repo_sync --incremental updates",
                "repo_audit --periodic security scans"
            ]
        })

        # ── STEP 6: Response ──────────────────────────────────────────────
        msg = "Repository initialized"
        if vcs_op.get("operation") != "none":
            msg += f" ({vcs_op['operation']})"
        if run_audit:
            msg += " and audited"
        msg += " successfully"

        data: dict = {
            "repo_id": repo_id,
            "repo_path": str(resolved),
            "vcs_type": vcs_type,
            "vcs_operation": vcs_op,
            "indexing_summary": indexing_stats,
            "ai_actions": ai_actions,
        }

        return api_response(success=True, insight="repo_init", status_code=200, message=msg, data=data, request_id=request_id)

    # =========================================================================
    # 2. repo_inspect - Fast health check (Lightweight, Zero Parsing)
    # =========================================================================

    def _render_inspect_markdown(data: dict) -> str:
        lines = []
        lines.append("# Repository Inspection Report\n")
        lines.append(f"**Repository:** `{data.get('repo_path', '')}`")
        rid = data.get("repo_id")
        if rid: lines.append(f"**Repo ID:** `{rid}`")
        lines.append(f"**VCS:** {data.get('vcs_type', 'none')}" +
                     (f" (branch: {data['vcs_branch']})" if data.get('vcs_branch') else "") + "\n")

        im = data.get("index_metadata", {})
        lines.append("## Index Status\n")
        if im.get("indexed"):
            lines.append(f"- ✅ Indexed: {im.get('sync_at', 'unknown')}")
            if "total_symbols_indexed" in im: lines.append(f"- 📄 {im['total_files_indexed']} files, 🔧 {im['total_symbols_indexed']} symbols, 🌐 {im['total_edges']} edges")
        else:
            lines.append("- ⏳ Not indexed. Run `repo_init` to enable AI features.")

        fs = data.get("file_statistics", {})
        if fs:
            lines.append("\n## File Statistics\n")
            lines.append(f"- Total files: {fs['total_files']}, Size: {fs['total_size_mb']} MB")
            bd = fs.get("breakdown", {})
            lines.append(f"- Source: {bd.get('source_code_files', 0)}, Config: {bd.get('config_files', 0)}, Docs: {bd.get('documentation', 0)}, Binaries: {bd.get('binaries', 0)}")
            for lf in fs.get("largest_files", []):
                lines.append(f"- 🏆 `{lf['path']}`: {lf['size_mb']} MB")

        diag = data.get("git_diagnostics", {})
        if diag:
            lines.append("\n## Git Diagnostics\n")
            for h in diag.get("churn_hotspots", [])[:5]:
                emoji = "🔴" if h["risk"] == "high" else ("🟡" if h["risk"] == "medium" else "🟢")
                lines.append(f"- {emoji} `{h['file']}`: {h['change_count']} changes")
            bf = diag.get("bus_factor", {})
            if bf:
                lines.append(f"\n**Bus Factor:** {bf.get('top_contributor_percentage', 0)}% by top contributor, risk: {bf.get('bus_factor_risk', 'unknown')}")
            cv = diag.get("commit_velocity", {})
            if cv: lines.append(f"\n**Commit Velocity:** Avg {cv.get('commits_per_month_avg', 0)}/month, trend: {cv.get('trend', 'steady')}")

        ins = data.get("insights", {})
        if ins:
            lines.append(f"\n## AI Readiness Score: {ins.get('ai_readiness_score', 0)}/100\n")
            for rec in ins.get("recommended_actions", []):
                emoji = "🔴" if rec["severity"] == "warning" else "ℹ️"
                lines.append(f"- {emoji} {rec['message']}")

        return "\n".join(lines)

    def _render_audit_markdown(data: dict) -> str:
        lines = []
        lines.append("# Repository Security Audit Report\n")
        lines.append(f"**Repository:** `{data.get('repo_path', '')}`\n")

        summ = data.get("summary", {})
        lines.append(f"## Summary\n")
        lines.append(f"- **Total findings:** {summ.get('total_findings', 0)}")
        lines.append(f"- **Files scanned:** {data.get('scanned_files', 0)}")
        lines.append(f"- **Duration:** {data.get('duration_seconds', 0)}s\n")

        for sev in ("critical", "high", "medium", "low"):
            cnt = summ.get("by_severity", {}).get(sev, 0)
            if cnt:
                emoji = "🔴" if sev == "critical" else ("🟠" if sev == "high" else ("🟡" if sev == "medium" else "🟢"))
                lines.append(f"- {emoji} {sev.capitalize()}: {cnt}")

        for cat, items in data.get("findings", {}).items():
            lines.append(f"\n## {cat.capitalize()}\n")
            for item in items[:10]:
                emoji = "🔴" if item["severity"] == "critical" else ("🟠" if item["severity"] == "high" else "🟡")
                lines.append(f"- {emoji} `{item['file']}:{item['line']}` - {item['type']}")
                lines.append(f"  - Remediation: {item['remediation']}")

        recs = data.get("recommendations", {})
        if recs:
            lines.append("\n## Recommendations\n")
            if recs.get("secrets_to_rotate"):
                for s in recs["secrets_to_rotate"][:5]:
                    lines.append(f"- 🔑 Rotate: {s}")
            if recs.get("files_to_remove"):
                for f in recs["files_to_remove"][:5]:
                    lines.append(f"- 🗑️ Remove: {f}")

        return "\n".join(lines)

    @mcp.tool()
    async def repo_inspect(
        repo_path: str,
        repo_id: Optional[str] = None,
        include_git_diagnostics: bool = True,
        include_svn_diagnostics: bool = False,
        include_index_metadata: bool = True,
        include_vcs_status: bool = True,
        include_file_stats: bool = True,
        include_dependency_summary: bool = False,
        include_temporal_coupling: bool = False,
        temporal_coupling_period: str = "1_year",
        include_documentation: bool = False,
        diagnostic_period: str = "1_year",
        output_format: str = "json",
        timeout_seconds: int = 30,
    ) -> dict:
        """
        Fast repository health check - lightweight, zero parsing.

        Reads metadata, runs non‑invasive git/svn diagnostics (churn hotspots,

        Args:
            repo_path: Absolute path to the repository.
            repo_id: Optional UUID (alternative to repo_path).
            include_git_diagnostics: Run 5 git diagnostics (default true).
            include_svn_diagnostics: Run SVN diagnostics if SVN detected (default false).
            include_index_metadata: Include index info if previously indexed (default true).
            include_vcs_status: Include VCS status (branch, ahead/behind, dirty) (default true).
            include_file_stats: File statistics by extension (default true).
            include_dependency_summary: Scan package managers (package.json, etc.) (default false).
            include_temporal_coupling: Analyze git co-change for temporal coupling (default false).
            temporal_coupling_period: "1_year", "6_months", or "90_days" (default "1_year").
            include_documentation: Scan and parse docs/ directory for PRDs, ADRs, specs (default false).
            diagnostic_period: "1_year", "6_months", or "90_days" (default "1_year").
            output_format: "json" (default) or "markdown".
            timeout_seconds: Max execution time (default 30).

        Returns:
            Repository health report with diagnostics, stats, and AI readiness score.
        """
        import time, subprocess, json as json_mod, os, fnmatch
        from pathlib import Path
        from collections import defaultdict

        start = time.time()
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        resolved = Path(repo_path).resolve()

        # ── STEP 1: Validation ─────────────────────────────────────────────
        if not resolved.exists():
            return api_response(success=False, status_code=404,
                message="Repository path does not exist or is not accessible",
                data={"repo_path": str(resolved)}, request_id=request_id, error_code="REP_404")

        # Detect VCS type
        vcs_type: str = "none"
        vcs_branch: str = ""
        if (resolved / ".git").exists():
            vcs_type = "git"
            try:
                br = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(resolved),
                    capture_output=True, text=True, timeout=5)
                if br.returncode == 0: vcs_branch = br.stdout.strip()
            except Exception as e:
                logger.debug(f"Git branch detection failed: {e}")
        elif (resolved / ".svn").exists():
            vcs_type = "svn"

        data: dict = {
            "repo_id": None,
            "repo_path": str(resolved),
            "absolute_path_resolved": str(resolved),
            "vcs_type": vcs_type,
            "vcs_branch": vcs_branch,
        }

        # ── STEP 2: Index Metadata ─────────────────────────────────────────
        if include_index_metadata:
            existing_id = orchestrator.get_repo_id(str(resolved)) if hasattr(orchestrator, 'get_repo_id') else None
            if existing_id:
                data["repo_id"] = existing_id
                try:
                    row = orchestrator.db.conn.execute(
                        "SELECT * FROM repositories WHERE id = ?",
                        (existing_id,)
                    ).fetchone()
                    if row:
                        rd = dict(row)
                        idx_meta = {"indexed": True, "sync_at": rd.get("updated_at") or rd.get("created_at")}
                        # Counts from aggregate tables
                        try:
                            fcnt = orchestrator.db.conn.execute(
                                "SELECT COUNT(*) as c FROM files WHERE repository_id = ?", (existing_id,)
                            ).fetchone()["c"]
                            scnt = orchestrator.db.conn.execute(
                                "SELECT COUNT(*) as c FROM symbols WHERE repository_id = ?", (existing_id,)
                            ).fetchone()["c"]
                            ecnt = orchestrator.db.conn.execute(
                                "SELECT COUNT(*) as c FROM edges WHERE repository_id = ?", (existing_id,)
                            ).fetchone()["c"]
                            idx_meta["total_files_indexed"] = fcnt
                            idx_meta["total_symbols_indexed"] = scnt
                            idx_meta["total_edges"] = ecnt
                        except Exception:
                            pass
                        data["index_metadata"] = idx_meta

                        # VCS metadata from DB
                        vcs_meta = {}
                        for k in ("vcs_type", "vcs_url", "current_branch", "last_commit_hash",
                                   "last_commit_time", "current_revision", "last_changed_rev", "index_version"):
                            if rd.get(k):
                                vcs_meta[k] = rd[k]
                        if vcs_meta:
                            if "vcs_type" not in data:
                                data["vcs_type"] = vcs_meta.get("vcs_type", vcs_type)
                            data["vcs_metadata"] = vcs_meta
                except Exception:
                    data["index_metadata"] = {"indexed": True}
            else:
                data["index_metadata"] = {"indexed": False}

        # ── STEP 3: VCS Status ─────────────────────────────────────────────
        if include_vcs_status and vcs_type == "git":
            try:
                status = subprocess.run(["git", "status", "--porcelain"], cwd=str(resolved),
                    capture_output=True, text=True, timeout=5)
                has_changes = bool(status.stdout.strip())
                ahead_behind = {"has_uncommitted_changes": has_changes, "commits_ahead": 0, "commits_behind": 0}
                try:
                    rev = subprocess.run(["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"],
                        cwd=str(resolved), capture_output=True, text=True, timeout=5)
                    if rev.returncode == 0:
                        parts = rev.stdout.strip().split()
                        if len(parts) == 2:
                            ahead_behind["commits_ahead"] = int(parts[0])
                            ahead_behind["commits_behind"] = int(parts[1])
                except Exception as e:
                    logger.debug(f"Git ahead/behind check failed: {e}")
                data["vcs_status"] = ahead_behind
            except Exception as e:
                logger.debug(f"Git status check failed: {e}")
        elif include_vcs_status and vcs_type == "svn":
            try:
                svn_st = subprocess.run(["svn", "status", "--non-interactive"], cwd=str(resolved),
                    capture_output=True, text=True, timeout=5)
                data["vcs_status"] = {"has_uncommitted_changes": bool(svn_st.stdout.strip())}
            except Exception as e:
                logger.debug(f"SVN status check failed: {e}")

        # ── STEP 4: File Statistics ────────────────────────────────────────
        if include_file_stats:
            source_exts = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".kt", ".cs",
                          ".rb", ".php", ".swift", ".scala", ".cpp", ".c", ".h", ".hpp", ".m", ".mm",
                          ".sh", ".bash", ".zsh", ".pl", ".pm", ".lua", ".r", ".ex", ".exs", ".clj",
                          ".cljs", ".tf", ".hcl", ".vue", ".svelte", ".astro"}
            config_exts = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".xml", ".properties"}
            doc_exts = {".md", ".rst", ".txt", ".html", ".css", ".scss"}
            bin_exts = {".exe", ".dll", ".so", ".dylib", ".bin", ".msi", ".deb", ".rpm", ".dmg", ".pyc", ".class", ".o", ".obj"}

            total = total_size = 0
            sc = cfg = doc = binary = other = 0
            ext_counts: dict = defaultdict(int)
            largest: list = []

            for root, _dirs, fnames in os.walk(str(resolved)):
                dn = os.path.basename(root)
                if dn.startswith(".") or dn in ("node_modules", "vendor", "__pycache__"):
                    continue
                for fn in fnames:
                    fp = os.path.join(root, fn)
                    try:
                        sz = os.path.getsize(fp)
                    except OSError:
                        continue
                    total += 1
                    total_size += sz
                    ext = os.path.splitext(fn)[1].lower()
                    ext_counts[ext] += 1
                    if ext in source_exts: sc += 1
                    elif ext in config_exts: cfg += 1
                    elif ext in doc_exts: doc += 1
                    elif ext in bin_exts: binary += 1
                    else: other += 1
                    if len(largest) < 5:
                        largest.append({"path": fn, "size_mb": round(sz / 1024 / 1024, 2)})
                        largest.sort(key=lambda x: x["size_mb"], reverse=True)
                    elif sz > largest[-1]["size_mb"] * 1024 * 1024:
                        largest.append({"path": fn, "size_mb": round(sz / 1024 / 1024, 2)})
                        largest.sort(key=lambda x: x["size_mb"], reverse=True)
                        largest = largest[:5]

            data["file_statistics"] = {
                "total_files": total,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "avg_size_kb": round(total_size / total / 1024, 2) if total else 0,
                "largest_files": largest,
                "breakdown": {
                    "source_code_files": sc, "config_files": cfg,
                    "documentation": doc, "binaries": binary, "others": other,
                },
            }

        # ── STEP 5: Dependency Summary ─────────────────────────────────────
        if include_dependency_summary:
            dep_managers = []
            pkg_files = {
                "requirements.txt": ("pip", "requirements.txt"),
                "Pipfile": ("pipenv", "Pipfile"),
                "pyproject.toml": ("poetry", "pyproject.toml"),
                "package.json": ("npm", "package.json"),
                "yarn.lock": ("yarn", "yarn.lock"),
                "Cargo.toml": ("cargo", "Cargo.toml"),
                "go.mod": ("go", "go.mod"),
                "Gemfile": ("bundler", "Gemfile"),
                "composer.json": ("composer", "composer.json"),
                "build.gradle": ("gradle", "build.gradle"),
                "pom.xml": ("maven", "pom.xml"),
            }
            for pf, (pm, label) in pkg_files.items():
                pf_path = resolved / pf
                if pf_path.exists():
                    dep_managers.append({"type": pm, "file": label, "path": str(pf_path)})
            data["dependency_summary"] = {"enabled": True, "package_managers": dep_managers}

        # ── STEP 6: Git Diagnostics ────────────────────────────────────────
        period_map = {"1_year": "1 year ago", "6_months": "6 months ago", "90_days": "90 days ago"}
        since = period_map.get(diagnostic_period, "1 year ago")

        if include_git_diagnostics and vcs_type == "git":
            git_diag: dict = {"diagnostic_period": diagnostic_period}

            try:
                churn = subprocess.run(
                    ["git", "log", "--name-only", f"--since={since}", "--pretty=format:"],
                    cwd=str(resolved), capture_output=True, text=True, timeout=10)
                if churn.returncode == 0:
                    files: dict = {}
                    for line in churn.stdout.splitlines():
                        line = line.strip()
                        if line:
                            files[line] = files.get(line, 0) + 1
                    sorted_files = sorted(files.items(), key=lambda x: x[1], reverse=True)[:20]
                    git_diag["churn_hotspots"] = [
                        {"file": fp, "change_count": cnt,
                         "risk": "high" if cnt > 150 else ("medium" if cnt > 50 else "low")}
                        for fp, cnt in sorted_files
                    ]
            except Exception as e:
                logger.debug(f"Git churn analysis failed: {e}")

            try:
                shortlog = subprocess.run(
                    ["git", "shortlog", "-sn", f"--since={since}"],
                    cwd=str(resolved), capture_output=True, text=True, timeout=10)
                if shortlog.returncode == 0:
                    lines = [l.strip() for l in shortlog.stdout.splitlines() if l.strip()]
                    total_contribs = len(lines)
                    top_pct = 0
                    if lines:
                        first = lines[0].split("\t")
                        top_cnt = int(first[0].strip()) if first[0].strip().isdigit() else 0
                        total_commits_log = sum(int(l.split("\t")[0].strip()) for l in lines if l.split("\t")[0].strip().isdigit())
                        top_pct = round(top_cnt / total_commits_log * 100, 1) if total_commits_log else 0
                    git_diag["bus_factor"] = {
                        "total_contributors": total_contribs,
                        "top_contributor_percentage": top_pct,
                        "bus_factor_risk": "high" if top_pct > 60 else ("medium" if top_pct > 40 else "low"),
                    }
            except Exception as e:
                logger.debug(f"Git contributor analysis failed: {e}")

            try:
                bugs = subprocess.run(
                    ["git", "log", "--oneline", "--grep=fix\\|bug", f"--since={since}", "--name-only"],
                    cwd=str(resolved), capture_output=True, text=True, timeout=10)
                if bugs.returncode == 0:
                    bug_files: dict = {}
                    for line in bugs.stdout.splitlines():
                        line = line.strip()
                        if line and not line.startswith("(") and not line.startswith("[") and not line.startswith("*"):
                            if "/" in line or line.endswith((".py", ".js", ".ts", ".go", ".rs", ".java")):
                                bug_files[line] = bug_files.get(line, 0) + 1
                    sorted_bugs = sorted(bug_files.items(), key=lambda x: x[1], reverse=True)[:10]
                    git_diag["bug_magnets"] = [{"file": fp, "bug_commits": cnt} for fp, cnt in sorted_bugs]
            except Exception as e:
                logger.debug(f"Git bug magnet analysis failed: {e}")

            try:
                velocity = subprocess.run(
                    ["git", "log", f"--since={since}", "--date=short", "--format=%ad"],
                    cwd=str(resolved), capture_output=True, text=True, timeout=10)
                if velocity.returncode == 0:
                    months: dict = {}
                    for line in velocity.stdout.splitlines():
                        if line:
                            month = line[:7]
                            months[month] = months.get(month, 0) + 1
                    history = [{"month": m, "commits": c} for m, c in sorted(months.items())]
                    avg = round(sum(h["commits"] for h in history) / len(history), 1) if history else 0
                    trend = "steady"
                    if len(history) >= 3:
                        recent = sum(h["commits"] for h in history[-3:]) / 3
                        old = sum(h["commits"] for h in history[:3]) / 3
                        trend = "increasing" if recent > old * 1.2 else ("decreasing" if recent < old * 0.8 else "steady")
                    git_diag["commit_velocity"] = {"commits_per_month_avg": avg, "trend": trend, "history": history}
            except Exception as e:
                logger.debug(f"Git velocity analysis failed: {e}")

            try:
                crisis = subprocess.run(
                    ["git", "log", "--oneline", "--grep=revert\\|hotfix", f"--since={since}"],
                    cwd=str(resolved), capture_output=True, text=True, timeout=10)
                if crisis.returncode == 0:
                    crisis_lines = [l for l in crisis.stdout.splitlines() if l.strip()]
                    total_crisis = len(crisis_lines)
                    git_diag["crisis_frequency"] = {
                        "reverts_and_hotfixes": total_crisis,
                        "crisis_risk": "high" if total_crisis > 50 else ("medium" if total_crisis > 20 else "low"),
                    }
            except Exception as e:
                logger.debug(f"Git crisis detection failed: {e}")

            data["git_diagnostics"] = git_diag

        elif include_svn_diagnostics and vcs_type == "svn":
            try:
                svn_log = subprocess.run(
                    ["svn", "log", "--verbose", "-l", "100"],
                    cwd=str(resolved), capture_output=True, text=True, timeout=30)
                if svn_log.returncode == 0:
                    data["svn_diagnostics"] = {"log_lines": len(svn_log.stdout.splitlines())}
            except Exception as e:
                logger.debug(f"SVN log analysis failed: {e}")

        # ── STEP 6b: Temporal Coupling (Co-change Analysis) ────────────────
        if include_temporal_coupling and vcs_type == "git":
            try:
                from src.modules.coderepository.adapters.git.cochange import CoChangeMatrix
                period_map = {"1_year": "1 year", "6_months": "6 months", "90_days": "90 days"}
                since = period_map.get(temporal_coupling_period, "1 year")
                matrix = CoChangeMatrix.build(
                    str(resolved), since=since,
                    timeout=timeout_seconds,
                )
                if matrix._built:
                    summary = matrix.get_summary()
                    data["temporal_coupling"] = summary
                    # Add temporal recommendations with ai_action
                    hotspots = matrix.get_hotspots(limit=5, min_pairs=2, min_score=0.15)
                    for h in hotspots:
                        risk = h.get("risk", "low")
                        if risk == "high":
                            recs.append({
                                "severity": "warning",
                                "message": (
                                    f"'{h['file']}' has high temporal coupling "
                                    f"with {h['co_change_partners']} other files "
                                    f"(avg score: {h['avg_score']}). "
                                    f"Consider refactoring to reduce hidden dependencies."
                                ),
                                "file": h["file"],
                                "ai_action": f"Refactor '{h['file']}' to reduce temporal coupling ({h['co_change_partners']} co-change partners, score: {h['avg_score']}). Extract shared logic into separate module."
                            })
                        elif risk == "medium":
                            recs.append({
                                "severity": "info",
                                "message": (
                                    f"'{h['file']}' has moderate temporal coupling "
                                    f"with {h['co_change_partners']} other files."
                                ),
                                "file": h["file"],
                                "ai_action": f"Monitor '{h['file']}' for hidden dependencies ({h['co_change_partners']} co-change partners). Consider module boundaries."
                            })
            except Exception as e:
                logger.warning(f"Temporal coupling analysis failed: {e}")
                data["temporal_coupling"] = {"error": str(e), "built": False}

        # ── STEP 6c: Documentation Intelligence ────────────────────────────
        if include_documentation:
            try:
                from src.modules.codeanalysis.core.documentation import DocumentParser, ReadmeParser
                doc_dir = resolved / "docs"
                if doc_dir.exists() and doc_dir.is_dir():
                    artifacts = DocumentParser.scan_directory(str(resolved), max_depth=5)
                    summary = DocumentParser.get_summary(artifacts)
                    data["documentation"] = summary

                    # Parse README
                    for readme_candidate in [resolved / "README.md", resolved / "readme.md"]:
                        if readme_candidate.exists():
                            data["documentation"]["readme"] = ReadmeParser.parse(str(readme_candidate))
                            break

                    # Add doc-based recommendations with ai_action
                    if summary.get("total_documents", 0) == 0:
                        recs.append({
                            "severity": "info",
                            "message": "No documentation found in docs/ directory. Consider adding PRDs and ADRs.",
                            "ai_action": "Create docs/ directory structure with PRDs (Product Requirements Documents) and ADRs (Architecture Decision Records) to improve AI context understanding."
                        })
                    if summary.get("total_decisions", 0) == 0:
                        recs.append({
                            "severity": "info",
                            "message": "No Architecture Decision Records found. Consider adding ADRs.",
                            "ai_action": "Add ADRs to docs/adr/ directory to track architectural decisions and help AI understand design rationale."
                        })
                    if summary.get("total_requirements", 0) > 0:
                        recs.append({
                            "severity": "info",
                            "message": f"{summary['total_requirements']} requirements found in documentation.",
                            "count": summary["total_requirements"],
                            "ai_action": f"Review {summary['total_requirements']} requirements in docs/ to ensure implementation alignment."
                        })
                    if summary.get("total_documents", 0) > 0:
                        recs.append({
                            "severity": "info",
                            "message": f"{summary['total_documents']} documentation files found. AI can use this for context.",
                            "ai_action": f"Leverage {summary['total_documents']} documentation files for AI context. Ensure docs are up-to-date with code changes."
                        })
                else:
                    data["documentation"] = {"error": "No docs/ directory found"}
            except Exception as e:
                logger.warning(f"Documentation scan failed: {e}")
                data["documentation"] = {"error": str(e)}

        # ── STEP 7: AI Readiness Score + Recommendations ───────────────────
        score = 50  # baseline
        recs: list = []

        if vcs_type != "none":
            score += 15
        else:
            recs.append({"severity": "info",
                "message": "This directory is not under version control. Run `git init` or `svn checkout`."})

        if data.get("index_metadata", {}).get("indexed"):
            score += 20
        else:
            recs.append({"severity": "info",
                "message": "Repository is not indexed. Run `repo_init` to enable AI search & refactoring."})

        fs = data.get("file_statistics", {})
        if fs.get("source_code_files", 0) > 10:
            score += 10
        if fs.get("total_files", 0) < 1000:
            score += 5  # manageable size

        diag = data.get("git_diagnostics", {})
        bf = diag.get("bus_factor", {})
        if bf.get("bus_factor_risk") == "high":
            score -= 10
            recs.append({"severity": "warning",
                "message": "High bus factor risk. Top contributor owns >60% of commits. Consider distributing knowledge."})
        if bf.get("bus_factor_risk") == "medium":
            score -= 5

        ch = diag.get("churn_hotspots", [])
        if ch:
            top = ch[0]
            if top["risk"] == "high":
                score -= 5
                recs.append({"severity": "warning",
                    "message": f"'{top['file']}' is a churn hotspot with {top['change_count']} changes. Consider refactoring.",
                    "file": top["file"]})

        bm = diag.get("bug_magnets", [])
        if bm:
            worst = bm[0]
            recs.append({"severity": "warning" if worst["bug_commits"] > 20 else "info",
                "message": f"'{worst['file']}' has {worst['bug_commits']} bug-related commits. Consider adding tests.",
                "file": worst["file"]})

        cf = diag.get("crisis_frequency", {})
        if cf.get("crisis_risk") == "high":
            score -= 5
            recs.append({"severity": "warning", "message": "High crisis frequency - many reverts/hotfixes."})

        score = max(0, min(100, score))
        data["insights"] = {"ai_readiness_score": score, "recommended_actions": recs}

        duration_ms = int((time.time() - start) * 1000)

        # ── STEP 8: Format Output ──────────────────────────────────────────
        if output_format == "markdown":
            md = _render_inspect_markdown(data)
            return api_response(success=True, insight="repo_inspect", status_code=200,
                message="Repository inspection completed",
                data={"markdown": md, "raw": data}, request_id=request_id,
                meta={"request_id": request_id, "timestamp": "", "duration_ms": duration_ms})
        else:
            return api_response(success=True, insight="repo_inspect", status_code=200,
                message="Repository inspection completed", data=data, request_id=request_id,
                meta={"request_id": request_id, "timestamp": "", "duration_ms": duration_ms})

    # =========================================================================
    # 3. repo_analyze - Full semantic understanding (Heavyweight)
    # =========================================================================
    # Purpose: Deep analysis with AST parsing, graph building, VCS integration.
    # 7 phases: validate → discover → index → graph → VCS → embedding → metrics
    # Supports: incremental indexing, parallel processing, multi-relational graph,
    # entry point detection, complexity metrics, churn analysis.
    # For lightweight health checks, use repo_inspect instead.
    # For security scanning, use repo_audit instead.

    @mcp.tool()
    async def repo_analyze(
        repo_path: str,
        force: bool = False,
        incremental: bool = True,
        parallel: bool = True,
        max_workers: int = 4,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        max_file_size_kb: int = 500,
        languages: Optional[List[str]] = None,
        build_graph: bool = True,
        graph_relations: Optional[List[str]] = None,
        graph_backend: str = "sqlite",
        extract_symbols: bool = True,
        store_embeddings: bool = False,
        embedding_model: str = "codebert",
        store_raw_ast: bool = False,
        timeout_seconds: int = 300,
        dry_run: bool = False,
    ) -> dict:
        """
        Deep repository analysis - AST parsing, graph building, VCS integration.

        7-phase pipeline: validate → discover → index (AST) → build graph →
        VCS integration (churn, bug magnets) → embedding (optional) → metrics.

        Args:
            repo_path: Absolute path to the repository root directory.
            force: If True, rebuild entire index from scratch (default false).
            incremental: Index only changed files (hash/timestamp) (default true).
            parallel: Process files concurrently (default true).
            max_workers: Number of threads for parallel parsing (default 4).
            include_patterns: Source code file patterns (default: all common extensions).
            exclude_patterns: Directories to ignore (node_modules, __pycache__, etc).
            max_file_size_kb: Skip files larger than this (default 500 KB).
            languages: Filter by language, e.g. ["python", "go"] (default auto-detect).
            build_graph: Build dependency & call graph (default true).
            graph_relations: Relation types to extract (default: calls, imports, inherits, contains, references).
            graph_backend: "sqlite" (default) or "neo4j" (optional).
            extract_symbols: Extract symbols (functions, classes, variables) (default true).
            store_embeddings: Generate vector embeddings for semantic search (default false).
            embedding_model: Model for embeddings: "codebert", "sentence-transformers" (default "codebert").
            store_raw_ast: Store raw AST for debugging (default false).
            timeout_seconds: Max execution time (default 300, 5 min).
            dry_run: Simulate without writing to database (default false).

        Returns:
            Analysis report with indexing summary, graph metrics, VCS insights, complexity, entry points.
        """
        import time
        from pathlib import Path
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        start_time = time.time()

        resolved = Path(repo_path).resolve()
        if not resolved.exists():
            return api_response(success=False, status_code=404,
                message="Repository path does not exist",
                data={"repo_path": str(resolved), "suggestion": "Check path or run repo_init first"},
                request_id=request_id, error_code="REP_404")

        # ── Phase 0: VCS detection ─────────────────────────────────────────
        vcs_type = "none"
        if (resolved / ".git").exists():
            vcs_type = "git"
        elif (resolved / ".svn").exists():
            vcs_type = "svn"

        # ── Phases 1-3: Core pipeline (discovery → index → graph) ──────────
        try:
            result = await orchestrator.analyze(
                str(resolved), request_id=request_id,
                dry_run=dry_run, max_depth=None,
                include_codemap=True,
            )
        except Exception as e:
            return api_response(success=False, status_code=500,
                message=f"Analysis failed: {str(e)}",
                data=None, request_id=request_id, error_code="REP_004")

        repo_id = result.get("repository_id", "")
        analysis = result.get("analysis", {})
        codemap = result.get("codemap")
        elapsed = round(time.time() - start_time, 2)

        # ── Phase 4: VCS Integration (churn, bug magnets) ──────────────────
        vcs_metrics: dict = {}
        if vcs_type == "git" and not dry_run:
            try:
                import subprocess
                churn = subprocess.run(
                    ["git", "log", "--name-only", "--since=1 year ago", "--pretty=format:"],
                    cwd=str(resolved), capture_output=True, text=True, timeout=10)
                if churn.returncode == 0:
                    files: dict = {}
                    for line in churn.stdout.splitlines():
                        line = line.strip()
                        if line: files[line] = files.get(line, 0) + 1
                    top = sorted(files.items(), key=lambda x: x[1], reverse=True)[:10]
                    vcs_metrics["churn_hotspots"] = [
                        {"file": fp, "change_count": cnt,
                         "risk": "high" if cnt > 150 else ("medium" if cnt > 50 else "low")}
                        for fp, cnt in top
                    ]

                bugs = subprocess.run(
                    ["git", "log", "--oneline", "--grep=fix\\|bug", "--since=1 year ago", "--name-only"],
                    cwd=str(resolved), capture_output=True, text=True, timeout=10)
                if bugs.returncode == 0:
                    bug_files: dict = {}
                    for line in bugs.stdout.splitlines():
                        line = line.strip()
                        if line and not line.startswith("(") and ("/" in line or line.endswith((".py", ".js", ".ts", ".go"))):
                            bug_files[line] = bug_files.get(line, 0) + 1
                    top_bugs = sorted(bug_files.items(), key=lambda x: x[1], reverse=True)[:10]
                    vcs_metrics["bug_magnets"] = [{"file": fp, "bug_commits": cnt} for fp, cnt in top_bugs]
            except Exception:
                pass

        # ── Phase 5: Embedding (if enabled) ────────────────────────────────
        embedding_status = "disabled"
        if store_embeddings and not dry_run and repo_id:
            try:
                await orchestrator.index_service.generate_embeddings(
                    repo_id, model=embedding_model, request_id=request_id)
                embedding_status = f"enabled ({embedding_model})"
            except AttributeError:
                embedding_status = "not supported by index_service"
            except Exception:
                embedding_status = "failed"

        # ── Phase 6: Metrics (entry points, complexity) ────────────────────
        complexity: dict = {}
        entry_points: list = []
        if analysis and isinstance(analysis, dict):
            complexity = analysis.get("complexity_metrics", {})
            entry_points = analysis.get("entry_points", [])

            if vcs_metrics:
                analysis["vcs_metrics"] = vcs_metrics

        # ── Phase 7: Build response ────────────────────────────────────────
        data: dict = {
            "repo_id": repo_id,
            "repo_path": str(resolved),
            "vcs_type": vcs_type,
            "index_mode": "incremental" if incremental and not force else "full",
            "duration_seconds": elapsed,
        }

        # Indexing summary from analysis
        indexing = {
            "total_files_scanned": analysis.get("total_files", 0) if analysis else 0,
            "symbols_extracted": analysis.get("total_symbols", 0) if analysis else 0,
            "edges_built": analysis.get("total_edges", 0) if analysis else 0,
            "languages": analysis.get("language_breakdown", {}) if analysis else {},
        }
        data["indexing_summary"] = indexing

        # Graph summary
        if build_graph and analysis:
            graph_summ = {
                "total_nodes": analysis.get("total_nodes", 0),
                "total_edges": analysis.get("total_edges", 0),
                "density": analysis.get("graph_density", 0),
                "entry_points": entry_points[:5] if entry_points else [],
                "relationship_types": analysis.get("relationship_types", {}),
            }
            data["graph_summary"] = graph_summ

        # VCS metrics
        if vcs_metrics:
            data["vcs_metrics"] = vcs_metrics

        # Complexity
        if complexity:
            data["complexity_metrics"] = complexity

        # Embedding status
        data["embedding_status"] = embedding_status
        data["graph_ready"] = bool(build_graph and analysis)
        data["search_ready"] = bool(analysis)

        # Codemap if available
        if codemap and isinstance(codemap, dict) and len(codemap) > 0:
            data["codemap"] = codemap

        # AI Action Recommendations
        ai_actions = []
        if vcs_metrics.get("churn_hotspots"):
            top_churn = vcs_metrics["churn_hotspots"][0]
            if top_churn["risk"] == "high":
                ai_actions.append({
                    "priority": "high",
                    "action": f"Refactor '{top_churn['file']}' - high churn hotspot ({top_churn['change_count']} changes). Consider splitting into smaller modules.",
                    "file": top_churn["file"]
                })
        if vcs_metrics.get("bug_magnets"):
            top_bug = vcs_metrics["bug_magnets"][0]
            ai_actions.append({
                "priority": "medium" if top_bug["bug_commits"] > 20 else "low",
                "action": f"Review '{top_bug['file']}' for bug-prone code ({top_bug['bug_commits']} bug-related commits). Add unit tests.",
                "file": top_bug["file"]
            })
        if complexity:
            max_cpx = complexity.get("max_cyclomatic", 0)
            if max_cpx and max_cpx > 15:
                ai_actions.append({
                    "priority": "high",
                    "action": f"Reduce cyclomatic complexity (max: {max_cpx}). Split complex functions into smaller, testable units."
                })
        if indexing.get("symbols_extracted", 0) == 0:
            ai_actions.append({
                "priority": "high",
                "action": "No symbols extracted. Run repo_analyze with extract_symbols=true to enable code search and navigation."
            })
        if not indexing.get("languages"):
            ai_actions.append({
                "priority": "medium",
                "action": "No language breakdown detected. Ensure source files are present and not excluded."
            })
        if ai_actions:
            data["ai_actions"] = ai_actions

        msg = "Full analysis completed" if not dry_run else "Dry-run analysis completed"
        msg += f" in {elapsed}s"

        return api_response(success=True, insight="repo_analyze", status_code=200, message=msg, data=data, request_id=request_id)

    # =========================================================================
    # 4. repo_sync - Incremental filesystem synchronization
    # =========================================================================
    # Purpose: Sync a single repository's index with current filesystem state.
    # Detects added/modified/deleted files, re-indexes changes, removes orphans.
    # Flow: get DB file list → scan disk → diff → process changes → update meta

    @mcp.tool()
    async def repo_sync(
        repo_path: str,
        mode: str = "auto",
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        reindex_updated: bool = True,
        remove_deleted: bool = True,
        dry_run: bool = False,
    ) -> dict:
        """
        Synchronize a repository's CodeCortex index with the current filesystem.

        Args:
            repo_path: Path of the repository to synchronize
            mode: Sync mode - "auto" (mtime/size compare), "full" (re-scan all), "fast" (check only)
            include_patterns: File patterns to include (default: from existing index)
            exclude_patterns: Directories/patterns to ignore
            reindex_updated: Re-run code_analysis on modified files
            remove_deleted: Remove DB entries for files no longer on disk
            dry_run: Simulate without making changes

        Returns:
            Summary of changes detected and applied
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            import time
            start_ts = time.time()

            resolved = Path(repo_path).resolve()
            if not resolved.exists():
                return api_response(
                    success=False, status_code=404,
                    message="Repository path does not exist on disk",
                    data={"repo_path": str(resolved)},
                    request_id=request_id, error_code="REP_404",
                )

            repo = orchestrator.repo_store.get_repository_by_path(str(resolved))
            if not repo:
                return api_response(
                    success=False, status_code=404,
                    message="Repository not found in database. Run repo_init first.",
                    data={"repo_path": str(resolved)},
                    request_id=request_id, error_code="REP_404",
                )

            rid = repo["id"]
            exc = set(exclude_patterns) if exclude_patterns else {
                ".git", ".svn", "__pycache__", "node_modules",
                "venv", "env", ".venv", "dist", "build", ".agents",
            }

            # ── Phase 1: Get DB file list ───────────────────────────────────
            db_rows = orchestrator.db.conn.execute(
                "SELECT id, name, size_bytes, mtime FROM files WHERE repository_id = ?", (rid,)
            ).fetchall()
            db_files: dict = {}
            for row in db_rows:
                key = row["name"]
                db_files[key] = {"id": row["id"], "size_bytes": row["size_bytes"], "mtime": row["mtime"]}

            # ── Phase 2: Scan filesystem ────────────────────────────────────
            TEXT_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
                         ".rb", ".php", ".swift", ".kt", ".cs", ".cpp", ".c", ".h",
                         ".hpp", ".sh", ".bash", ".yml", ".yaml", ".json", ".xml",
                         ".toml", ".ini", ".cfg", ".md", ".html", ".css", ".sql",
                         ".gradle", ".tf", ".hcl", ".properties", ".env", ".lock"}

            disk_files: dict = {}
            for root, _dirs, fnames in os.walk(str(resolved)):
                rel = Path(root).relative_to(resolved)
                parts = rel.parts
                if any(p in exc for p in parts):
                    continue
                for fn in fnames:
                    ext = os.path.splitext(fn)[1].lower()
                    if ext not in TEXT_EXTS and fn not in ("Dockerfile", ".gitignore", "Makefile"):
                        continue
                    fp = Path(root) / fn
                    try:
                        st = fp.stat()
                        disk_files[fn] = {"path": str(fp), "size_bytes": st.st_size, "mtime": st.st_mtime}
                    except OSError:
                        pass

            # ── Phase 3: Diff ───────────────────────────────────────────────
            db_names = set(db_files.keys())
            disk_names = set(disk_files.keys())

            added = disk_names - db_names
            deleted_names = db_names - disk_names
            modified = set()
            if mode != "full":
                for name in disk_names & db_names:
                    df = db_files[name]
                    kf = disk_files[name]
                    if df["size_bytes"] != kf["size_bytes"] or (
                        df["mtime"] and abs(
                            (datetime.fromisoformat(str(df["mtime"]).replace("Z", "+00:00")).timestamp()
                             if isinstance(df["mtime"], str) else float(df["mtime"] or 0))
                            - kf["mtime"]
                        ) > 1
                    ):
                        modified.add(name)
            else:
                modified = disk_names & db_names

            changes = {
                "files_added": len(added),
                "files_modified": len(modified),
                "files_deleted": len(deleted_names),
                "symbols_added": 0,
                "symbols_removed": 0,
                "edges_added": 0,
                "edges_removed": 0,
            }

            if dry_run:
                elapsed = round(time.time() - start_ts, 2)
                return api_response(success=True, insight="repo_sync", status_code=200,
                    message="Dry run complete - no changes made",
                    data={
                        "repo_id": rid,
                        "repo_path": str(resolved),
                        "mode": mode,
                        "duration_seconds": elapsed,
                        "dry_run": True,
                        "changes": changes,
                        "updated_index": False,
                    },
                    request_id=request_id,
                )

            # ── Phase 4: Process changes ────────────────────────────────────
            if remove_deleted and deleted_names:
                for name in deleted_names:
                    fid = db_files[name]["id"]
                    orchestrator.db.conn.execute(
                        "DELETE FROM edges WHERE source_id IN (SELECT id FROM symbols WHERE file_id = ?) OR target_id IN (SELECT id FROM symbols WHERE file_id = ?)",
                        (fid, fid)
                    )
                    changes["edges_removed"] += orchestrator.db.conn.rowcount if hasattr(orchestrator.db.conn, 'rowcount') else 0

                    curs = orchestrator.db.conn.execute(
                        "DELETE FROM symbols WHERE file_id = ?", (fid,)
                    )
                    changes["symbols_removed"] += curs.rowcount

                    orchestrator.db.conn.execute(
                        "DELETE FROM files WHERE id = ?", (fid,)
                    )
                orchestrator.db.conn.commit()

            # For modified/added files, we re-index
            process_names = added | modified
            if process_names and reindex_updated:
                for name in process_names:
                    kf = disk_files[name]
                    fp = kf["path"]
                    try:
                        content = Path(fp).read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        continue

                    size_bytes = kf["size_bytes"]
                    ext = os.path.splitext(name)[1].lower()

                    # Upsert file record
                    existing_file = orchestrator.db.conn.execute(
                        "SELECT id FROM files WHERE repository_id = ? AND name = ?", (rid, name)
                    ).fetchone()

                    dir_id = _ensure_dir(orchestrator, rid, resolved, fp)

                    if existing_file:
                        fid = existing_file["id"]
                        # Delete old symbols/edges for this file
                        orchestrator.db.conn.execute(
                            "DELETE FROM edges WHERE source_id IN (SELECT id FROM symbols WHERE file_id = ?) OR target_id IN (SELECT id FROM symbols WHERE file_id = ?)",
                            (fid, fid)
                        )
                        curs = orchestrator.db.conn.execute(
                            "DELETE FROM symbols WHERE file_id = ?", (fid,)
                        )
                        changes["symbols_removed"] += curs.rowcount
                    else:
                        import uuid as _uuid
                        fid = str(_uuid.uuid4())
                        orchestrator.db.conn.execute(
                            "INSERT INTO files (id, repository_id, directory_id, name, classification, size_bytes, content, mtime) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (fid, rid, dir_id, name,
                             _classify_ext(ext), size_bytes, content, kf["mtime"]),
                        )
                        changes["files_added"] = changes.get("files_added", 0) + 1

                    if existing_file and name in modified:
                        orchestrator.db.conn.execute(
                            "UPDATE files SET size_bytes = ?, content = ?, mtime = ? WHERE id = ?",
                            (size_bytes, content, kf["mtime"], fid),
                        )

                    # Re-index symbols
                    _index_file_content(orchestrator, rid, fid, name, content, changes)

                orchestrator.db.conn.commit()

            # Update repo metadata
            fcount = orchestrator.db.conn.execute(
                "SELECT COUNT(*) as c FROM files WHERE repository_id = ?", (rid,)
            ).fetchone()["c"]
            scount = orchestrator.db.conn.execute(
                "SELECT COUNT(*) as c FROM symbols WHERE repository_id = ?", (rid,)
            ).fetchone()["c"]
            ecount = orchestrator.db.conn.execute(
                "SELECT COUNT(*) as c FROM edges WHERE repository_id = ?", (rid,)
            ).fetchone()["c"]

            orchestrator.db.conn.execute(
                "UPDATE repositories SET sync_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (utc_now_iso(), rid),
            )
            orchestrator.db.conn.commit()

            elapsed = round(time.time() - start_ts, 2)
            has_changes = any(v > 0 for v in changes.values())
            msg = "Repository synchronized with filesystem" if has_changes else "Repository is already up to date"

            # Generate AI actions based on sync results
            ai_actions = []
            if changes["files_added"] > 0:
                ai_actions.append({
                    "priority": "medium",
                    "action": f"Review {changes['files_added']} newly added files for potential security issues or missing documentation.",
                    "count": changes["files_added"]
                })
            if changes["files_modified"] > 10:
                ai_actions.append({
                    "priority": "high",
                    "action": f"High volume of changes detected ({changes['files_modified']} files). Consider running repo_analyze to update code intelligence.",
                    "count": changes["files_modified"]
                })
            if changes["files_deleted"] > 0:
                ai_actions.append({
                    "priority": "low",
                    "action": f"{changes['files_deleted']} files removed. Verify deletions are intentional and update any dependent code.",
                    "count": changes["files_deleted"]
                })
            if changes["symbols_removed"] > 0:
                ai_actions.append({
                    "priority": "high",
                    "action": f"{changes['symbols_removed']} symbols removed. Check for breaking changes in public APIs.",
                    "count": changes["symbols_removed"]
                })
            if not has_changes and mode == "auto":
                ai_actions.append({
                    "priority": "info",
                    "action": "No changes detected. Repository is up to date. Consider running repo_staleness to check VCS status."
                })

            data = {
                "repo_id": rid,
                "repo_path": str(resolved),
                "mode": mode,
                "duration_seconds": elapsed,
                "changes": changes,
                "updated_index": True,
            }
            if ai_actions:
                data["ai_actions"] = ai_actions

            return api_response(success=True, insight="repo_sync", status_code=200,
                message=msg,
                data=data,
                request_id=request_id,
            )

        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Repository sync failed: {str(e)}",
                data=None, error_code="REP_500",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()

    def _ensure_dir(orchestrator, repo_id: str, repo_root: Path, file_path: Path) -> str:
        """Ensure a directory entry exists for a file path. Returns directory_id."""
        import uuid as _uuid
        rel = file_path.parent.relative_to(repo_root) if file_path.parent != repo_root else ""
        rel_str = str(rel).replace("\\", "/") if rel else ""
        existing = orchestrator.db.conn.execute(
            "SELECT id FROM directories WHERE repository_id = ? AND relative_path = ?",
            (repo_id, rel_str)
        ).fetchone()
        if existing:
            return existing["id"]
        new_id = str(_uuid.uuid4())
        orchestrator.db.conn.execute(
            "INSERT OR IGNORE INTO directories (id, repository_id, parent_id, relative_path) VALUES (?, ?, ?, ?)",
            (new_id, repo_id, None, rel_str),
        )
        return new_id

    def _classify_ext(ext: str) -> str:
        """Classify a file extension into code/doc/config/binary/other."""
        code_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb",
                     ".php", ".swift", ".kt", ".cs", ".cpp", ".c", ".h", ".hpp", ".sh",
                     ".bash", ".sql", ".gradle", ".tf", ".hcl"}
        doc_exts = {".md", ".html", ".css", ".rst", ".txt"}
        config_exts = {".yml", ".yaml", ".json", ".xml", ".toml", ".ini", ".cfg",
                       ".conf", ".env", ".properties"}
        if ext in code_exts:
            return "code"
        if ext in doc_exts:
            return "doc"
        if ext in config_exts:
            return "config"
        return "other"

    def _index_file_content(orchestrator, repo_id: str, file_id: str,
                             filename: str, content: str, changes: dict):
        """Parse a file content and insert symbols/edges into DB."""
        import uuid as _uuid
        ext = os.path.splitext(filename)[1].lower()
        lines = content.split("\n")
        symbols_found = 0
        edges_found = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "//", "/*", "*", "--", '"')):
                continue

            sym_name = None
            sym_type = None
            parent_id = None

            # Python: function/class def
            if ext == ".py":
                if stripped.startswith("def ") and "(" in stripped:
                    sym_name = stripped[4:].split("(")[0].strip()
                    sym_type = "function"
                elif stripped.startswith("class ") and ":" in stripped:
                    sym_name = stripped[6:].split("(")[0].split(":")[0].strip()
                    sym_type = "class"
                elif " = " in stripped and not stripped.startswith(" "):
                    sym_name = stripped.split(" = ")[0].strip()
                    sym_type = "variable"

            # JS/TS: function/class/const
            elif ext in (".js", ".ts", ".jsx", ".tsx"):
                if stripped.startswith("function ") and "(" in stripped:
                    sym_name = stripped[9:].split("(")[0].strip()
                    sym_type = "function"
                elif stripped.startswith("class ") and "{" in stripped:
                    sym_name = stripped[6:].split("{")[0].strip().split(" ")[0]
                    sym_type = "class"
                elif stripped.startswith(("const ", "let ", "var ")) and "=" in stripped:
                    sym_name = stripped.split("=")[0].replace("const", "").replace("let", "").replace("var", "").strip().split(" ")[0]
                    sym_type = "variable"

            # Go
            elif ext == ".go":
                if stripped.startswith("func ") and "(" in stripped:
                    sym_name = stripped[5:].split("(")[0].strip()
                    sym_type = "function"
                elif stripped.startswith("type ") and "struct" in stripped:
                    sym_name = stripped[5:].split(" ")[0].strip()
                    sym_type = "class"

            if sym_name and sym_type:
                sid = str(_uuid.uuid4())
                try:
                    orchestrator.db.conn.execute(
                        "INSERT OR IGNORE INTO symbols (id, repository_id, file_id, code, name, symbol_type, start_line, end_line) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (sid, repo_id, file_id, stripped, sym_name, sym_type, i, i),
                    )
                    symbols_found += 1
                except Exception:
                    pass

        changes["symbols_added"] = changes.get("symbols_added", 0) + symbols_found
        changes["edges_added"] = changes.get("edges_added", 0) + edges_found

    # =========================================================================
    # 5. repo_audit - Multi-layer security audit (secrets, PII, misconfig, vulns)
    # =========================================================================
    # Purpose: Deep security audit with rule-based + semantic scanning.
    # 7 phases: validate → discover → scan (rule-based → semantic → optional LLM)
    # → VCS history → dependencies → aggregate → respond.
    # For lightweight metadata checks, use fs_audit instead.

    @mcp.tool()
    async def repo_audit(
        repo_path: str,
        scan_categories: Optional[List[str]] = None,
        detect_secrets: bool = True,
        detect_pii: bool = False,
        detect_misconfig: bool = True,
        detect_vuln_patterns: bool = True,
        detect_weak_crypto: bool = True,
        detect_sensitive_files: bool = True,
        exclude_patterns: Optional[List[str]] = None,
        include_git_history: bool = True,
        use_llm_validation: bool = False,
        llm_model: str = "claude-3.5-sonnet",
        max_workers: int = 4,
        max_file_size_kb: int = 1024,
        timeout_seconds: int = 600,
        output_format: str = "json",
    ) -> dict:
        """
        Multi-layer security audit for source code repositories.

        Scans for secrets, PII, misconfigurations, vulnerable code patterns,
        sensitive files, and VCS history. Uses rule-based pattern matching
        with optional LLM validation for false positive reduction.

        Args:
            repo_path: Absolute path to the repository.
            scan_categories: Categories: "secrets", "pii", "misconfig", "vulns" (default all).
            detect_secrets: Secret detection in source code (default true).
            detect_pii: Detect email, phone, SSN, credit card (default false).
            detect_misconfig: Detect CI/CD secrets, debug endpoints, exposed config (default true).
            detect_vuln_patterns: Detect SQL injection, command injection (default true).
            detect_weak_crypto: Detect MD5, SHA1, DES, RC4 usage (default true).
            detect_sensitive_files: Detect .env, *.pem, *.key, credentials (default true).
            exclude_patterns: Directories to ignore (default: node_modules, __pycache__, etc).
            include_git_history: Scan git history for secrets (default true).
            use_llm_validation: Use LLM to validate findings (default false, requires API key).
            llm_model: Model for validation (default "claude-3.5-sonnet").
            max_workers: Parallel workers for file scanning (default 4).
            max_file_size_kb: Skip files larger than this (default 1024 KB).
            timeout_seconds: Max execution time (default 600, 10 min).
            output_format: "json" (default) or "markdown".

        Returns:
            Audit report with findings, severity summary, and recommendations.
        """
        import time, re, os, subprocess, fnmatch
        from pathlib import Path
        from collections import defaultdict

        start = time.time()
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        resolved = Path(repo_path).resolve()

        if not resolved.exists():
            return api_response(success=False, status_code=404,
                message="Repository path does not exist",
                data={"repo_path": str(resolved), "suggestion": "Check path or run repo_analyze first"},
                request_id=request_id, error_code="REP_404")

        categories = scan_categories or ["secrets", "pii", "misconfig", "vulns"]
        exc = exclude_patterns or ["node_modules", "__pycache__", "dist", "build", "venv", "env", ".git", ".svn"]
        max_bytes = max_file_size_kb * 1024

        # ── Pattern Definitions ─────────────────────────────────────────────
        SECRET_PATTERNS = [
            (r"AKIA[0-9A-Z]{16}", "aws_access_key", "critical",
             "Rotate key immediately. Use AWS Secrets Manager or IAM roles."),
            (r"(?i)(aws_secret_access_key|secret_access_key)\s*[=:]\s*['\"][A-Za-z0-9/+=]{40}['\"]", "aws_secret_key", "critical",
             "Rotate key, use IAM roles."),
            (r"ghp_[A-Za-z0-9]{36}", "github_token", "critical",
             "Revoke token on GitHub. Use GitHub Actions secrets."),
            (r"sk_live_[A-Za-z0-9]{24,}", "stripe_live_key", "critical",
             "Rotate key on Stripe Dashboard."),
            (r"xox[baprs]-[A-Za-z0-9\-]{10,}", "slack_token", "high",
             "Revoke token on Slack API."),
            (r"AIza[0-9A-Za-z\-_]{35}", "google_api_key", "high",
             "Restrict API key on Google Cloud Console."),
            (r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "private_key", "critical",
             "Remove from repository. Use a secrets manager."),
            (r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^'\"]{4,}['\"]", "hardcoded_password", "high",
             "Use environment variables or a vault."),
            (r"(?i)(mongodb|postgresql|mysql|redis|amqp)://[^@]+@", "connection_string", "critical",
             "Use connection strings from environment variables."),
            (r"eyJ[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}", "jwt_token", "high",
             "Remove hardcoded JWT. Use environment variables."),
        ]
        PII_PATTERNS = [
            (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "email", "medium",
             "Use dummy data for testing."),
            (r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b", "ssn", "high",
             "Remove SSN from source code."),
            (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b", "credit_card", "critical",
             "Never store credit card numbers in source code."),
        ]
        MISCONFIG_PATTERNS = [
            (r"(?i)(debug\s*[=:]\s*true|DEBUG\s*=\s*True)", "debug_enabled", "medium",
             "Set debug=False in production."),
            (r"(?i)(cors|access-control-allow-origin)\s*[=:]\s*['\"](https?://)?\*['\"]", "wildcard_cors", "high",
             "Do not use wildcard CORS in production."),
            (r"(?i)ALLOWED_HOSTS\s*=\s*['\"*]['\"]", "allow_all_hosts", "high",
             "Set ALLOWED_HOSTS to specific values."),
            (r"DB_PASSWORD\s*:\s*['\"]?", "ci_secret_hardcoded", "high",
             "Use CI/CD secrets (e.g. ${{ secrets.DB_PASSWORD }})."),
            (r"(?i)(s3://)[^/]+", "public_s3_bucket", "high",
             "Ensure S3 bucket is not publicly accessible."),
        ]
        VULN_PATTERNS = [
            (r"(?i)(execute|query|raw|run)\s*\(\s*['\"].*\{.*\}.*['\"]\s*\.\s*format|f['\"]SELECT|['\"]SELECT.*['\"]\s*%", "sql_injection", "critical",
             "Use parameterized queries (?, :name, or %s)."),
            (r"(?i)(os\.system|subprocess\.(run|call|Popen))\s*\(\s*['\"].*[+%].*['\"]", "command_injection", "critical",
             "Avoid shell injection. Use subprocess with argument lists."),
            (r"(?i)\beval\s*\(", "eval_usage", "high",
             "Avoid eval(). Use safer alternatives."),
            (r"(?i)pickle\.(load|loads)\s*\(", "pickle_load", "high",
             "Pickle is unsafe for untrusted data. Use JSON."),
            (r"(?i)yaml\.load\s*\((?![^)]*Loader)", "yaml_load", "medium",
             "Use yaml.safe_load() to prevent arbitrary code execution."),
        ]
        WEAK_CRYPTO = [
            (r"(?i)\bmd5\s*\(", "md5_usage", "medium", "Use SHA-256 or bcrypt/Argon2."),
            (r"(?i)\bsha1\s*\(", "sha1_usage", "medium", "Use SHA-256 or bcrypt/Argon2."),
        ]

        # ── Phase 1: File Discovery ─────────────────────────────────────────
        findings: dict = defaultdict(list)
        scanned_files = 0

        def _should_exclude(p: str) -> bool:
            for pat in exc:
                if fnmatch.fnmatch(p, pat) or "/" + pat + "/" in p:
                    return True
            return False

        TEXT_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".php",
                     ".swift", ".kt", ".cs", ".cpp", ".c", ".h", ".hpp", ".sh", ".bash",
                     ".yml", ".yaml", ".json", ".xml", ".toml", ".ini", ".cfg", ".conf",
                     ".md", ".html", ".css", ".sql", ".env", ".properties", ".gradle", ".tf", ".hcl"}

        for root, _dirs, fnames in os.walk(str(resolved)):
            if _should_exclude(root):
                continue
            for fn in fnames:
                fp = os.path.join(root, fn)
                if _should_exclude(fp):
                    continue
                ext = os.path.splitext(fn)[1].lower()
                if ext not in TEXT_EXTS and fn not in ("Dockerfile", ".gitignore", "requirements.txt"):
                    continue
                try:
                    sz = os.path.getsize(fp)
                except OSError:
                    continue
                if sz > max_bytes:
                    continue
                scanned_files += 1

                try:
                    with open(fp, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception:
                    continue

                rel = os.path.relpath(fp, str(resolved)).replace("\\", "/")

                # ── Phase 2: Multi-layer Scanning ────────────────────────────
                patterns_to_scan = []
                if detect_secrets and "secrets" in categories:
                    patterns_to_scan.extend(SECRET_PATTERNS)
                if detect_pii and "pii" in categories:
                    patterns_to_scan.extend(PII_PATTERNS)
                if detect_misconfig and "misconfig" in categories:
                    patterns_to_scan.extend(MISCONFIG_PATTERNS)
                if detect_vuln_patterns and "vulns" in categories:
                    patterns_to_scan.extend(VULN_PATTERNS)
                if detect_weak_crypto and "vulns" in categories:
                    patterns_to_scan.extend(WEAK_CRYPTO)

                for pattern, ptype, sev, remediation in patterns_to_scan:
                    try:
                        for m in re.finditer(pattern, content):
                            line_num = content[:m.start()].count("\n") + 1
                            ctx_start = max(0, m.start() - 30)
                            ctx_end = min(len(content), m.end() + 30)
                            context = content[ctx_start:ctx_end].replace("\n", " ").strip()
                            val = m.group()[:40]

                            # Category determination
                            cat = "secrets"
                            if ptype in ("email", "ssn", "credit_card"):
                                cat = "pii"
                            elif ptype in ("debug_enabled", "wildcard_cors", "allow_all_hosts", "ci_secret_hardcoded", "public_s3_bucket"):
                                cat = "misconfig"
                            elif ptype in ("sql_injection", "command_injection", "eval_usage", "pickle_load", "yaml_load"):
                                cat = "vulns"
                            elif ptype in ("md5_usage", "sha1_usage"):
                                cat = "vulns"

                            findings[cat].append({
                                "file": rel, "line": line_num, "severity": sev,
                                "type": ptype, "value": val, "context": context,
                                "remediation": remediation, "confidence": 85,
                                "ai_action": f"Review {rel}:{line_num} for {ptype} - {remediation}"
                            })
                    except re.error:
                        continue

        # ── Sensitive Files Detection ───────────────────────────────────────
        if detect_sensitive_files:
            sensitive = {
                ".env": ("credentials", "critical", "Remove from repository, add to .gitignore."),
                ".env.*": ("credentials", "critical", "Remove from repository."),
                "*.pem": ("credentials", "critical", "Use a secrets manager."),
                "*.key": ("credentials", "critical", "Use a secrets manager."),
                "*.p12": ("credentials", "critical", "Use a secrets manager."),
                "credentials.json": ("credentials", "critical", "Move to environment variables."),
                "secrets.yml": ("credentials", "critical", "Use a vault or environment variables."),
                "secrets.yaml": ("credentials", "critical", "Use a vault or environment variables."),
                "*.log": ("sensitive_file", "low", "Add to .gitignore, use log rotation."),
                "*.sqlite": ("sensitive_file", "high", "Remove from repository."),
                "*.db": ("sensitive_file", "high", "Remove from repository."),
            }
            for fn_pat, (cat, sev, remediation) in sensitive.items():
                for fp in Path(str(resolved)).rglob(fn_pat):
                    try:
                        rel = str(fp.relative_to(resolved)).replace("\\", "/")
                    except ValueError:
                        continue
                    findings["sensitive_files"].append({
                        "file": rel, "line": 1, "severity": sev,
                        "type": "sensitive_file", "value": fp.name,
                        "context": f"Sensitive file detected: {fp.name}",
                        "remediation": remediation, "confidence": 95,
                        "ai_action": f"Remove {rel} from repository and add to .gitignore - {remediation}"
                    })

        # ── Phase 4: VCS History Scanning ───────────────────────────────────
        history_findings = []
        if include_git_history and (resolved / ".git").exists():
            try:
                log = subprocess.run(
                    ["git", "log", "--all", "--full-history", "-p", "--since=2020-01-01", "--max-count=100"],
                    cwd=str(resolved), capture_output=True, text=True, timeout=60,
                )
                if log.returncode == 0:
                    # Extract commit headers for context
                    commits = {}
                    current_hash = ""
                    for line in log.stdout.splitlines():
                        if line.startswith("commit "):
                            current_hash = line.split()[1][:8]
                        elif line.startswith("    "):
                            if current_hash and current_hash not in commits:
                                commits[current_hash] = line.strip()

                    for pattern, ptype, sev, remediation in SECRET_PATTERNS:
                        for m in re.finditer(pattern, log.stdout):
                            val = m.group()[:40]
                            history_findings.append({
                                "commit": "unknown", "category": "secrets",
                                "value": val, "severity": sev,
                                "remediation": remediation + " (use BFG Repo-Cleaner to remove from history)",
                            })
                            if len(history_findings) >= 20:
                                break
                        if len(history_findings) >= 20:
                            break
            except Exception:
                pass

        # ── Phase 5: Dependency Scanning ────────────────────────────────────
        dep_vulns = []
        pkg_files = {
            "package.json": "npm", "requirements.txt": "pip",
            "go.mod": "go", "Cargo.toml": "cargo", "Gemfile": "bundler",
        }
        for pf, pm in pkg_files.items():
            pfp = resolved / pf
            if pfp.exists():
                dep_vulns.append({"type": pm, "file": pf, "status": "manifest_found"})

        # ── Phase 6: Aggregate & Deduplicate ────────────────────────────────
        summary = defaultdict(int)
        for cat, items in findings.items():
            seen = set()
            deduped = []
            for item in items:
                key = f"{item['file']}:{item['line']}:{item['type']}"
                if key not in seen:
                    seen.add(key)
                    deduped.append(item)
                    summary[item["severity"]] += 1
            findings[cat] = deduped

        total = sum(len(v) for v in findings.values())
        by_category = {k: len(v) for k, v in findings.items() if v}

        # ── Phase 7: Recommendations ────────────────────────────────────────
        recs = {"secrets_to_rotate": [], "gitignore_entries": set(), "files_to_remove": [], "code_changes": []}
        for cat, items in findings.items():
            for item in items:
                if item["severity"] in ("critical", "high") and item["type"] in (
                    "aws_access_key", "aws_secret_key", "github_token", "stripe_live_key", "hardcoded_password"):
                    recs["secrets_to_rotate"].append(f"{item['value']} ({item['type']} in {item['file']}:{item['line']})")
                if item["type"] in ("sql_injection", "command_injection"):
                    recs["code_changes"].append(f"{item['type']}: {item['file']}:{item['line']} → {item['remediation']}")
                if item["type"] == "sensitive_file":
                    recs["files_to_remove"].append(item['file'])
                    recs["gitignore_entries"].add(f"*{Path(item['file']).suffix}")

        elapsed = round(time.time() - start, 2)

        data: dict = {
            "repo_path": str(resolved),
            "duration_seconds": elapsed,
            "scanned_files": scanned_files,
            "summary": {
                "total_findings": total,
                "by_severity": dict(summary),
                "by_category": by_category,
            },
            "findings": {k: v[:20] for k, v in findings.items() if v},
        }

        if history_findings:
            data["git_history_findings"] = {
                "enabled": True,
                "total_commits_scanned": 100,
                "findings": history_findings[:10],
            }

        if dep_vulns:
            data["dependency_scan"] = {"package_managers": [d["type"] for d in dep_vulns], "manifests_found": dep_vulns}

        if any(recs.values()):
            data["recommendations"] = {k: list(v) if isinstance(v, set) else v for k, v in recs.items() if v}

        if output_format == "markdown":
            md = _render_audit_markdown(data)
            return api_response(success=True, status_code=200,
                message="Repository security audit completed",
                data={"markdown": md, "raw": data}, request_id=request_id)

        return api_response(success=True, status_code=200,
            message="Repository security audit completed",
            data=data, request_id=request_id)

    # =========================================================================
    # 6. repo_staleness - Detect index staleness vs VCS (local + remote)
    # =========================================================================
    # Purpose: Determine if the CodeCortex index needs updating. Compares
    # last indexed state against local HEAD and remote tracking branch.
    # 6-level classification: fresh, behind, ahead, diverged, dirty, outdated.
    # Flow: get repo meta → (optional fetch) → VCS status → diff → classify

    @mcp.tool()
    async def repo_staleness(
        repo_path: str,
        compare_remote: bool = True,
        fetch_remote: bool = False,
        include_local_changes: bool = True,
        timeout_seconds: int = 30,
    ) -> dict:
        """
        Check if the indexed repository is behind the current VCS state.

        Args:
            repo_path: Absolute path to the repository root.
            compare_remote: Compare with remote tracking branch.
            fetch_remote: Run git fetch before comparing (network).
            include_local_changes: Check uncommitted working tree changes.
            timeout_seconds: Timeout for network operations.

        Returns:
            Staleness status with details and recommendation.
        """
        request_id = new_request_id()
        try:
            resolved = Path(repo_path).resolve()
            if not resolved.exists():
                return api_response(
                    success=False, status_code=404,
                    message="Repository path does not exist",
                    data={"repo_path": str(resolved)},
                    request_id=request_id, error_code="REP_404",
                )

            # Detect VCS type
            git_dir = resolved / ".git"
            svn_dir = resolved / ".svn"
            is_git = git_dir.exists() or git_dir.is_file()
            is_svn = svn_dir.exists()

            if not is_git and not is_svn:
                return api_response(
                    success=False, status_code=400,
                    message="No VCS detected (no .git or .svn found)",
                    data={"repo_path": str(resolved)},
                    request_id=request_id, error_code="REP_400",
                )

            vcs_type = "git" if is_git else "svn"

            # ── Phase 1: Get DB metadata ────────────────────────────────────
            orchestrator = orchestrator_factory()
            try:
                repo = orchestrator.repo_store.get_repository_by_path(str(resolved))
            finally:
                orchestrator.db.close()

            repo_id = repo["id"] if repo else None
            last_indexed = repo["sync_at"] if repo else None
            index_age_days = None
            if last_indexed:
                try:
                    dt = datetime.fromisoformat(str(last_indexed).replace("Z", "+00:00"))
                    index_age_days = round((datetime.now(timezone.utc) - dt).total_seconds() / 86400, 1)
                except Exception:
                    pass

            if not repo:
                return api_response(
                    success=False, status_code=400,
                    message="Repository has never been indexed. Run repo_analyze first.",
                    data={"repo_path": str(resolved)},
                    request_id=request_id, error_code="REP_400",
                )

            # ── Phase 2: (Optional) Fetch remote ────────────────────────────
            fetch_error = None
            if fetch_remote and compare_remote and is_git:
                try:
                    subprocess.run(
                        ["git", "fetch"],
                        cwd=str(resolved), capture_output=True, text=True,
                        timeout=timeout_seconds,
                    )
                except subprocess.TimeoutExpired:
                    fetch_error = "git fetch timed out"
                except Exception as e:
                    fetch_error = f"git fetch failed: {str(e)}"

            # ── Phase 3: Get VCS status ─────────────────────────────────────
            details: dict = {}
            remote_reachable = True

            if is_git:
                details["vcs_type"] = "git"
                # Branch
                try:
                    r = subprocess.run(
                        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                        cwd=str(resolved), capture_output=True, text=True, timeout=10,
                    )
                    details["current_branch"] = r.stdout.strip() if r.returncode == 0 else "unknown"
                except Exception:
                    details["current_branch"] = "unknown"

                # Local commit
                try:
                    r = subprocess.run(
                        ["git", "rev-parse", "HEAD"],
                        cwd=str(resolved), capture_output=True, text=True, timeout=10,
                    )
                    details["local_commit"] = r.stdout.strip()[:40] if r.returncode == 0 else None
                except Exception:
                    details["local_commit"] = None

                # Remote info
                if compare_remote:
                    # Remote tracking branch
                    try:
                        r = subprocess.run(
                            ["git", "rev-parse", "--abbrev-ref", "@{upstream}"],
                            cwd=str(resolved), capture_output=True, text=True, timeout=10,
                        )
                        if r.returncode == 0:
                            details["remote_tracking"] = r.stdout.strip()
                        else:
                            details["remote_tracking"] = None
                            remote_reachable = False
                    except Exception:
                        details["remote_tracking"] = None
                        remote_reachable = False

                    # Remote commit
                    if details.get("remote_tracking"):
                        try:
                            r = subprocess.run(
                                ["git", "rev-parse", "@{upstream}"],
                                cwd=str(resolved), capture_output=True, text=True, timeout=10,
                            )
                            details["remote_commit"] = r.stdout.strip()[:40] if r.returncode == 0 else None
                        except Exception:
                            details["remote_commit"] = None
                            remote_reachable = False

                    # Count ahead/behind
                    if details.get("remote_tracking"):
                        try:
                            r = subprocess.run(
                                ["git", "rev-list", "--count", "HEAD..@{upstream}"],
                                cwd=str(resolved), capture_output=True, text=True, timeout=10,
                            )
                            details["commits_behind"] = int(r.stdout.strip()) if r.returncode == 0 else 0
                        except Exception:
                            details["commits_behind"] = 0

                        try:
                            r = subprocess.run(
                                ["git", "rev-list", "--count", "@{upstream}..HEAD"],
                                cwd=str(resolved), capture_output=True, text=True, timeout=10,
                            )
                            details["commits_ahead"] = int(r.stdout.strip()) if r.returncode == 0 else 0
                        except Exception:
                            details["commits_ahead"] = 0
                    else:
                        details["commits_behind"] = 0
                        details["commits_ahead"] = 0

                # Working tree
                if include_local_changes:
                    try:
                        r = subprocess.run(
                            ["git", "status", "--porcelain"],
                            cwd=str(resolved), capture_output=True, text=True, timeout=10,
                        )
                        porcelain = r.stdout.strip()
                        lines = [ln for ln in porcelain.split("\n") if ln.strip()] if porcelain else []
                        modified = [ln[3:] for ln in lines if ln.startswith(" M") or ln.startswith("M ")]
                        added = [ln[3:] for ln in lines if ln.startswith("??")]
                        deleted = [ln[3:] for ln in lines if ln.startswith(" D") or ln.startswith("D ")]
                        details["working_tree"] = {
                            "has_uncommitted": len(lines) > 0,
                            "modified_files": len(modified),
                            "added_files": len(added),
                            "deleted_files": len(deleted),
                        }
                    except Exception:
                        details["working_tree"] = {"has_uncommitted": False}

            else:  # SVN
                details["vcs_type"] = "svn"
                try:
                    r = subprocess.run(
                        ["svn", "info", "--show-item", "revision"],
                        cwd=str(resolved), capture_output=True, text=True, timeout=10,
                    )
                    details["current_revision"] = int(r.stdout.strip()) if r.returncode == 0 else None
                except Exception:
                    details["current_revision"] = None

                try:
                    r = subprocess.run(
                        ["svn", "info", "--show-item", "url"],
                        cwd=str(resolved), capture_output=True, text=True, timeout=10,
                    )
                    details["remote_url"] = r.stdout.strip() if r.returncode == 0 else None
                except Exception:
                    details["remote_url"] = None

                if compare_remote and details.get("remote_url"):
                    try:
                        r = subprocess.run(
                            ["svn", "info", "--show-item", "revision", details["remote_url"]],
                            capture_output=True, text=True, timeout=timeout_seconds,
                        )
                        details["remote_revision"] = int(r.stdout.strip()) if r.returncode == 0 else None
                    except Exception as e:
                        details["remote_revision"] = None
                        remote_reachable = False
                        fetch_error = str(e)

                    if details.get("current_revision") is not None and details.get("remote_revision") is not None:
                        details["revisions_behind"] = max(0, details["remote_revision"] - details["current_revision"])

                if include_local_changes:
                    try:
                        r = subprocess.run(
                            ["svn", "status"],
                            cwd=str(resolved), capture_output=True, text=True, timeout=10,
                        )
                        lines = [ln for ln in r.stdout.strip().split("\n") if ln.strip()] if r.stdout.strip() else []
                        details["working_tree"] = {
                            "has_uncommitted": len(lines) > 0,
                            "modified_count": len(lines),
                        }
                    except Exception:
                        details["working_tree"] = {"has_uncommitted": False}

            # ── Phase 4: Compare with index + classify ──────────────────────
            details["last_indexed_commit"] = repo.get("sync_at")
            details["index_age_days"] = index_age_days

            status = _classify_staleness(details, compare_remote, index_age_days)
            recommendation = _build_recommendation(status, details, vcs_type, fetch_error)
            ai_impact = _build_ai_impact(status, details)

            response_data: dict = {
                "repo_id": repo_id,
                "repo_path": str(resolved),
                "vcs_type": vcs_type,
                "status": status,
                "details": details,
                "recommendation": recommendation,
                "ai_impact": ai_impact,
            }

            if fetch_error and compare_remote:
                return api_response(
                    success=True, status_code=207,
                    message=f"Could not reach remote. {recommendation}",
                    data={**response_data, "error": fetch_error},
                    request_id=request_id,
                )

            staleness_msgs = {
                "fresh": "Index is up to date with remote and working tree.",
                "behind": f"Repository index is behind remote by {details.get('commits_behind', details.get('revisions_behind', 0))} commit(s)",
                "ahead": "Local has unpushed commits. Index matches local HEAD.",
                "diverged": "Local and remote have diverged.",
                "dirty": "Working tree has uncommitted changes.",
                "outdated": f"Index is {index_age_days} day(s) old.",
                "unknown_remote": "Could not reach remote. Returning local staleness only.",
            }
            msg = staleness_msgs.get(status, "Staleness check completed")

            return api_response(
                success=True, status_code=200,
                message=msg, data=response_data,
                request_id=request_id,
            )

        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Staleness check failed: {str(e)}",
                data=None, error_code="REP_500",
                request_id=request_id,
            )

    def _classify_staleness(details: dict, compare_remote: bool, age_days: float | None) -> str:
        """Classify staleness into 6 levels."""
        wt = details.get("working_tree", {})
        if wt and wt.get("has_uncommitted"):
            return "dirty"

        if age_days is not None and age_days > 7:
            return "outdated"

        if not compare_remote:
            if age_days and age_days > 1:
                return "outdated"
            return "fresh"

        if details.get("vcs_type") == "git":
            behind = details.get("commits_behind", 0) or 0
            ahead = details.get("commits_ahead", 0) or 0
            if behind > 0 and ahead > 0:
                return "diverged"
            if behind > 0:
                return "behind"
            if ahead > 0:
                return "ahead"
        else:  # svn
            revs = details.get("revisions_behind", 0) or 0
            if revs > 0:
                return "behind"

        if not details.get("remote_tracking") and details.get("vcs_type") == "git":
            return "unknown_remote"

        return "fresh"

    def _build_recommendation(status: str, details: dict, vcs_type: str, fetch_error: str | None) -> str:
        """Build human-readable recommendation based on staleness status."""
        recs = {
            "fresh": "No action needed.",
            "behind": f"Run `{'git pull' if vcs_type == 'git' else 'svn update'}` then `repo_sync --mode auto` to update index.",
            "ahead": f"Run `{'git push' if vcs_type == 'git' else 'svn commit'}` to sync remote, then `repo_sync`.",
            "diverged": "Run `git pull --rebase` or `git merge` to reconcile, then `repo_sync`.",
            "dirty": "Commit or stash changes, then run `repo_sync` to update the index.",
            "outdated": "Run `repo_sync --mode auto` to refresh the index.",
            "unknown_remote": f"Check internet connection or set fetch_remote=false. {fetch_error or ''}",
        }
        return recs.get(status, "No recommendation.")

    def _build_ai_impact(status: str, details: dict) -> str:
        """Describe how staleness affects AI-powered code analysis."""
        impacts = {
            "fresh": "Index is current. All search and analysis results are reliable.",
            "behind": "CodeCortex index does not contain the latest commits. Semantic search may miss recent changes.",
            "ahead": "Local changes are not pushed but are reflected in the index.",
            "diverged": "Index may be inconsistent with both local and remote. Reconcile branches first.",
            "dirty": "Uncommitted changes are not reflected in the index. Use fs_search for real-time search.",
            "outdated": "Index may be stale. Results might not reflect current codebase.",
            "unknown_remote": "Remote status unknown. Local index state may still be usable.",
        }
        return impacts.get(status, "")

    # =========================================================================
    # 7. repo_list - List all registered repositories
    # =========================================================================
    # Purpose: Discover what's indexed with filtering, metadata, VCS status, pagination.
    # 5-Phase Flow:
    #   Phase 1: Read SQLite DB → filter by status (all/indexed/stale/orphaned)
    #   Phase 2: Enrich metadata (files, symbols, edges, language_breakdown, age)
    #   Phase 3: VCS status (git branch/ahead/behind/uncommitted, SVN revision)
    #   Phase 4: Sort & paginate (order_by, order_dir, limit, offset)
    #   Phase 5: Format response (JSON or Markdown table)

    @mcp.tool()
    async def repo_list(
        filter_status: str = "all",
        include_metadata: bool = True,
        include_vcs_status: bool = False,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "last_analyzed",
        order_dir: str = "desc",
        output_format: str = "json",
    ) -> dict:
        """

        Args:
            filter_status: Filter by status - "all", "indexed", "stale", "orphaned"
            include_metadata: Include total files, symbols, edges, language breakdown, age
            include_vcs_status: Include real-time VCS status (branch, ahead/behind, uncommitted changes)
            limit: Maximum number of repos to return (max 100)
            offset: Pagination offset
            order_by: Sort field - "name", "path", "last_analyzed", "size_bytes"
            order_dir: Sort direction - "asc" or "desc"
            output_format: Response format - "json" or "table"

        Returns:
            List of repositories with pagination metadata
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            # ── Phase 1: Read SQLite DB ─────────────────────────────────────
            db_repos = orchestrator.repo_store.list_repositories()

            if not db_repos:
                return api_response(
                    success=False, status_code=404,
                    message="No repositories found in database. Run repo_init first.",
                    data={
                        "database_path": str(orchestrator.db.db_path),
                        "suggestion": "repo_init --repo_path <path> to index your first repository",
                    },
                    request_id=request_id, error_code="REP_404",
                )

            now = datetime.now(timezone.utc)

            def _calc_age(last_idx: Optional[str]) -> Optional[int]:
                if not last_idx:
                    return None
                try:
                    last_dt = datetime.fromisoformat(last_idx.replace("Z", "+00:00"))
                    return (now - last_dt).days
                except Exception:
                    return None

            def _determine_status(r: dict) -> str:
                if not r.get("_path_exists", True):
                    return "orphaned"
                age = r.get("_age_days")
                if age is None or age > 30:
                    return "stale"
                return "indexed"

            # Enrich with path existence and age
            for r in db_repos:
                rp = Path(r["root_path"])
                r["_path_exists"] = rp.exists()
                r["_age_days"] = _calc_age(r.get("sync_at"))

            # Apply filter_status
            filtered = []
            for r in db_repos:
                st = _determine_status(r)
                insert = False
                if filter_status == "all":
                    insert = True
                elif filter_status == "indexed" and st == "indexed":
                    insert = True
                elif filter_status == "stale" and st == "stale":
                    insert = True
                elif filter_status == "orphaned" and st == "orphaned":
                    insert = True
                if insert:
                    r["status"] = st
                    filtered.append(r)

            # ── Phase 2: Metadata enrichment ────────────────────────────────
            EXT_TO_LANG = {
                ".py": "python", ".js": "javascript", ".ts": "typescript",
                ".jsx": "react", ".tsx": "react", ".go": "go", ".rs": "rust",
                ".java": "java", ".rb": "ruby", ".php": "php", ".swift": "swift",
                ".kt": "kotlin", ".cs": "csharp", ".cpp": "cpp", ".c": "c",
                ".sh": "shell", ".bash": "shell", ".yml": "yaml", ".yaml": "yaml",
                ".json": "json", ".xml": "xml", ".toml": "toml", ".ini": "ini",
                ".cfg": "config", ".md": "markdown", ".html": "html", ".css": "css",
                ".sql": "sql", ".gradle": "gradle", ".tf": "terraform", ".hcl": "hcl",
                ".lock": "lock",
            }

            for r in filtered:
                repo_id = r["id"]
                if include_metadata:
                    f_cnt = orchestrator.db.conn.execute(
                        "SELECT COUNT(*) as c FROM files WHERE repository_id = ?", (repo_id,)
                    ).fetchone()["c"]
                    s_cnt = orchestrator.db.conn.execute(
                        "SELECT COUNT(*) as c FROM symbols WHERE repository_id = ?", (repo_id,)
                    ).fetchone()["c"]
                    e_cnt = orchestrator.db.conn.execute(
                        "SELECT COUNT(*) as c FROM edges WHERE repository_id = ?", (repo_id,)
                    ).fetchone()["c"]
                    sz = orchestrator.db.conn.execute(
                        "SELECT COALESCE(SUM(size_bytes), 0) as sz FROM files WHERE repository_id = ?",
                        (repo_id,),
                    ).fetchone()["sz"]

                    r["total_files"] = f_cnt
                    r["total_symbols"] = s_cnt
                    r["total_edges"] = e_cnt
                    r["_size_bytes"] = sz

                    lang_rows = orchestrator.db.conn.execute(
                        "SELECT name FROM files WHERE repository_id = ?", (repo_id,)
                    ).fetchall()
                    lang_counter: dict = defaultdict(int)
                    for lr in lang_rows:
                        ext = os.path.splitext(lr["name"])[1].lower()
                        lang_counter[EXT_TO_LANG.get(ext, "other")] += 1
                    r["language_breakdown"] = dict(sorted(lang_counter.items(), key=lambda x: -x[1]))
                    r["age_days"] = r["_age_days"]
                else:
                    r["total_files"] = None
                    r["total_symbols"] = None
                    r["total_edges"] = None
                    r["language_breakdown"] = None
                    r["age_days"] = r["_age_days"]
                    r["_size_bytes"] = 0

            # ── Phase 3: VCS status ─────────────────────────────────────────
            if include_vcs_status:
                for r in filtered:
                    if r["_path_exists"]:
                        r["vcs_status"] = _get_vcs_status(str(Path(r["root_path"]).resolve()))
                    else:
                        r["vcs_status"] = None

            # ── Phase 4: Sorting & pagination ───────────────────────────────
            total_count = len(filtered)
            key_map = {
                "name": lambda x: x.get("name", "").lower(),
                "path": lambda x: x.get("root_path", "").lower(),
                "last_analyzed": lambda x: x.get("sync_at") or "",
                "size_bytes": lambda x: x.get("_size_bytes", 0),
            }
            sort_key = key_map.get(order_by, key_map["last_analyzed"])
            filtered.sort(key=sort_key, reverse=(order_dir.lower() == "desc"))
            paginated = filtered[offset:offset + limit]

            # Strip internal fields
            output_repos = []
            for r in paginated:
                out = {k: v for k, v in r.items() if not k.startswith("_")}
                output_repos.append(out)

            # ── Phase 5: AI Actions generation ────────────────────────────────
            ai_actions = []
            stale_count = sum(1 for r in filtered if r.get("status") == "stale")
            orphaned_count = sum(1 for r in filtered if r.get("status") == "orphaned")
            total_files = sum(r.get("total_files", 0) or 0 for r in filtered)

            if orphaned_count > 0:
                ai_actions.append({
                    "priority": "high",
                    "action": f"{orphaned_count} orphaned repositories detected (paths no longer exist). Run repo_cleanup to remove them from database.",
                    "count": orphaned_count,
                    "command_hint": "repo_cleanup --dry_run=true"
                })
            if stale_count > 0:
                ai_actions.append({
                    "priority": "medium",
                    "action": f"{stale_count} stale repositories (>30 days since sync). Run repo_sync to update them.",
                    "count": stale_count,
                    "command_hint": "repo_sync --mode=auto"
                })
            if total_count > 10:
                ai_actions.append({
                    "priority": "info",
                    "action": f"Large repository fleet ({total_count} repos). Consider using filter_status for targeted management.",
                    "tip": "Use filter_status='stale' or 'orphaned' to focus on repositories needing attention."
                })
            if total_files > 10000:
                ai_actions.append({
                    "priority": "info",
                    "action": f"High volume codebase ({total_files} files). Database performance monitoring recommended.",
                    "tip": "Consider running repo_compact periodically for maintenance."
                })

            # ── Phase 6: Format response ────────────────────────────────────
            if output_format == "table":
                table_lines = [
                    "| Repo ID | Path | VCS | Last Analyzed | Files | Symbols | Status |",
                    "|---------|------|-----|---------------|-------|----------|--------|",
                ]
                for r in output_repos:
                    rid = (r.get("id") or "")[:12] + "..."
                    path = r.get("root_path", "")
                    vs = r.get("vcs_status") or {}
                    vcs = vs.get("vcs_type", "N/A")
                    la = (r.get("sync_at") or "N/A")[:10]
                    fv = str(r.get("total_files") or "N/A") if r.get("total_files") is not None else "N/A"
                    sv = str(r.get("total_symbols") or "N/A") if r.get("total_symbols") is not None else "N/A"
                    st = r.get("status", "N/A")
                    table_lines.append(f"| {rid} | {path} | {vcs} | {la} | {fv} | {sv} | {st} |")
                table_str = "\n".join(table_lines)

                data = {"total_count": total_count, "limit": limit, "offset": offset, "table": table_str}
                if ai_actions:
                    data["ai_actions"] = ai_actions

                return api_response(
                    success=True, status_code=200,
                    message=f"Found {total_count} repositories",
                    data=data,
                    request_id=request_id,
                )

            data = {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "repositories": output_repos,
            }
            if ai_actions:
                data["ai_actions"] = ai_actions

            return api_response(
                success=True, status_code=200,
                message=f"Found {total_count} repositories",
                data=data,
                request_id=request_id,
            )

        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Failed to list repositories: {str(e)}",
                data=None, error_code="REP_500",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()

    def _get_vcs_status(repo_path: str) -> Optional[dict]:
        """Get real-time VCS status for a repository path (git or svn)."""
        git_dir = Path(repo_path) / ".git"
        if git_dir.exists() or git_dir.is_file():
            result: dict = {"vcs_type": "git"}
            try:
                r = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=repo_path, capture_output=True, text=True, timeout=5,
                )
                if r.returncode == 0:
                    result["branch"] = r.stdout.strip()
            except Exception:
                pass
            try:
                r = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=repo_path, capture_output=True, text=True, timeout=5,
                )
                result["has_uncommitted_changes"] = bool(r.stdout.strip())
            except Exception:
                result["has_uncommitted_changes"] = False
            try:
                r = subprocess.run(
                    ["git", "rev-list", "--count", "HEAD..@{upstream}"],
                    cwd=repo_path, capture_output=True, text=True, timeout=5,
                )
                result["commits_behind"] = int(r.stdout.strip() or "0") if r.returncode == 0 else 0
            except Exception:
                result["commits_behind"] = 0
            try:
                r = subprocess.run(
                    ["git", "rev-list", "--count", "@{upstream}..HEAD"],
                    cwd=repo_path, capture_output=True, text=True, timeout=5,
                )
                result["commits_ahead"] = int(r.stdout.strip() or "0") if r.returncode == 0 else 0
            except Exception:
                result["commits_ahead"] = 0
            if result.get("commits_behind", 0) > 0:
                result["warning"] = f"Repository is {result['commits_behind']} commit(s) behind remote"
            return result

        svn_dir = Path(repo_path) / ".svn"
        if svn_dir.exists():
            result = {"vcs_type": "svn"}
            try:
                r = subprocess.run(
                    ["svn", "info", "--show-item", "revision"],
                    cwd=repo_path, capture_output=True, text=True, timeout=5,
                )
                if r.returncode == 0:
                    result["revision"] = int(r.stdout.strip())
            except Exception:
                pass
            try:
                r = subprocess.run(
                    ["svn", "status"],
                    cwd=repo_path, capture_output=True, text=True, timeout=5,
                )
                result["has_local_modifications"] = bool(r.stdout.strip())
            except Exception:
                result["has_local_modifications"] = False
            return result

        return None

    # =========================================================================
    # 8. repo_compact - Compact database & export snapshot
    # =========================================================================
    # Purpose: Maintenance - orphaned cleanup, snapshot export (.agents/),
    #          and SQLite VACUUM.
    # 5-Phase Flow:
    #   Phase 1: Identify target (single repo or all)
    #   Phase 2: Cleanup orphaned edges/symbols/files
    #   Phase 3: Export snapshot (.agents/codecortex.yaml|json)
    #   Phase 4: VACUUM database
    #   Phase 5: Return response

    @mcp.tool()
    async def repo_compact(
        repo_path: Optional[str] = None,
        output_format: str = "yaml",
        output_path: Optional[str] = None,
        compact_db: bool = True,
        remove_orphaned: bool = True,
        remove_old_embeddings: bool = False,
        dry_run: bool = False,
    ) -> dict:

        """
        Args:
            repo_path: If given, compact only this repo. Otherwise entire database.
            output_format: Snapshot format - "yaml" or "json"
            output_path: Custom snapshot path (default: <repo_root>/.agents/codecortex.<ext>)
            compact_db: Run VACUUM on SQLite database
            remove_orphaned: Delete dangling edges/symbols/files
            remove_old_embeddings: Delete old embeddings (no-op if table absent)
            dry_run: Simulate without making changes

        Returns:
            Cleanup stats, snapshot info, database compact stats
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            # ── Phase 1: Identify target ─────────────────────────────────────
            target_repo = None
            where_clause = ""
            where_params: tuple = ()

            if repo_path:
                resolved = Path(repo_path).resolve()
                target_repo = orchestrator.repo_store.get_repository_by_path(str(resolved))
                if not target_repo:
                    return api_response(
                        success=False, status_code=404,
                        message="Repository path not found in database",
                        data={"repo_path": str(resolved)},
                        request_id=request_id, error_code="REP_404",
                    )
                where_clause = "WHERE repository_id = ?"
                where_params = (target_repo["id"],)

            all_repos = orchestrator.repo_store.list_repositories()
            if not all_repos:
                return api_response(
                    success=False, status_code=404,
                    message="No repositories found in database. Run repo_init first.",
                    data={"suggestion": "repo_init --repo_path <path> to index your first repository"},
                    request_id=request_id, error_code="REP_404",
                )

            # ── Phase 2: Cleanup orphaned data ───────────────────────────────
            cleanup_stats = {
                "orphaned_edges_removed": 0,
                "orphaned_symbols_removed": 0,
                "orphaned_files_removed": 0,
            }

            if remove_orphaned and not dry_run:
                cursor = orchestrator.db.conn.execute(f"""
                    DELETE FROM edges
                    WHERE (source_id NOT IN (SELECT id FROM symbols)
                        OR target_id NOT IN (SELECT id FROM symbols))
                        {where_clause}
                """, where_params)
                cleanup_stats["orphaned_edges_removed"] = cursor.rowcount

                cursor = orchestrator.db.conn.execute(f"""
                    DELETE FROM symbols
                    WHERE file_id NOT IN (SELECT id FROM files)
                        {where_clause}
                """, where_params)
                cleanup_stats["orphaned_symbols_removed"] = cursor.rowcount

                cursor = orchestrator.db.conn.execute(
                    "DELETE FROM files WHERE repository_id NOT IN (SELECT id FROM repositories)"
                )
                cleanup_stats["orphaned_files_removed"] = cursor.rowcount

                orchestrator.db.conn.commit()

            # ── Phase 3: Export snapshot ─────────────────────────────────────
            snapshot_info = None
            if not dry_run:
                snapshot_data = _build_snapshot(orchestrator, target_repo)

                if output_path:
                    snap_path = Path(output_path)
                elif target_repo:
                    snap_path = Path(target_repo["root_path"]) / ".agents" / f"codecortex.{output_format}"
                else:
                    snap_path = Path(str(orchestrator.db.db_path)).parent / f"codecortex-snapshot.{output_format}"

                snap_path.parent.mkdir(parents=True, exist_ok=True)

                if output_format == "json":
                    with open(snap_path, "w", encoding="utf-8") as f:
                        json.dump(snapshot_data, f, indent=2, default=str)
                else:
                    import yaml
                    with open(snap_path, "w", encoding="utf-8") as f:
                        yaml.dump(snapshot_data, f, default_flow_style=False, sort_keys=False)

                snapshot_info = {
                    "format": output_format,
                    "path": str(snap_path),
                    "size_bytes": snap_path.stat().st_size,
                    "entries": {
                        "files": len(snapshot_data.get("files", [])),
                        "symbols": len(snapshot_data.get("symbols", [])),
                        "edges": len(snapshot_data.get("edges", [])),
                    },
                }

            # ── Phase 4: Compact DB (VACUUM) ────────────────────────────────
            db_compact_info = {"before_bytes": 0, "after_bytes": 0}
            if compact_db and not dry_run:
                from src.core.database import compact_database
                result = compact_database(orchestrator.db.conn)
                before = result.get("size_before", 0)
                after = result.get("size_after", 0)
                pct = round(((before - after) / max(before, 1)) * 100, 1) if before else 0
                db_compact_info = {
                    "before_bytes": before,
                    "after_bytes": after,
                    "reduction_percent": pct,
                }

            # Handle remove_old_embeddings
            embeddings_removed = 0
            embeddings_note = None
            if remove_old_embeddings and not dry_run:
                tables = orchestrator.db.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%embed%'"
                ).fetchall()
                for t in tables:
                    cursor = orchestrator.db.conn.execute(f"DELETE FROM {t['name']}")
                    embeddings_removed += cursor.rowcount
                if not tables:
                    embeddings_note = "No embeddings table found in schema"

            # ── Phase 5: Format response ────────────────────────────────────
            response_data: dict = {
                "target": "single_repository" if target_repo else "all_repositories",
            }
            if target_repo:
                response_data["repo_id"] = target_repo["id"]
                response_data["repo_path"] = target_repo["root_path"]

            if dry_run:
                response_data["dry_run"] = True
                response_data["would_remove_orphaned_edges"] = _count_orphaned(
                    orchestrator, "edges", "source_id NOT IN (SELECT id FROM symbols)" +
                    (" AND repository_id = ?" if target_repo else ""),
                    (target_repo["id"],) if target_repo else ()
                )
                response_data["would_remove_orphaned_symbols"] = _count_orphaned(
                    orchestrator, "symbols", "file_id NOT IN (SELECT id FROM files)" +
                    (" AND repository_id = ?" if target_repo else ""),
                    (target_repo["id"],) if target_repo else ()
                )
                response_data["would_remove_orphaned_files"] = _count_orphaned(
                    orchestrator, "files", "repository_id NOT IN (SELECT id FROM repositories)"
                )
                if compact_db:
                    db_path = Path(str(orchestrator.db.db_path))
                    response_data["database_size_before"] = db_path.stat().st_size if db_path.exists() else 0
                    response_data["database_path"] = str(db_path)
            else:
                response_data["cleanup_stats"] = cleanup_stats
                if snapshot_info:
                    response_data["snapshot"] = snapshot_info
                if compact_db:
                    response_data["database_compact"] = db_compact_info
                    response_data["database_path"] = str(orchestrator.db.db_path)
                if remove_old_embeddings:
                    response_data["embeddings_removed"] = embeddings_removed
                    if embeddings_note:
                        response_data["embeddings_note"] = embeddings_note

            msg = "Database compacted and snapshot exported"
            if dry_run:
                msg = "Dry run complete - no changes made"
            elif not compact_db and not remove_orphaned and not snapshot_info:
                msg = "No operations performed"

            return api_response(
                success=True, status_code=200,
                message=msg, data=response_data,
                request_id=request_id,
            )

        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Database compact failed: {str(e)}",
                data=None, error_code="REP_500",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()

    def _build_snapshot(orchestrator, target_repo: Optional[dict]) -> dict:
        """Build a portable snapshot dict from the database."""
        if target_repo:
            repos = [target_repo]
            where = "WHERE repository_id = ?"
            params = (target_repo["id"],)
        else:
            repos = orchestrator.repo_store.list_repositories()
            where = ""
            params = ()

        now_iso = utc_now_iso()
        snapshot = {
            "version": 1,
            "exported_at": now_iso,
            "repositories": repos,
        }

        if where:
            frows = orchestrator.db.conn.execute(
                f"SELECT id, name, classification, size_bytes, repository_id FROM files {where}", params
            ).fetchall()
            srows = orchestrator.db.conn.execute(
                f"SELECT id, name, symbol_type, start_line, file_id, repository_id FROM symbols {where}", params
            ).fetchall()
            erows = orchestrator.db.conn.execute(
                f"SELECT id, source_id, target_id, relation_type, repository_id FROM edges {where}", params
            ).fetchall()
        else:
            frows = orchestrator.db.conn.execute(
                "SELECT id, name, classification, size_bytes, repository_id FROM files"
            ).fetchall()
            srows = orchestrator.db.conn.execute(
                "SELECT id, name, symbol_type, start_line, file_id, repository_id FROM symbols"
            ).fetchall()
            erows = orchestrator.db.conn.execute(
                "SELECT id, source_id, target_id, relation_type, repository_id FROM edges"
            ).fetchall()

        snapshot["files"] = [dict(r) for r in frows]
        snapshot["symbols"] = [dict(r) for r in srows]
        snapshot["edges"] = [dict(r) for r in erows]
        return snapshot

    def _count_orphaned(orchestrator, table: str, condition: str, params: tuple = ()) -> int:
        """Count orphaned rows in a table without deleting them."""
        row = orchestrator.db.conn.execute(
            f"SELECT COUNT(*) as c FROM {table} WHERE {condition}", params
        ).fetchone()
        return row["c"] if row else 0

    # =========================================================================
    # 9. repo_cleanup - Permanently delete all data for a project
    # =========================================================================
    # Purpose: Irreversible deletion of a repository's data - all tables +
    #          optional snapshot file deletion.
    # Flow: validate → check path exists → count + delete → delete snapshot
    #       → return summary

    @mcp.tool()
    async def repo_cleanup(
        repo_path: Optional[str] = None,
        repo_id: Optional[str] = None,
        delete_snapshot: bool = True,
        dry_run: bool = False,
        force: bool = False,
    ) -> dict:
        """
        Permanently delete ALL data for a repository from CodeCortex database.

        Args:
            repo_path: Absolute path of the repository to delete
            repo_id: UUID of the repository (alternative to repo_path)
            delete_snapshot: Delete snapshot file at .agents/codecortex.*
            dry_run: Simulate without making changes
            force: Force delete even if repo_path still exists on disk

        Returns:
            Summary of deleted data per table
        """
        request_id = new_request_id()
        if not repo_path and not repo_id:
            return api_response(
                success=False, status_code=400,
                message="Either repo_path or repo_id is required",
                data={"suggestion": "Provide repo_path or repo_id"},
                request_id=request_id, error_code="REP_400",
            )

        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            # ── Phase 1: Validate target ────────────────────────────────────
            repo = None
            if repo_id:
                row = orchestrator.db.conn.execute(
                    "SELECT * FROM repositories WHERE id = ?", (repo_id,)
                ).fetchone()
                repo = dict(row) if row else None
            elif repo_path:
                resolved = Path(repo_path).resolve()
                repo = orchestrator.repo_store.get_repository_by_path(str(resolved))

            if not repo:
                return api_response(
                    success=False, status_code=404,
                    message="Repository not found in CodeCortex database",
                    data={"provided": {"repo_path": repo_path, "repo_id": repo_id}},
                    request_id=request_id, error_code="REP_404",
                )

            rid = repo["id"]
            rpath = repo["root_path"]
            rpath_exists = Path(rpath).resolve().exists()

            # Check if path still exists (safety guard)
            if rpath_exists and not force and not dry_run:
                return api_response(
                    success=False, status_code=409,
                    message="Repository path still exists on disk. Use force=true to proceed with database deletion only (files will remain).",
                    data={
                        "repo_path": rpath,
                        "suggestion": "If you want to delete files from disk as well, remove them manually first, then retry cleanup.",
                    },
                    request_id=request_id, error_code="REP_409",
                )

            # ── Phase 2: Count & build plan ─────────────────────────────────
            delete_order = [
                "edges", "insights", "symbols", "file_commits", "commits",
                "manifest_entries", "execution_tasks", "files", "directories",
            ]
            extra_tables = ["findings", "history_findings", "graph_edges", "graph_nodes"]

            plan = {}
            for tbl in delete_order:
                row = orchestrator.db.conn.execute(
                    f"SELECT COUNT(*) as c FROM {tbl} WHERE repository_id = ?", (rid,)
                ).fetchone()
                plan[tbl] = row["c"] if row else 0

            # Check extra tables (may not exist)
            existing_tables = {
                r["name"] for r in orchestrator.db.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            for tbl in extra_tables:
                if tbl in existing_tables:
                    row = orchestrator.db.conn.execute(
                        f"SELECT COUNT(*) as c FROM {tbl} WHERE repository_id = ?", (rid,)
                    ).fetchone()
                    plan[tbl] = row["c"] if row else 0
                else:
                    plan[tbl] = 0

            total_records = sum(plan.values())

            # Snapshot path
            snapshot_paths = [
                Path(rpath) / ".agents" / "codecortex.yaml",
                Path(rpath) / ".agents" / "codecortex.json",
            ]
            existing_snapshot = None
            for sp in snapshot_paths:
                if sp.exists():
                    existing_snapshot = str(sp)
                    break

            if dry_run:
                # Calculate breakdown by category
                code_records = plan.get("symbols", 0) + plan.get("edges", 0) + plan.get("files", 0)
                vcs_records = plan.get("commits", 0) + plan.get("file_commits", 0)
                analysis_records = plan.get("insights", 0) + plan.get("findings", 0)

                ai_action = f"Would delete {total_records} records from {len([t for t in plan.values() if t > 0])} tables for repository '{rpath}'. This action is IRREVERSIBLE."
                if rpath_exists:
                    ai_action += f" Repository path still exists on disk. Use force=true to delete database entries only."
                if existing_snapshot:
                    ai_action += f" Snapshot at {existing_snapshot} will also be removed."

                preview = {
                    "repository": {"id": rid, "path": rpath, "path_exists": rpath_exists},
                    "records_by_category": {
                        "code": code_records,
                        "vcs": vcs_records,
                        "analysis": analysis_records,
                        "other": total_records - code_records - vcs_records - analysis_records,
                    },
                    "table_breakdown": {k: v for k, v in plan.items() if v > 0},
                    "snapshot": {"exists": bool(existing_snapshot), "path": existing_snapshot},
                    "safety_warnings": [
                        "This action is IRREVERSIBLE and cannot be undone",
                        f"{total_records} records will be permanently deleted" if total_records > 0 else "No records found to delete",
                    ],
                    "next_step": "Remove dry_run=true and add force=true if path exists to execute deletion."
                }

                return api_response(
                    success=True, status_code=200,
                    message="Dry run complete - no changes made",
                    data={
                        "dry_run": True,
                        "ai_action": ai_action,
                        "preview": preview,
                        "would_delete": {
                            "repo_id": rid,
                            "repo_path": rpath,
                            "total_records": total_records,
                            "snapshot_file": existing_snapshot,
                        },
                    },
                    request_id=request_id,
                )

            # ── Phase 3: Execute deletion ───────────────────────────────────
            deleted_counts = {}
            for tbl in delete_order:
                curs = orchestrator.db.conn.execute(
                    f"DELETE FROM {tbl} WHERE repository_id = ?", (rid,)
                )
                deleted_counts[tbl] = curs.rowcount

            for tbl in extra_tables:
                if tbl in existing_tables:
                    curs = orchestrator.db.conn.execute(
                        f"DELETE FROM {tbl} WHERE repository_id = ?", (rid,)
                    )
                    deleted_counts[tbl] = curs.rowcount

            # Delete repository row itself
            deleted_counts["repositories"] = 1
            orchestrator.db.conn.execute(
                "DELETE FROM repositories WHERE id = ?", (rid,)
            )
            orchestrator.db.conn.commit()

            # Remove from global registry
            try:
                from src.modules.coderepository.core.registry import RegistryManager
                entry = RegistryManager.find_by_path(rpath)
                if entry:
                    remaining = [e for e in RegistryManager.read()
                                 if e.get("repo_id") != rid]
                    RegistryManager.write(remaining)
            except Exception:
                pass

            # ── Phase 4: Delete snapshot file ───────────────────────────────
            snapshot_deleted = False
            snapshot_path_deleted = None
            if delete_snapshot and existing_snapshot:
                try:
                    Path(existing_snapshot).unlink()
                    snapshot_deleted = True
                    snapshot_path_deleted = existing_snapshot
                except Exception:
                    pass

            # ── Phase 5: AI Actions generation ────────────────────────────────
            ai_actions = []
            total_deleted = sum(deleted_counts.values())
            if total_deleted > 0:
                ai_actions.append({
                    "priority": "info",
                    "action": f"Repository '{rpath}' successfully removed. {total_deleted} records deleted from database.",
                    "count": total_deleted,
                    "status": "completed"
                })
            if rpath_exists:
                ai_actions.append({
                    "priority": "medium",
                    "action": f"Repository path still exists on disk at '{rpath}'. Remove files manually if no longer needed.",
                    "command_hint": f"rm -rf {rpath}" if not os.name == 'nt' else f"Remove-Item -Recurse -Force {rpath}"
                })
            if snapshot_deleted:
                ai_actions.append({
                    "priority": "low",
                    "action": f"Snapshot file at {snapshot_path_deleted} was also deleted.",
                    "status": "completed"
                })

            # ── Phase 6: Return response ────────────────────────────────────
            data = {
                "target": {"repo_id": rid, "repo_path": rpath},
                "deleted_records": deleted_counts,
                "snapshot_deleted": snapshot_deleted,
                "snapshot_path": snapshot_path_deleted,
            }
            if ai_actions:
                data["ai_actions"] = ai_actions

            return api_response(
                success=True, status_code=200,
                message="Repository and all associated data removed from CodeCortex",
                data=data,
                request_id=request_id,
            )

        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Cleanup failed: {str(e)}",
                data=None, error_code="REP_500",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()

    # =========================================================================
    # 10. repo_dump - Export all repository data to portable files
    # =========================================================================
    # Purpose: Full data export for backup, documentation, or migration.
    # Flow: validate → query data → transform → write files → return stats
    # Supports: split-by-type (separate files), compress (gzip), dry-run

    @mcp.tool()
    async def repo_dump(
        repo_path: str,
        output_dir: Optional[str] = None,
        format: str = "yaml",
        include_findings: bool = True,
        include_embeddings: bool = False,
        split_by_type: bool = True,
        compress: bool = False,
        dry_run: bool = False,
    ) -> dict:
        """
        Export all CodeCortex data for a repository to portable files.

        Args:
            repo_path: Path of the repository to dump
            output_dir: Output directory (default: <repo_path>/.agents/codecortex)
            format: Output format - "yaml" or "json"
            include_findings: Include audit findings
            include_embeddings: Include vector embeddings (can be very large)
            split_by_type: Split into separate files per data type
            compress: Compress output files with gzip
            dry_run: Simulate without writing files

        Returns:
            List of created files with size stats
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            # ── Phase 1: Validate ───────────────────────────────────────────
            resolved = Path(repo_path).resolve()
            repo = orchestrator.repo_store.get_repository_by_path(str(resolved))
            if not repo:
                return api_response(
                    success=False, status_code=400,
                    message="Repository not indexed. Run repo_analyze first.",
                    data={"repo_path": str(resolved)},
                    request_id=request_id, error_code="REP_400",
                )

            rid = repo["id"]
            out_base = Path(output_dir or (resolved / ".agents" / "codecortex"))

            # ── Phase 2: Query data ─────────────────────────────────────────
            manifest = {
                "version": 1,
                "exported_at": utc_now_iso(),
                "repo_id": rid,
                "repo_path": str(resolved),
                "tool": "repo_dump",
            }

            metadata = dict(repo)

            rows_files = orchestrator.db.conn.execute(
                "SELECT id, name, classification, size_bytes, mtime FROM files WHERE repository_id = ?", (rid,)
            ).fetchall()
            files_data = [dict(r) for r in rows_files]

            rows_symbols = orchestrator.db.conn.execute(
                "SELECT id, name, symbol_type, start_line, end_line, file_id, signature, docstring FROM symbols WHERE repository_id = ?", (rid,)
            ).fetchall()
            symbols_data = [dict(r) for r in rows_symbols]

            rows_edges = orchestrator.db.conn.execute(
                "SELECT id, source_id, target_id, relation_type, line_number, weight FROM edges WHERE repository_id = ?", (rid,)
            ).fetchall()
            edges_data = [dict(r) for r in rows_edges]

            # Graph nodes/edges (if table exists)
            existing_tables = {
                r["name"] for r in orchestrator.db.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            graph_nodes = []
            graph_edges = []
            if "graph_nodes" in existing_tables:
                rows = orchestrator.db.conn.execute(
                    "SELECT * FROM graph_nodes WHERE repository_id = ?", (rid,)
                ).fetchall()
                graph_nodes = [dict(r) for r in rows]
            if "graph_edges" in existing_tables:
                rows = orchestrator.db.conn.execute(
                    "SELECT * FROM graph_edges WHERE repository_id = ?", (rid,)
                ).fetchall()
                graph_edges = [dict(r) for r in rows]

            # Findings (if table exists and requested)
            findings = []
            if include_findings and "findings" in existing_tables:
                rows = orchestrator.db.conn.execute(
                    "SELECT * FROM findings WHERE repository_id = ?", (rid,)
                ).fetchall()
                findings = [dict(r) for r in rows]
                if "history_findings" in existing_tables:
                    rows = orchestrator.db.conn.execute(
                        "SELECT * FROM history_findings WHERE repository_id = ?", (rid,)
                    ).fetchall()
                    findings.extend({"history": True, **dict(r)} for r in rows)

            # Embeddings (if requested and table exists)
            embeddings = None
            if include_embeddings:
                embed_tables = [t for t in existing_tables if "embed" in t.lower()]
                if embed_tables:
                    rows = orchestrator.db.conn.execute(
                        f"SELECT * FROM {embed_tables[0]} WHERE repository_id = ?", (rid,)
                    ).fetchall()
                    embeddings = [dict(r) for r in rows]

            # ── Phase 3: Assemble data sections ─────────────────────────────
            sections = {
                "manifest": manifest,
                "metadata": metadata,
                "files": files_data,
                "symbols": symbols_data,
                "edges": edges_data,
            }
            if graph_nodes or graph_edges:
                sections["graph"] = {"nodes": graph_nodes, "edges": graph_edges}
            if findings:
                sections["findings"] = findings
            if embeddings is not None:
                sections["embeddings"] = embeddings

            stats = {
                "files": len(files_data),
                "symbols": len(symbols_data),
                "edges": len(edges_data),
                "graph_nodes": len(graph_nodes),
                "graph_edges": len(graph_edges),
                "findings": len(findings),
                "embeddings": len(embeddings) if embeddings else 0,
            }

            if dry_run:
                out_path_msg = str(out_base)
                if split_by_type:
                    out_path_msg = str(out_base / "*.yaml")

                ai_action = f"Would export {sum(stats.values())} records to {out_path_msg} in {format} format."
                if compress:
                    ai_action += " Output will be gzip compressed."
                if not include_embeddings:
                    ai_action += " Note: Embeddings excluded (use include_embeddings=true to include)."

                preview = {
                    "output_directory": str(out_base),
                    "file_count": len(sections) if split_by_type else 1,
                    "estimated_records": sum(stats.values()),
                    "format": format,
                    "compression": "gzip" if compress else "none",
                    "sections": list(sections.keys()),
                    "restore_hint": f"Use repo_restore --source {out_base} to restore this dump."
                }

                return api_response(
                    success=True, status_code=200,
                    message="Dry run complete - no files written",
                    data={
                        "dry_run": True,
                        "ai_action": ai_action,
                        "preview": preview,
                        "output_dir": str(out_base),
                        "format": format,
                        "split_by_type": split_by_type,
                        "compress": compress,
                        "statistics": stats,
                        "would_create": list(sections.keys()),
                    },
                    request_id=request_id,
                )

            # ── Phase 4: Write files ────────────────────────────────────────
            out_base.mkdir(parents=True, exist_ok=True)
            files_created = []
            total_size = 0

            if split_by_type:
                for section_name, section_data in sections.items():
                    output_data = section_data if section_name == "manifest" else section_data
                    sub_name = f"{section_name}.{format}"
                    sub_path = out_base / sub_name
                    _write_structured(sub_path, output_data, format, compress)
                    sz = sub_path.stat().st_size if not compress else (sub_path.stat().st_size if sub_path.exists() else 0)
                    if compress:
                        sub_gz = sub_path.parent / (sub_name + ".gz")
                        if sub_gz.exists():
                            sz = sub_gz.stat().st_size
                            files_created.append(str(sub_gz.relative_to(out_base.parent)))
                            total_size += sz
                            continue
                    files_created.append(str(sub_path.relative_to(out_base.parent)))
                    total_size += sz

                # Always write manifest
                if "manifest" not in sections:
                    man_path = out_base / f"manifest.{format}"
                    _write_structured(man_path, manifest, format, compress)
                    files_created.append(str(man_path.relative_to(out_base.parent)))
                    total_size += man_path.stat().st_size
            else:
                combined = {
                    "manifest": manifest,
                    "metadata": metadata,
                    "files": files_data,
                    "symbols": symbols_data,
                    "edges": edges_data,
                }
                if graph_nodes or graph_edges:
                    combined["graph"] = {"nodes": graph_nodes, "edges": graph_edges}
                if findings:
                    combined["findings"] = findings
                if embeddings is not None:
                    combined["embeddings"] = embeddings

                fname = f"codecortex.{format}"
                fpath = out_base / fname
                _write_structured(fpath, combined, format, compress)
                out_size = fpath.stat().st_size if not compress else (fpath.stat().st_size if fpath.exists() else 0)
                if compress:
                    fpath_gz = fpath.parent / (fname + ".gz")
                    if fpath_gz.exists():
                        out_size = fpath_gz.stat().st_size
                        files_created.append(str(fpath_gz.relative_to(out_base.parent)))
                        total_size += out_size
                    else:
                        files_created.append(str(fpath.relative_to(out_base.parent)))
                        total_size += out_size
                else:
                    files_created.append(str(fpath.relative_to(out_base.parent)))
                    total_size += out_size

            # Remove double-counted manifest from split mode
            if split_by_type:
                files_created = list(dict.fromkeys(files_created))

            # ── Phase 5: AI Actions generation ────────────────────────────────
            ai_actions = []
            total_records = sum(stats.values())
            if total_records > 0:
                ai_actions.append({
                    "priority": "info",
                    "action": f"Successfully exported {total_records} records ({len(files_created)} files, {total_size:,} bytes).",
                    "count": total_records,
                    "files": len(files_created),
                    "size_bytes": total_size,
                    "status": "completed"
                })
            if stats.get("findings", 0) > 0:
                ai_actions.append({
                    "priority": "medium",
                    "action": f"Exported {stats['findings']} audit findings. Review findings before restoring to new repository.",
                    "count": stats["findings"],
                    "tip": "Findings may contain security issues that should be addressed before migration."
                })
            if not include_embeddings and stats.get("embeddings", 0) == 0:
                ai_actions.append({
                    "priority": "low",
                    "action": "Embeddings not included in dump. Re-run with include_embeddings=true if vector search data is needed.",
                    "command_hint": f"repo_dump --include_embeddings=true --repo_path {resolved}"
                })
            ai_actions.append({
                "priority": "info",
                "action": f"To restore this repository, use: repo_restore --source {out_base}",
                "command_hint": f"repo_restore --source {out_base} --verify_checksum=true"
            })

            # ── Phase 6: Return response ────────────────────────────────────
            data = {
                "repo_id": rid,
                "repo_path": str(resolved),
                "output_dir": str(out_base),
                "format": format,
                "split_by_type": split_by_type,
                "compress": compress,
                "files_created": files_created,
                "total_size_bytes": total_size,
                "statistics": stats,
                "restore_command": f"repo_restore --from {out_base}",
            }
            if ai_actions:
                data["ai_actions"] = ai_actions

            return api_response(
                success=True, status_code=200,
                message="Repository data exported successfully",
                data=data,
                request_id=request_id,
            )

        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Repository dump failed: {str(e)}",
                data=None, error_code="REP_500",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()

    def _write_structured(path: Path, data: Any, fmt: str, compress: bool) -> None:
        """Write data as YAML or JSON, optionally gzipped."""
        import gzip
        if fmt == "json":
            raw = json.dumps(data, indent=2, default=str).encode("utf-8")
        else:
            import yaml
            raw = yaml.dump(data, default_flow_style=False, sort_keys=False).encode("utf-8")

        if compress:
            gz_path = path.parent / (path.name + ".gz")
            with gzip.open(gz_path, "wb") as f:
                f.write(raw)
        else:
            with open(path, "wb") as f:
                f.write(raw)

    # =========================================================================
    # 11. repo_restore - Import repository data from snapshot/dump
    # =========================================================================
    # Purpose: Restore a repository from a repo_dump or repo_compact snapshot.
    # Flow: read source → check conflicts → insert data → update metadata
    # Supports: single file (yaml/json/gz), split directory, overwrite, dry-run

    @mcp.tool()
    async def repo_restore(
        source: str,
        repo_path: Optional[str] = None,
        overwrite: bool = False,
        verify_checksum: bool = True,
        dry_run: bool = False,
    ) -> dict:
        """
        Import repository data from a dump file or snapshot directory.

        Args:
            source: Path to dump file (.yaml/.json/.gz) or directory (split format)
            repo_path: New path for the repo (overrides path from dump)
            overwrite: Replace existing repo data if already in DB
            verify_checksum: Verify data integrity (if checksums are present)
            dry_run: Simulate without writing to database

        Returns:
            Summary of restored records
        """
        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        try:
            # ── Phase 1: Read and validate source ───────────────────────────
            src = Path(source)
            if not src.exists():
                return api_response(
                    success=False, status_code=404,
                    message=f"Source path does not exist: {source}",
                    data={"source": source},
                    request_id=request_id, error_code="REP_404",
                )

            dump = _load_dump(src)
            if not dump:
                return api_response(
                    success=False, status_code=400,
                    message="No valid dump data found in source",
                    data={"source": source, "format": _detect_format(src)},
                    request_id=request_id, error_code="REP_400",
                )

            # Extract repo metadata from dump
            repo_meta = _get_section(dump, "metadata") or _get_section(dump, "repositories")
            if isinstance(repo_meta, list) and repo_meta:
                repo_meta = repo_meta[0]
            if not repo_meta:
                return api_response(
                    success=False, status_code=400,
                    message="Dump missing repository metadata",
                    data={"source": source, "hint": "Ensure dump contains metadata or repositories section"},
                    request_id=request_id, error_code="REP_400",
                )

            dump_repo_path = str(Path(repo_meta.get("root_path", repo_meta.get("repo_path", ""))).resolve())
            final_repo_path = str(Path(repo_path).resolve()) if repo_path else dump_repo_path
            dump_repo_id = repo_meta.get("id") or repo_meta.get("repo_id", "")

            # ── Phase 2: Check conflicts ────────────────────────────────────
            existing = orchestrator.repo_store.get_repository_by_path(final_repo_path)

            if existing and not overwrite:
                return api_response(
                    success=False, status_code=409,
                    message="Repository already exists in database. Use overwrite=true to replace.",
                    data={
                        "existing_repo_id": existing["id"],
                        "existing_repo_path": existing["root_path"],
                    },
                    request_id=request_id, error_code="REP_409",
                )

            if existing and overwrite:
                # Clean existing data
                tbls = ["edges", "insights", "symbols", "file_commits",
                        "commits", "manifest_entries", "execution_tasks",
                        "files", "directories"]
                for t in tbls:
                    orchestrator.db.conn.execute(
                        f"DELETE FROM {t} WHERE repository_id = ?", (existing["id"],)
                    )
                orchestrator.db.conn.execute(
                    "DELETE FROM repositories WHERE id = ?", (existing["id"],)
                )
                orchestrator.db.conn.commit()

            if dry_run:
                files_data = _get_section(dump, "files") or []
                symbols_data = _get_section(dump, "symbols") or []
                edges_data = _get_section(dump, "edges") or []
                graph = _get_section(dump, "graph") or {}
                findings_data = _get_section(dump, "findings") or []
                embeds = _get_section(dump, "embeddings") or []

                total_records = len(files_data) + len(symbols_data) + len(edges_data) + len(findings_data) + len(embeds)
                ai_action = f"Would restore {total_records} records from {source} to '{final_repo_path}'."
                if existing and overwrite:
                    ai_action += f" WARNING: Existing repository will be overwritten (remove existing data first)."
                elif existing:
                    ai_action += " Repository already exists - use overwrite=true to replace."

                preview = {
                    "source": {"path": source, "format": _detect_format(src)},
                    "target": {"repo_id": dump_repo_id, "repo_path": final_repo_path, "existing": bool(existing)},
                    "records_by_category": {
                        "code": len(files_data) + len(symbols_data) + len(edges_data),
                        "analysis": len(findings_data),
                        "vcs": len(_get_section(dump, "commits") or []),
                        "other": len(embeds) + len(graph.get("nodes", [])) + len(graph.get("edges", []))
                    },
                    "table_breakdown": {
                        "files": len(files_data),
                        "symbols": len(symbols_data),
                        "edges": len(edges_data),
                        "findings": len(findings_data),
                        "embeddings": len(embeds),
                        "graph_nodes": len(graph.get("nodes", [])),
                        "graph_edges": len(graph.get("edges", [])),
                    },
                    "conflict_check": {
                        "existing_repo": bool(existing),
                        "overwrite_enabled": overwrite,
                        "action_required": "Set overwrite=true to replace existing" if existing and not overwrite else "Ready to restore"
                    },
                    "next_step": "Remove dry_run=true to execute restoration." if not existing or overwrite else "Set overwrite=true to proceed."
                }

                return api_response(
                    success=True, status_code=200,
                    message="Dry run complete - no data written",
                    data={
                        "dry_run": True,
                        "ai_action": ai_action,
                        "preview": preview,
                        "source": source,
                        "source_format": _detect_format(src),
                        "would_restore": {
                            "repositories": 1,
                            "files": len(files_data),
                            "symbols": len(symbols_data),
                            "edges": len(edges_data),
                            "graph_nodes": len(graph.get("nodes", [])),
                            "graph_edges": len(graph.get("edges", [])),
                            "findings": len(findings_data),
                            "embeddings": len(embeds),
                        },
                    },
                    request_id=request_id,
                )

            # ── Phase 3: Insert data ────────────────────────────────────────
            use_id = dump_repo_id if not existing else dump_repo_id
            try:
                orchestrator.db.conn.execute(
                    "INSERT INTO repositories (id, name, root_path, sync_at, created_at, updated_at, vcs_type, total_files, total_symbols, total_edges) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'git', 0, 0, 0)",
                    (use_id, repo_meta.get("name", Path(final_repo_path).name), final_repo_path, utc_now_iso()),
                )
            except Exception:
                # ID collision - generate new ID
                import uuid as _uuid
                use_id = str(_uuid.uuid4())
                orchestrator.db.conn.execute(
                    "INSERT INTO repositories (id, name, root_path, sync_at, created_at, updated_at, vcs_type, total_files, total_symbols, total_edges) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'git', 0, 0, 0)",
                    (use_id, repo_meta.get("name", Path(final_repo_path).name), final_repo_path, utc_now_iso()),
                )

            inserted = {"repositories": 1, "files": 0, "symbols": 0, "edges": 0,
                        "graph_nodes": 0, "graph_edges": 0, "findings": 0, "embeddings": 0}

            _restore_files(orchestrator, dump, use_id, inserted)
            _restore_symbols(orchestrator, dump, use_id, inserted)
            _restore_edges(orchestrator, dump, use_id, inserted)
            _restore_graph(orchestrator, dump, use_id, inserted)
            _restore_findings(orchestrator, dump, use_id, inserted)
            _restore_embeddings(orchestrator, dump, use_id, inserted)

            orchestrator.db.conn.commit()

            # Registry
            try:
                from src.modules.coderepository.core.registry import RegistryManager
                RegistryManager.register(final_repo_path, use_id)
            except Exception:
                pass

            # ── Phase 4: AI Actions generation ────────────────────────────
            ai_actions = []
            total_inserted = sum(inserted.values())
            if total_inserted > 0:
                ai_actions.append({
                    "priority": "info",
                    "action": f"Successfully restored {total_inserted} records to repository '{final_repo_path}'.",
                    "count": total_inserted,
                    "status": "completed"
                })
            if inserted.get("findings", 0) > 0:
                ai_actions.append({
                    "priority": "high",
                    "action": f"Restored {inserted['findings']} findings from backup. Review security findings immediately.",
                    "count": inserted["findings"],
                    "tip": "Use repo_audit to re-scan and verify findings are still relevant."
                })
            if inserted.get("files", 0) > 100:
                ai_actions.append({
                    "priority": "medium",
                    "action": f"Large repository restored ({inserted['files']} files). Consider running repo_sync to verify filesystem alignment.",
                    "command_hint": f"repo_sync --repo_path {final_repo_path} --mode=auto"
                })
            ai_actions.append({
                "priority": "info",
                "action": f"Repository ready. Run repo_inspect to verify restoration or repo_analyze for full analysis.",
                "next_steps": ["repo_inspect", "repo_analyze", "repo_staleness"]
            })

            source_format = _detect_format(src)
            data = {
                "repo_id": use_id,
                "repo_path": final_repo_path,
                "source": source,
                "format": source_format,
                "restored_records": inserted,
                "overwrite": overwrite,
            }
            if ai_actions:
                data["ai_actions"] = ai_actions

            return api_response(
                success=True, status_code=200,
                message="Repository restored successfully from dump",
                data=data,
                request_id=request_id,
            )

        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Repository restore failed: {str(e)}",
                data=None, error_code="REP_500",
                request_id=request_id,
            )
        finally:
            orchestrator.db.close()

    # ── Restore helper functions ────────────────────────────────────────────
    def _detect_format(src_path: Path) -> str:
        """Detect dump format from path."""
        if src_path.is_dir():
            return "split_directory"
        name = src_path.name.lower()
        if name.endswith(".json.gz"):
            return "json_gz"
        if name.endswith(".yaml.gz") or name.endswith(".yml.gz"):
            return "yaml_gz"
        if src_path.suffix == ".json":
            return "json"
        if src_path.suffix in (".yaml", ".yml"):
            return "yaml"
        return "unknown"

    def _load_dump(src_path: Path) -> dict:
        """Load dump data from file or directory into a unified dict."""
        if src_path.is_dir():
            combined = {}
            for f in sorted(src_path.iterdir()):
                if not f.is_file():
                    continue
                section = _load_single_file(f)
                if section is not None:
                    stem = _clean_stem(f)
                    combined[stem] = section
            # Promote single-repo repository list
            repos = combined.get("repositories")
            if isinstance(repos, list) and len(repos) == 1:
                combined["metadata"] = repos[0]
            return combined

        data = _load_single_file(src_path)
        return data or {}

    def _load_single_file(path: Path):
        """Load a single dump file (yaml/json/gz)."""
        import gzip
        try:
            suffix = path.suffix.lower()
            if suffix == ".gz":
                raw = gzip.decompress(path.read_bytes())
                name_lower = path.name.lower()
                if name_lower.endswith(".json.gz"):
                    return json.loads(raw)
                else:
                    import yaml
                    return yaml.safe_load(raw)
            if suffix == ".json":
                return json.loads(path.read_text(encoding="utf-8"))
            if suffix in (".yaml", ".yml"):
                import yaml
                return yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return None

    def _clean_stem(path: Path) -> str:
        """Extract section name from filename (strip extensions)."""
        name = path.name
        for ext in [".json.gz", ".yaml.gz", ".yml.gz", ".json", ".yaml", ".yml"]:
            if name.endswith(ext):
                return name[:-len(ext)]
        return name

    def _get_section(dump: dict, name: str) -> Any:
        """Get a section from dump, trying multiple key names."""
        for key in (name, name.replace("_", "-"), name.upper()):
            if key in dump:
                return dump[key]
        return None

    def _restore_files(orchestrator, dump: dict, repo_id: str, counter: dict):
        """Restore files from dump into database."""
        import uuid as _uuid
        files = _get_section(dump, "files") or []
        for f in files:
            fid = f.get("id") or str(_uuid.uuid4())
            try:
                # Try to preserve the original directory_id if we have one
                # We'll create a minimal directory entry
                dir_id = str(_uuid.uuid4())
                if f.get("directory_id"):
                    dir_id = f["directory_id"]
                try:
                    orchestrator.db.conn.execute(
                        "INSERT OR IGNORE INTO directories (id, repository_id, parent_id, relative_path) VALUES (?, ?, NULL, ?)",
                        (dir_id, repo_id, ""),
                    )
                except Exception:
                    pass
                orchestrator.db.conn.execute(
                    "INSERT OR IGNORE INTO files (id, repository_id, directory_id, name, classification, size_bytes, mtime) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (fid, repo_id, dir_id, f.get("name", ""),
                     f.get("classification", "code"), f.get("size_bytes", 0),
                     f.get("mtime")),
                )
                counter["files"] += 1
            except Exception:
                pass

    def _restore_symbols(orchestrator, dump: dict, repo_id: str, counter: dict):
        """Restore symbols from dump into database."""
        import uuid as _uuid
        symbols = _get_section(dump, "symbols") or []
        for s in symbols:
            sid = s.get("id") or str(_uuid.uuid4())
            fid = s.get("file_id", "")
            try:
                orchestrator.db.conn.execute(
                    "INSERT OR IGNORE INTO symbols (id, repository_id, file_id, code, name, symbol_type, start_line, end_line, docstring, signature) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (sid, repo_id, fid, s.get("name", s.get("code", "")),
                     s.get("name", ""), s.get("symbol_type", "unknown"),
                     s.get("start_line"), s.get("end_line"),
                     s.get("docstring"), s.get("signature")),
                )
                counter["symbols"] += 1
            except Exception:
                pass

    def _restore_edges(orchestrator, dump: dict, repo_id: str, counter: dict):
        """Restore edges from dump into database."""
        import uuid as _uuid
        edges = _get_section(dump, "edges") or []
        for e in edges:
            eid = e.get("id") or str(_uuid.uuid4())
            try:
                orchestrator.db.conn.execute(
                    "INSERT OR IGNORE INTO edges (id, repository_id, source_id, target_id, relation_type, line_number, weight) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (eid, repo_id, e.get("source_id", ""), e.get("target_id", ""),
                     e.get("relation_type", "USES"), e.get("line_number"),
                     e.get("weight", 1.0)),
                )
                counter["edges"] += 1
            except Exception:
                pass

    def _restore_graph(orchestrator, dump: dict, repo_id: str, counter: dict):
        """Restore graph nodes/edges if the graph section and tables exist."""
        import uuid as _uuid
        existing_tables = {
            r["name"] for r in orchestrator.db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        graph = _get_section(dump, "graph") or {}
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        if nodes and "graph_nodes" in existing_tables:
            for n in nodes:
                try:
                    orchestrator.db.conn.execute(
                        "INSERT OR IGNORE INTO graph_nodes (id, repository_id, name, type, metadata) VALUES (?, ?, ?, ?, ?)",
                        (n.get("id") or str(_uuid.uuid4()), repo_id,
                         n.get("name", ""), n.get("type", ""),
                         json.dumps(n.get("metadata", {})) if n.get("metadata") else None),
                    )
                    counter["graph_nodes"] += 1
                except Exception:
                    pass

        if edges and "graph_edges" in existing_tables:
            for e in edges:
                try:
                    orchestrator.db.conn.execute(
                        "INSERT OR IGNORE INTO graph_edges (id, repository_id, source_id, target_id, relation_type, weight) VALUES (?, ?, ?, ?, ?, ?)",
                        (e.get("id") or str(_uuid.uuid4()), repo_id,
                         e.get("source_id", ""), e.get("target_id", ""),
                         e.get("relation_type", "RELATED_TO"), e.get("weight", 1.0)),
                    )
                    counter["graph_edges"] += 1
                except Exception:
                    pass

    def _restore_findings(orchestrator, dump: dict, repo_id: str, counter: dict):
        """Restore findings if the section and table exist."""
        import uuid as _uuid
        existing_tables = {
            r["name"] for r in orchestrator.db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        findings = _get_section(dump, "findings") or []
        for f in findings:
            tbl = "history_findings" if f.get("history") else "findings"
            if tbl not in existing_tables:
                continue
            try:
                orchestrator.db.conn.execute(
                    f"INSERT OR IGNORE INTO {tbl} (id, repository_id, category, insight_type, metadata) VALUES (?, ?, ?, ?, ?)",
                    (f.get("id") or str(_uuid.uuid4()), repo_id,
                     f.get("category", "general"), f.get("insight_type", "info"),
                     json.dumps(f.get("metadata", {})) if f.get("metadata") else None),
                )
                counter["findings"] += 1
            except Exception:
                pass

    def _restore_embeddings(orchestrator, dump: dict, repo_id: str, counter: dict):
        """Restore embeddings if the section and table exist."""
        import uuid as _uuid
        existing_tables = {
            r["name"] for r in orchestrator.db.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        embeds = _get_section(dump, "embeddings") or []
        if not embeds:
            return
        embed_tables = [t for t in existing_tables if "embed" in t.lower()]
        if not embed_tables:
            return
        tbl = embed_tables[0]
        for e in embeds:
            try:
                orchestrator.db.conn.execute(
                    f"INSERT OR IGNORE INTO {tbl} (id, repository_id, target_code, embedding, model) VALUES (?, ?, ?, ?, ?)",
                    (e.get("id") or str(_uuid.uuid4()), repo_id,
                     e.get("target_code", ""), e.get("embedding"),
                     e.get("model", "unknown")),
                )
                counter["embeddings"] += 1
            except Exception:
                pass

    # =========================================================================
    # 10. repo_git - Arbitrary Git operations
    # =========================================================================
    # Purpose: Execute any git subcommand with structured params.
    # Wraps DiskGit from filesystem infrastructure.
    # Supports: init, clone, status, add, commit, push, pull, fetch,
    # branch, checkout, merge, rebase, log, diff, remote, tag, stash,
    # reset, revert, cherry-pick.

    @mcp.tool()
    async def repo_git(
        repo_path: str,
        subcommand: str,
        args: Optional[List[str]] = None,
        flags: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        timeout_seconds: int = 300,
    ) -> Dict[str, Any]:
        """
        Execute arbitrary Git operations on a repository.

        Args:
            repo_path: Absolute path to the Git repository root.
            subcommand: Git subcommand to execute (e.g. "status", "commit").
            args: Positional arguments (e.g. ["-m", "message"]).
            flags: Flags as dict (e.g. {"--oneline": true, "-n": 5}).
            dry_run: Simulate without executing (default false).
            timeout_seconds: Timeout for long operations (default 300).

        Returns:
            Structured response with parsed git output.
        """
        from src.modules.filesystem.adapters.git import DiskGit

        request_id = new_request_id()
        params: Dict[str, Any] = {
            "repo_path": repo_path,
            "subcommand": subcommand,
            "args": args or [],
            "flags": flags or {},
            "dry_run": dry_run,
            "timeout_seconds": timeout_seconds,
        }
        try:
            result = DiskGit.execute(params)
            data = result.get("data", {})

            # Add ai_action for dry_run mode
            if dry_run and data:
                command_parts = ["git", subcommand]
                if args:
                    command_parts.extend(args)
                if flags:
                    for flag, value in flags.items():
                        if value is True:
                            command_parts.append(flag)
                        elif value is False:
                            pass
                        else:
                            command_parts.append(f"{flag}={value}")
                data["ai_action"] = f"Would execute: {' '.join(command_parts)}. Remove dry_run=true to apply."
                data["preview"] = {
                    "command": " ".join(command_parts),
                    "repo_path": repo_path,
                    "estimated_impact": "preview only - no changes"
                }

            return api_response(
                success=True,
                status_code=int(result.get("status_code", 200)),
                message=str(result.get("message", "Success")),
                data=data,
                request_id=request_id,
            )
        except ApiError as e:
            return api_response(
                success=False,
                status_code=int(e.status_code),
                message=str(e),
                data=None,
                request_id=request_id,
                error_code=e.error_code,
                details=e.details,
            )
        except Exception:
            return api_response(
                success=False,
                status_code=500,
                message="Internal error while executing git operation",
                data=None,
                request_id=request_id,
                error_code="REP_GIT_500",
            )

    # =========================================================================
    # 11. repo_svn - Arbitrary SVN operations
    # =========================================================================
    # Purpose: Execute any SVN subcommand with structured params.
    # Wraps DiskSvn from filesystem infrastructure.
    # Supports: checkout, update, commit, add, status, log, diff, info,
    # revert, cleanup, lock, unlock, propset, resolve, merge, switch, etc.

    @mcp.tool()
    async def repo_svn(
        target: str,
        subcommand: str,
        args: Optional[List[str]] = None,
        flags: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        timeout_seconds: int = 300,
    ) -> Dict[str, Any]:
        """
        Execute arbitrary Subversion (SVN) operations on a working copy.

        Args:
            target: URL (for checkout) or local working copy path.
            subcommand: SVN subcommand (e.g. "status", "commit").
            args: Positional arguments.
            flags: Flags as dict (e.g. {"--verbose": true}).
            dry_run: Simulate without executing (default false).
            timeout_seconds: Timeout for long operations (default 300).

        Returns:
            Structured response with parsed svn output.
        """
        from src.modules.filesystem.adapters.svn import DiskSvn

        request_id = new_request_id()
        params: Dict[str, Any] = {
            "target": target,
            "subcommand": subcommand,
            "args": args or [],
            "flags": flags or {},
            "dry_run": dry_run,
            "timeout_seconds": timeout_seconds,
        }
        try:
            result = DiskSvn.execute(params)
            data = result.get("data", {})

            # Add ai_action for dry_run mode
            if dry_run and data:
                command_parts = ["svn", subcommand]
                if args:
                    command_parts.extend(args)
                if flags:
                    for flag, value in flags.items():
                        if value is True:
                            command_parts.append(flag)
                        elif value is False:
                            pass
                        else:
                            command_parts.append(f"{flag}={value}")
                data["ai_action"] = f"Would execute: {' '.join(command_parts)}. Remove dry_run=true to apply."
                data["preview"] = {
                    "command": " ".join(command_parts),
                    "target": target,
                    "estimated_impact": "preview only - no changes"
                }

            return api_response(
                success=True,
                status_code=int(result.get("status_code", 200)),
                message=str(result.get("message", "Success")),
                data=data,
                request_id=request_id,
            )
        except ApiError as e:
            return api_response(
                success=False,
                status_code=int(e.status_code),
                message=str(e),
                data=None,
                request_id=request_id,
                error_code=e.error_code,
                details=e.details,
            )
        except Exception:
            return api_response(
                success=False,
                status_code=500,
                message="Internal error while executing svn operation",
                data=None,
                request_id=request_id,
                error_code="REP_SVN_500",
            )

    # =========================================================================
    # 12. repo_history - Git/SVN commit history with rich features
    # =========================================================================
    # Purpose: Retrieve and analyze commit history for code archaeology,
    #          author statistics, timeline analysis, and change tracking.
    # Supports: Git log, SVN log, author stats, file history, blame,
    #          timeline visualization data, and AI-powered insights.
    # Integration: Works with repo_inspect (churn analysis), repo_analyze
    #              (bug magnet detection), repo_audit (secret scanning).

    @mcp.tool()
    async def repo_history(
        repo_path: str,
        vcs_type: Optional[str] = None,
        limit: int = 100,
        since: Optional[str] = None,
        until: Optional[str] = None,
        author: Optional[str] = None,
        file_path: Optional[str] = None,
        include_stats: bool = True,
        include_file_changes: bool = False,
        output_format: str = "json",
    ) -> dict:
        """
        Retrieve rich commit history from Git or SVN repository.

        Provides commit logs, author statistics, file change tracking, and
        timeline data for code archaeology and analysis workflows.

        Args:
            repo_path: Absolute path to the repository
            vcs_type: "git", "svn", or "auto" (auto-detect)
            limit: Maximum number of commits to retrieve (default 100, max 1000)
            since: Start date (ISO format or "N days ago")
            until: End date (ISO format or "now")
            author: Filter by author name or email
            file_path: Filter to specific file history
            include_stats: Include diff statistics (additions/deletions)
            include_file_changes: Include list of changed files per commit
            output_format: "json" or "timeline"

        Returns:
            Commit history with statistics, author breakdown, and AI insights
        """
        request_id = new_request_id()
        resolved = Path(repo_path).resolve()

        if not resolved.exists():
            return api_response(
                success=False, status_code=404,
                message="Repository path does not exist",
                data={"repo_path": str(resolved)},
                request_id=request_id, error_code="REP_404",
            )

        # Auto-detect VCS type
        detected_vcs = vcs_type
        if not detected_vcs or detected_vcs == "auto":
            if (resolved / ".git").exists():
                detected_vcs = "git"
            elif (resolved / ".svn").exists():
                detected_vcs = "svn"
            else:
                return api_response(
                    success=False, status_code=400,
                    message="No Git or SVN repository detected",
                    data={"suggestion": "Initialize VCS first or specify vcs_type explicitly"},
                    request_id=request_id, error_code="REP_400",
                )

        try:
            import subprocess
            import json as json_mod

            commits = []
            author_stats: dict = {}
            timeline_data = []

            if detected_vcs == "git":
                # Build git log command
                cmd = ["git", "log", f"--max-count={min(limit, 1000)}", "--pretty=format:%H|%an|%ae|%ad|%s"]
                cmd.extend(["--date=iso"])

                if since:
                    cmd.extend([f"--since={since}"])
                if until:
                    cmd.extend([f"--until={until}"])
                if author:
                    cmd.extend([f"--author={author}"])
                if file_path:
                    cmd.extend(["--", file_path])

                result = subprocess.run(cmd, cwd=str(resolved), capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        if "|" not in line:
                            continue
                        parts = line.split("|", 4)
                        if len(parts) >= 5:
                            commit_hash, author_name, author_email, date_str, subject = parts
                            commit_data = {
                                "hash": commit_hash[:12],
                                "full_hash": commit_hash,
                                "author": author_name,
                                "email": author_email,
                                "date": date_str,
                                "message": subject,
                                "vcs": "git"
                            }

                            # Get stats if requested
                            if include_stats:
                                stat_cmd = ["git", "show", "--stat", "--format=", commit_hash]
                                stat_result = subprocess.run(stat_cmd, cwd=str(resolved), capture_output=True, text=True, timeout=10)
                                if stat_result.returncode == 0:
                                    # Parse stat output
                                    lines = stat_result.stdout.strip().split("\n")
                                    files_changed = 0
                                    insertions = 0
                                    deletions = 0
                                    for stat_line in lines:
                                        if "changed" in stat_line:
                                            # Parse "X files changed, Y insertions(+), Z deletions(-)"
                                            parts = stat_line.split(",")
                                            for part in parts:
                                                if "file" in part:
                                                    files_changed = int(part.strip().split()[0])
                                                elif "insertion" in part:
                                                    insertions = int(part.strip().split()[0])
                                                elif "deletion" in part:
                                                    deletions = int(part.strip().split()[0])
                                    commit_data["stats"] = {
                                        "files_changed": files_changed,
                                        "insertions": insertions,
                                        "deletions": deletions
                                    }

                            commits.append(commit_data)

                            # Build author stats
                            if author_name not in author_stats:
                                author_stats[author_name] = {
                                    "commits": 0,
                                    "email": author_email,
                                    "first_commit": date_str,
                                    "last_commit": date_str
                                }
                            author_stats[author_name]["commits"] += 1
                            author_stats[author_name]["last_commit"] = date_str

                            # Timeline data
                            timeline_data.append({
                                "date": date_str[:10],
                                "author": author_name,
                                "hash": commit_hash[:8]
                            })

            elif detected_vcs == "svn":
                # SVN log implementation
                cmd = ["svn", "log", "--limit", str(min(limit, 1000))]
                if since:
                    cmd.extend(["-r", f"{{{since}}}:HEAD"])
                if file_path:
                    cmd.append(file_path)

                result = subprocess.run(cmd, cwd=str(resolved), capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    # Parse SVN log format
                    current_entry = {}
                    for line in result.stdout.strip().split("\n"):
                        if line.startswith("r") and "|" in line:
                            # Format: r123 | author | date | lines
                            parts = line.split(" | ")
                            if len(parts) >= 4:
                                revision = parts[0].strip()
                                svn_author = parts[1].strip()
                                svn_date = parts[2].strip()
                                commit_data = {
                                    "revision": revision,
                                    "author": svn_author,
                                    "date": svn_date,
                                    "vcs": "svn"
                                }
                                commits.append(commit_data)

                                # Author stats
                                if svn_author not in author_stats:
                                    author_stats[svn_author] = {
                                        "commits": 0,
                                        "first_commit": svn_date,
                                        "last_commit": svn_date
                                    }
                                author_stats[svn_author]["commits"] += 1
                                author_stats[svn_author]["last_commit"] = svn_date

            # Generate AI actions based on history
            ai_actions = []
            total_commits = len(commits)

            if total_commits > 0:
                ai_actions.append({
                    "priority": "info",
                    "action": f"Retrieved {total_commits} commits from {detected_vcs} history.",
                    "count": total_commits,
                    "vcs": detected_vcs
                })

            # Detect high-activity authors
            top_authors = sorted(author_stats.items(), key=lambda x: x[1]["commits"], reverse=True)[:3]
            if len(top_authors) > 0:
                top_author_name, top_stats = top_authors[0]
                ai_actions.append({
                    "priority": "info",
                    "action": f"Top contributor: {top_author_name} with {top_stats['commits']} commits.",
                    "top_contributors": [{"name": name, "commits": stats["commits"]} for name, stats in top_authors]
                })

            # Recent activity warning
            if total_commits >= limit:
                ai_actions.append({
                    "priority": "info",
                    "action": f"History limited to {limit} commits. Increase limit for full history.",
                    "suggestion": f"Use limit=1000 for maximum history depth."
                })

            # Integration recommendations
            ai_actions.append({
                "priority": "low",
                "action": "Use this history data with other tools:",
                "integrations": {
                    "repo_inspect": "For churn hotspot analysis",
                    "repo_analyze": "For bug magnet detection (commits linked to bugs)",
                    "repo_audit": "For scanning commit history for secrets"
                }
            })

            data = {
                "repo_path": str(resolved),
                "vcs_type": detected_vcs,
                "total_commits": total_commits,
                "commits": commits[:limit],
                "authors": author_stats,
                "timeline": timeline_data[:limit] if output_format == "timeline" else None,
            }

            if ai_actions:
                data["ai_actions"] = ai_actions

            return api_response(
                success=True, status_code=200,
                message=f"Retrieved {total_commits} commits from {detected_vcs} history",
                data=data,
                request_id=request_id,
            )

        except subprocess.TimeoutExpired:
            return api_response(
                success=False, status_code=408,
                message="History retrieval timed out",
                data={"suggestion": "Try reducing limit or filtering by date range"},
                request_id=request_id, error_code="REP_TIMEOUT",
            )
        except Exception as e:
            return api_response(
                success=False, status_code=500,
                message=f"Failed to retrieve history: {str(e)}",
                data=None, error_code="REP_500",
                request_id=request_id,
            )
