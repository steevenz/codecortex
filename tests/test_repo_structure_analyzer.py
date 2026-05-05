from pathlib import Path


def test_repo_structure_analyzer_respects_gitignore(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (repo_root / "kept.txt").write_text("ok", encoding="utf-8")
    (repo_root / "ignored.txt").write_text("no", encoding="utf-8")

    from src.domain.repository.analyzer import RepoStructureAnalyzer

    a = RepoStructureAnalyzer(repo_root)
    tree = a.get_structure(max_depth=2)
    assert tree.type == "directory"
    names = {c.path for c in tree.children}
    assert "kept.txt" in names
    assert "ignored.txt" not in names

