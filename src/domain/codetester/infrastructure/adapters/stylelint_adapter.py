import subprocess
import os
from typing import Dict, Any, Optional
from src.domain.codetester.infrastructure.adapters.base import BaseQAAdapter

class StylelintAdapter(BaseQAAdapter):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "stylelint", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Check for stylelint configuration: .stylelintrc, .stylelintrc.js, stylelint.config.js, etc.
        # Or check for stylelint in package.json devDependencies
        stylelint_config_files = [
            ".stylelintrc",
            ".stylelintrc.json",
            ".stylelintrc.yaml",
            ".stylelintrc.yml",
            ".stylelintrc.js",
            "stylelint.config.js",
            "stylelint.config.json"
        ]
        
        has_config = any(os.path.exists(os.path.join(repo_path, f)) for f in stylelint_config_files)
        
        # Also check package.json for stylelint dependency
        package_json_path = os.path.join(repo_path, "package.json")
        has_stylelint_in_package = False
        if os.path.exists(package_json_path):
            try:
                import json
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)
                dev_deps = package_data.get("devDependencies", {})
                deps = package_data.get("dependencies", {})
                all_deps = {**dev_deps, **deps}
                if "stylelint" in all_deps:
                    has_stylelint_in_package = True
            except Exception:
                pass  # If we can't parse package.json, we'll rely on config files
        
        if not (has_config or has_stylelint_in_package):
            return {"tool": "stylelint", "status": "error", "error": "Stylelint not found (missing config file or not in package.json dependencies)"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "stylelint", "status": "error", "error": "Target path is outside the repository"}
        
        # Build the stylelint command
        cmd = ["npx", "stylelint"]
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
            
            # stylelint exit code: 0 = no warnings, 1 = warnings present, >1 = error
            if result.returncode == 0:
                status = "success"
            elif result.returncode == 1:
                status = "warning"  # CSS issues found but stylelint ran successfully
            else:
                status = "error"
            
            return {
                "tool": "stylelint",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "stylelint", "status": "error", "error": "Stylelint execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "stylelint", "status": "error", "error": "An error occurred while running stylelint"}

    def get_name(self) -> str:
        return "stylelint"