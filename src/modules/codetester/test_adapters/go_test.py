"""
Go Test.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Go_test
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeTester-v1.0
"""

import subprocess
import os
from typing import Dict, Any, Optional
from src.modules.codetester.test_adapters.base import BaseQA

class GoTest(BaseQA):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "go_test", "status": "error", "error": f"Repository path does not exist: {repo_path}"}

        # Check for go.mod to ensure we are in a Go module
        go_mod_path = os.path.join(repo_path, "go.mod")
        if not os.path.exists(go_mod_path):
            return {"tool": "go_test", "status": "error", "error": "go.mod not found - Go test requires a Go module"}

        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "go_test", "status": "error", "error": "Target path is outside the repository"}

        # Build the go test command
        cmd = ["go", "test", "./..."]
        if target_path:
            # If target_path is provided, we can test specific packages
            # We'll use the target_path as a package pattern relative to repo_path
            cmd[-1] = target_path  # replace "./..." with target_path
        if extra_args:
            cmd.extend(extra_args.split())

        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120
            )

            # go test exit code: 0 = success, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"

            return {
                "tool": "go_test",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "go_test", "status": "error", "error": "Go test execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "go_test", "status": "error", "error": "An error occurred while running go test"}

    def get_name(self) -> str:
        return "go_test"
