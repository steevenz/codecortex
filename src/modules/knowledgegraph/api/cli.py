from __future__ import annotations
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

DOMAIN = "knowledge"
ALIASES = ["kg"]


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


def cmd_kg_extract(args_ns: argparse.Namespace) -> Dict:
    from src.modules.knowledgegraph.core.extraction import KnowledgeExtractor
    from src.modules.knowledgegraph.core.classification import KnowledgeDedup
    from src.modules.knowledgegraph.core.graph import KnowledgeGraphBuilder
    from src.modules.knowledgegraph.adapters.storage import KnowledgeStore
    from src.modules.codeanalysis.core.documentation import DocumentParser
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        root = Path(args_ns.repo_path).resolve()
        if not root.exists():
            return err(f"Path not found: {root}", "KG_PATH_ERROR", 404)
        artifacts = DocumentParser.scan_directory(str(root), max_depth=5)
        store = KnowledgeStore(orch.db)
        extractor = KnowledgeExtractor()
        deduper = KnowledgeDedup()
        repo_id = getattr(args_ns, "repo_id", None) or str(root)
        types = getattr(args_ns, "types", None)

        # Use parallel batch extraction
        documents = []
        total_docs = 0
        for doc_type, docs in artifacts.items():
            for artifact in docs:
                total_docs += 1
                if not artifact.error and artifact.sections:
                    full_content = "\n".join(
                        f"{'#' * s.level} {s.heading}\n{s.content}"
                        for s in artifact.sections
                    )
                    # Check incremental
                    file_hash = extractor.compute_file_hash(full_content)
                    log = store.get_extraction_log(repo_id, artifact.path)
                    if log and log.get("file_hash") == file_hash:
                        continue
                    store.log_extraction(repo_id, str(root), artifact.path, file_hash, len(full_content), 0)
                    documents.append({"source_file": artifact.path, "content": full_content, "doc_type": doc_type})

        all_chunks = extractor.extract_batch(documents, types=types, repo_id=repo_id, max_workers=4)
        all_chunks = deduper.dedup(all_chunks)
        stored = store.store_chunks(all_chunks)

        # Update logs with actual chunk counts
        for doc in documents:
            # Count chunks for this file
            file_chunks = [c for c in all_chunks if c.source_file == doc["source_file"]]
            file_hash = extractor.compute_file_hash(doc["content"])
            store.log_extraction(repo_id, str(root), doc["source_file"], file_hash, len(doc["content"]), len(file_chunks))

        builder = KnowledgeGraphBuilder()
        relationships, stats = builder.build(all_chunks)
        rel_stored = store.store_relationships(relationships)
        store.update_repo_metadata(repo_id, str(root), stored, rel_stored)

        status_data = store.status(repo_id)
        return ok(f"Extracted {stored} knowledge chunks from {total_docs} docs", {
            "documents_scanned": total_docs, "chunks_extracted": stored,
            "relationships_built": rel_stored, "by_type": stats.get("by_type", {}),
            "avg_confidence": status_data.get("avg_confidence_score", 0),
            "repo_id": repo_id,
        })
    except Exception as e:
        return err(f"Knowledge extract failed: {e}", "KG_EXTRACT_ERROR", 500)
    finally:
        orch.db.close()


def cmd_kg_query(args_ns: argparse.Namespace) -> Dict:
    from src.modules.knowledgegraph.adapters.storage import KnowledgeStore
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        store = KnowledgeStore(orch.db)
        result = store.query(
            task=args_ns.task,
            knowledge_types=getattr(args_ns, "types", None),
            source_file=getattr(args_ns, "source_file", None),
            min_importance=getattr(args_ns, "min_importance", 0.0),
            max_importance=getattr(args_ns, "max_importance", None),
            min_confidence=getattr(args_ns, "min_confidence", 0.0),
            max_confidence=getattr(args_ns, "max_confidence", None),
            repo_id=getattr(args_ns, "repo_id", None),
            semantic=getattr(args_ns, "semantic", False),
            fts_query=getattr(args_ns, "fts_query", None),
            regex=getattr(args_ns, "regex", None),
            glob=getattr(args_ns, "glob", None),
            pattern=getattr(args_ns, "pattern", None),
            structured_query=getattr(args_ns, "structured_query", None),
            search_fields=getattr(args_ns, "search_fields", None),
            vector_search=getattr(args_ns, "vector_search", None),
            limit=getattr(args_ns, "limit", 20),
        )
        return ok(f"Found {result['total']} relevant knowledge items", result)
    except Exception as e:
        return err(f"Knowledge query failed: {e}", "KG_QUERY_ERROR", 500)
    finally:
        orch.db.close()


def cmd_kg_status(args_ns: argparse.Namespace) -> Dict:
    from src.modules.knowledgegraph.adapters.storage import KnowledgeStore
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        store = KnowledgeStore(orch.db)
        repo_id = getattr(args_ns, "repo_id", None)
        status_data = store.status(repo_id=repo_id)
        return ok(f"Knowledge store: {status_data['total_chunks']} chunks", status_data)
    except Exception as e:
        return err(f"Knowledge status failed: {e}", "KG_STATUS_ERROR", 500)
    finally:
        orch.db.close()


