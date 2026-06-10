#!/usr/bin/env python
"""
Filesystem Security Audit Script.

Audits directory structure, permissions, and security compliance.
"""

import os
import stat
import json
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).parent.parent.parent

DIRECTORIES_TO_CHECK = [
    'src/modules/filesystem',
    'src/modules/codeindex',
    'src/modules/codegraph',
    'database',
    'logs',
    'outputs',
    '.config',
    'scripts',
]

SENSITIVE_EXTENSIONS = {'.env', '.key', '.pem', '.p12', '.pfx', '.crt', '.sql'}
SENSITIVE_FILES = {'passwords.txt', 'secrets.txt', 'credentials.json'}


def get_permissions(mode: int) -> str:
    """Convert mode to rwx string."""
    return stat.filemode(mode)


def audit_filesystem() -> Dict[str, Any]:
    """Run filesystem security audit."""
    results = {
        "directories": {},
        "sensitive_files_found": [],
        "issues": [],
        "summary": {}
    }
    
    for dir_path in DIRECTORIES_TO_CHECK:
        p = PROJECT_ROOT / dir_path
        if p.exists():
            results["directories"][dir_path] = {
                "exists": True,
                "files": [],
                "subdirs": []
            }
            
            for item in p.iterdir():
                if item.is_file():
                    mode = item.stat().st_mode
                    perms = get_permissions(mode)
                    results["directories"][dir_path]["files"].append({
                        "name": item.name,
                        "permissions": perms,
                        "size": item.stat().st_size
                    })
                    
                    if item.suffix in SENSITIVE_EXTENSIONS or item.name in SENSITIVE_FILES:
                        results["sensitive_files_found"].append(str(item.relative_to(PROJECT_ROOT)))
                        results["issues"].append(f"Sensitive file found: {item}")
                        
                elif item.is_dir():
                    results["directories"][dir_path]["subdirs"].append(item.name)
        else:
            results["directories"][dir_path] = {"exists": False}
            results["issues"].append(f"Directory missing: {dir_path}")
    
    results["summary"] = {
        "total_dirs_checked": len(DIRECTORIES_TO_CHECK),
        "dirs_exist": sum(1 for d in results["directories"].values() if d.get("exists")),
        "sensitive_files": len(results["sensitive_files_found"]),
        "issues_count": len(results["issues"])
    }
    
    return results


def main():
    print("Filesystem Security Audit")
    print("=" * 60)
    
    results = audit_filesystem()
    
    print(f"\nDirectories Checked: {results['summary']['dirs_exist']}/{results['summary']['total_dirs_checked']}")
    print(f"Sensitive Files Found: {results['summary']['sensitive_files']}")
    print(f"Issues: {results['summary']['issues_count']}")
    
    if results["issues"]:
        print("\nIssues:")
        for issue in results["issues"]:
            print(f"  - {issue}")
    
    output_dir = PROJECT_ROOT / "outputs" / "validation" / "2026-06-01"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "filesystem_audit.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nAudit saved to: {output_dir / 'filesystem_audit.json'}")
    
    return 0 if results['summary']['issues_count'] == 0 else 1


if __name__ == "__main__":
    exit(main())