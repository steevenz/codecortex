"""
Class Search - Regex-based search and replace across the codebase using DB persistence.

:project: CodeCortex
:package: Modules.Codetester.Services.Search
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeTester-v1.0
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Iterator
from src.core.database import DatabaseManager
from src.core.logging import get_logger
from src.core.logging.event_logger import log_event

logger = get_logger("CodeCortex.Domain.CodeTester.Search")

class Search:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def _log_event(self, level: str, event_code: str, context: Dict, request_id: Optional[str] = None):
        log_event(level, event_code, context, request_id=request_id, logger=getattr(self, 'logger', None))

    def search_code(self, repo_id: str, query: str, is_regex: bool = True, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Search across all files in a repository using DB-cached content."""
        try:
            # 1. Fetch all code content
            # Optimization: Use SQL LIKE or REGEXP if available, but Python 're' is more consistent across environments.
            # 1. Fetch all code content in batches to prevent memory overflow
            cursor = self.db.conn.execute(
                """
                SELECT f.id, f.name, f.content, d.relative_path
                FROM files f
                JOIN directories d ON d.id = f.directory_id
                WHERE f.repository_id = ? AND f.is_deleted = 0 AND f.content IS NOT NULL
                """,
                (repo_id,)
            )

            results = []
            flags = 0 if case_sensitive else re.IGNORECASE

            pattern = query if is_regex else re.escape(query)
            regex = re.compile(pattern, flags)

            while True:
                files = cursor.fetchmany(100)
                if not files:
                    break

                for f in files:
                    content = f["content"]
                    matches = list(regex.finditer(content))
                    if matches:
                        file_results = {
                            "file_id": f["id"],
                            "file_path": f"{f['relative_path']}/{f['name']}" if f["relative_path"] else f["name"],
                            "match_count": len(matches),
                            "matches": []
                        }

                        # Extract context (line number and surrounding text)
                        lines = content.splitlines()
                        for match in matches:
                            start_pos = match.start()
                            # Calculate line number
                            line_no = content.count('\n', 0, start_pos) + 1

                            file_results["matches"].append({
                                "line": line_no,
                                "match": match.group(0),
                                "context": lines[line_no-1].strip() if line_no <= len(lines) else ""
                            })
                        results.append(file_results)

            return results
        except Exception as e:
            self._log_event("ERROR", "SEARCH_FAILED", {"repo_id": repo_id, "query": query, "error": str(e)})
            return [{"error": str(e)}]

    def replace_code(self, repo_id: str, find_query: str, replace_text: str, is_regex: bool = True, dry_run: bool = True) -> Dict[str, Any]:
        """Global find and replace across the repository."""
        try:
            search_results = self.search_code(repo_id, find_query, is_regex=is_regex, case_sensitive=True)

            if not search_results or "error" in search_results[0]:
                return {"status": "no_matches", "results": []}

            affected_files = []
            total_matches = 0

            flags = 0
            pattern = find_query if is_regex else re.escape(find_query)
            regex = re.compile(pattern, flags)

            for res in search_results:
                file_id = res["file_id"]
                file_path = res["file_path"]

                # Get full content
                row = self.db.conn.execute("SELECT content FROM files WHERE id = ?", (file_id,)).fetchone()
                new_content = regex.sub(replace_text, row["content"])

                affected_files.append({
                    "file_id": file_id,
                    "path": file_path,
                    "match_count": res["match_count"]
                })
                total_matches += res["match_count"]

                if not dry_run:
                    # Physically update disk (needs repo root)
                    cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
                    repo_root = Path(cursor.fetchone()["root_path"])
                    abs_path = repo_root / file_path

                    abs_path.write_text(new_content, encoding="utf-8")

                    # Update DB
                    with self.db.transaction() as txn:
                        txn.execute("UPDATE files SET content = ? WHERE id = ?", (new_content, file_id))

            return {
                "status": "dry_run" if dry_run else "success",
                "total_matches": total_matches,
                "files_count": len(affected_files),
                "affected_files": affected_files
            }
        except Exception as e:
            self._log_event("ERROR", "REPLACE_FAILED", {"repo_id": repo_id, "find": find_query, "error": str(e)})
            return {"error": str(e)}
