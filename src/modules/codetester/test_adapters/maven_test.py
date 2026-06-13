"""
Maven Test.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Maven_test
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeTester-v1.0
"""

import subprocess
import os
from typing import Dict, Any, Optional
from src.modules.codetester.test_adapters.base import BaseQA

class MavenTest(BaseQA):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "maven_test", "status": "error", "error": f"Repository path does not exist: {repo_path}"}

        # Check for pom.xml to ensure we are in a Maven project
        pom_xml_path = os.path.join(repo_path, "pom.xml")
        if not os.path.exists(pom_xml_path):
            return {"tool": "maven_test", "status": "error", "error": "pom.xml not found - Maven test requires a Maven project"}

        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "maven_test", "status": "error", "error": "Target path is outside the repository"}

        # Build the maven test command
        cmd = ["mvn", "test"]
        if target_path:
            # Maven allows specifying test classes or methods to run
            # For simplicity, we'll add it as an argument (though proper usage would be -Dtest=ClassName#methodName)
            cmd.append(target_path)
        if extra_args:
            cmd.extend(extra_args.split())

        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=180  # Longer timeout for JVM-based builds
            )

            # maven test exit code: 0 = success, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"

            return {
                "tool": "maven_test",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "maven_test", "status": "error", "error": "Maven test execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "maven_test", "status": "error", "error": "An error occurred while running maven test"}

    def get_name(self) -> str:
        return "maven_test"
