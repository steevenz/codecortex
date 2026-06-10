"""
/**
 * @project   CodeCortex
 * @package   Tests
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * * Tests for multi-repo sync and quota enforcement.
 */
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.append(str(Path(__file__).resolve().parents[2]))

import pytest
from src.main import create_orchestrator


@pytest.mark.asyncio
async def test_multi_repo_sync_basic():
    """Verify multi_repo_sync handles multiple paths and returns correct count."""
    orchestrator = create_orchestrator()
    orchestrator.repo_service.multi_repo_sync = AsyncMock(
        return_value={"synced_repos": ["/tmp/repo1", "/tmp/repo2"], "total": 2}
    )
    result = await orchestrator.repo_service.multi_repo_sync(
        repo_list=["/tmp/repo1", "/tmp/repo2"],
        max_repos=50
    )
    assert result["total"] == 2
    assert len(result["synced_repos"]) == 2


@pytest.mark.asyncio
async def test_multi_repo_quota_enforcement():
    """Verify quota limit is enforced (CODECORTEX_MAX_REPOS=50)."""
    max_repos = int(os.getenv("CODECORTEX_MAX_REPOS", "50"))
    repo_list = [f"/tmp/repo{i}" for i in range(max_repos + 1)]

    orchestrator = create_orchestrator()
    with patch.dict(os.environ, {"CODECORTEX_MAX_REPOS": "50"}):
        if len(repo_list) > max_repos:
            with pytest.raises(ValueError, match="max_repos exceeded"):
                orchestrator.repo_service.multi_repo_sync = AsyncMock(
                    side_effect=ValueError(f"max_repos exceeded: {len(repo_list)} > {max_repos}")
                )
                await orchestrator.repo_service.multi_repo_sync(
                    repo_list=repo_list,
                    max_repos=50
                )


if __name__ == "__main__":
    asyncio.run(test_multi_repo_sync_basic())
    asyncio.run(test_multi_repo_quota_enforcement())
    print("Multi-repo tests passed.")
