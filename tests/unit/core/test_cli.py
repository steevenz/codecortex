"""
Tests for CLI and MCP multi-IDE support.
"""
import sys, os, subprocess, json
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

CLI_PATH = str(Path(__file__).resolve().parents[1] / "scripts" / "cli.py")


def test_cli_version():
    result = subprocess.run(
        [sys.executable, "scripts/cli.py", "version"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0
    assert "CodeCortex" in result.stdout


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "scripts/cli.py", "help"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0
    assert "repository" in result.stdout


def test_cli_list_repos():
    result = subprocess.run(
        [sys.executable, "scripts/cli.py", "repo", "list"],
        capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0
    assert '"repositories"' in result.stdout


def test_cli_status_offline():
    result = subprocess.run(
        [sys.executable, "scripts/cli.py", "server", "status"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode != 0  # expected: server not running
    assert '"SERVER_OFFLINE"' in result.stdout


def test_cli_fs_read():
    result = subprocess.run(
        [sys.executable, "scripts/cli.py", "fs", "read", "scripts/cli.py"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0
    assert "success" in result.stdout


def test_cli_sc_stacks():
    result = subprocess.run(
        [sys.executable, "scripts/cli.py", "sc", "list-stacks"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0
    assert '"stacks"' in result.stdout


def test_package_node():
    pkg = json.loads(Path("package.json").read_text())
    assert "bin" in pkg
    assert "codecortex-mcp" in pkg["bin"]
    assert "config" in pkg
    assert "codeCortex" in pkg["config"]
    assert pkg["config"]["codeCortex"]["graphBackend"] == "kuzu"


if __name__ == "__main__":
    print("ALL CLI TESTS PASSED!")
