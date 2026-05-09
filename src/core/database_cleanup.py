"""
/**
 * @project   CodeCortex
 * @package   Core/Database
 * @standard  Aegis-CrossStack-v1.0
 * * Manual database compaction and project cleanup.
 *   User-triggered, no automatic TTL.
 */
"""

import logging
from typing import Optional

logger = logging.getLogger("CodeCortex.Core.Database.Cleanup")


def compact_database(conn) -> dict:
    """
    Compact the SQLite database to reclaim space.
    Runs VACUUM and reindexes.
    """
    import os
    
    db_path = None
    try:
        cursor = conn.execute("PRAGMA database_list")
        row = cursor.fetchone()
        if row:
            db_path = row[2]
    except Exception:
        pass
    
    size_before = os.path.getsize(db_path) if db_path and os.path.exists(db_path) else 0
    
    # Must be outside any transaction for VACUUM
    conn.rollback()
    conn.execute("VACUUM")
    conn.execute("REINDEX")
    conn.execute("ANALYZE")
    conn.commit()
    
    size_after = os.path.getsize(db_path) if db_path and os.path.exists(db_path) else 0
    saved = size_before - size_after
    
    return {
        "action": "compact",
        "size_before": size_before,
        "size_after": size_after,
        "space_reclaimed": max(0, saved),
        "space_reclaimed_mb": round(max(0, saved) / (1024 * 1024), 2),
    }


def cleanup_project(conn, repo_id: str) -> dict:
    """
    Delete ALL data for a specific repository/project.
    Removes: files, symbols, edges, insights, commits, manifest, directories, repo entry.
    """
    results = {}
    
    # Verify repo exists
    cursor = conn.execute("SELECT name, root_path FROM repositories WHERE id = ?", (repo_id,))
    repo = cursor.fetchone()
    if not repo:
        return {"action": "cleanup", "error": f"Repository {repo_id} not found"}
    
    repo_name = repo[0]
    repo_path = repo[1]
    
    # Count before deletion
    counts = {}
    for table in ["edges", "insights", "symbols", "file_commits", "commits", "manifest_entries", "files", "directories"]:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE repository_id = ?", (repo_id,))
        counts[table] = cursor.fetchone()[0]
    
    # Delete in dependency order
    conn.execute("DELETE FROM edges WHERE repository_id = ?", (repo_id,))
    conn.execute("DELETE FROM insights WHERE repository_id = ?", (repo_id,))
    conn.execute("DELETE FROM symbols WHERE repository_id = ?", (repo_id,))
    conn.execute("DELETE FROM file_commits WHERE repository_id = ?", (repo_id,)) 
    conn.execute("DELETE FROM commits WHERE repository_id = ?", (repo_id,))
    conn.execute("DELETE FROM manifest_entries WHERE repository_id = ?", (repo_id,))
    conn.execute("DELETE FROM execution_tasks WHERE repository_id = ?", (repo_id,))
    conn.execute("DELETE FROM files WHERE repository_id = ?", (repo_id,))
    conn.execute("DELETE FROM directories WHERE repository_id = ?", (repo_id,))
    conn.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))
    
    conn.commit()
    
    # Also clean from global registry
    try:
        from src.domain.coderepository.application.registry import RegistryManager
        RegistryManager.unregister(repo_path)
    except Exception:
        pass
    
    results = {
        "action": "cleanup",
        "repository": repo_name,
        "repo_id": repo_id,
        "deleted": counts,
        "total_entries": sum(counts.values()),
    }
    
    logger.info(f"Cleaned up project '{repo_name}' ({repo_id}): {sum(counts.values())} entries removed")
    return results
