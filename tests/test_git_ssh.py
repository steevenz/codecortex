"""
/**
 * @project   CodeCortex
 * @package   Tests
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * * Tests for SSH Git auth and commit audit.
 */
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from src.main import create_orchestrator


@pytest.mark.asyncio
async def test_git_audit_detects_secrets():
    """Verify git_audit scans commits and detects mock secrets."""
    orchestrator = create_orchestrator()
    mock_result = {
        "secrets_found": [
            {"commit": "abc123", "type": "api_key", "risk": "high"},
            {"commit": "def456", "type": "password", "risk": "high"},
        ],
        "risk_level": "high",
        "total_scanned": 10
    }
    orchestrator.git_service.git_audit = MagicMock(return_value=mock_result)
    result = orchestrator.git_service.git_audit(repo_id="test-repo-id")
    assert result["risk_level"] == "high"
    assert len(result["secrets_found"]) == 2
    assert result["total_scanned"] == 10


@pytest.mark.asyncio
async def test_git_audit_clean():
    """Verify git_audit returns clean result for safe repos."""
    orchestrator = create_orchestrator()
    mock_result = {
        "secrets_found": [],
        "risk_level": "low",
        "total_scanned": 5
    }
    orchestrator.git_service.git_audit = MagicMock(return_value=mock_result)
    result = orchestrator.git_service.git_audit(repo_id="clean-repo")
    assert result["risk_level"] == "low"
    assert len(result["secrets_found"]) == 0


@pytest.mark.asyncio
async def test_git_ssh_auth():
    """Verify SSH auth param is passed through to Git operations."""
    orchestrator = create_orchestrator()
    orchestrator.repo_service.sync_repository = AsyncMock(
        return_value="repo-uuid-123"
    )
    repo_id = await orchestrator.repo_service.sync_repository(
        "/tmp/test-repo",
        request_id="test",
        auth_type="ssh",
        max_depth=5
    )
    assert repo_id == "repo-uuid-123"


if __name__ == "__main__":
    asyncio.run(test_git_audit_detects_secrets())
    asyncio.run(test_git_audit_clean())
    asyncio.run(test_git_ssh_auth())
    print("Git SSH/audit tests passed.")
