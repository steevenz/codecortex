#!/usr/bin/env python
"""
/**
 * @project   CodeCortex
 * @package   CLI
 * @standard  Aegis-CrossStack-v1.0
 * * CodeCortex CLI — terminal interface for MCP tools.
 *   Usage: codecortex --version
 *          codecortex --init /path/to/project
 *          codecortex --search "query"
 *          codecortex --analyze /path
 *          codecortex --mcp (run MCP stdio server)
 *          codecortex --serve (run HTTP server)
 *          codecortex --list-repos
 *          codecortex --status
 */
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path

# Ensure project root is in Python path
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def main():
    parser = argparse.ArgumentParser(
        description="CodeCortex — Universal Code Intelligence Engine",
        prog="codecortex",
    )
    
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--init", metavar="PATH", help="Initialize a repository for analysis")
    parser.add_argument("--search", metavar="QUERY", help="Semantic search codebase")
    parser.add_argument("--analyze", metavar="PATH", help="Full analysis pipeline")
    parser.add_argument("--mcp", action="store_true", help="Run MCP stdio server")
    parser.add_argument("--serve", action="store_true", help="Run HTTP server")
    parser.add_argument("--list-repos", action="store_true", help="List indexed repositories")
    parser.add_argument("--status", action="store_true", help="Check server status")
    parser.add_argument("--sync", metavar="PATH", help="Sync a repository")
    parser.add_argument("--sync-incremental", metavar="PATH", help="Incremental git diff sync")
    parser.add_argument("--rename", nargs=3, metavar=("PATH", "OLD", "NEW"), help="Rename symbol across files")
    parser.add_argument("--audit", metavar="PATH", help="Git security audit")
    parser.add_argument("--batch", metavar="JSON", help="Batch file operations (JSON)")
    parser.add_argument("--repositories", "--projects", action="store_true", dest="repositories", help="List all registered repositories")
    parser.add_argument("--workspaces", action="store_true", help="(Coming soon) List all workspaces")
    parser.add_argument("--compact", metavar="REPO_ID", help="Compact database for a project")
    parser.add_argument("--cleanup", metavar="REPO_ID", help="Delete all data for a project (IRREVERSIBLE)")
    parser.add_argument("--takeout", metavar="REPO_ID", help="Export project data to portable file")
    parser.add_argument("--import-dump", metavar="FILE", help="Import project from takeout dump file")
    parser.add_argument("--output-dir", metavar="DIR", default="database/exports", help="Output directory for takeout exports")
    parser.add_argument("--db", metavar="PATH", help="Custom database path")
    
    args = parser.parse_args()
    
    if args.version:
        from src.core import load_version
        print(f"CodeCortex v{load_version()}")
        return

    if args.mcp:
        os.environ["CODECORTEX_TRANSPORT"] = "stdio"
        from src.main import mcp
        mcp.run()
        return

    if args.serve:
        os.environ["CODECORTEX_TRANSPORT"] = "http"
        from scripts.server.http import main as run_server
        run_server()
        return

    # Commands that need db path
    db_path = args.db or os.getenv("CODECORTEX_DB_PATH")
    
    if args.init:
        import asyncio
        from src.main import create_orchestrator
        orch = create_orchestrator(db_path)
        repo_id = asyncio.run(orch.repo_service.initialize(args.init))
        print(json.dumps({"status": "initialized", "repository_id": repo_id}, indent=2))
        orch.db.close()
        return

    if args.sync:
        import asyncio
        from src.main import create_orchestrator
        orch = create_orchestrator(db_path)
        repo_id = asyncio.run(orch.repo_service.sync_repository(args.sync))
        print(json.dumps({"status": "synced", "repository_id": repo_id}, indent=2))
        orch.db.close()
        return

    if args.sync_incremental:
        import asyncio
        from src.main import create_orchestrator
        orch = create_orchestrator(db_path)
        repo_id, changed = asyncio.run(orch.repo_service.sync_repository_incremental(args.sync_incremental))
        print(json.dumps({"status": "synced", "repository_id": repo_id, "changed": len(changed)}, indent=2))
        orch.db.close()
        return

    if args.search:
        import asyncio
        from src.domain.codeindex.infrastructure.embeddings import semantic_search, generate_embedding
        import tempfile
        db = db_path or os.getenv("CODECORTEX_DB_PATH") or "database/codecortex.db"
        results = asyncio.run(asyncio.to_thread(semantic_search, args.search, db))
        print(json.dumps({"query": args.search, "results": results}, indent=2))
        return

    if args.analyze:
        import asyncio
        from src.main import create_orchestrator
        orch = create_orchestrator(db_path)
        result = asyncio.run(orch.analyze(args.analyze, dry_run=False))
        print(json.dumps(result, indent=2, default=str))
        orch.db.close()
        return

    if args.list_repos:
        from src.domain.coderepository.application.registry import RegistryManager
        repos = RegistryManager.list_all()
        print(json.dumps({"repositories": repos, "count": len(repos)}, indent=2))
        return

    if args.status:
        try:
            import urllib.request
            resp = urllib.request.urlopen("http://127.0.0.1:8001/status", timeout=3)
            print(resp.read().decode())
        except Exception:
            print(json.dumps({"status": "offline", "message": "HTTP server not running on port 8001"}))
        return

    if args.rename:
        path, old, new = args.rename
        import asyncio
        from src.main import create_orchestrator
        orch = create_orchestrator(db_path)
        from src.domain.filesystem.application.service import FilesystemService
        from src.domain.coderepository.application.git_service import GitService
        from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
        from src.domain.codegraph.application.service import CodeGraphService
        from src.domain.coderefactor.application.service import CodeRefactorService
        from src.core.database import DatabaseManager
        db = DatabaseManager(db_path) if db_path else orch.db
        store = SQLiteCodeRepositoryStore(db)
        fs = FilesystemService(db, store)
        git = GitService(store)
        cg = CodeGraphService(db)
        svc = CodeRefactorService(db, fs, git, cg)
        result = asyncio.run(svc.rename_symbol(path, old, new, dry_run=False))
        print(json.dumps({"status": result.status, "message": result.message}, indent=2))
        orch.db.close()
        return

    if args.audit:
        import asyncio
        from src.domain.coderepository.infrastructure.git_history import GitHistoryWorker
        from src.core.database import DatabaseManager
        from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
        db = DatabaseManager(db_path) if db_path else DatabaseManager()
        store = SQLiteCodeRepositoryStore(db)
        worker = GitHistoryWorker(store, Path(args.audit))
        findings = worker.audit_commits("cli-audit", limit=100)
        print(json.dumps({"findings": findings, "count": len(findings)}, indent=2))
        db.close()
        return

    if args.batch:
        ops = json.loads(args.batch)
        from src.domain.filesystem.infrastructure.watcher import batch_file_operations
        results = batch_file_operations(ops, Path.cwd())
        print(json.dumps({"results": results}, indent=2))
        return

    if args.compact:
        from src.core.database import DatabaseManager
        from src.core.database_cleanup import compact_database
        db = DatabaseManager(args.db)
        result = compact_database(db.conn)
        print(json.dumps(result, indent=2))
        db.close()
        return

    if args.repositories:
        from src.domain.coderepository.application.registry import RegistryManager
        from scripts.formatter import print_project_list
        repos = RegistryManager.list_all()
        print_project_list(repos)
        return

    if args.workspaces:
        from scripts.formatter import print_workspace_list
        print_workspace_list([])
        return

    if args.cleanup:
        from src.core.database import DatabaseManager
        from src.core.database_cleanup import cleanup_project
        db = DatabaseManager(args.db)
        result = cleanup_project(db.conn, args.cleanup)
        print(json.dumps(result, indent=2))
        db.close()
        return

    if args.takeout:
        from src.core.database import DatabaseManager
        from src.core.takeout import takeout_project
        db = DatabaseManager(args.db)
        result = takeout_project(db.conn, args.takeout, args.output_dir)
        print(json.dumps(result, indent=2))
        db.close()
        return

    if args.import_dump:
        from src.core.database import DatabaseManager
        from src.core.takeout import import_project
        db = DatabaseManager(args.db)
        result = import_project(db.conn, args.import_dump)
        print(json.dumps(result, indent=2))
        db.close()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
