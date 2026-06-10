"""
Dotnet Test.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Dotnet_test
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeTester-v1.0
"""

import subprocess
import os
from typing import Dict, Any, Optional
from src.modules.codetester.test_adapters.base import BaseQA

class DotNetTest(BaseQA):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        # Validate that repo_path exists and is a directory
        if not os.path.isdir(repo_path):
            return {"tool": "dotnet_test", "status": "error", "error": f"Repository path does not exist: {repo_path}"}
        
        # Check for .NET project signs: .csproj, .fsproj, .vcxproj, or solution files
        has_csproj = any(f.endswith(".csproj") for f in os.listdir(repo_path) if os.path.isfile(os.path.join(repo_path, f)))
        has_fsproj = any(f.endswith(".fsproj") for f in os.listdir(repo_path) if os.path.isfile(os.path.join(repo_path, f)))
        has_vcxproj = any(f.endswith(".vcxproj") for f in os.listdir(repo_path) if os.path.isfile(os.path.join(repo_path, f)))
        has_sln = any(f.endswith(".sln") for f in os.listdir(repo_path) if os.path.isfile(os.path.join(repo_path, f)))
        
        if not (has_csproj or has_fsproj or has_vcxproj or has_sln):
            return {"tool": "dotnet_test", "status": "error", "error": "No .NET project found (missing .csproj, .fsproj, .vcxproj, or .sln)"}
        
        # Prevent path traversal for target_path
        if target_path:
            # Normalize paths
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            # Check if target_path_abs starts with repo_path_abs
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "dotnet_test", "status": "error", "error": "Target path is outside the repository"}
        
        # Build the dotnet test command
        cmd = ["dotnet", "test"]
        if target_path:
            # dotnet test can take a project file or directory
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
            
            # dotnet test exit code: 0 = success, non-zero = failure
            status = "success" if result.returncode == 0 else "failed"
            
            return {
                "tool": "dotnet_test",
                "status": status,
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:]
            }
        except subprocess.TimeoutExpired:
            return {"tool": "dotnet_test", "status": "error", "error": "DotNet test execution timed out"}
        except Exception as e:
            # Avoid leaking internal error details in production
            return {"tool": "dotnet_test", "status": "error", "error": "An error occurred while running dotnet test"}

    def get_name(self) -> str:
        return "dotnet_test"
