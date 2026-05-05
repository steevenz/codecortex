import subprocess
from typing import Dict, Any, Optional
from src.domain.codetester.infrastructure.adapters.base import BaseQAAdapter

class Flake8Adapter(BaseQAAdapter):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Using --format=default for easier parsing if needed, but for now we'll return stdout
        cmd = ["flake8", "--max-line-length=120"]
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
        except Exception as e:
            return {"tool": "flake8", "status": "error", "error": str(e)}

    def get_name(self) -> str:
        return "flake8"
