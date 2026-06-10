"""
Kotlin Test.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Kotlin_test
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeTester-v1.0
"""

import subprocess
import os
from typing import Dict, Any, Optional
from src.modules.codetester.test_adapters.base import BaseQA

class KotlinTest(BaseQA):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "kotlin_test", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Check for signs of a Kotlin/Gradle project (build.gradle, build.gradle.kts, settings.gradle, etc.)
        gradle_files = ["build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"]
        has_gradle = any(os.path.exists(os.path.join(repo_path, f)) for f in gradle_files)
        
        # Also check for Maven pom.xml
        maven_pom = os.path.join(repo_path, "pom.xml")
        has_maven = os.path.exists(maven_pom)
        
        if not (has_gradle or has_maven):
            return {"tool": "kotlin_test", "status": "error", "error": "No Kotlin project found (missing Gradle or Maven build files)"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "kotlin_test", "status": "error", "error": "Target path is outside the repository"}
        
        # Build the test command - prefer Gradle if both are present
        if has_gradle:
            cmd = ["./gradlew", "test"]  # Using wrapper if available
            # Check if gradlew exists, otherwise use gradle
            gradlew_path = os.path.join(repo_path, "gradlew")
            if not os.path.exists(gradlew_path):
                cmd[0] = "gradle"
        else:  # Maven
            cmd = ["mvn", "test"]
            
        if target_path:
            # For Gradle/Maven, target_path could be used as a test filter or specific test class
            # We'll add it as an additional argument
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
            
            # Gradle/Maven test exit code: 0 = success, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"
            
            return {
                "tool": "kotlin_test",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "kotlin_test", "status": "error", "error": "Kotlin test execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "kotlin_test", "status": "error", "error": "An error occurred while running Kotlin tests"}

    def get_name(self) -> str:
        return "kotlin_test"
