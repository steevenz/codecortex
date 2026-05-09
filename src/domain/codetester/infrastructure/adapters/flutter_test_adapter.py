import subprocess
import os
from typing import Dict, Any, Optional
from src.domain.codetester.infrastructure.adapters.base import BaseQAAdapter

class FlutterTestAdapter(BaseQAAdapter):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "flutter_test", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Check for Flutter project signs: pubspec.yaml and presence of lib/ or test/
        pubspec_path = os.path.join(repo_path, "pubspec.yaml")
        if not os.path.exists(pubspec_path):
            return {"tool": "flutter_test", "status": "error", "error": "pubspec.yaml not found - Flutter test requires a Flutter project"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "flutter_test", "status": "error", "error": "Target path is outside the repository"}
        
        # Build the flutter test command
        cmd = ["flutter", "test"]
        if target_path:
            # flutter test can take a test file or directory to run
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
            
            # flutter test exit code: 0 = success, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"
            
            return {
                "tool": "flutter_test",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "flutter_test", "status": "error", "error": "Flutter test execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "flutter_test", "status": "error", "error": "An error occurred while running flutter test"}

    def get_name(self) -> str:
        return "flutter_test"