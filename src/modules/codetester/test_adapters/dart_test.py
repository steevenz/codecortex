"""
Dart Test.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Dart_test
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeTester-v1.0
"""

import subprocess
import os
from typing import Dict, Any, Optional
from src.modules.codetester.test_adapters.base import BaseQA

class DartTest(BaseQA):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "dart_test", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Check for Dart project signs: pubspec.yaml
        pubspec_path = os.path.join(repo_path, "pubspec.yaml")
        if not os.path.exists(pubspec_path):
            return {"tool": "dart_test", "status": "error", "error": "pubspec.yaml not found - Dart test requires a Dart project"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "dart_test", "status": "error", "error": "Target path is outside the repository"}
        
        # Build the dart test command
        cmd = ["dart", "test"]
        if target_path:
            # dart test can take a test file or directory to run
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
            
            # dart test exit code: 0 = success, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"
            
            return {
                "tool": "dart_test",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "dart_test", "status": "error", "error": "Dart test execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "dart_test", "status": "error", "error": "An error occurred while running dart test"}

    def get_name(self) -> str:
        return "dart_test"
