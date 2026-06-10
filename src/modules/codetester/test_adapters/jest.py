"""
Jest.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Jest
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeTester-v1.0
"""

import subprocess
import json
import os
from typing import Dict, Any, Optional
from src.modules.codetester.test_adapters.base import BaseQA

class Jest(BaseQA):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "jest", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Check if we have package.json and jest configured
        package_json_path = os.path.join(repo_path, "package.json")
        if not os.path.exists(package_json_path):
            return {"tool": "jest", "status": "error", "error": "package.json not found - Jest requires a Node.js project"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "jest", "status": "error", "error": "Target path is outside the repository"}
        
        # Build the jest command
        cmd = ["npx", "jest", "--json", "--outputFile=/tmp/jest_report.json"]
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
            
            # Try to read the JSON report if it was created
            report_data = {}
            report_path = "/tmp/jest_report.json"
            if os.path.exists(report_path):
                try:
                    with open(report_path, "r") as f:
                        report_data = json.load(f)
                    os.remove(report_path)
                except Exception:
                    pass  # If we can't read the report, we'll still return the basic result
            
            # Jest exit code: 0 = all tests passed, 1 = some tests failed
            status = "success" if result.returncode == 0 else "failed"
            
            response = {
                "tool": "jest",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
            
            # Add report data if available
            if report_data:
                response["report"] = {
                    "total_tests": report_data.get("numTotalTests", 0),
                    "passed": report_data.get("numPassedTests", 0),
                    "failed": report_data.get("numFailedTests", 0),
                    "pending": report_data.get("numPendingTests", 0),
                    "duration": report_data.get("testResults", [{}])[0].get("perfStats", {}).get("end", 0) - 
                               report_data.get("testResults", [{}])[0].get("perfStats", {}).get("start", 0)
                }
            
            return response
        except subprocess.TimeoutExpired:
            # Clean up temp file if it exists
            if os.path.exists("/tmp/jest_report.json"):
                try:
                    os.remove("/tmp/jest_report.json")
                except:
                    pass
            return {"tool": "jest", "status": "error", "error": "Jest execution timed out"}
        except Exception as e:
            # Clean up temp file if it exists
            if os.path.exists("/tmp/jest_report.json"):
                try:
                    os.remove("/tmp/jest_report.json")
                except:
                    pass
            # Avoid leaking internal error details in production
            return {"tool": "jest", "status": "error", "error": "An error occurred while running jest"}

    def get_name(self) -> str:
        return "jest"
