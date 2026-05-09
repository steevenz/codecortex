"""
Tests for CLI and MCP multi-IDE support.
"""
import sys, os, subprocess, json
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

CLI_PATH = str(Path(__file__).resolve().parents[1] / "scripts" / "cli.py")


def test_cli_version():
    result = subprocess.run(
        [sys.executable, "scripts/cli.py", "--version"],
        capture_output=True, text=True, timeout=15
    )
    assert result.returncode == 0
    assert "CodeCortex" in result.stdout


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "scripts/cli.py", "--help"],
        capture_output=True, text=True, timeout=15
    )
    assert result.returncode == 0
    assert "--init" in result.stdout


def test_cli_list_repos():
    result = subprocess.run(
        [sys.executable, "scripts/cli.py", "--list-repos"],
        capture_output=True, text=True, timeout=15
    )
    assert result.returncode == 0
    assert '"repositories"' in result.stdout


def test_cli_status_offline():
    result = subprocess.run(
        [sys.executable, "scripts/cli.py", "--status"],
        capture_output=True, text=True, timeout=15
    )
    assert result.returncode == 0


def test_cli_batch():
    import tempfile
    cli_path = str(Path(__file__).resolve().parents[1] / "scripts" / "cli.py")
    tmpdir_obj = tempfile.TemporaryDirectory()
    try:
        tmpdir = tmpdir_obj.name
        batch_json = json.dumps([{"action": "create", "path": "test.txt", "content": "hello"}])
        result = subprocess.run(
            [sys.executable, cli_path, "--batch", batch_json],
            capture_output=True, text=True, timeout=15, cwd=tmpdir
        )
        assert result.returncode == 0, f"stderr: {result.stderr[:200]}"
        assert Path(tmpdir, "test.txt").exists()
    finally:
        try: tmpdir_obj.cleanup()
        except: pass


def test_cli_audit():
    import tempfile
    cli_path = str(Path(__file__).resolve().parents[1] / "scripts" / "cli.py")
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [sys.executable, cli_path, "--audit", tmpdir],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0


def test_package_node():
    pkg = json.loads(Path("package.json").read_text())
    assert "bin" in pkg
    assert "codecortex" in pkg["bin"]
    assert "mcp" in pkg
    assert "server" in pkg["mcp"]
    assert "stdio" in pkg["mcp"]


if __name__ == "__main__":
    print("ALL CLI TESTS PASSED!")
