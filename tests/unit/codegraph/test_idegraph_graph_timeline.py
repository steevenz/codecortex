"""
@project   CodeCortex
@package   modules.idegraph.tests
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:standard: CODDY-IdeGraph-v1.0

End-to-end tests for graph timeline — verifies 100% functionality
and AI-optimized JSON output quality.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from src.modules.idegraph.domain.engram import Engram, Message
from src.modules.idegraph.domain.graph import (
    ConversationGraph, EngramNode, ConversationEdge, EdgeType,
    ProjectState, StateTransition,
    DigitalArtifact, ArtifactType,
    ArtifactUsage, UsageType,
)
from src.modules.idegraph.services.graph_builder import GraphBuilder


class TestDomainModelSerialization:
    """Verify all domain models serialize/deserialize correctly."""

    def test_conversation_edge_roundtrip(self):
        """Edge: to_dict() → from_dict() produces equivalent object."""
        original = ConversationEdge(
            id="edge-001",
            source_engram_id="engram-a",
            target_engram_id="engram-b",
            edge_type=EdgeType.CONTINUES_FROM,
            confidence=0.95,
            metadata={"time_gap": 15},
        )
        data = original.to_dict()
        restored = ConversationEdge.from_dict(data)
        assert restored.source_engram_id == original.source_engram_id
        assert restored.edge_type == original.edge_type
        assert restored.confidence == original.confidence

    def test_project_state_roundtrip(self):
        """ProjectState: full serialization cycle."""
        original = ProjectState(
            id="state-001",
            engram_id="engram-001",
            captured_at=datetime(2026, 5, 29, 10, 0, tzinfo=timezone.utc),
            git_branch="feature/auth",
            git_commit="abc123",
            repo_path="/projects/myapp",
            open_files=["auth.py", "models.py"],
            ide_name="cursor",
        )
        data = original.to_dict()
        restored = ProjectState.from_dict(data)
        assert restored.git_branch == "feature/auth"
        assert restored.repo_path == "/projects/myapp"
        assert restored.open_files == ["auth.py", "models.py"]

    def test_digital_artifact_roundtrip(self):
        """DigitalArtifact: full serialization cycle."""
        original = DigitalArtifact(
            id="art-001",
            artifact_type=ArtifactType.BUGFIX,
            engram_id="engram-001",
            title="JWT Validation Fix",
            content="def validate_token(token): ...",
            language="python",
            confidence=0.92,
            verified=True,
        )
        data = original.to_dict()
        restored = DigitalArtifact.from_dict(data)
        assert restored.artifact_type == ArtifactType.BUGFIX
        assert restored.confidence == 0.92
        assert restored.verified is True


class TestGraphBuilder:
    """End-to-end graph construction tests."""

    def _make_engram(self, id: str, title: str, minutes_ago: int, source: str = "cursor") -> Engram:
        """Helper to create test engrams."""
        return Engram(
            id=id,
            source=source,
            source_file=f"/path/to/{id}.json",
            messages=[Message(role="user", content=f"Test: {title}")],
            title=title,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        )

    def test_build_timeline_basic(self):
        """Graph builder creates correct node count and ordering."""
        engrams = [
            self._make_engram("eg-1", "First conversation", 60),
            self._make_engram("eg-2", "Second conversation", 30),
            self._make_engram("eg-3", "Third conversation", 10),
        ]
        builder = GraphBuilder()
        graph = builder.build_timeline(engrams, "ws-key-123")

        assert len(graph.nodes) == 3
        assert graph.head_node_id == "eg-3"
        assert graph.nodes[0].engram.id == "eg-1"  # Oldest first
        assert graph.nodes[2].engram.id == "eg-3"  # Newest last

    def test_session_grouping(self):
        """Conversations within same hour are grouped into same session."""
        now = datetime.now(timezone.utc)
        engrams = [
            Engram(id="a", source="cursor", source_file="/a.json",
                   messages=[Message(role="user", content="msg1")],
                   created_at=now - timedelta(minutes=10)),
            Engram(id="b", source="cursor", source_file="/b.json",
                   messages=[Message(role="user", content="msg2")],
                   created_at=now - timedelta(minutes=5)),
            Engram(id="c", source="trae", source_file="/c.json",
                   messages=[Message(role="user", content="msg3")],
                   created_at=now - timedelta(minutes=2)),
        ]
        builder = GraphBuilder()
        graph = builder.build_timeline(engrams, "ws-test")

        # a and b should share session (same IDE, same hour)
        session_a = graph.nodes[0].session_id
        session_b = graph.nodes[1].session_id
        session_c = graph.nodes[2].session_id
        assert session_a == session_b, "Same IDE+hour should share session"
        assert session_c != session_a, "Different IDE should have different session"

    def test_continuation_edge_detection(self):
        """Conversations within 30 min in same session get CONTINUES_FROM edge."""
        now = datetime.now(timezone.utc)
        engrams = [
            Engram(id="first", source="cursor", source_file="/a.json",
                   messages=[Message(role="user", content="start")],
                   created_at=now - timedelta(minutes=20)),
            Engram(id="second", source="cursor", source_file="/b.json",
                   messages=[Message(role="user", content="continue")],
                   created_at=now - timedelta(minutes=10)),
        ]
        builder = GraphBuilder()
        graph = builder.build_timeline(engrams, "ws-123")

        assert len(graph.edges) >= 1
        edge_types = {e.edge_type for e in graph.edges}
        assert EdgeType.CONTINUES_FROM in edge_types or EdgeType.SAME_SESSION in edge_types

    def test_lineage_computation(self):
        """Depth and lineage are computed correctly for continuation chain."""
        now = datetime.now(timezone.utc)
        engrams = [
            Engram(id="root", source="cursor", source_file="/r.json",
                   messages=[Message(role="user", content="root")],
                   created_at=now - timedelta(minutes=30)),
            Engram(id="child", source="cursor", source_file="/c.json",
                   messages=[Message(role="user", content="child")],
                   created_at=now - timedelta(minutes=20)),
            Engram(id="grandchild", source="cursor", source_file="/g.json",
                   messages=[Message(role="user", content="grandchild")],
                   created_at=now - timedelta(minutes=10)),
        ]
        builder = GraphBuilder()
        graph = builder.build_timeline(engrams, "ws-lineage")

        # Find nodes by ID
        root = next(n for n in graph.nodes if n.engram.id == "root")
        child = next(n for n in graph.nodes if n.engram.id == "child")
        grandchild = next(n for n in graph.nodes if n.engram.id == "grandchild")

        assert root.depth == 0
        assert child.depth == 1
        assert child.lineage == ["root"]
        assert grandchild.depth == 2
        assert grandchild.lineage == ["root", "child"]

    def test_empty_engrams(self):
        """Empty input produces valid empty graph."""
        builder = GraphBuilder()
        graph = builder.build_timeline([], "empty-ws")
        assert graph.nodes == []
        assert graph.edges == []
        assert graph.head_node_id is None


class TestGraphQueries:
    """Test graph traversal and query operations."""

    def _build_sample_graph(self) -> ConversationGraph:
        """Build a sample graph for query testing."""
        now = datetime.now(timezone.utc)
        nodes = [
            EngramNode(
                engram=Engram(id="a", source="cursor", source_file="/a.json",
                             messages=[Message(role="user", content="root")],
                             created_at=now - timedelta(minutes=30)),
                depth=0, lineage=[], session_id="sess1", day_bucket="2026-05-29",
            ),
            EngramNode(
                engram=Engram(id="b", source="cursor", source_file="/b.json",
                             messages=[Message(role="user", content="child")],
                             created_at=now - timedelta(minutes=20)),
                depth=1, lineage=["a"], session_id="sess1", day_bucket="2026-05-29",
            ),
            EngramNode(
                engram=Engram(id="c", source="trae", source_file="/c.json",
                             messages=[Message(role="user", content="unrelated")],
                             created_at=now - timedelta(minutes=10)),
                depth=0, lineage=[], session_id="sess2", day_bucket="2026-05-29",
            ),
        ]
        edges = [
            ConversationEdge(id="e1", source_engram_id="a", target_engram_id="b",
                           edge_type=EdgeType.CONTINUES_FROM, confidence=1.0),
        ]
        graph = ConversationGraph(workspace_key="ws-test", nodes=nodes, edges=edges, head_node_id="c")
        # Wire edges manually
        for e in edges:
            src = next((n for n in nodes if n.engram.id == e.source_engram_id), None)
            tgt = next((n for n in nodes if n.engram.id == e.target_engram_id), None)
            if src:
                src.outgoing_edges.append(e.id)
            if tgt:
                tgt.incoming_edges.append(e.id)
        return graph

    def test_get_node(self):
        """Retrieve node by engram ID."""
        graph = self._build_sample_graph()
        node = graph.get_node("b")
        assert node is not None
        assert node.engram.id == "b"
        assert graph.get_node("nonexistent") is None

    def test_get_related(self):
        """Find related conversations via edges."""
        graph = self._build_sample_graph()
        related = graph.get_related("a")
        assert len(related) == 1
        assert related[0].engram.id == "b"

    def test_get_timeline(self):
        """Get chronological path from root to target."""
        graph = self._build_sample_graph()
        timeline = graph.get_timeline("b")
        assert len(timeline) == 2
        assert timeline[0].engram.id == "a"
        assert timeline[1].engram.id == "b"

    def test_get_branch(self):
        """Get all conversations in same session."""
        graph = self._build_sample_graph()
        branch = graph.get_branch("sess1")
        assert len(branch) == 2
        assert branch[0].engram.id == "a"
        assert branch[1].engram.id == "b"

    def test_get_day_summary(self):
        """Get summary for a specific day."""
        graph = self._build_sample_graph()
        summary = graph.get_day_summary("2026-05-29")
        assert summary["conversation_count"] == 3
        assert summary["session_count"] == 2
        assert "sess1" in summary["sessions"]


class TestAIOptimizedOutput:
    """Verify JSON output is optimized for AI coder consumption."""

    def _build_rich_graph(self) -> ConversationGraph:
        """Build graph with realistic data for AI output testing."""
        now = datetime.now(timezone.utc)
        nodes = [
            EngramNode(
                engram=Engram(
                    id="fix-auth", source="cursor", source_file="/auth.py",
                    messages=[Message(role="user", content="Fix JWT bug")] * 5,
                    title="Fix JWT authentication bug", project_name="myapp",
                    created_at=now - timedelta(hours=2),
                ),
                depth=0, lineage=[], session_id="sess1", day_bucket="2026-05-29",
                outgoing_edges=["e1"],
            ),
            EngramNode(
                engram=Engram(
                    id="add-oauth", source="cursor", source_file="/oauth.py",
                    messages=[Message(role="user", content="Add OAuth")] * 3,
                    title="Add OAuth2 login", project_name="myapp",
                    created_at=now - timedelta(hours=1),
                ),
                depth=1, lineage=["fix-auth"], session_id="sess1", day_bucket="2026-05-29",
                incoming_edges=["e1"],
            ),
            EngramNode(
                engram=Engram(
                    id="setup-db", source="trae", source_file="/db.py",
                    messages=[Message(role="user", content="Setup DB")] * 25,
                    title="Setup PostgreSQL database", project_name="myapp",
                    created_at=now - timedelta(minutes=30),
                ),
                depth=0, lineage=[], session_id="sess2", day_bucket="2026-05-29",
            ),
        ]
        edges = [
            ConversationEdge(id="e1", source_engram_id="fix-auth", target_engram_id="add-oauth",
                           edge_type=EdgeType.CONTINUES_FROM, confidence=1.0),
        ]
        return ConversationGraph(workspace_key="ws-myapp", nodes=nodes, edges=edges, head_node_id="setup-db")

    def test_ai_summary_structure(self):
        """AI summary has actionable, structured fields."""
        graph = self._build_rich_graph()
        summary = graph.to_ai_summary(max_nodes=10)

        # Must have top-level structure
        assert "workspace_key" in summary
        assert "summary" in summary
        assert "recent_activity" in summary
        assert "suggested_context" in summary
        assert "actions_available" in summary

        # Summary stats must be present
        stats = summary["summary"]
        assert stats["total_conversations"] == 3
        assert stats["latest_conversation_id"] == "setup-db"
        assert "date_range" in stats

        # Recent activity items must have AI-useful fields
        for item in summary["recent_activity"]:
            assert "id" in item
            assert "title" in item
            assert "source" in item
            assert "message_count" in item
            assert "has_artifacts" in item

        # Actions must be actionable strings
        for action in summary["actions_available"]:
            assert "(" in action and ")" in action, f"Action '{action}' missing callable signature"
            assert "—" in action, f"Action '{action}' missing description separator"

    def test_ai_context_structure(self):
        """AI context format has rich context for LLM prompts."""
        graph = self._build_rich_graph()
        context = graph.to_ai_context("add-oauth")

        # Must have target info
        assert "target" in context
        assert context["target"]["id"] == "add-oauth"
        assert context["target"]["title"] == "Add OAuth2 login"
        assert context["target"]["message_count"] == 3
        assert context["target"]["project_name"] == "myapp"

        # Must have context sections
        assert "context" in context
        ctx = context["context"]
        assert "timeline_position" in ctx
        assert "ancestors" in ctx
        assert "siblings_same_session" in ctx
        assert "related_conversations" in ctx

        # Related must have reasons
        for rel in ctx["related_conversations"]:
            assert "reason" in rel
            assert rel["reason"] != ""

        # Must have suggested actions
        assert "suggested_next_actions" in context
        assert len(context["suggested_next_actions"]) > 0

    def test_ai_context_missing_target(self):
        """Graceful handling when target not found."""
        graph = self._build_rich_graph()
        result = graph.to_ai_context("nonexistent")
        assert "error" in result

    def test_json_serializable(self):
        """All output methods produce JSON-serializable output."""
        graph = self._build_rich_graph()

        # Test to_dict
        data = graph.to_dict()
        json_str = json.dumps(data, default=str)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        # Test to_ai_summary
        summary = graph.to_ai_summary()
        json_str = json.dumps(summary, default=str)
        assert isinstance(json_str, str)

        # Test to_ai_context
        context = graph.to_ai_context("fix-auth")
        json_str = json.dumps(context, default=str)
        assert isinstance(json_str, str)

    def test_token_efficiency(self):
        """AI output is token-efficient: no message content in summary."""
        graph = self._build_rich_graph()
        summary = graph.to_ai_summary()

        # Convert to string and check for large content
        json_str = json.dumps(summary, default=str)
        # Should not contain full message content
        assert "Fix JWT bug" not in json_str, "Message content leaked into summary"
        assert len(json_str) < 5000, f"Summary too large: {len(json_str)} chars"


class TestProjectStateCapture:
    """Test project state snapshot domain model."""

    def test_state_has_repo_path(self):
        """State captures repository path for workspace linking."""
        state = ProjectState(
            id="state-1", engram_id="eg-1",
            captured_at=datetime.now(timezone.utc),
            repo_path="/home/user/projects/myapp",
            repo_remote_url="github.com/user/myapp",
        )
        data = state.to_dict()
        assert data["repo_path"] == "/home/user/projects/myapp"
        assert data["repo_remote_url"] == "github.com/user/myapp"

    def test_state_git_context(self):
        """State captures git branch and commit."""
        state = ProjectState(
            id="state-2", engram_id="eg-2",
            captured_at=datetime.now(timezone.utc),
            git_branch="feature/oauth",
            git_commit="def4567890",
            git_dirty_files=["auth.py", "test_auth.py"],
        )
        data = state.to_dict()
        assert data["git_branch"] == "feature/oauth"
        assert data["git_commit"] == "def4567890"
        assert data["git_dirty_files"] == ["auth.py", "test_auth.py"]

    def test_state_transition(self):
        """State transition captures file changes."""
        transition = StateTransition(
            id="trans-1",
            from_state_id="state-a",
            to_state_id="state-b",
            files_added=["new.py"],
            files_modified=["changed.py"],
            lines_changed=45,
            branch_changed=False,
            commit_distance=2,
        )
        data = transition.to_dict()
        assert data["files_added"] == ["new.py"]
        assert data["lines_changed"] == 45
        assert data["commit_distance"] == 2


class TestDigitalArtifact:
    """Test digital artifact domain model."""

    def test_artifact_quality_fields(self):
        """Artifacts have confidence, verified, tests_pass fields."""
        art = DigitalArtifact(
            id="art-1", artifact_type=ArtifactType.BUGFIX,
            engram_id="eg-1", title="Fix race condition",
            content="lock.acquire()", language="python",
            confidence=0.95, verified=True, tests_pass=True,
        )
        data = art.to_dict()
        assert data["confidence"] == 0.95
        assert data["verified"] is True
        assert data["tests_pass"] is True

    def test_artifact_types(self):
        """All artifact types are valid enum values."""
        for art_type in ArtifactType:
            art = DigitalArtifact(
                id=f"art-{art_type.value}",
                artifact_type=art_type,
                engram_id="eg-1",
                title=f"Test {art_type.value}",
            )
            data = art.to_dict()
            assert data["artifact_type"] == art_type.value

    def test_artifact_usage(self):
        """Usage tracking records application of artifacts."""
        usage = ArtifactUsage(
            id="use-1", artifact_id="art-1",
            usage_type=UsageType.APPLIED_IN_PROJECT,
            target_file_path="src/auth.py",
            target_commit_hash="abc123",
            success=True,
        )
        data = usage.to_dict()
        assert data["usage_type"] == "applied_in_project"
        assert data["target_file_path"] == "src/auth.py"
        assert data["success"] is True

    def test_artifact_to_ai_dict(self):
        """Artifact serialization is AI-friendly with context."""
        art = DigitalArtifact(
            id="art-fix", artifact_type=ArtifactType.CODE_SOLUTION,
            engram_id="eg-1", title="JWT Validator",
            description="Validates JWT tokens with expiry check",
            content="def validate(token): ...",
            language="python",
            file_path="src/auth/jwt.py",
            confidence=0.92, verified=True,
        )
        data = art.to_dict()
        # AI can understand what this is and where it goes
        assert data["title"] == "JWT Validator"
        assert data["description"] != ""
        assert data["file_path"] == "src/auth/jwt.py"
        assert data["language"] == "python"
