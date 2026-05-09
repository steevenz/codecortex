import subprocess
import json
import tempfile
import os
from typing import Dict, Any, Optional
from src.domain.codetester.infrastructure.adapters.base import BaseQAAdapter

class PytestAdapter(BaseQAAdapter):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "pytest", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "pytest", "status": "error", "error": "Target path is outside the repository"}
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            report_path = tmp.name
         
        cmd = ["pytest", f"--json-report", f"--json-report-file={report_path}"]
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
                timeout=120 # Increased timeout for production
            )
             
            summary = {"tool": "pytest", "status": "success" if result.returncode in (0, 1) else "failed"}
             
            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                    summary["report"] = {
                        "total_tests": report_data.get("summary", {}).get("total", 0),
                        "passed": report_data.get("summary", {}).get("passed", 0),
                        "failed": report_data.get("summary", {}).get("failed", 0),
                        "skipped": report_data.get("summary", {}).get("skipped", 0),
                        "duration": report_data.get("duration", 0)
                    }
                os.remove(report_path)
             
            summary.update({
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:], # Cap output to avoid token overflow
                "stderr": result.stderr[-2000:]
            })
             
            return summary
        except subprocess.TimeoutExpired:
            if os.path.exists(report_path): os.remove(report_path)
            return {"tool": "pytest", "status": "error", "error": "Pytest execution timed out"}
        except Exception as e:
            if os.path.exists(report_path): os.remove(report_path)
            # Avoid leaking internal error details in production
            return {"tool": "pytest", "status": "error", "error": "An error occurred while running pytest"}
 
    def get_name(self) -> str:
        return "pytest"
