"""
/**
 * @project   CodeCortex
 * @package   Core/Database
 * @standard  Aegis-CrossStack-v1.0
 * * Project Takeout & Import — portable project data export/import.
 *   Dumps all project data to a portable JSON file.
 *   Imports back from that file.
 */
"""

import json
import uuid
import logging
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger("CodeCortex.Core.Database.Takeout")


def takeout_project(conn, repo_id: str, output_dir: str) -> dict:
    """Export all data for a project to a portable JSON dump file."""
    cursor = conn.execute("SELECT name, root_path FROM repositories WHERE id = ?", (repo_id,))
    repo = cursor.fetchone()
    if not repo:
        return {"action": "takeout", "error": f"Repository {repo_id} not found"}
    
    repo_name = repo[0]
    repo_path = repo[1]
    
    # Export data — all tables with repository_id
    tables = {
        "repositories": {"column": "id"},
        "directories": {"column": "repository_id"},
        "files": {"column": "repository_id"},
        "symbols": {"column": "repository_id"},
        "edges": {"column": "repository_id"},
        "insights": {"column": "repository_id"},
        "manifest_entries": {"column": "repository_id"},
        "commits": {"column": "repository_id"},
        "file_commits": {"column": "repository_id"},
    }
    dump = {"repo_id": repo_id, "repo_name": repo_name, "repo_path": repo_path}
    
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in cursor.fetchall()}
    
    for table, config in tables.items():
        if table not in existing_tables:
            dump[table] = []
            continue
        col = config["column"]
        try:
            cursor = conn.execute(f"SELECT * FROM {table} WHERE {col} = ?", (repo_id,))
            rows = [dict(row) for row in cursor.fetchall()]
            dump[table] = rows
        except Exception as e:
            logger.warning(f"Skip table {table}: {e}")
            dump[table] = []
    
    output_path = Path(output_dir) / f"codecortex_takeout_{repo_name}_{repo_id[:8]}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dump, f, indent=2, default=str)
    
    file_size = output_path.stat().st_size
    
    logger.info(f"Takeout completed: {output_path} ({file_size} bytes, {sum(len(v) for k,v in dump.items() if isinstance(v, list))} records)")
    return {
        "action": "takeout",
        "repository": repo_name,
        "repo_id": repo_id,
        "output_path": str(output_path),
        "file_size": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "tables": {t: len(dump[t]) for t in tables if t in dump},
        "total_records": sum(len(dump[t]) for t in tables if t in dump),
    }


def import_project(conn, import_path: str) -> dict:
    """Import a project from a takeout dump file."""
    path = Path(import_path)
    if not path.exists():
        return {"action": "import", "error": f"File not found: {import_path}"}
    
    with open(path, "r", encoding="utf-8") as f:
        dump = json.load(f)
    
    repo_id = dump.get("repo_id")
    repo_name = dump.get("repo_name", "unknown")
    repo_path = dump.get("repo_path", "")
    
    if not repo_id:
        return {"action": "import", "error": "Invalid dump file: missing repo_id"}
    
    # Import in dependency order — delete stale rows first for true disaster recovery
    counts = {}
    
    # repositories (upsert)
    existing = conn.execute("SELECT id FROM repositories WHERE id = ?", (repo_id,)).fetchone()
    if existing:
        conn.execute("UPDATE repositories SET name = ?, root_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                     (repo_name, repo_path, repo_id))
    else:
        repo_row = dump.get("repositories", [{}])[0] if dump.get("repositories") else {}
        conn.execute("INSERT OR REPLACE INTO repositories (id, name, root_path, last_indexed_at, created_at, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                     (repo_id, repo_name, repo_path, repo_row.get("last_indexed_at")))
    counts["repositories"] = 1
    
    # Import child tables — delete-then-insert for clean restore
    table_order = ["directories", "files", "symbols", "edges", "insights", "manifest_entries", "commits", "file_commits"]
    for table in table_order:
        rows = dump.get(table, [])
        if not rows:
            counts[table] = 0
            continue
        
        # Wipe stale rows before inserting fresh data
        conn.execute(f"DELETE FROM {table} WHERE repository_id = ?", (repo_id,))
        
        for row in rows:
            row["repository_id"] = repo_id
            
            columns = [c for c in row.keys() if c != "id"] + ["id"]
            placeholders = ", ".join(["?" for _ in columns])
            col_names = ", ".join(columns)
            
            try:
                values = [row.get(c) for c in columns]
                conn.execute(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", values)
            except Exception as e:
                logger.warning(f"Import row failed for {table}: {e}")
        
        counts[table] = len(rows)
    
    conn.commit()
    
    total = sum(counts.values())
    logger.info(f"Import completed: {repo_name} ({total} records restored)")
    
    return {
        "action": "import",
        "repository": repo_name,
        "repo_id": repo_id,
        "source": import_path,
        "tables": counts,
        "total_records": total,
    }
