"""
Cargo Test.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Cargo_test
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeTester-v1.0
"""

import subprocess
import os
from typing import Dict, Any, Optional
from src.modules.codetester.test_adapters.base import BaseQA

class CargoTest(BaseQA):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "cargo_test", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Check for Cargo.toml to ensure we are in a Rust project
        cargo_toml_path = os.path.join(repo_path, "Cargo.toml")
        if not os.path.exists(cargo_toml_path):
            return {"tool": "cargo_test", "status": "error", "error": "Cargo.toml not found - Rust test requires a Cargo project"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "cargo_test", "status": "error", "error": "Target path is outside the repository"}
        
        # Build the cargo test command
        cmd = ["cargo", "test"]
        if target_path:
            # If target_path is provided, we can run a specific test (filter)
            # We'll use the --test flag? Actually, cargo test allows a filter argument.
            # We'll just append the target_path as a filter.
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
            
            # cargo test exit code: 0 = success, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"
            
            return {
                "tool": "cargo_test",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "cargo_test", "status": "error", "error": "Cargo test execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "cargo_test", "status": "error", "error": "An error occurred while running cargo test"}

    def get_name(self) -> str:
        return "cargo_test"
