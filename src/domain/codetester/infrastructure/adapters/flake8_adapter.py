import subprocess
import os
from typing import Dict, Any, Optional
from src.domain.codetester.infrastructure.adapters.base import BaseQAAdapter

class Flake8Adapter(BaseQAAdapter):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "flake8", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Using --format=default for easier parsing if needed, but for now we'll return stdout
        cmd = ["flake8", "--max-line-length=120"]
        if target_path:
            # Prevent path traversal: ensure target_path is within repo_path
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            if target_path:
                target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
                # Check if target_path_abs starts with repo_path_abs
                if not target_path_abs.startswith(repo_path_abs):
                    return {"tool": "flake8", "status": "error", "error": "Target path is outside the repository"}
            cmd.append(target_path)
        if extra_args:
            cmd.extend(extra_args.split())

        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Flake8 returns 0 if no errors, 1 if errors found
            return {
                "tool": "flake8",
                "status": "success" if result.returncode == 0 else "warning",
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:],
                "error_count": len(result.stdout.splitlines()) if result.returncode != 0 else 0
            }
        except subprocess.TimeoutExpired:
            return {"tool": "flake8", "status": "error", "error": "Flake8 execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "flake8", "status": "error", "error": "An error occurred while running flake8"}

    def get_name(self) -> str:
        return "flake8"
