"""
Npm.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Npm
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeTester-v1.0
"""

import subprocess
import os
from typing import Dict, Any, Optional
from src.modules.codetester.test_adapters.base import BaseQA

class Npm(BaseQA):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "npm", "status": "error", "error": f"Repository path does not exist: {repo_path}"}

        # Check for package.json to ensure we are in an npm project
        package_json_path = os.path.join(repo_path, "package.json")
        if not os.path.exists(package_json_path):
            return {"tool": "npm", "status": "error", "error": "package.json not found - npm requires a Node.js project"}

        # Prevent path traversal for target_path (though npm test doesn't take a target path in the same way, we'll still check if provided)
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "npm", "status": "error", "error": "Target path is outside the repository"}

        # Build the npm test command
        cmd = ["npm", "test"]
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

            # npm test exit code: 0 = success, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"

            return {
                "tool": "npm",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "npm", "status": "error", "error": "npm test execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "npm", "status": "error", "error": "An error occurred while running npm test"}

    def get_name(self) -> str:
        return "npm"
