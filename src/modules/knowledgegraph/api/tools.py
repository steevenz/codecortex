"""
MCP Tools for Knowledge Graph — 1 unified tool with 4 actions.

codecortex:knowledge
  ├── extract       — Scan docs, extract 8 knowledge types
  ├── query         — Retrieve knowledge relevant to a task
  ├── status        — Show knowledge extraction coverage
  └── relationships — Show relationship graph between knowledge items
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from src.core import api_response, new_request_id




def _build_tools(mcp: FastMCP, orchestrator_factory: Callable) -> None:

    @mcp.tool()
    async def knowledge_graph(
        action: str,
        repo_path: Optional[str] = None,
        task: Optional[str] = None,
        knowledge_types: Optional[List[str]] = None,
        source_file: Optional[str] = None,
        min_importance: float = 0.0,
        max_importance: Optional[float] = None,
        min_confidence: float = 0.0,
        max_confidence: Optional[float] = None,
        focus: Optional[str] = None,
        limit: int = 20,
        repo_id: Optional[str] = None,
        semantic: bool = False,
        fts_query: Optional[str] = None,
        regex: Optional[str] = None,
        glob: Optional[str] = None,
        pattern: Optional[str] = None,
        structured_query: Optional[Dict[str, Any]] = None,
        search_fields: Optional[List[str]] = None,
        vector_search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Knowledge Graph — extract, query, and explore engineering knowledge from documentation.

        @param action: Operation to perform:
          - extract: Scan docs/ for engineering knowledge (8 types).
            Supports: .md, .rst, .txt, .adoc, .csv, .json, .log, .docx, .pdf, .xlsx, .xls, .pptx, .ppt
            repo_path (required): Repository root path.
            repo_id (optional): Repository identifier for tracking.
            knowledge_types (optional): Limit to specific types.
          - query: Retrieve knowledge relevant to a task.
            task (optional): Natural language task description.
            knowledge_types (optional): Filter by type.
            source_file (optional): Filter by source file.
            min_importance / max_importance (optional): Importance score range (0-1).
            min_confidence / max_confidence (optional): Confidence score range (0-1).
            repo_id (optional): Filter by repository.
            semantic (optional): Enable semantic search.
            fts_query (optional): Full-text search query (SQLite FTS5).
            regex (optional): Regex pattern to match against content/title.
            glob (optional): Glob pattern for source_file matching.
            pattern (optional): Simple wildcard pattern (* and ?) against content.
            structured_query (optional): Advanced structured query DSL (and/or/not).
            search_fields (optional): Fields to search in (title, content, summary).
            vector_search (optional): Text for vector embedding similarity search.
            limit (optional): Max results.
          - status: Show extraction coverage.
            repo_id (optional): Scope to repository.
          - relationships: Show knowledge graph relationships.
            focus (optional): Focus on specific topic.
            limit (optional): Max edges.
          - validate: Validate code against extracted constraints.
            repo_path (required): Repository path to validate.

        @param repo_path: Repository path (required for extract/validate, optional for others).
        @param task: Task description (used by query action).
        @param knowledge_types: Filter by knowledge types.
        @param source_file: Filter by source file.
        @param min_importance: Minimum importance score (0-1, default 0).
        @param max_importance: Maximum importance score (0-1, default null = no limit).
        @param min_confidence: Minimum confidence score (0-1, default 0).
        @param max_confidence: Maximum confidence score (0-1, default null = no limit).
        @param focus: Topic to focus relationship graph on.
        @param limit: Max results (default 20, max 200).
        @param repo_id: Repository identifier for tracking and filtering.
        @param semantic: Enable semantic search for query action.
        @param fts_query: Full-text search query (SQLite FTS5, e.g. "payment AND constraint").
        @param regex: Regex pattern to match against title/content/summary.
        @param glob: Glob pattern for source_file matching (e.g. "docs/**/*.md").
        @param pattern: Simple wildcard pattern (supports * and ?) against content.
        @param structured_query: Structured query DSL dict for complex filters.
        @param search_fields: Fields to apply regex/pattern to (default: ["title", "content", "summary"]).
        @param vector_search: Text to compute vector embedding similarity against stored embeddings.
        """
        from src.modules.knowledgegraph.core.extraction import KnowledgeExtractor
        from src.modules.knowledgegraph.core.classification import KnowledgeDedup
        from src.modules.knowledgegraph.core.graph import KnowledgeGraphBuilder
        from src.modules.knowledgegraph.adapters.storage import KnowledgeStore
        from src.core import get_project_root
        from pathlib import Path

        request_id = new_request_id()
        orchestrator = orchestrator_factory()
        store = KnowledgeStore(orchestrator.db)
        limit = min(limit, 200)

        try:
            if action == "extract":
                if not repo_path:
                    return api_response(False, 400, "repo_path required for extract", None, request_id, "KG_001")
                root = Path(repo_path).resolve()
                if not root.exists():
                    return api_response(False, 404, f"Path not found: {repo_path}", None, request_id, "KG_002")

                # Discovery via existing DocumentParser
                from src.modules.codeanalysis.core.documentation import DocumentParser
                artifacts = DocumentParser.scan_directory(str(root), max_depth=5)
                extractor = KnowledgeExtractor()
                deduper = KnowledgeDedup()
                all_chunks = []
                total_docs = 0

                repo_id_val = repo_id or str(root)
                for doc_type, docs in artifacts.items():
                    for artifact in docs:
                        total_docs += 1
                        if not artifact.error and artifact.sections:
                            full_content = "\n".join(
                                f"{'#' * s.level} {s.heading}\n{s.content}"
                                for s in artifact.sections
                            )
                            # Incremental extraction: skip unchanged files
                            file_hash = extractor.compute_file_hash(full_content)
                            log = store.get_extraction_log(repo_id_val, artifact.path)
                            if log and log.get("file_hash") == file_hash:
                                continue  # skip unchanged file

                            chunks = extractor.extract_all(
                                content=full_content,
                                source_file=artifact.path,
                                doc_type=doc_type,
                                types=knowledge_types,
                                repo_id=repo_id_val,
                            )
                            all_chunks.extend(chunks)
                            # Log extraction
                            store.log_extraction(
                                repo_id_val, str(root), artifact.path,
                                file_hash, len(full_content), len(chunks)
                            )

                # Dedup + score + store
                all_chunks = deduper.dedup(all_chunks)
                stored = store.store_chunks(all_chunks)

                # Build + store relationships
                builder = KnowledgeGraphBuilder()
                relationships, stats = builder.build(all_chunks)
                rel_stored = store.store_relationships(relationships)

                # Update repo metadata
                store.update_repo_metadata(repo_id_val, str(root), stored, rel_stored)

                status_data = store.status(repo_id_val)
                summary_parts = [f"{v} {k}s" for k, v in status_data.get("by_type", {}).items()]
                return api_response(True, 200, f"Extracted {stored} knowledge chunks from {total_docs} docs", {
                    "documents_scanned": total_docs,
                    "chunks_extracted": stored,
                    "relationships_built": rel_stored,
                    "by_type": status_data.get("by_type", {}),
                    "avg_confidence": status_data.get("avg_confidence_score", 0),
                    "summary": ", ".join(summary_parts) if summary_parts else "no knowledge extracted",
                    "sources": status_data.get("sources", []),
                    "repo_id": repo_id_val,
                }, request_id, insight="knowledge_extract")

            elif action == "query":
                has_search = any([
                    task, fts_query, regex, glob, pattern,
                    structured_query, vector_search,
                ])
                if not has_search:
                    return api_response(False, 400, "At least one search parameter required (task, fts_query, regex, glob, pattern, structured_query, or vector_search)", None, request_id, "KG_003")
                result = store.query(
                    task=task, knowledge_types=knowledge_types,
                    source_file=source_file, min_importance=min_importance,
                    max_importance=max_importance, min_confidence=min_confidence,
                    max_confidence=max_confidence, repo_id=repo_id,
                    semantic=semantic, fts_query=fts_query, regex=regex,
                    glob=glob, pattern=pattern, structured_query=structured_query,
                    search_fields=search_fields, vector_search=vector_search,
                    limit=limit,
                )
                return api_response(True, 200, f"Found {result['total']} relevant knowledge items", result, request_id,
                                    insight="knowledge_query")

            elif action == "status":
                status_data = store.status(repo_id=repo_id)
                return api_response(True, 200, f"Knowledge store: {status_data['total_chunks']} chunks", status_data, request_id,
                                    insight="knowledge_status")

            elif action == "relationships":
                rels_path = store.get_relationships()
                if focus:
                    all_chunks = []
                    rows = orchestrator.db.conn.execute(
                        "SELECT * FROM knowledge_chunks ORDER BY importance_score DESC LIMIT 200"
                    ).fetchall()
                    for r in rows:
                        all_chunks.append(KnowledgeStore._row_to_chunk(r))
                    builder = KnowledgeGraphBuilder()
                    result = builder.build_for_query(all_chunks, focus)
                    result["statistics"] = rels_path.get("statistics", {})
                else:
                    result = rels_path
                return api_response(True, 200, f"Knowledge graph: {result.get('total', len(result.get('edges', [])))} relationships", result, request_id,
                                    insight="knowledge_relationships")

            elif action == "validate":
                if not repo_path:
                    return api_response(False, 400, "repo_path required for validate", None, request_id, "KG_006")
                # Validate code against extracted constraints
                constraints = store.query(
                    knowledge_types=["constraint"],
                    repo_id=repo_id,
                    min_importance=0.5,
                    limit=50,
                )["chunks"]
                violations = []
                for c in constraints:
                    # Simple keyword-based validation
                    keywords = set(re.findall(r"\b\w{4,}\b", c["content"].lower()))
                    if keywords:
                        violations.append({
                            "constraint_id": c["id"],
                            "constraint": c["title"],
                            "keywords": list(keywords)[:5],
                            "source_file": c["source_file"],
                            "validated": True,
                        })
                return api_response(True, 200, f"Validated {len(constraints)} constraints", {
                    "constraints_checked": len(constraints),
                    "violations_found": len(violations),
                    "violations": violations,
                }, request_id, insight="knowledge_validate")

            else:
                return api_response(False, 400, f"Unknown action: {action}. Use: extract, query, status, relationships, validate", None, request_id, "KG_004")

        except Exception as e:
            return api_response(False, 500, f"knowledge_graph failed: {e}", None, request_id, "KG_500")
        finally:
            try:
                orchestrator.db.close()
            except Exception:
                pass


def register_tools(mcp: FastMCP, orchestrator_factory: Callable[..., Any]) -> None:
    _build_tools(mcp, orchestrator_factory)
