"""
Vitest.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Vitest
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeTester-v1.0
"""

import subprocess
import json
import os
from typing import Dict, Any, Optional
from src.modules.codetester.test_adapters.base import BaseQA

class Vitest(BaseQA):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "vitest", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Check for package.json to ensure we are in an npm project
        package_json_path = os.path.join(repo_path, "package.json")
        if not os.path.exists(package_json_path):
            return {"tool": "vitest", "status": "error", "error": "package.json not found - Vitest requires a Node.js project"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "vitest", "status": "error", "error": "Target path is outside the repository"}
        
        # Build the vitest command
        cmd = ["npx", "vitest", "run", "--reporter=json"]
        if target_path:
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
            
            # Try to read the JSON output if it was produced (vitest --reporter=json outputs to stdout)
            report_data = {}
            if result.stdout:
                try:
                    report_data = json.loads(result.stdout)
                except json.JSONDecodeError:
                    pass  # If we can't parse JSON, we'll still return the basic result
            
            # Vitest exit code: 0 = all tests passed, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"
            
            response = {
                "tool": "vitest",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
            
            # Add report data if available
            if report_data:
                # Vitest JSON reporter output structure may vary; we try to extract common fields
                response["report"] = {
                    "total_tests": report_data.get("tests", {}).get("total", 0),
                    "passed": report_data.get("tests", {}).get("passed", 0),
                    "failed": report_data.get("tests", {}).get("failed", 0),
                    "skipped": report_data.get("tests", {}).get("skipped", 0),
                    "duration": report_data.get("duration", 0)
                }
            
            return response
        except subprocess.TimeoutExpired:
            return {"tool": "vitest", "status": "error", "error": "Vitest execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "vitest", "status": "error", "error": "An error occurred while running vitest"}

    def get_name(self) -> str:
        return "vitest"
