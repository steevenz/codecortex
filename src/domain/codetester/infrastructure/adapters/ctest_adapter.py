import subprocess
import os
from typing import Dict, Any, Optional
from src.domain.codetester.infrastructure.adapters.base import BaseQAAdapter

class CtestAdapter(BaseQAAdapter):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "ctest", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Check for CMake project (CMakeLists.txt)
        cmake_lists_path = os.path.join(repo_path, "CMakeLists.txt")
        if not os.path.exists(cmake_lists_path):
            return {"tool": "ctest", "status": "error", "error": "CMakeLists.txt not found - Ctest requires a CMake project"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "ctest", "status": "error", "error": "Target path is outside the repository"}
        
        # Build the ctest command
        cmd = ["ctest", "--output-on-failure"]
        if target_path:
            # ctest can take a test name or regex to run specific tests
            cmd.extend(["-R", target_path])
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
            
            # ctest exit code: 0 = success, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"
            
            return {
                "tool": "ctest",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "ctest", "status": "error", "error": "Ctest execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "ctest", "status": "error", "error": "An error occurred while running ctest"}

    def get_name(self) -> str:
        return "ctest"