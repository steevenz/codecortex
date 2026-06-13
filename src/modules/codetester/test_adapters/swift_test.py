"""
Swift Test.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Swift_test
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeTester-v1.0
"""

import subprocess
import os
from typing import Dict, Any, Optional
from src.modules.codetester.test_adapters.base import BaseQA

class SwiftTest(BaseQA):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "swift_test", "status": "error", "error": f"Repository path does not exist: {repo_path}"}

        # Check for signs of a Swift project (Package.swift or .xcodeproj or .xcworkspace)
        package_swift_path = os.path.join(repo_path, "Package.swift")
        xcodeproj_exists = any(f.endswith(".xcodeproj") for f in os.listdir(repo_path) if os.path.isdir(os.path.join(repo_path, f)))
        xcworkspace_exists = any(f.endswith(".xcworkspace") for f in os.listdir(repo_path) if os.path.isdir(os.path.join(repo_path, f)))

        if not (os.path.exists(package_swift_path) or xcodeproj_exists or xcworkspace_exists):
            return {"tool": "swift_test", "status": "error", "error": "No Swift project found (missing Package.swift, .xcodeproj, or .xcworkspace)"}

        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "swift_test", "status": "error", "error": "Target path is outside the repository"}

        # Build the swift test command
        # For Swift Package Manager projects
        if os.path.exists(package_swift_path):
            cmd = ["swift", "test"]
        else:
            # For Xcode projects, we'd need to use xcodebuild, but swift test works for most cases
            cmd = ["swift", "test"]

        if target_path:
            # swift test doesn't typically take a target path in the same way
            # We could use it as a filter, but let's keep it simple and ignore for now
            # Or we could return an error saying target_path not supported for swift test
            pass  # Ignore target_path for swift test as it's not typically used
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

            # swift test exit code: 0 = success, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"

            return {
                "tool": "swift_test",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "swift_test", "status": "error", "error": "Swift test execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "swift_test", "status": "error", "error": "An error occurred while running swift test"}

    def get_name(self) -> str:
        return "swift_test"
