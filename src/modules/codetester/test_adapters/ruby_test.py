"""
Ruby Test.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Ruby_test
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeTester-v1.0
"""

import subprocess
import os
from typing import Dict, Any, Optional
from src.modules.codetester.test_adapters.base import BaseQA

class RubyTest(BaseQA):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "ruby_test", "status": "error", "error": f"Repository path does not exist: {repo_path}"}

        # Check for signs of a Ruby project (Gemfile or .ruby-version or .rbenv-version)
        gemfile_path = os.path.join(repo_path, "Gemfile")
        ruby_version_path = os.path.join(repo_path, ".ruby-version")
        rbenv_version_path = os.path.join(repo_path, ".rbenv-version")

        if not (os.path.exists(gemfile_path) or os.path.exists(ruby_version_path) or os.path.exists(rbenv_version_path)):
            return {"tool": "ruby_test", "status": "error", "error": "No Ruby project found (missing Gemfile, .ruby-version, or .rbenv-version)"}

        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "ruby_test", "status": "error", "error": "Target path is outside the repository"}

        # Build the ruby test command
        # Try to use bundler if Gemfile exists, otherwise use ruby directly
        if os.path.exists(gemfile_path):
            cmd = ["bundle", "exec", "rake", "test"]
        else:
            # Fallback to ruby - we'll look for test files
            cmd = ["ruby", "-e", "Dir['test/**/*_test.rb'].each { |f| require f }"]

        if target_path:
            # If using bundle/rake, target_path could be a specific test file
            if os.path.exists(gemfile_path):
                cmd = ["bundle", "exec", "ruby", "-Itest", target_path]
            else:
                cmd = ["ruby", "-Itest", target_path]
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

            # ruby test exit code: 0 = success, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"

            return {
                "tool": "ruby_test",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "ruby_test", "status": "error", "error": "Ruby test execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "ruby_test", "status": "error", "error": "An error occurred while running ruby tests"}

    def get_name(self) -> str:
        return "ruby_test"
