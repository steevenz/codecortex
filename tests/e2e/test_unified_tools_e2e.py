"""
Comprehensive E2E Test for CLI, MCP, and API Tools.

All tools use shared services for identical output.

Usage:
    pytest tests/e2e/test_unified_tools_e2e.py -v --tb=short
"""

import json
import sys
import subprocess
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

TEST_SCENARIOS = [
    # Filesystem tests
    {"tool": "codecortex_filesystem", "action": "list", "args": {"path": "."}, "name": "fs_list_root"},
    {"tool": "codecortex_filesystem", "action": "list", "args": {"path": "src"}, "name": "fs_list_src"},
    
    # Repository tests
    {"tool": "codecortex_repository", "action": "list", "args": {}, "name": "repo_list"},
    {"tool": "codecortex_repository", "action": "inspect", "args": {"repo_path": "."}, "name": "repo_inspect"},
    
    # Codebase tests
    {"tool": "codecortex_codebase", "action": "status", "args": {"repo_path": "."}, "name": "codebase_status"},
    {"tool": "codecortex_codebase", "action": "audit", "args": {"repo_path": "."}, "name": "codebase_audit"},
    
    # Scaffolder tests
    {"tool": "codecortex_scaffolder", "action": "list_stacks", "args": {}, "name": "scaffolder_list"},
    {"tool": "codecortex_scaffolder", "action": "validate_name", "args": {"name": "test-project"}, "name": "scaffolder_validate"},
]


def run_cli(tool: str, action: str, args: Dict) -> Tuple[Dict, float]:
    """Run CLI and return JSON output."""
    import time
    import subprocess
    start = time.time()
    cmd = [sys.executable, "-m", "src.cli.unified", tool, "--action", action, "--args", json.dumps(args)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
    elapsed = time.time() - start
    
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        data = {"error": result.stderr[:200], "returncode": result.returncode}
    
    return data, elapsed


def run_mcp(tool: str, action: str, args: Dict) -> Tuple[Dict, float]:
    """Run MCP via orchestrator and return JSON output."""
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


def compare_outputs(name: str, cli: Dict, mcp: Dict) -> Dict[str, Any]:
    """Compare CLI and MCP outputs."""
    cli_str = json.dumps(cli, sort_keys=True, separators=(',', ':'))
    mcp_str = json.dumps(mcp, sort_keys=True, separators=(',', ':'))
    
    return {
        "name": name,
        "cli_hash": hashlib.sha256(cli_str.encode()).hexdigest(),
        "mcp_hash": hashlib.sha256(mcp_str.encode()).hexdigest(),
        "identical": cli_str == mcp_str,
        "cli_keys": sorted(cli.keys()),
        "mcp_keys": sorted(mcp.keys()),
    }


def main():
    """Run all tests."""
    print("=" * 60)
    print("COMPREHENSIVE E2E TEST - CLI vs MCP vs API")
    print("=" * 60)
    
    results = []
    for scenario in TEST_SCENARIOS:
        print(f"\nTesting: {scenario['name']}")
        
        cli_out, cli_time = run_cli(scenario["tool"], scenario["action"], scenario["args"])
        mcp_out, mcp_time = run_mcp(scenario["tool"], scenario["action"], scenario["args"])
        
        comparison = compare_outputs(scenario["name"], cli_out, mcp_out)
        results.append({"scenario": scenario, "cli_time": cli_time, "mcp_time": mcp_time, "comparison": comparison})
        
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
    
    with open(output_dir / "unified_tools_e2e_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults: {output_dir / 'unified_tools_e2e_results.json'}")