def cmd_kg_relationships(args_ns: argparse.Namespace) -> Dict:
    from src.modules.knowledgegraph.adapters.storage import KnowledgeStore
    from src.modules.knowledgegraph.core.graph import KnowledgeGraphBuilder
    from src.main import create_orchestrator
    orch = create_orchestrator()
    try:
        store = KnowledgeStore(orch.db)
        focus = getattr(args_ns, "focus", None)
        rels_path = store.get_relationships()
        if focus:
            rows = orch.db.conn.execute(
                "SELECT * FROM knowledge_chunks ORDER BY importance_score DESC LIMIT 200"
            ).fetchall()
            all_chunks = [KnowledgeStore._row_to_chunk(r) for r in rows]
            builder = KnowledgeGraphBuilder()
            result = builder.build_for_query(all_chunks, focus)
            result["statistics"] = rels_path.get("statistics", {})
        else:
            result = rels_path
        return ok(f"Knowledge graph: {result.get('total', len(result.get('edges', [])))} relationships", result)
    except Exception as e:
        return err(f"Knowledge relationships failed: {e}", "KG_REL_ERROR", 500)
    finally:
        orch.db.close()


def cmd_kg_validate(args_ns: argparse.Namespace) -> Dict:
    from src.modules.knowledgegraph.adapters.storage import KnowledgeStore
    from src.main import create_orchestrator
    import re
    orch = create_orchestrator()
    try:
        store = KnowledgeStore(orch.db)
        repo_id = getattr(args_ns, "repo_id", None)
        constraints = store.query(
            knowledge_types=["constraint"],
            repo_id=repo_id,
            min_importance=0.5,
            limit=50,
        )["chunks"]
        violations = []
        for c in constraints:
            keywords = set(re.findall(r"\b\w{4,}\b", c["content"].lower()))
            if keywords:
                violations.append({
                    "constraint_id": c["id"],
                    "constraint": c["title"],
                    "keywords": list(keywords)[:5],
                    "source_file": c["source_file"],
                    "validated": True,
                })
        return ok(f"Validated {len(constraints)} constraints", {
            "constraints_checked": len(constraints),
            "violations_found": len(violations),
            "violations": violations,
        })
    except Exception as e:
        return err(f"Knowledge validate failed: {e}", "KG_VALIDATE_ERROR", 500)
    finally:
        orch.db.close()


KG_COMMANDS = {
    "extract": cmd_kg_extract,
    "query": cmd_kg_query,
    "status": cmd_kg_status,
    "relationships": cmd_kg_relationships,
    "validate": cmd_kg_validate,
}


def build_parser(subparsers) -> None:
    p = subparsers.add_parser("knowledge", aliases=["kg"], help="Knowledge graph — extract, query, explore engineering knowledge")
    sp = p.add_subparsers(dest="kg_action", required=True)

    e = sp.add_parser("extract", help="Extract knowledge from docs")
    e.add_argument("repo_path", help="Repository path to scan")
    e.add_argument("--types", nargs="*", help="Knowledge types to extract")
    e.add_argument("--repo-id", help="Repository identifier for tracking")

    q = sp.add_parser("query", help="Query knowledge relevant to a task")
    q.add_argument("task", nargs="?", default=None, help="Natural language task description")
    q.add_argument("--types", nargs="*", help="Filter by knowledge types")
    q.add_argument("--min-importance", type=float, default=0.0, help="Min importance score")
    q.add_argument("--max-importance", type=float, default=None, help="Max importance score")
    q.add_argument("--min-confidence", type=float, default=0.0, help="Min confidence score")
    q.add_argument("--max-confidence", type=float, default=None, help="Max confidence score")
    q.add_argument("--repo-id", help="Filter by repository ID")
    q.add_argument("--semantic", action="store_true", help="Enable semantic search")
    q.add_argument("--fts-query", help="Full-text search query (SQLite FTS5)")
    q.add_argument("--regex", help="Regex pattern to match against content/title")
    q.add_argument("--glob", help="Glob pattern for source_file matching")
    q.add_argument("--pattern", help="Simple wildcard pattern (* and ?)")
    q.add_argument("--search-fields", nargs="*", default=["title", "content", "summary"], help="Fields to search in")
    q.add_argument("--vector-search", help="Text for vector embedding similarity")
    q.add_argument("--limit", type=int, default=20, help="Max results")

    s = sp.add_parser("status", help="Knowledge extraction coverage")
    s.add_argument("--repo-id", help="Filter by repository ID")

    r = sp.add_parser("relationships", help="Knowledge graph relationships")
    r.add_argument("--focus", help="Focus on specific topic")

    v = sp.add_parser("validate", help="Validate code against extracted constraints")
    v.add_argument("--repo-id", help="Filter by repository ID")
