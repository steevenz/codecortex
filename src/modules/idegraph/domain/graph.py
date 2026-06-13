"""
@project   CodeCortex
@package   modules.idegraph.domain
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.domain
:standard: CODDY-IdeGraph-v1.0

Graph Timeline — Domain model for historical conversation graph,
project state snapshots, and digital artifact tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any

from src.modules.idegraph.domain.engram import Engram


class EdgeType(str, Enum):
    """Types of relationships between conversations."""
    CONTINUES_FROM = "continues_from"      # Same session, natural continuation
    FORKED_FROM = "forked_from"             # Branched to new topic
    REFERENCES = "references"               # Mentions prior conversation
    SAME_SESSION = "same_session"            # Within same IDE session
    SAME_TOPIC = "same_topic"               # Similar keywords (ML-detected)
    HAS_ARTIFACT = "has_artifact"           # Produces digital artifact
    USES_ARTIFACT = "uses_artifact"         # Consumes digital artifact


class ArtifactType(str, Enum):
    """Types of digital artifacts extracted from conversations."""
    CODE_SOLUTION = "code_solution"
    CONFIG_CHANGE = "config_change"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    ARCHITECTURE_DECISION = "architecture"
    LEARNED_PATTERN = "pattern"
    DEBUG_TECHNIQUE = "debug"
    COMMAND = "command"
    WORKFLOW = "workflow"
    DATA_MODEL = "data_model"
    API_SPEC = "api_spec"


class UsageType(str, Enum):
    """How an artifact was used after creation."""
    APPLIED_IN_PROJECT = "applied_in_project"
    REFERENCED_IN_CONVERSATION = "referenced"
    COPIED_TO_CLIPBOARD = "copied"
    MODIFIED_AND_REUSED = "modified"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass
class ConversationEdge:
    """Typed edge between two engram nodes in the conversation graph."""
    id: str
    source_engram_id: str
    target_engram_id: str
    edge_type: EdgeType
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_engram_id": self.source_engram_id,
            "target_engram_id": self.target_engram_id,
            "edge_type": self.edge_type.value,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "detected_at": self.detected_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationEdge":
        return cls(
            id=data.get("id", ""),
            source_engram_id=data.get("source_engram_id", ""),
            target_engram_id=data.get("target_engram_id", ""),
            edge_type=EdgeType(data.get("edge_type", "references")),
            confidence=float(data.get("confidence", 1.0)),
            metadata=data.get("metadata", {}),
            detected_at=datetime.fromisoformat(data["detected_at"]) if "detected_at" in data else datetime.now(timezone.utc),
        )


@dataclass
class EngramNode:
    """Graph-wrapped engram with positional and relational metadata."""
    engram: Engram
    depth: int = 0                      # Graph depth from root (0 = first)
    lineage: List[str] = field(default_factory=list)  # IDs of ancestor conversations
    branch_name: Optional[str] = None  # Named branch of conversation flow
    session_id: str = ""                # Groups conversations within single IDE session
    day_bucket: str = ""                # "2026-05-29" for fast date queries
    incoming_edges: List[str] = field(default_factory=list)  # Edge IDs pointing to this node
    outgoing_edges: List[str] = field(default_factory=list)   # Edge IDs from this node

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engram": self.engram.to_dict(),
            "depth": self.depth,
            "lineage": self.lineage,
            "branch_name": self.branch_name,
            "session_id": self.session_id,
            "day_bucket": self.day_bucket,
            "incoming_edges": self.incoming_edges,
            "outgoing_edges": self.outgoing_edges,
        }

    @property
    def id(self) -> str:
        return self.engram.id


@dataclass
class ProjectState:
    """Immutable snapshot of project state when a conversation occurred."""
    id: str
    engram_id: str
    captured_at: datetime

    # Git context
    git_branch: Optional[str] = None
    git_commit: Optional[str] = None
    git_commit_message: Optional[str] = None
    git_dirty_files: List[str] = field(default_factory=list)

    # Workspace context
    repo_path: Optional[str] = None
    repo_remote_url: Optional[str] = None
    repo_id: Optional[str] = None

    # File context
    open_files: List[str] = field(default_factory=list)
    active_file: Optional[str] = None
    file_line_count: Dict[str, int] = field(default_factory=dict)

    # Environment
    ide_name: str = ""
    ide_version: Optional[str] = None
    os_name: Optional[str] = None
    python_version: Optional[str] = None
    node_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "engram_id": self.engram_id,
            "captured_at": self.captured_at.isoformat(),
            "git_branch": self.git_branch,
            "git_commit": self.git_commit,
            "git_commit_message": self.git_commit_message,
            "git_dirty_files": self.git_dirty_files,
            "repo_path": self.repo_path,
            "repo_remote_url": self.repo_remote_url,
            "repo_id": self.repo_id,
            "open_files": self.open_files,
            "active_file": self.active_file,
            "file_line_count": self.file_line_count,
            "ide_name": self.ide_name,
            "ide_version": self.ide_version,
            "os_name": self.os_name,
            "python_version": self.python_version,
            "node_version": self.node_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectState":
        raw_captured = data.get("captured_at", "")
        captured_at = datetime.now(timezone.utc)
        if raw_captured and isinstance(raw_captured, str):
            try:
                captured_at = datetime.fromisoformat(raw_captured)
            except (ValueError, TypeError):
                pass
        return cls(
            id=data.get("id", ""),
            engram_id=data.get("engram_id", ""),
            captured_at=captured_at,
            git_branch=data.get("git_branch"),
            git_commit=data.get("git_commit"),
            git_commit_message=data.get("git_commit_message"),
            git_dirty_files=data.get("git_dirty_files", []),
            repo_path=data.get("repo_path"),
            repo_remote_url=data.get("repo_remote_url"),
            repo_id=data.get("repo_id"),
            open_files=data.get("open_files", []),
            active_file=data.get("active_file"),
            file_line_count=data.get("file_line_count", {}),
            ide_name=data.get("ide_name", ""),
            ide_version=data.get("ide_version"),
            os_name=data.get("os_name"),
            python_version=data.get("python_version"),
            node_version=data.get("node_version"),
        )


@dataclass
class StateTransition:
    """Captures what changed between two consecutive conversations."""
    id: str
    from_state_id: str
    to_state_id: str
    files_added: List[str] = field(default_factory=list)
    files_deleted: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    lines_changed: int = 0
    branch_changed: bool = False
    commit_distance: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_state_id": self.from_state_id,
            "to_state_id": self.to_state_id,
            "files_added": self.files_added,
            "files_deleted": self.files_deleted,
            "files_modified": self.files_modified,
            "lines_changed": self.lines_changed,
            "branch_changed": self.branch_changed,
            "commit_distance": self.commit_distance,
        }


@dataclass
class DigitalArtifact:
    """A code solution, config, or knowledge extracted from a conversation."""
    id: str
    artifact_type: ArtifactType
    engram_id: str
    title: str
    description: str = ""
    content: str = ""
    language: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Context
    file_path: Optional[str] = None
    target_function: Optional[str] = None
    imports_required: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    # Quality
    confidence: float = 0.0
    verified: bool = False
    tests_pass: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "artifact_type": self.artifact_type.value,
            "engram_id": self.engram_id,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "language": self.language,
            "created_at": self.created_at.isoformat(),
            "file_path": self.file_path,
            "target_function": self.target_function,
            "imports_required": self.imports_required,
            "dependencies": self.dependencies,
            "confidence": self.confidence,
            "verified": self.verified,
            "tests_pass": self.tests_pass,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DigitalArtifact":
        raw_created = data.get("created_at", "")
        created_at = datetime.now(timezone.utc)
        if raw_created and isinstance(raw_created, str):
            try:
                created_at = datetime.fromisoformat(raw_created)
            except (ValueError, TypeError):
                pass
        return cls(
            id=data.get("id", ""),
            artifact_type=ArtifactType(data.get("artifact_type", "code_solution")),
            engram_id=data.get("engram_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            content=data.get("content", ""),
            language=data.get("language"),
            created_at=created_at,
            file_path=data.get("file_path"),
            target_function=data.get("target_function"),
            imports_required=data.get("imports_required", []),
            dependencies=data.get("dependencies", []),
            confidence=float(data.get("confidence", 0.0)),
            verified=bool(data.get("verified", False)),
            tests_pass=data.get("tests_pass"),
        )


@dataclass
class ArtifactUsage:
    """Tracks where an artifact was applied or referenced."""
    id: str
    artifact_id: str
    usage_type: UsageType
    target_engram_id: Optional[str] = None
    target_file_path: Optional[str] = None
    target_commit_hash: Optional[str] = None
    applied_at: Optional[datetime] = None
    success: Optional[bool] = None
    diff_preview: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "artifact_id": self.artifact_id,
            "usage_type": self.usage_type.value,
            "target_engram_id": self.target_engram_id,
            "target_file_path": self.target_file_path,
            "target_commit_hash": self.target_commit_hash,
            "success": self.success,
            "diff_preview": self.diff_preview,
            "created_at": self.created_at.isoformat(),
        }
        if self.applied_at:
            result["applied_at"] = self.applied_at.isoformat()
        return result


@dataclass
class ConversationGraph:
    """Graph structure connecting all engrams for a workspace."""
    workspace_key: str
    nodes: List[EngramNode] = field(default_factory=list)
    edges: List[ConversationEdge] = field(default_factory=list)
    head_node_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_key": self.workspace_key,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "head_node_id": self.head_node_id,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }

    def to_ai_summary(self, max_nodes: int = 10) -> Dict[str, Any]:
        """Produce condensed, actionable summary optimized for AI coders."""
        # Sort by creation time, take most recent
        recent_nodes = sorted(self.nodes, key=lambda n: n.engram.created_at, reverse=True)[:max_nodes]
        sessions = sorted({n.session_id for n in self.nodes if n.session_id})
        days = sorted({n.day_bucket for n in self.nodes if n.day_bucket})

        # Find high-confidence artifacts
        artifact_nodes = [n for n in recent_nodes if n.engram.title and "fix" in n.engram.title.lower()]

        return {
            "workspace_key": self.workspace_key,
            "summary": {
                "total_conversations": len(self.nodes),
                "total_relationships": len(self.edges),
                "active_sessions": len(sessions),
                "date_range": {"from": days[0] if days else None, "to": days[-1] if days else None},
                "latest_conversation_id": self.head_node_id,
            },
            "recent_activity": [
                {
                    "id": n.engram.id,
                    "title": n.engram.title,
                    "source": n.engram.source,
                    "day": n.day_bucket,
                    "depth": n.depth,
                    "message_count": len(n.engram.messages),
                    "has_artifacts": bool(n.outgoing_edges),
                }
                for n in recent_nodes
            ],
            "suggested_context": {
                "related_to_latest": [
                    {"id": r.engram.id, "title": r.engram.title, "relationship": "connected"}
                    for r in self.get_related(self.head_node_id)[:5]
                ] if self.head_node_id else [],
                "recent_fixes": [
                    {"id": n.engram.id, "title": n.engram.title}
                    for n in artifact_nodes[:3]
                ],
            },
            "actions_available": [
                "get_timeline(engram_id) — chronological path to any conversation",
                "get_related(engram_id) — find connected conversations",
                "get_branch(session_id) — see all conversations in a session",
                "get_day_summary(day) — daily activity overview",
            ],
        }

    def to_ai_context(self, target_engram_id: str) -> Dict[str, Any]:
        """Rich context format for feeding into LLM prompts."""
        target = self.get_node(target_engram_id)
        if not target:
            return {"error": f"Engram {target_engram_id} not found in graph"}

        timeline = self.get_timeline(target_engram_id)
        related = self.get_related(target_engram_id)
        branch = self.get_branch(target.session_id) if target.session_id else []

        return {
            "target": {
                "id": target.engram.id,
                "title": target.engram.title,
                "source": target.engram.source,
                "created_at": target.engram.created_at.isoformat(),
                "message_count": len(target.engram.messages),
                "project_name": target.engram.project_name,
            },
            "context": {
                "timeline_position": f"{timeline.index(target) + 1} of {len(timeline)} in lineage",
                "ancestors": [
                    {"id": n.engram.id, "title": n.engram.title}
                    for n in timeline[:-1]
                ],
                "siblings_same_session": [
                    {"id": n.engram.id, "title": n.engram.title}
                    for n in branch if n.engram.id != target_engram_id
                ],
                "related_conversations": [
                    {
                        "id": n.engram.id,
                        "title": n.engram.title,
                        "source": n.engram.source,
                        "reason": self._get_edge_reason(target_engram_id, n.engram.id),
                    }
                    for n in related[:5]
                ],
            },
            "suggested_next_actions": self._suggest_actions(target),
        }

    def _get_edge_reason(self, from_id: str, to_id: str) -> str:
        """Get human-readable reason for edge between two nodes."""
        for edge in self.edges:
            if (edge.source_engram_id == from_id and edge.target_engram_id == to_id) or \
               (edge.source_engram_id == to_id and edge.target_engram_id == from_id):
                reasons = {
                    EdgeType.CONTINUES_FROM: "continues conversation flow",
                    EdgeType.SAME_SESSION: "same IDE session",
                    EdgeType.SAME_TOPIC: "similar topic/content",
                    EdgeType.FORKED_FROM: "branched from",
                    EdgeType.REFERENCES: "references this",
                    EdgeType.HAS_ARTIFACT: "produces artifact",
                    EdgeType.USES_ARTIFACT: "uses artifact from",
                }
                return reasons.get(edge.edge_type, "related")
        return "related"

    def _suggest_actions(self, node: EngramNode) -> List[str]:
        """Suggest next actions based on node context."""
        actions = []
        if node.depth > 0:
            actions.append("Follow conversation lineage to understand decision history")
        if node.outgoing_edges:
            actions.append("Explore related conversations for additional context")
        if not node.engram.project_name:
            actions.append("Link conversation to project for better organization")
        if len(node.engram.messages) > 20:
            actions.append("Consider compacting this conversation to reduce tokens")
        return actions or ["Continue current task with context from this conversation"]

    def get_node(self, engram_id: str) -> Optional[EngramNode]:
        """Get node by engram ID."""
        for node in self.nodes:
            if node.engram.id == engram_id:
                return node
        return None

    def get_related(self, engram_id: str, edge_types: Optional[List[EdgeType]] = None) -> List[EngramNode]:
        """Get conversations related to given engram via edges."""
        related_ids = set()
        for edge in self.edges:
            if edge.source_engram_id == engram_id:
                if edge_types is None or edge.edge_type in edge_types:
                    related_ids.add(edge.target_engram_id)
            elif edge.target_engram_id == engram_id:
                if edge_types is None or edge.edge_type in edge_types:
                    related_ids.add(edge.source_engram_id)
        return [n for n in self.nodes if n.engram.id in related_ids]

    def get_timeline(self, engram_id: str) -> List[EngramNode]:
        """Get chronological timeline from root to given engram."""
        node = self.get_node(engram_id)
        if not node:
            return []
        # Build path from lineage
        timeline = []
        for ancestor_id in node.lineage:
            ancestor = self.get_node(ancestor_id)
            if ancestor:
                timeline.append(ancestor)
        timeline.append(node)
        return timeline

    def get_branch(self, session_id: str) -> List[EngramNode]:
        """Get all conversations in a session branch."""
        return sorted(
            [n for n in self.nodes if n.session_id == session_id],
            key=lambda n: n.engram.created_at
        )

    def get_day_summary(self, day_bucket: str) -> Dict[str, Any]:
        """Get summary of conversations for a specific day."""
        day_nodes = [n for n in self.nodes if n.day_bucket == day_bucket]
        sessions = {}
        for node in day_nodes:
            sid = node.session_id or "unknown"
            sessions.setdefault(sid, []).append(node)
        return {
            "day": day_bucket,
            "conversation_count": len(day_nodes),
            "session_count": len(sessions),
            "sessions": {
                sid: [n.engram.title or n.engram.id for n in sorted(nodes, key=lambda x: x.engram.created_at)]
                for sid, nodes in sessions.items()
            },
        }
