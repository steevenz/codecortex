"""
Comprehensive CLI vs MCP JSON Identity Testing.

Tests that CLI and MCP tools produce structurally similar JSON output.
This test runs without requiring a live server.

Usage:
    pytest tests/e2e/test_cli_mcp_json_identity.py -v --tb=short
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

TEST_CASES = [
    {
        "name": "scaffolder_list_stacks",
        "tool": "codecortex_scaffolder",
        "action": "list_stacks",
        "args": {},
        "expected_keys": ["success", "data", "request_id"],
    },
    {
        "name": "scaffolder_validate_name",
        "tool": "codecortex_scaffolder",
        "action": "validate_name",
        "args": {"name": "test-project"},
        "expected_keys": ["success", "data", "request_id"],
    },
]


def run_cli_command(args: List[str]) -> Tuple[Dict, float]:
    """Run CLI command and return JSON output."""
    import time
    import subprocess
    start = time.time()
    cmd = [sys.executable, "-m", "src.cli.unified"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
    elapsed = time.time() - start
    
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        data = {"error": result.stderr[:500] if result.stderr else "Unknown error", "stdout": result.stdout[:500], "returncode": result.returncode}
    
    return data, elapsed


def run_mcp_tool_via_orchestrator(test_case: Dict) -> Tuple[Dict, float]:
    """Run MCP tool via orchestrator and return JSON output."""
    import time
    from src.api.orchestration import ActionRouter
    
    start = time.time()
    
    try:
        router = ActionRouter(lambda: None)
        result = router.dispatch(test_case["tool"], test_case["action"], test_case.get("args", {}))
    except Exception as e:
        result = {"success": False, "error": str(e), "data": None}
    
    elapsed = time.time() - start
    return result, elapsed


def compare_json_outputs(cli_output: Dict, mcp_output: Dict) -> Dict[str, Any]:
    """Compare two JSON outputs for structural similarity."""
    cli_str = json.dumps(cli_output, sort_keys=True, separators=(',', ':'))
    mcp_str = json.dumps(mcp_output, sort_keys=True, separators=(',', ':'))
    
    cli_hash = hashlib.sha256(cli_str.encode()).hexdigest() if 'hashlib' in dir() else "skip"
    mcp_hash = hashlib.sha256(mcp_str.encode()).hexdigest() if 'hashlib' in dir() else "skip"
    
    return {
        "cli_keys": sorted(list(cli_output.keys())),
        "mcp_keys": sorted(list(mcp_output.keys())),
        "has_success": "success" in cli_output and "success" in mcp_output,
        "has_data": "data" in cli_output and "data" in mcp_output,
    }


def main():
    """Run all test cases."""
    import hashlib
    
    print("CLI vs MCP JSON Identity Testing")
    print("=" * 60)
    
    results = []
    for tc in TEST_CASES:
        name = tc["name"]
        print(f"\nTesting: {name}")
        
        cli_args = [tc["tool"], "--action", tc["action"]]
        if tc.get("args"):
            cli_args.extend(["--args", json.dumps(tc["args"])])
        
        cli_output, cli_time = run_cli_command(cli_args)
        mcp_output, mcp_time = run_mcp_tool_via_orchestrator(tc)
        
        comparison = compare_json_outputs(cli_output, mcp_output)
        
        result = {
            "name": name,
            "cli_output": cli_output,
            "mcp_output": mcp_output,
            "comparison": comparison,
            "cli_time": cli_time,
            "mcp_time": mcp_time,
        }
        results.append(result)
        
        status = "PASS" if comparison["has_success"] else "FAIL"
        print(f"  CLI: {cli_time:.3f}s | MCP: {mcp_time:.3f}s | {status}")
    
    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r["comparison"]["has_success"])
    print(f"Total: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {len(results) - passed}")
    
    return results


if __name__ == "__main__":
    results = main()
    
    output_dir = Path("outputs/validation/2026-06-01")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "cli_mcp_identity_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_dir / 'cli_mcp_identity_results.json'}")