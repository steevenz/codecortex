"""
@project   CodeCortex
@package   modules.idegraph.services
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:standard: Aegis-IdeGraph-v1.0

Graph Builder — Constructs conversation graph from engrams with timeline,
state snapshots, and digital artifact tracking.
"""

import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from typing import List, Optional, Dict, Any, Tuple

from src.modules.idegraph.core.logging_service import get_logger
from src.modules.idegraph.domain.engram import Engram
from src.modules.idegraph.domain.graph import (
    ConversationGraph, EngramNode, ConversationEdge, EdgeType,
    ProjectState, StateTransition,
    DigitalArtifact, ArtifactType,
)

logger = get_logger(__name__)

# Constants for edge detection
CONTINUATION_GAP_MINUTES = 30
SAME_TOPIC_THRESHOLD = 0.7  # SequenceMatcher ratio


class GraphBuilder:
    """Builds conversation graphs from collections of engrams."""

    def __init__(self, db=None):
        self._db = db

    def build_timeline(self, engrams: List[Engram], workspace_key: str) -> ConversationGraph:
        """Build chronological conversation graph from engrams."""
        if not engrams:
            return ConversationGraph(workspace_key=workspace_key)

        # Sort by creation time
        sorted_engrams = sorted(engrams, key=lambda e: e.created_at)

        # Create nodes with metadata
        nodes: List[EngramNode] = []
        session_map: Dict[str, str] = {}  # Maps session signatures to session IDs

        for idx, engram in enumerate(sorted_engrams):
            # Compute session ID from IDE + date + hour
            session_sig = f"{engram.source}:{engram.created_at.strftime('%Y%m%d%H')}"
            if session_sig not in session_map:
                session_map[session_sig] = f"sess_{uuid.uuid4().hex[:8]}"
            session_id = session_map[session_sig]

            # Compute depth and lineage
            depth = 0
            lineage: List[str] = []
            if idx > 0:
                # Check if this continues from previous
                prev = nodes[-1]
                time_gap = (engram.created_at - prev.engram.created_at).total_seconds() / 60
                if time_gap <= CONTINUATION_GAP_MINUTES and prev.session_id == session_id:
                    depth = prev.depth + 1
                    lineage = prev.lineage + [prev.engram.id]

            node = EngramNode(
                engram=engram,
                depth=depth,
                lineage=lineage,
                session_id=session_id,
                day_bucket=engram.created_at.strftime("%Y-%m-%d"),
            )
            nodes.append(node)

        # Detect edges
        edges = self._detect_edges(nodes)

        # Set head node (most recent)
        head_node_id = nodes[-1].engram.id if nodes else None

        # Wire up edge references on nodes
        edge_by_id = {e.id: e for e in edges}
        for node in nodes:
            node.incoming_edges = [e.id for e in edges if e.target_engram_id == node.engram.id]
            node.outgoing_edges = [e.id for e in edges if e.source_engram_id == node.engram.id]

        graph = ConversationGraph(
            workspace_key=workspace_key,
            nodes=nodes,
            edges=edges,
            head_node_id=head_node_id,
        )

        logger.info(
            "Timeline graph built",
            extra={"extra_data": {
                "workspace_key": workspace_key,
                "nodes": len(nodes),
                "edges": len(edges),
                "sessions": len(set(n.session_id for n in nodes)),
            }},
        )
        return graph

    def _detect_edges(self, nodes: List[EngramNode]) -> List[ConversationEdge]:
        """Detect relationships between conversation nodes."""
        edges: List[ConversationEdge] = []
        seen_pairs = set()

        for i, source in enumerate(nodes):
            for j, target in enumerate(nodes):
                if i >= j:
                    continue  # Only forward in time

                pair_key = (source.engram.id, target.engram.id)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                edge = self._classify_edge(source, target)
                if edge:
                    edges.append(edge)

        return edges

    def _classify_edge(self, source: EngramNode, target: EngramNode) -> Optional[ConversationEdge]:
        """Classify relationship between two conversation nodes."""
        time_gap = (target.engram.created_at - source.engram.created_at).total_seconds() / 60

        # SAME_SESSION: explicit match
        if source.session_id and source.session_id == target.session_id:
            # Within same session
            if time_gap <= CONTINUATION_GAP_MINUTES:
                return ConversationEdge(
                    id=f"edge_{uuid.uuid4().hex[:8]}",
                    source_engram_id=source.engram.id,
                    target_engram_id=target.engram.id,
                    edge_type=EdgeType.CONTINUES_FROM,
                    confidence=1.0,
                    metadata={"time_gap_minutes": time_gap},
                )
            else:
                return ConversationEdge(
                    id=f"edge_{uuid.uuid4().hex[:8]}",
                    source_engram_id=source.engram.id,
                    target_engram_id=target.engram.id,
                    edge_type=EdgeType.SAME_SESSION,
                    confidence=0.9,
                )

        # SAME_TOPIC: similarity detection
        similarity = self._compute_similarity(source.engram, target.engram)
        if similarity >= SAME_TOPIC_THRESHOLD:
            return ConversationEdge(
                id=f"edge_{uuid.uuid4().hex[:8]}",
                source_engram_id=source.engram.id,
                target_engram_id=target.engram.id,
                edge_type=EdgeType.SAME_TOPIC,
                confidence=similarity,
                metadata={"similarity_ratio": round(similarity, 3)},
            )

        return None

    def _compute_similarity(self, a: Engram, b: Engram) -> float:
        """Compute text similarity between two engrams."""
        texts_a = []
        if a.title:
            texts_a.append(a.title)
        for m in a.messages[:3]:
            if m.content:
                texts_a.append(m.content[:200])

        texts_b = []
        if b.title:
            texts_b.append(b.title)
        for m in b.messages[:3]:
            if m.content:
                texts_b.append(m.content[:200])

        if not texts_a or not texts_b:
            return 0.0

        text_a = " ".join(texts_a).lower()
        text_b = " ".join(texts_b).lower()

        return SequenceMatcher(None, text_a, text_b).ratio()

    def persist_graph(self, graph: ConversationGraph, request_id: Optional[str] = None) -> Dict[str, int]:
        """Persist graph to SQLite storage."""
        if not self._db:
            logger.warning("No database connection, graph not persisted")
            return {"edges_persisted": 0}

        conn = self._db.conn if hasattr(self._db, "conn") else self._db
        cursor = conn.cursor()

        inserted = 0
        for edge in graph.edges:
            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO conversation_edges
                    (id, source_engram_id, target_engram_id, edge_type, confidence, metadata_json, detected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        edge.id,
                        edge.source_engram_id,
                        edge.target_engram_id,
                        edge.edge_type.value,
                        edge.confidence,
                        str(edge.metadata) if edge.metadata else None,
                        edge.detected_at.isoformat() if edge.detected_at else datetime.now(timezone.utc).isoformat(),
                    ),
                )
                if cursor.rowcount > 0:
                    inserted += 1
            except Exception as e:
                logger.warning(f"Failed to persist edge {edge.id}: {e}")

        conn.commit()
        logger.info(f"Graph persisted: {inserted} edges", extra={"extra_data": {"edges_persisted": inserted}})
        return {"edges_persisted": inserted}

    def load_graph(self, workspace_key: str) -> ConversationGraph:
        """Load existing graph from database."""
        if not self._db:
            return ConversationGraph(workspace_key=workspace_key)

        conn = self._db.conn if hasattr(self._db, "conn") else self._db
        cursor = conn.cursor()

        # Get all engrams for workspace
        cursor.execute(
            """
            SELECT c.id FROM conversations c
            JOIN workspaces w ON w.id = c.workspace_id
            WHERE w.workspace_key = ?
            ORDER BY c.created_at ASC
            """,
            (workspace_key,),
        )
        engram_ids = [r[0] for r in cursor.fetchall()]

        # Load full engrams (simplified - in production would hydrate full objects)
        # For now return empty graph if no DB hydration available
        logger.info(f"Graph loaded request for workspace {workspace_key}: {len(engram_ids)} conversations")
        return ConversationGraph(workspace_key=workspace_key)
