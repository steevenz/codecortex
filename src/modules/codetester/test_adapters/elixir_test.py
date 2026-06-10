"""
Elixir Test.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Elixir_test
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeTester-v1.0
"""

import subprocess
import os
from typing import Dict, Any, Optional
from src.modules.codetester.test_adapters.base import BaseQA

class ElixirTest(BaseQA):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "elixir_test", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Check for Elixir project signs: mix.exs
        mix_exs_path = os.path.join(repo_path, "mix.exs")
        if not os.path.exists(mix_exs_path):
            return {"tool": "elixir_test", "status": "error", "error": "mix.exs not found - Elixir test requires a Mix project"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "elixir_test", "status": "error", "error": "Target path is outside the repository"}
        
        # Build the elixir test command
        cmd = ["mix", "test"]
        if target_path:
            # mix test can take a specific test file or directory
            cmd.append(target_path)
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
            
            # elixir test exit code: 0 = success, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"
            
            return {
                "tool": "elixir_test",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "elixir_test", "status": "error", "error": "Elixir test execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "elixir_test", "status": "error", "error": "An error occurred while running elixir tests"}

    def get_name(self) -> str:
        return "elixir_test"
