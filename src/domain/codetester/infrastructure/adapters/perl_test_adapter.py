import subprocess
import os
from typing import Dict, Any, Optional
from src.domain.codetester.infrastructure.adapters.base import BaseQAAdapter

class PerlTestAdapter(BaseQAAdapter):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "perl_test", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Check for Perl project signs: Makefile.PL, Build.PL, or a t/ directory with tests
        # We'll also check for a META.json or META.yml (modern Perl distributions)
        build_pl = os.path.join(repo_path, "Build.PL")
        makefile_pl = os.path.join(repo_path, "Makefile.PL")
        meta_json = os.path.join(repo_path, "META.json")
        meta_yml = os.path.join(repo_path, "META.yml")
        test_dir = os.path.join(repo_path, "t")
        
        # If none of these exist, we might still have a single .pl file with tests, but we'll require at least one sign
        if not (os.path.exists(build_pl) or os.path.exists(makefile_pl) or os.path.exists(meta_json) or os.path.exists(meta_yml) or os.path.isdir(test_dir)):
            return {"tool": "perl_test", "status": "error", "error": "No Perl project found (missing Build.PL, Makefile.PL, META.json, META.yml, or t/ directory)"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "perl_test", "status": "error", "error": "Target path is outside the repository"}
        
        # Build the prove command
        # We'll use prove with verbose output and maybe other options
        cmd = ["prove", "-v"]  # verbose
        if target_path:
            # prove can take a list of files or directories to test
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
            
            # prove exit code: 0 = all tests passed, non-zero = some tests failed
            status = "success" if result.returncode == 0 else "failed"
            
            return {
                "tool": "perl_test",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "perl_test", "status": "error", "error": "Perl test execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "perl_test", "status": "error", "error": "An error occurred while running perl tests"}

    def get_name(self) -> str:
        return "perl_test"