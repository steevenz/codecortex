from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional


DOMAIN = "repository"
ALIASES = ["repo"]


# ── JSON Output ───────────────────────────────────────────

def output(data: Any, pretty: bool = True) -> None:
    """Print JSON to stdout as UTF-8 bytes (avoids Windows cp1252 issues)."""
    kwargs: Dict[str, Any] = {"ensure_ascii": False}
    if pretty:
        kwargs["indent"] = 2
    text = json.dumps(data, **kwargs, default=str)
    buf = sys.stdout.buffer
    buf.write(text.encode("utf-8", errors="replace"))
    buf.write(b"\n")
    buf.flush()


def ok(message: str, data: Any = None) -> Dict[str, Any]:
    return {"success": True, "status_code": 200, "message": message, "data": data}


def err(message: str, code: str = "CLI_ERROR", status: int = 400) -> Dict[str, Any]:
    return {"success": False, "status_code": status, "message": message, "data": None, "error_code": code}


# ── Async Runner ──────────────────────────────────────────

def run_async(coro):
    """Safely run a coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)


# ══════════════════════════════════════════════════════════════
# REPOSITORY (13 actions)
# ══════════════════════════════════════════════════════════════

def cmd_repo_init(args_ns: argparse.Namespace) -> Dict:
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        resolved = str(Path(args_ns.path).resolve())
        existing_id = orch.get_repo_id(resolved)
        if existing_id and not getattr(args_ns, "force", False):
            return ok("Repository already initialized", {"repo_id": existing_id})
        remote_url = getattr(args_ns, "remote_url", None)
        if not remote_url:
            try:
                import subprocess
                result = subprocess.run(
                    ["git", "-C", resolved, "config", "--get", "remote.origin.url"],
                    capture_output=True, text=True, shell=False, timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    remote_url = result.stdout.strip()
            except Exception:
                pass
        repo_id = run_async(orch.repo_service.initialize(
            resolved,
            remote_url=remote_url,
        ))
        tree = orch.fs_service.get_codebase_tree(path=resolved)
        return ok("Repository initialized", {"repo_id": repo_id, "tree": tree})
    except Exception as e:
        return err(f"Init failed: {e}", "INIT_ERROR", 500)
    finally:
        orch.db.close()


def cmd_repo_inspect(args_ns: argparse.Namespace) -> Dict:
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        resolved = str(Path(args_ns.path).resolve())
        rid = orch.get_repo_id(resolved)
        data = {"target": resolved, "repo_id": rid, "exists": os.path.exists(resolved)}
        if rid:
            nfiles = orch.db.conn.execute(
                "SELECT COUNT(*) FROM files WHERE repository_id=? AND is_deleted = 0", (rid,)
            ).fetchone()[0]
            nsym = orch.db.conn.execute(
                "SELECT COUNT(*) FROM symbols WHERE repository_id=?", (rid,)
            ).fetchone()[0]
            data["stats"] = {"files": nfiles, "symbols": nsym}
        return ok("Inspection complete", data)
    except Exception as e:
        return err(f"Inspect failed: {e}", "INSPECT_ERROR", 500)
    finally:
        orch.db.close()


def cmd_repo_analyze(args_ns: argparse.Namespace) -> Dict:
    import asyncio
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        resolved = str(Path(args_ns.path).resolve())
        result = run_async(orch.analyze(
            resolved, dry_run=getattr(args_ns, "dry_run", False),
            max_depth=getattr(args_ns, "max_depth", None),
            include_codemap=getattr(args_ns, "codemap", False),
        ))
        return ok("Analysis complete", result)
    except Exception as e:
        return err(f"Analysis failed: {e}", "ANALYZE_ERROR", 500)
    finally:
        orch.db.close()


def cmd_repo_sync(args_ns: argparse.Namespace) -> Dict:
    import asyncio
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        resolved = str(Path(args_ns.path).resolve())
        repo = orch.repo_store.get_repository_by_path(resolved)
        if not repo:
            return err(f"Repository not found at {resolved}", "REPO_NOT_FOUND", 404)
        rid = repo.get("id")
        if getattr(args_ns, "dry_run", False):
            changed = orch.db.conn.execute(
                "SELECT COUNT(*) FROM files WHERE repository_id=? AND updated_at > COALESCE(indexed_at, '1970-01-01')",
                (rid,),
            ).fetchone()[0]
            return ok("Dry run — would sync", {"changed_files": changed, "repo_id": rid})
        rid = run_async(orch.repo_service.sync_repository(resolved))
        run_async(orch.index_service.index_repository(rid))
        return ok("Sync complete", {"repo_id": rid})
    except Exception as e:
        return err(f"Sync failed: {e}", "SYNC_ERROR", 500)
    finally:
        orch.db.close()


def cmd_repo_audit(args_ns: argparse.Namespace) -> Dict:
    import os
    from pathlib import Path
    from src.modules.coderepository.core.utils import scan_secrets
    try:
        resolved = str(Path(args_ns.path).resolve())
        findings = scan_secrets(
            resolved,
            exclude_paths=getattr(args_ns, "exclude", None),
        )
        return ok("Audit complete", {
            "target": resolved, "findings": findings,
            "count": len(findings) if isinstance(findings, list) else 0,
        })
    except Exception as e:
        return err(f"Audit failed: {e}", "AUDIT_ERROR", 500)


def cmd_repo_audit_with_orch(args_ns: argparse.Namespace) -> Dict:
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        resolved = str(Path(args_ns.path).resolve())
        findings = orch.repo_service.audit_project(
            resolved,
            exclude_paths=getattr(args_ns, "exclude", None),
        )
        return ok("Audit complete", {
            "target": resolved, "findings": findings,
            "count": len(findings) if isinstance(findings, list) else 0,
        })
    except Exception as e:
        return err(f"Audit failed: {e}", "AUDIT_ERROR", 500)
    finally:
        orch.db.close()


def cmd_repo_staleness(args_ns: argparse.Namespace) -> Dict:
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        resolved = str(Path(args_ns.path).resolve())
        rid = orch.get_repo_id(resolved)
        if not rid:
            return err("Repository not found", "REPO_NOT_FOUND", 404)
        total = orch.db.conn.execute(
            "SELECT COUNT(*) FROM files WHERE repository_id=?", (rid,),
        ).fetchone()[0]
        return ok("Staleness check complete", {"repo_id": rid, "total_files": total})
    except Exception as e:
        return err(f"Staleness check failed: {e}", "STALE_ERROR", 500)
    finally:
        orch.db.close()


def cmd_repo_history(args_ns: argparse.Namespace) -> Dict:
    from src.main import create_orchestrator
    from src.modules.coderepository.adapters.git.history import GitHistoryWorker
    orch = create_orchestrator()
    try:
        resolved = str(Path(args_ns.path).resolve())
        repo = orch.repo_store.get_repository_by_path(resolved)
        if not repo:
            return err(f"Repository not found at {resolved}", "REPO_NOT_FOUND", 404)
        limit = getattr(args_ns, "limit", 100)
        worker = GitHistoryWorker(orch.repo_store, Path(resolved))
        commits = worker.get_commit_log(limit=limit)
        author_filter = getattr(args_ns, "author", None)
        if author_filter:
            commits = [c for c in commits if author_filter.lower() in (c.get("author", "") + c.get("email", "")).lower()]
        return ok(f"Found {len(commits)} commits", {
            "commits": commits,
            "total": len(commits),
            "repo_path": str(resolved),
        })
    except Exception as e:
        return err(f"History failed: {e}", "HISTORY_ERROR", 500)
    finally:
        orch.db.close()


def cmd_repo_list(args_ns: argparse.Namespace) -> Dict:
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        repos = orch.db.conn.execute(
            "SELECT id, root_path, vcs_type, created_at, updated_at FROM repositories ORDER BY created_at DESC"
        ).fetchall()
        return ok(f"Found {len(repos)} repositories", {
            "repositories": [dict(r) for r in repos], "count": len(repos),
        })
    except Exception as e:
        return err(f"List failed: {e}", "LIST_ERROR", 500)
    finally:
        orch.db.close()


def cmd_repo_compact(args_ns: argparse.Namespace) -> Dict:
    from src.core.database import compact_database
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        result = compact_database(orch.db.conn)
        return ok("Database compacted", result)
    except Exception as e:
        return err(f"Compact failed: {e}", "COMPACT_ERROR", 500)
    finally:
        orch.db.close()


def cmd_repo_cleanup(args_ns: argparse.Namespace) -> Dict:
    from src.core.database import cleanup_project
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        result = cleanup_project(str(orch.db._db_path))
        return ok("Project cleaned up", result)
    except Exception as e:
        return err(f"Cleanup failed: {e}", "CLEANUP_ERROR", 500)
    finally:
        orch.db.close()


def cmd_repo_dump(args_ns: argparse.Namespace) -> Dict:
    from src.core.database import takeout_project
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        out_dir = getattr(args_ns, "output_dir", "database/exports")
        result = takeout_project(str(orch.db._db_path), out_dir)
        return ok("Project exported", result)
    except Exception as e:
        return err(f"Dump failed: {e}", "DUMP_ERROR", 500)
    finally:
        orch.db.close()


def cmd_repo_restore(args_ns: argparse.Namespace) -> Dict:
    from src.core.database import import_project
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        result = import_project(orch.db.conn, args_ns.file)
        return ok("Project restored", result)
    except Exception as e:
        return err(f"Restore failed: {e}", "RESTORE_ERROR", 500)
    finally:
        orch.db.close()


def cmd_repo_git(args_ns: argparse.Namespace) -> Dict:
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        resolved = str(Path(args_ns.path).resolve())
        repo = orch.repo_store.get_repository_by_path(resolved)
        if not repo:
            return err(f"Repository not found at {resolved}", "REPO_NOT_FOUND", 404)
        git_action = args_ns.git_action
        if git_action == "log":
            from src.modules.coderepository.adapters.git.history import GitHistoryWorker
            worker = GitHistoryWorker(orch.repo_store, Path(resolved))
            limit = getattr(args_ns, "limit", 50)
            commits = worker.get_commit_log(limit=limit)
            return ok(f"Found {len(commits)} commits", {"commits": commits})
        elif git_action == "diff":
            from src.modules.coderepository.adapters.git.history import GitHistoryWorker
            worker = GitHistoryWorker(orch.repo_store, Path(resolved))
            commits = worker.get_commit_log(limit=1)
            return ok("Latest diff", {"diff": commits[0] if commits else None})
        elif git_action == "branches":
            import subprocess
            result = subprocess.run(
                ["git", "-C", resolved, "branch", "-a"],
                capture_output=True, text=True, shell=False,
            )
            branches = [b.strip().removeprefix("* ") for b in result.stdout.strip().splitlines() if b.strip()]
            return ok(f"Found {len(branches)} branches", {"branches": branches})
        else:
            return err(f"Unknown git action: {git_action}", "GIT_ERROR")
    except Exception as e:
        return err(f"Git failed: {e}", "GIT_ERROR", 500)
    finally:
        orch.db.close()


def cmd_repo_svn(args_ns: argparse.Namespace) -> Dict:
    from src.modules.coderepository.adapters.svn.service import SvnService
    try:
        svn = SvnService()
        result = svn.info(args_ns.url)
        return ok("SVN info retrieved", result)
    except Exception as e:
        return err(f"SVN failed: {e}", "SVN_ERROR", 500)


def cmd_repo_deduplicate(args_ns: argparse.Namespace) -> Dict:
    """Detect and merge duplicate repository entries in the database."""
    from src.main import create_orchestrator
    from pathlib import Path as _Path
    orch = create_orchestrator()
    conn = orch.db.conn
    try:
        dry_run = not getattr(args_ns, "apply", False)
        all_repos = [
            dict(r) for r in conn.execute("SELECT * FROM repositories").fetchall()
        ]
        duplicates = []
        seen_paths = {}
        seen_urls = {}

        # 1. Detect case-insensitive path duplicates
        for r in all_repos:
            rp = r["root_path"]
            key = rp.lower().replace("\\", "/").rstrip("/")
            if key in seen_paths:
                duplicates.append((seen_paths[key], r))
            else:
                seen_paths[key] = r

        # 2. Detect subdirectory monorepo duplicates
        for r in all_repos:
            for o in all_repos:
                if r["id"] == o["id"]:
                    continue
                try:
                    _Path(o["root_path"]).resolve().relative_to(_Path(r["root_path"]).resolve())
                    has_own_vcs = (
                        (_Path(o["root_path"]).resolve() / ".git").is_dir()
                        or (_Path(o["root_path"]).resolve() / ".svn").is_dir()
                    )
                    if not has_own_vcs and (r, o) not in duplicates and (o, r) not in duplicates:
                        duplicates.append((r, o))
                except ValueError:
                    pass

        # 3. Detect remote_url duplicates
        for r in all_repos:
            url = r.get("vcs_url")
            if not url:
                continue
            for o in all_repos:
                if r["id"] == o["id"]:
                    continue
                if o.get("vcs_url") == url and (r, o) not in duplicates and (o, r) not in duplicates:
                    duplicates.append((r, o))

        if not duplicates:
            return ok("No duplicates found", {"duplicates": [], "merged": 0})

        # FK tables to update
        fk_tables = [
            "files", "symbols", "directories", "commits", "manifest_entries",
            "file_commits", "edges", "edge_hashes", "embeddings",
            "index_query_cache", "index_stats", "insights", "audit_findings",
            "execution_tasks", "test_results", "file_tree", "disk_usage",
            "repo_sync_state", "device_path_mappings",
        ]
        col_map = {"device_path_mappings": "repo_id"}

        merged_count = 0
        merge_actions = []
        removed_ids = set()  # track IDs already deleted

        for canonical, duplicate in duplicates:
            cid = canonical["id"]
            did = duplicate["id"]

            # Skip if either ID already processed
            if cid in removed_ids or did in removed_ids:
                continue

            # Pick canonical: prefer non-null vcs_url, then most FK refs
            fk_counts = {}
            for repo_id in (cid, did):
                total = 0
                for tbl in fk_tables:
                    col = col_map.get(tbl, "repository_id")
                    try:
                        row = conn.execute(
                            f"SELECT COUNT(*) FROM {tbl} WHERE {col} = ?", (repo_id,)
                        ).fetchone()
                        total += row[0] if row else 0
                    except Exception:
                        pass
                fk_counts[repo_id] = total

            if fk_counts.get(did, 0) > fk_counts.get(cid, 0):
                cid, did = did, cid

            if dry_run:
                merge_actions.append({
                    "keep_id": cid, "keep_path": canonical["root_path"],
                    "remove_id": did, "remove_path": duplicate["root_path"],
                    "fk_records_to_move": fk_counts.get(did, 0),
                })
                continue

            total_moved = 0
            for tbl in fk_tables:
                col = col_map.get(tbl, "repository_id")
                try:
                    cur = conn.execute(
                        f"UPDATE {tbl} SET {col} = ? WHERE {col} = ?",
                        (cid, did),
                    )
                    total_moved += cur.rowcount
                except Exception:
                    pass

            conn.execute("DELETE FROM repositories WHERE id = ?", (did,))
            conn.commit()
            removed_ids.add(did)
            merged_count += 1
            merge_actions.append({
                "keep_id": cid, "remove_id": did,
                "fk_records_moved": total_moved,
            })

        mode = "dry-run" if dry_run else "merged"
        return ok(f"{mode.capitalize()} {len(duplicates)} duplicate pair(s)", {
            "mode": mode, "duplicates": len(duplicates),
            "merged": merged_count, "actions": merge_actions,
        })
    except Exception as e:
        return err(f"Deduplicate failed: {e}", "DEDUP_ERROR", 500)
    finally:
        orch.db.close()


def cmd_repo_link(args_ns: argparse.Namespace) -> Dict:
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        path = str(Path(args_ns.path).resolve())
        remote_url = args_ns.remote_url
        existing = orch.repo_store.get_repository_by_path(path)
        if not existing:
            return err(f"Repository not found at {path}. Init it first.", "REPO_NOT_FOUND", 404)
        if existing.get("vcs_url"):
            return ok("Already linked", {"repo_id": existing["id"], "vcs_url": existing["vcs_url"]})
        orch.repo_store.update_vcs_metadata(existing["id"], {"vcs_url": remote_url})
        return ok("Linked", {"repo_id": existing["id"], "vcs_url": remote_url})
    except Exception as e:
        return err(f"Link failed: {e}", "LINK_ERROR", 500)
    finally:
        orch.db.close()


COMMANDS = {
    "init": cmd_repo_init,
    "inspect": cmd_repo_inspect,
    "analyze": cmd_repo_analyze,
    "sync": cmd_repo_sync,
    "audit": cmd_repo_audit,
    "staleness": cmd_repo_staleness,
    "history": cmd_repo_history,
    "list": cmd_repo_list,
    "compact": cmd_repo_compact,
    "cleanup": cmd_repo_cleanup,
    "dump": cmd_repo_dump,
    "restore": cmd_repo_restore,
    "git": cmd_repo_git,
    "svn": cmd_repo_svn,
    "link": cmd_repo_link,
    "deduplicate": cmd_repo_deduplicate,
}


def build_parser(subparsers) -> None:
    p = subparsers.add_parser("repository", aliases=["repo"], help="Repository lifecycle and analysis")
    sp = p.add_subparsers(dest="repo_action", required=True)

    i = sp.add_parser("init", help="Initialize a repository for analysis")
    i.add_argument("path", help="Path to repository")
    i.add_argument("--vcs-type", default="git", choices=["git", "svn"], help="VCS type")
    i.add_argument("--remote-url", help="Remote URL")
    i.add_argument("--force", action="store_true", help="Re-initialize if exists")

    sp.add_parser("inspect", help="Inspect repository metadata").add_argument("path", help="Path to repository")

    a = sp.add_parser("analyze", help="Full analysis pipeline")
    a.add_argument("path", help="Path to repository")
    a.add_argument("--dry-run", action="store_true", help="Analyze existing data without re-indexing")
    a.add_argument("--max-depth", type=int, help="Max directory depth")
    a.add_argument("--codemap", action="store_true", help="Include symbol codemap")

    s = sp.add_parser("sync", help="Sync repository")
    s.add_argument("path", help="Path to repository")
    s.add_argument("--dry-run", action="store_true", help="Show what would sync")

    sp.add_parser("audit", help="Security audit").add_argument("path", help="Path to repository")

    sp.add_parser("staleness", help="Check staleness").add_argument("path", help="Path to repository")

    h = sp.add_parser("history", help="Retrieve commit history and author statistics")
    h.add_argument("path", help="Path to repository")
    h.add_argument("--limit", type=int, default=100, help="Maximum commits to retrieve")
    h.add_argument("--author", help="Filter by author name or email")

    sp.add_parser("list", help="List all registered repositories")

    sp.add_parser("compact", help="Compact database")

    sp.add_parser("cleanup", help="Delete project data").add_argument("repo_id", help="Repository ID")

    d = sp.add_parser("dump", help="Export project data")
    d.add_argument("repo_id", help="Repository ID")
    d.add_argument("--output-dir", default="database/exports", help="Output directory")

    sp.add_parser("restore", help="Import project from dump").add_argument("file", help="Dump file path")

    g = sp.add_parser("git", help="Git operations")
    g.add_argument("path", help="Path to repository")
    g.add_argument("git_action", choices=["log", "diff", "branches"], help="Git action")
    g.add_argument("--limit", type=int, default=50, help="Commit limit (log only)")

    sv = sp.add_parser("svn", help="SVN operations")
    sv.add_argument("url", help="SVN repository URL")

    lk = sp.add_parser("link", help="Associate a repo path with a remote URL (cross-device identity)")
    lk.add_argument("path", help="Repository path")
    lk.add_argument("remote_url", help="Git remote origin URL")

    dd = sp.add_parser("deduplicate", help="Detect and merge duplicate repository entries")
    dd.add_argument("--apply", action="store_true", help="Apply merge (default is dry-run preview)")
