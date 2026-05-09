from pathlib import Path


def test_file_reader_read_and_hash(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "x.txt").write_text("hello\n", encoding="utf-8")

    from src.domain.coderepository.infrastructure.file_reader import FileReader

    r = FileReader(repo_root)
    content = r.read("x.txt")
    assert content == "hello\n"

    h = r.calculate_hash("x.txt")
    assert isinstance(h, str)
    assert len(h) == 64


def test_file_reader_blocks_path_traversal(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "x.txt").write_text("hello\n", encoding="utf-8")

    from src.domain.coderepository.infrastructure.file_reader import FileReader

    r = FileReader(repo_root)
    assert "Path traversal detected" in r.read("../x.txt")
    assert "Path traversal detected" in r.read("..\\x.txt")
    assert "Path traversal detected" in r.read("/x.txt")
    assert "Path traversal detected" in r.read("sub\\x.txt")


