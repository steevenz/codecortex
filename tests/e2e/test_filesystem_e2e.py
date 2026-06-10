"""
End-to-End Filesystem Testing for CLI vs MCP.

Tests identical scenarios on both CLI and MCP tools to verify JSON output identity.

Usage:
    pytest tests/e2e/test_filesystem_e2e.py -v --tb=short
"""

import json
import os
import sys
import subprocess
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

TEST_SCENARIOS = [
    {
        "name": "list_current_directory",
        "description": "List contents of current directory",
        "cli_action": "list",
        "mcp_action": "list",
        "args": {"path": "."},
    },
    {
        "name": "list_src_directory",
        "description": "List contents of src directory",
        "cli_action": "list",
        "mcp_action": "list",
        "args": {"path": "src"},
    },
    {
        "name": "read_package_json",
        "description": "Read package.json file",
        "cli_action": "read",
        "mcp_action": "read",
        "args": {"path": "package.json"},
    },
    {
        "name": "check_dir_exists",
        "description": "Check if directory exists",
        "cli_action": "list",
        "mcp_action": "list",
        "args": {"path": "."},
    },
]


def run_cli_test(tool: str, action: str, args: Dict) -> Tuple[Dict, float]:
    """Run CLI test and return JSON output."""
    import time
    start = time.time()
    cmd = [sys.executable, "-m", "src.cli.unified", tool, "--action", action, "--args", json.dumps(args)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
    elapsed = time.time() - start

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        data = {"error": result.stderr[:500], "returncode": result.returncode}

    return data, elapsed


def run_mcp_test(tool: str, action: str, args: Dict) -> Tuple[Dict, float]:
    """Run MCP test via orchestrator and return JSON output."""
    import time
    import asyncio
    from src.api.orchestration import ActionRouter

    start = time.time()
    try:
        router = ActionRouter(lambda: None)
        result = asyncio.run(router.dispatch(tool, action, args))
    except Exception as e:
        result = {"success": False, "error": str(e)}
    elapsed = time.time() - start
    return result, elapsed


def compare_outputs(cli: Dict, mcp: Dict) -> Dict[str, Any]:
    """Deep compare two JSON outputs."""
    cli_str = json.dumps(cli, sort_keys=True, separators=(',', ':'))
    mcp_str = json.dumps(mcp, sort_keys=True, separators=(',', ':'))

    return {
        "cli_keys": sorted(cli.keys()),
        "mcp_keys": sorted(mcp.keys()),
        "identical": cli_str == mcp_str,
        "cli_hash": hashlib.sha256(cli_str.encode()).hexdigest(),
        "mcp_hash": hashlib.sha256(mcp_str.encode()).hexdigest(),
    }


def main():
    """Run all E2E tests."""
    print("Filesystem E2E Testing - CLI vs MCP")
    print("=" * 60)

    results = []
    for scenario in TEST_SCENARIOS:
        print(f"\nTesting: {scenario['name']}")
        print(f"  Description: {scenario['description']}")

        cli_out, cli_time = run_cli_test("codecortex_filesystem", scenario["cli_action"], scenario["args"])
        mcp_out, mcp_time = run_mcp_test("codecortex_filesystem", scenario["mcp_action"], scenario["args"])

        comparison = compare_outputs(cli_out, mcp_out)

        result = {
            "scenario": scenario,
            "cli_output": cli_out,
            "mcp_output": mcp_out,
            "comparison": comparison,
            "cli_time": cli_time,
            "mcp_time": mcp_time,
        }
        results.append(result)

        status = "PASS" if comparison["identical"] else "FAIL"
        print(f"  CLI: {cli_time:.3f}s | MCP: {mcp_time:.3f}s | {status}")

    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r["comparison"]["identical"])
    print(f"Total: {len(results)} | Passed: {passed} | Failed: {len(results) - passed}")

    return results


if __name__ == "__main__":
    results = main()
    output_dir = Path("outputs/validation/2026-06-01")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "filesystem_e2e_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nResults: {output_dir / 'filesystem_e2e_results.json'}")
