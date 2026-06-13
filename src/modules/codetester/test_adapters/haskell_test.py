"""
Haskell Test.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Haskell_test
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeTester-v1.0
"""

import subprocess
import os
from typing import Dict, Any, Optional
from src.modules.codetester.test_adapters.base import BaseQA

class HaskellTest(BaseQA):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "haskell_test", "status": "error", "error": f"Repository path does not exist: {repo_path}"}

        # Check for Haskell project signs: .cabal file or package.yaml or stack.yaml
        has_cabal = any(f.endswith(".cabal") for f in os.listdir(repo_path) if os.path.isfile(os.path.join(repo_path, f)))
        has_package_yaml = os.path.exists(os.path.join(repo_path, "package.yaml"))
        has_stack_yaml = os.path.exists(os.path.join(repo_path, "stack.yaml"))

        if not (has_cabal or has_package_yaml or has_stack_yaml):
            return {"tool": "haskell_test", "status": "error", "error": "No Haskell project found (missing .cabal, package.yaml, or stack.yaml)"}

        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "haskell_test", "status": "error", "error": "Target path is outside the repository"}

        # Build the haskell test command
        # Prefer stack if stack.yaml exists, otherwise try cabal
        if has_stack_yaml:
            cmd = ["stack", "test"]
        elif has_cabal or has_package_yaml:
            cmd = ["cabal", "test"]
        else:
            return {"tool": "haskell_test", "status": "error", "error": "Could not determine Haskell test method"}

        if target_path:
            # For Haskell testing, target could be a test suite name
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

            # Haskell test exit code: 0 = success, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"

            return {
                "tool": "haskell_test",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "haskell_test", "status": "error", "error": "Haskell test execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "haskell_test", "status": "error", "error": "An error occurred while running Haskell tests"}

    def get_name(self) -> str:
        return "haskell_test"
