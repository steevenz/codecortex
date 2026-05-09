import subprocess
import os
from typing import Dict, Any, Optional
from src.domain.codetester.infrastructure.adapters.base import BaseQAAdapter

class SbtTestAdapter(BaseQAAdapter):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "sbt_test", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Check for build.sbt to ensure we are in an sbt project
        build_sbt_path = os.path.join(repo_path, "build.sbt")
        if not os.path.exists(build_sbt_path):
            # Also check for project/Build.scala
            project_dir = os.path.join(repo_path, "project")
            build_scala_path = os.path.join(project_dir, "Build.scala") if os.path.exists(project_dir) else None
            if not (os.path.exists(build_sbt_path) or (build_scala_path and os.path.exists(build_scala_path))):
                return {"tool": "sbt_test", "status": "error", "error": "build.sbt or project/Build.scala not found - Scala test requires an sbt project"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "sbt_test", "status": "error", "error": "Target path is outside the repository"}
        
        # Build the sbt test command
        cmd = ["sbt", "test"]
        if target_path:
            # sbt allows specifying a test to run
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
            
            # sbt test exit code: 0 = success, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"
            
            return {
                "tool": "sbt_test",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "sbt_test", "status": "error", "error": "sbt test execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "sbt_test", "status": "error", "error": "An error occurred while running sbt test"}

    def get_name(self) -> str:
        return "sbt_test"