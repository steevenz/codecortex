import subprocess
import os
from typing import Dict, Any, Optional
from src.domain.codetester.infrastructure.adapters.base import BaseQAAdapter

class PHPUnitAdapter(BaseQAAdapter):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "phpunit", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "phpunit", "status": "error", "error": "Target path is outside the repository"}
        
        # Check for phpunit.xml or phpunit.xml.dist to ensure we are in a PHPUnit project
        phpunit_xml = os.path.join(repo_path, "phpunit.xml")
        phpunit_xml_dist = os.path.join(repo_path, "phpunit.xml.dist")
        if not (os.path.exists(phpunit_xml) or os.path.exists(phpunit_xml_dist)):
            return {"tool": "phpunit", "status": "error", "error": "phpunit.xml or phpunit.xml.dist not found - PHPUnit requires a configuration file"}
        
        # Build the phpunit command
        cmd = ["phpunit"]
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
            
            # PHPUnit exit code: 0 = success, 1 = failures, 2 = errors, 3 = incomplete, 4 = skipped, 5 = risk, 6 = failure
            # We consider 0 and 1 as success (failures are still a successful run, just with failing tests)
            # But note: in the context of QA, we might want to know if tests passed or failed.
            # We'll set status to "success" if the run completed (exit code 0-5) and "error" for other exit codes (like 255 for command not found)
            # However, for consistency with other adapters, we'll consider:
            #   exit code 0: success
            #   exit code 1: warning (tests failed)
            #   exit code 2+: error (unless we know it's a specific PHPUnit code)
            # But let's keep it simple: 0 = success, non-zero = failed (but we'll capture the exit code)
            # We'll follow the pattern of flake8: 0 = success, non-zero = warning (for flake8, 1 means warnings/errors found)
            # For PHPUnit, 0 = success, 1 = tests failed, 2 = errors (like missing file), etc.
            # We'll map:
            #   0 -> success
            #   1 -> warning (tests failed)
            #   2+ -> error (unexpected error)
            if result.returncode == 0:
                status = "success"
            elif result.returncode == 1:
                status = "warning"
            else:
                status = "error"
            
            return {
                "tool": "phpunit",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "phpunit", "status": "error", "error": "PHPUnit execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "phpunit", "status": "error", "error": "An error occurred while running PHPUnit"}

    def get_name(self) -> str:
        return "phpunit"