import subprocess
import os
from typing import Dict, Any, Optional
from src.domain.codetester.infrastructure.adapters.base import BaseQAAdapter

class UnittestAdapter(BaseQAAdapter):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "unittest", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "unittest", "status": "error", "error": "Target path is outside the repository"}
        
        # We'll use the unittest module discovery with verbose output
        # unittest doesn't natively output JSON. We'll capture the output and consider a run successful if exit code is 0.
        # We'll run: python -m unittest discover -v [target_path] [extra_args]
        # But note: target_path might be a specific test file or directory.
        # We'll adjust the command accordingly.

        cmd = ["python", "-m", "unittest", "discover", "-v"]
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

            # unittest returns 0 if all tests pass, 1 if any test fails or errors.
            return {
                "tool": "unittest",
                "status": "success" if result.returncode == 0 else "failed",
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],  # Cap output
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "unittest", "status": "error", "error": "Unittest execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "unittest", "status": "error", "error": "An error occurred while running unittest"}

    def get_name(self) -> str:
        return "unittest"