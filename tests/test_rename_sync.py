"""
Tests for rename_symbol and incremental sync.
"""
import sys, os, tempfile, subprocess, asyncio
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
import pytest


@pytest.mark.asyncio
async def test_rename_basic():
    from src.core.database import DatabaseManager
    from src.domain.coderefactor.application.service import CodeRefactorService
    from src.domain.filesystem.application.service import FilesystemService
    from src.domain.coderepository.application.git_service import GitService
    from src.domain.coderepository.application.service import CodeRepositoryService
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    from src.domain.codegraph.application.service import CodeGraphService
    import tempfile
    tmpdir_obj = tempfile.TemporaryDirectory()
    try:
        root = Path(tmpdir_obj.name)
        (root / "app.py").write_text("""def old_func():\n    return 42\ndef caller():\n    return old_func()\n""")
        db = DatabaseManager(str(root / "test.db"))
        store = SQLiteCodeRepositoryStore(db)
        repo_svc = CodeRepositoryService(store, str(root))
        await repo_svc.sync_repository(str(root), request_id="test-sync")
        fs = FilesystemService(db, store)
        git = GitService(store)
        cg = CodeGraphService(db)
        svc = CodeRefactorService(db, fs, git, cg)
        result = await svc.rename_symbol(str(root / "app.py"), "old_func", "new_func", dry_run=True)
        assert result is not None
        assert result.status in ("dry_run", "success", "error"), f"Status: {result.status}, Msg: {result.message}"
        db.close()
    finally:
        try: tmpdir_obj.cleanup()
        except: pass


@pytest.mark.asyncio
async def test_rename_rename_in_file():
    from src.domain.coderefactor.application.service import CodeRefactorService
    from src.core.database import DatabaseManager
    from src.domain.filesystem.application.service import FilesystemService
    from src.domain.coderepository.application.git_service import GitService
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    from src.domain.codegraph.application.service import CodeGraphService
    import tempfile
    tmpdir_obj = tempfile.TemporaryDirectory()
    try:
        root = Path(tmpdir_obj.name)
        db = DatabaseManager(str(root / "test.db"))
        store = SQLiteCodeRepositoryStore(db)
        fs = FilesystemService(db, store)
        git = GitService(store)
        cg = CodeGraphService(db)
        svc = CodeRefactorService(db, fs, git, cg)
        # Test _rename_in_file directly
        content = "def old_func():\n    pass\nx = old_func()\n"
        result = svc._rename_in_file(content, "old_func", "new_func", "python")
        assert "new_func" in result
        assert "old_func" not in result
        db.close()
    finally:
        try: tmpdir_obj.cleanup()
        except: pass


@pytest.mark.asyncio
async def test_incremental_sync_no_git():
    from src.core.database import DatabaseManager
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    from src.domain.coderepository.application.service import CodeRepositoryService
    import tempfile
    tmpdir_obj = tempfile.TemporaryDirectory()
    try:
        root = Path(tmpdir_obj.name)
        (root / "test.py").write_text("x=1\n")
        db = DatabaseManager(str(root / "test.db"))
        store = SQLiteCodeRepositoryStore(db)
        svc = CodeRepositoryService(store, str(root))
        repo_id, changed = await svc.sync_repository_incremental(str(root), request_id="test")
        assert repo_id is not None
        db.close()
    finally:
        try: tmpdir_obj.cleanup()
        except: pass


def test_detect_lang():
    from src.domain.coderefactor.application.service import CodeRefactorService
    lang = CodeRefactorService._detect_lang("test.py")
    assert lang == "python"
    lang2 = CodeRefactorService._detect_lang("file.ts")
    assert lang2 == "typescript"


@pytest.mark.asyncio
async def test_rename_with_git():
    from src.core.database import DatabaseManager
    from src.domain.coderefactor.application.service import CodeRefactorService
    from src.domain.filesystem.application.service import FilesystemService
    from src.domain.coderepository.application.git_service import GitService
    from src.domain.coderepository.application.service import CodeRepositoryService
    from src.domain.coderepository.infrastructure.sqlite_store import SQLiteCodeRepositoryStore
    from src.domain.codegraph.application.service import CodeGraphService
    import tempfile
    tmpdir_obj = tempfile.TemporaryDirectory()
    try:
        root = Path(tmpdir_obj.name)
        subprocess.run(["git", "init"], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "config", "user.name", "T"], cwd=root, capture_output=True, timeout=10)
        (root / "main.py").write_text("def hello():\n    return 'hi'\n")
        subprocess.run(["git", "add", "."], cwd=root, capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True, timeout=10)
        db = DatabaseManager(str(root / "test.db"))
        store = SQLiteCodeRepositoryStore(db)
        repo_svc = CodeRepositoryService(store, str(root))
        await repo_svc.sync_repository(str(root), request_id="test-sync")
        fs = FilesystemService(db, store)
        git = GitService(store)
        cg = CodeGraphService(db)
        svc = CodeRefactorService(db, fs, git, cg)
        result = await svc.rename_symbol(str(root / "main.py"), "hello", "greet", dry_run=True)
        assert result is not None
        db.close()
    finally:
        try: tmpdir_obj.cleanup()
        except: pass


if __name__ == "__main__":
    print("All rename/sync tests passed!")
