"""
Audit.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Audit
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-Filesystem-v1.0
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from pathlib import Path
import os
import fnmatch
import stat as stat_module

from src.core import ApiError

from src.core.utils.path import norm_path as _norm


SENSITIVE_PATTERNS: List[Dict[str, Any]] = [
    {"patterns": [".env", ".env.*", "*.env"], "category": "credentials", "severity": "critical",
     "reason": ".env files typically contain secret keys and credentials.",
     "recommendation": "Remove from repository, add to .gitignore, rotate any exposed secrets."},
    {"patterns": ["*.key", "*.pem", "*.p12", "*.pfx", "*.cer", "*.crt", "id_rsa", "id_dsa", "*.asc"],
     "category": "credentials", "severity": "critical",
     "reason": "Private key or certificate file.",
     "recommendation": "Use a secrets manager. Do not store keys in repositories."},
    {"patterns": ["secrets.yml", "secrets.yaml", "credentials.json", "credentials.yml",
                   "config/credentials*", "config/secrets*", "*.password*", "passwd*"],
     "category": "credentials", "severity": "critical",
     "reason": "Credentials or secret configuration file.",
     "recommendation": "Move to a vault or environment variables."},
    {"patterns": ["*.log", "*.logs"], "category": "logs", "severity": "low",
     "reason": "Log file — check for large sizes.",
     "recommendation": "Add to .gitignore, use log rotation."},
    {"patterns": ["*.bak", "*.backup", "*.old", "*.orig", "*.tmp", "*.swp", "*.swo", "*~", "*.dpkg"],
     "category": "backup", "severity": "medium",
     "reason": "Backup or temporary file that should not be versioned.",
     "recommendation": "Delete and add pattern to .gitignore."},
    {"patterns": ["config.json", "application.properties", "application.yml", "application.yaml",
                   "database.yml", "database.yaml", "*.cfg", "config/**.json"],
     "category": "config", "severity": "high",
     "reason": "Configuration file that may contain passwords or tokens.",
     "recommendation": "Use environment variables or a vault for sensitive values."},
    {"patterns": ["dump*.sql", "*.dump", "*.sqlite", "*.db"],
     "category": "database", "severity": "high",
     "reason": "Database dump or database file — may contain sensitive data.",
     "recommendation": "Remove from repository. Never commit databases."},
    {"patterns": [".git/config", ".git/credentials", ".git-credentials"],
     "category": "vcs_hidden", "severity": "high",
     "reason": "Git configuration that may contain credentials.",
     "recommendation": "Use git config --global or a credential helper."},
    {"patterns": [".svn/entries", ".svn/auth"],
     "category": "vcs_hidden", "severity": "high",
     "reason": "Internal SVN files that may contain sensitive metadata.",
     "recommendation": "Do not commit .svn directories."},
    {"patterns": ["token*", "*token*", "*secret*", "*credential*", "*auth*"],
     "category": "suspicious_name", "severity": "medium",
     "reason": "Suspicious file name indicating tokens or credentials.",
     "recommendation": "Verify whether this file needs to be version-controlled."},
    {"patterns": ["*.exe", "*.dll", "*.bin", "*.msi", "*.dmg", "*.deb", "*.rpm"],
     "category": "binary", "severity": "medium",
     "reason": "Binary executable — generally should not be version-controlled.",
     "recommendation": "Use a package manager. Remove from repository."},
    {"patterns": ["*.pyc", "__pycache__/", "*.pyo", "*.class", "*.o", "*.obj", "*.so", "*.dylib"],
     "category": "build_artifact", "severity": "low",
     "reason": "Build artifact or compilation cache.",
     "recommendation": "Ensure these are in .gitignore."},
    {"patterns": ["node_modules/", "vendor/", "*.js.map"],
     "category": "dependency", "severity": "low",
     "reason": "Dependency folder — large and should not be versioned.",
     "recommendation": "Ensure .gitignore covers this. Use lock files instead."},
]

WORLD_WRITABLE = stat_module.S_IWOTH
EXECUTABLE = stat_module.S_IXUSR | stat_module.S_IXGRP | stat_module.S_IXOTH


class DiskAudit:
    """Filesystem security auditor — detects sensitive files, permissions issues, hidden VCS."""

    @classmethod
    def audit(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        target = params.get("target", "")
        recursive = params.get("recursive", True)
        severity_filter = params.get("severity", ["critical", "high", "medium", "low"])
        check_permissions = params.get("check_permissions", True)
        check_hidden = params.get("check_hidden", True)
        max_file_size_mb = params.get("max_file_size_mb", 100)
        exclude_patterns = params.get("exclude_patterns") or [".git", ".svn", "node_modules"]
        limit = min(params.get("limit", 200), 5000)

        target_path = Path(target).resolve()
        if not target_path.exists():
            raise ApiError(f"Target path does not exist: {target}", status_code=404, error_code="FS_008")

        max_bytes = max_file_size_mb * 1024 * 1024
        findings: List[Dict[str, Any]] = []

        def _should_exclude(rel: str) -> bool:
            for pat in exclude_patterns:
                p = pat.replace("\\", "/")
                if fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(rel, p + "/*"):
                    return True
                parts = rel.split("/")
                for part in parts:
                    if fnmatch.fnmatch(part, p):
                        return True
            return False

        def _walk(path: Path):
            try:
                for entry in path.iterdir():
                    if not check_hidden and entry.name.startswith("."):
                        continue
                    rel = _norm(str(entry.relative_to(target_path)))
                    if _should_exclude(rel):
                        continue
                    if entry.is_dir():
                        if recursive:
                            _walk(entry)
                    elif entry.is_file():
                        _inspect_file(entry, rel)
            except PermissionError:
                pass

        def _inspect_file(fpath: Path, rel: str):
            if len(findings) >= limit:
                return
            try:
                fstat = fpath.stat()
                if fstat.st_size > max_bytes:
                    return
            except OSError:
                return

            # Check patterns
            low = fpath.name.lower()
            for rule in SENSITIVE_PATTERNS:
                if len(findings) >= limit:
                    break
                if rule["severity"] not in severity_filter:
                    continue
                for pat in rule["patterns"]:
                    if fnmatch.fnmatch(low, pat.lower()) or fnmatch.fnmatch(rel, pat):
                        finding = {
                            "severity": rule["severity"],
                            "category": rule["category"],
                            "path": rel,
                            "reason": rule["reason"],
                            "recommendation": rule["recommendation"],
                        }
                        try:
                            mode = fstat.st_mode
                            finding["permissions"] = oct(mode)[-3:]
                        except OSError:
                            pass
                        findings.append(finding)
                        break
                if findings and findings[-1].get("path") == rel:
                    break

            # Check permissions
            if check_permissions and len(findings) < limit:
                try:
                    mode = fstat.st_mode
                    if mode & WORLD_WRITABLE:
                        findings.append({
                            "severity": "high",
                            "category": "permissions",
                            "path": rel,
                            "permissions": oct(mode)[-3:],
                            "reason": "World-writable file — anyone can modify.",
                            "recommendation": "Restrict permissions with chmod 644 or 755.",
                        })
                    elif mode & EXECUTABLE and not fpath.suffix:
                        findings.append({
                            "severity": "low",
                            "category": "permissions",
                            "path": rel,
                            "permissions": oct(mode)[-3:],
                            "reason": "Executable permission without extension — possibly accidental.",
                            "recommendation": "Remove executable bit if this is not a script.",
                        })
                except OSError:
                    pass

        _walk(target_path)

        summary: Dict[str, int] = {}
        for f in findings:
            sev = f.get("severity", "unknown")
            summary[sev] = summary.get(sev, 0) + 1

        return {
            "status_code": 200,
            "message": f"Audit complete: {len(findings)} findings",
            "data": {
                "target": _norm(str(target_path)),
                "summary": summary,
                "findings": findings[:limit],
            },
        }
