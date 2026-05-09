
import pytest
import os
import json
from pathlib import Path
from src.main import create_orchestrator
from src.domain.coderefactor.core.dtos import RefactorResult

@pytest.mark.asyncio
async def test_refactor_diff_generation():
    # Setup test repository
    test_repo_path = Path("scratch/test_refactor_diff").resolve()
    test_repo_path.mkdir(parents=True, exist_ok=True)
    
    hello_py = test_repo_path / "hello.py"
    hello_py.write_text("def old_func():\n    print('hello')\n", encoding="utf-8")
    
    main_py = test_repo_path / "main.py"
    main_py.write_text("from hello import old_func\nold_func()\n", encoding="utf-8")
    
    orchestrator = create_orchestrator()
    try:
        # 1. Init repo
        repo_id = await orchestrator.repo_service.initialize(str(test_repo_path))
        assert repo_id is not None
        
        # 2. Index repo
        await orchestrator.index_service.index_repository(repo_id)
        
        # 3. Test Rename with Diff
        result = await orchestrator.refactor_service.rename_symbol(
            path=str(hello_py),
            old_name="old_func",
            new_name="new_func",
            dry_run=True
        )
        
        assert result.status == "dry_run"
        assert len(result.changes) >= 2
        
        # Verify diff content
        hello_change = next(c for c in result.changes if "hello.py" in c.path)
        assert "-def old_func():" in hello_change.diff
        assert "+def new_func():" in hello_change.diff
        
        main_change = next(c for c in result.changes if "main.py" in c.path)
        assert "-from hello import old_func" in main_change.diff
        assert "+from hello import new_func" in main_change.diff
        assert "-old_func()" in main_change.diff
        assert "+new_func()" in main_change.diff
        
        print("SUCCESS: Diff generation verified for rename_symbol")

        # 4. Test Search/Replace with Diff
        search_res = await orchestrator.refactor_service.search.replace_code(
            repo_id=repo_id,
            find_query="hello",
            replace_text="greetings",
            dry_run=True
        )
        
        assert search_res["status"] == "dry_run"
        assert search_res["files_count"] > 0
        assert "diff" in search_res["affected_files"][0]
        assert "-    print('hello')" in search_res["affected_files"][0]["diff"]
        assert "+    print('greetings')" in search_res["affected_files"][0]["diff"]

        print("SUCCESS: Diff generation verified for search_replace")

    finally:
        orchestrator.db.close()
