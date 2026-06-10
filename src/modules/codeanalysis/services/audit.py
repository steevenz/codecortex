"""
Class Audit – ~/.aicoders/ compliance gate with security scan + coding standards + architecture audit.

:project: CodeCortex
:package: Modules.Codeanalysis.Services.Audit
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeAnalysis-v1.0
"""

from __future__ import annotations

import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Set, Tuple
from src.core.database import DatabaseManager
from src.core.logging import get_logger
from src.modules.filesystem.core.service import Filesystem
from src.modules.codeanalysis.core.dtos import (
    AuditRequest, AuditResult, AuditFinding,
)

logger = get_logger("CodeCortex.CodeAnalysis.AuditService")

SEVERITY_LEVELS = {"low": 0, "medium": 1, "high": 2, "critical": 3}

DEFAULT_EXCLUDE_PATTERNS: Set[str] = {
    "node_modules", "dist", "build", "target", ".git", ".svn",
    "*.min.js", "*.min.css", "*.pyc", "__pycache__", 
    "tests/fixtures", "test/fixtures", "mock", "stub", "fake",
    ".venv", "venv",
}

class Audit:
    """
    ~/.aicoders/ compliance gate — security scan + coding standards + architecture audit.
    DI: all dependencies injected via constructor.
    """

    def __init__(self, db: DatabaseManager, fs_service: Filesystem):
        self._db = db
        self._fs = fs_service

    def audit(self, request: AuditRequest) -> AuditResult:
        target = Path(request.target).resolve()
        if not target.exists():
            raise FileNotFoundError(f"Target does not exist: {request.target}")

        categories = request.scan_categories or [
            "secrets", "pii", "misconfig", "vulns", "comments",
            "naming", "type_hints", "file_structure", "class_docblock",
            "modular", "modular_structure", "architecture",
            "error_handling", "di_compliance", "docblock",
            "logging", "api_response",
            "semver", "pwa", "crossplatform",
            "test_debug", "codification", "coding_naming", "syntax",
        ]
        min_sev = SEVERITY_LEVELS.get(request.severity_threshold, 1)
        max_bytes = request.max_file_size_kb * 1024
        aiignore = self._load_aiignore(target)

        # Parse incremental scan timestamp
        since_timestamp = self._parse_since(request.since)
        if since_timestamp:
            logger.info(f"Incremental scan: only files modified since {since_timestamp.isoformat()}")

        findings: List[AuditFinding] = []
        errors: List[Dict[str, str]] = []
        scanned_files = 0
        all_dirs: Set[Path] = set()
        all_files: List[Path] = []

        for fp in self._walk_files(target, request.files, aiignore, since_timestamp):
            all_files.append(fp)
            all_dirs.add(fp.parent)
            if target.is_dir():
                all_dirs.add(target)
            if not self._is_text_file(fp):
                continue
            try:
                content = fp.read_text(encoding="utf-8", errors="replace")
                if len(content) > max_bytes:
                    content = content[:max_bytes]
            except Exception as e:
                errors.append({"file": str(fp), "error": f"Failed to read: {e}"})
                continue

            scanned_files += 1
            lines = content.splitlines()
            cat_map = {
                "secrets": self._find_secrets,
                "pii": self._find_pii,
                "misconfig": self._find_misconfig,
                "vulns": self._find_vulns,
                "naming": self._check_naming_convention,
                "type_hints": self._check_type_hints,
                "file_structure": self._check_file_structure,
                "modular": self._check_modular,
                "error_handling": self._check_error_handling,
                "di_compliance": self._check_di_compliance,
                "docblock": self._check_docblock,
                "class_docblock": self._check_class_docblock,
                "logging": self._check_logging,
                "api_response": self._check_api_response,
                "semver": self._check_semver_compliance,
                "pwa": self._check_pwa_compliance,
                "crossplatform": self._check_crossplatform_compliance,
                "test_debug": self._check_test_debug,
                "codification": self._check_codification,
                "coding_naming": self._check_coding_naming,
                "architecture": self._check_architecture,
                "syntax": self._check_syntax,
            }

            for cat in categories:
                checker = cat_map.get(cat)
                if checker is None:
                    continue
                try:
                    for finding in checker(content, str(fp), lines):
                        if SEVERITY_LEVELS.get(finding.severity, 0) >= min_sev:
                            finding.category = finding.category or cat
                            findings.append(finding)
                except Exception as e:
                    errors.append({"file": str(fp), "category": cat, "error": str(e)})

        if "comments" in categories:
            cat_findings = self._find_comment_tags(content if target.is_file() else "", str(target))
            for f in cat_findings:
                if SEVERITY_LEVELS.get(f.severity, 0) >= min_sev:
                    f.category = "comments"
                    findings.append(f)

        if "modular_structure" in categories and target.is_dir():
            for finding in self._check_modular_structure(target, all_dirs, all_files):
                if SEVERITY_LEVELS.get(finding.severity, 0) >= min_sev:
                    findings.append(finding)

        if "semver" in categories and target.is_dir():
            for finding in self._check_semver_project(target, all_files):
                if SEVERITY_LEVELS.get(finding.severity, 0) >= min_sev:
                    findings.append(finding)

        if "pwa" in categories and target.is_dir():
            for finding in self._check_pwa_project(target, all_files):
                if SEVERITY_LEVELS.get(finding.severity, 0) >= min_sev:
                    findings.append(finding)

        if "test_debug" in categories and target.is_dir():
            for finding in self._check_test_debug_project(target, all_files):
                if SEVERITY_LEVELS.get(finding.severity, 0) >= min_sev:
                    findings.append(finding)

        summary = self._build_summary(findings)
        score = self._calc_compliance_score(summary, findings)
        recommendations = self._build_recommendations(findings)

        # Generate auto-fix suggestions (10/10 AI coder impact feature)
        if request.enable_auto_fix:
            findings = self._generate_auto_fixes(findings)

        # Apply auto-fixes if requested (DANGEROUS - requires dry_run=False)
        if request.apply_auto_fix and not request.dry_run:
            applied_count = self._apply_auto_fixes(findings)
            logger.info(f"Applied {applied_count} auto-fixes")

        return AuditResult(
            target=str(target),
            scan_categories=categories,
            scanned_files=scanned_files,
            summary=summary,
            compliance_score=score,
            findings=findings,
            recommendations=recommendations,
            errors=errors,
        )

    # ═══════════════════════════════════════════════════════════════
    # FILE WALKING
    # ═══════════════════════════════════════════════════════════════

    def _load_aiignore(self, target: Path) -> Set[str]:
        patterns = set(DEFAULT_EXCLUDE_PATTERNS)
        parent = target.parent if target.is_file() else target
        aiignore = parent / ".aiignore"
        if aiignore.exists():
            for line in aiignore.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.add(line)
        return patterns

    def _parse_since(self, since: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 timestamp for incremental scan."""
        if not since:
            return None
        try:
            # Handle various ISO 8601 formats
            since = since.replace('Z', '+00:00')
            return datetime.fromisoformat(since)
        except ValueError:
            logger.warning(f"Invalid since timestamp format: {since}")
            return None

    def _is_file_modified_after(self, fp: Path, since: datetime) -> bool:
        """Check if file was modified after the given timestamp."""
        try:
            mtime = datetime.fromtimestamp(fp.stat().st_mtime)
            return mtime >= since
        except Exception:
            return True  # Include file if we can't determine modification time

    def _walk_files(self, target: Path, files: Optional[List[str]], exclude: Set[str], since: Optional[datetime] = None) -> List[Path]:
        if files:
            result = []
            for f in files:
                fp = Path(f)
                if fp.exists() and fp.is_file():
                    if since is None or self._is_file_modified_after(fp, since):
                        result.append(fp)
            return result
        if target.is_file():
            if since is None or self._is_file_modified_after(target, since):
                return [target]
            return []
        result = []
        for fp in target.rglob("*"):
            if fp.is_file() and not self._should_exclude(fp, exclude):
                if since is None or self._is_file_modified_after(fp, since):
                    result.append(fp)
        return result

    def _should_exclude(self, fp: Path, patterns: Set[str]) -> bool:
        import fnmatch
        fp_str = str(fp).replace("\\", "/")
        fp_lower = fp_str.lower()
        name_lower = fp.name.lower()
        for p in patterns:
            p_lower = p.lower()
            if fnmatch.fnmatch(fp_lower, p_lower) or fnmatch.fnmatch(name_lower, p_lower):
                return True
            if "/" in fp_str:
                parts = fp_str.split("/")
                for i in range(len(parts)):
                    partial = "/".join(parts[i:])
                    if fnmatch.fnmatch(partial, p_lower) or fnmatch.fnmatch(parts[i], p_lower):
                        return True
        return False

    def _is_text_file(self, fp: Path) -> bool:
        text_exts = {
            ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb",
            ".php", ".swift", ".kt", ".cs", ".cpp", ".c", ".h", ".hpp",
            ".sh", ".bash", ".yml", ".yaml", ".json", ".xml", ".toml",
            ".ini", ".cfg", ".env", ".md", ".html", ".css", ".scss", ".sql",
        }
        if fp.suffix.lower() in text_exts:
            return True
        try:
            head = fp.read_bytes()[:1024]
            return b"\x00" not in head
        except Exception:
            return False

    # ═══════════════════════════════════════════════════════════════
    # STANDARD COMPLIANCE CHECKERS
    # ═══════════════════════════════════════════════════════════════

    def _find_secrets(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        patterns = [
            ("aws_access_key", r"AKIA[0-9A-Z]{16}", "critical", "CA_SEC_001"),
            ("github_token", r"ghp_[A-Za-z0-9]{36}", "critical", "CA_SEC_002"),
            ("private_key", r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "critical", "CA_SEC_003"),
        ]
        for name, regex, severity, code in patterns:
            for m in re.finditer(regex, content):
                line_num = content[:m.start()].count("\n") + 1
                findings.append(AuditFinding(
                    category="secrets", severity=severity, file=file_path,
                    line=line_num, code=code,
                    message=f"Hardcoded {name} detected",
                    details={"match": m.group()[:20] + "..."},
                    remediation=f"Rotate immediately. Use environment variable or secret manager.",
                    confidence=0.95,
                ))
        # Variable name based detection
        var_pattern = r"(?P<var>(?:password|passwd|secret|api_key|apikey|token|credential|private_key|access_key)\s*[=:])\s*['\"](?P<val>[^'\"]{8,})['\"]"
        for m in re.finditer(var_pattern, content, re.IGNORECASE):
            line_num = content[:m.start()].count("\n") + 1
            findings.append(AuditFinding(
                category="secrets", severity="high", file=file_path,
                line=line_num, code="CA_SEC_004",
                message=f"High-risk variable '{m.group('var').strip()}' with inline value",
                remediation="Use environment variable or secret manager",
                confidence=0.85,
            ))
        return findings

    def _find_pii(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        patterns = [
            ("email", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "medium", "CA_PII_001"),
            ("ssn", r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b", "high", "CA_PII_002"),
            ("credit_card", r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "critical", "CA_PII_003"),
        ]
        for name, regex, severity, code in patterns:
            for m in re.finditer(regex, content):
                line_num = content[:m.start()].count("\n") + 1
                findings.append(AuditFinding(
                    category="pii", severity=severity, file=file_path,
                    line=line_num, code=code,
                    message=f"Potential {name} detected",
                    details={"match": m.group()[:20] + "..."},
                    confidence=0.8,
                ))
        return findings

    def _find_misconfig(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        if re.search(r"(?i)(debug\s*[=:]\s*true|DEBUG\s*=\s*True)", content):
            findings.append(AuditFinding(
                category="misconfig", severity="medium", file=file_path,
                line=1, code="CA_MIS_001",
                message="Debug mode enabled in production code",
                remediation="Set DEBUG=False in production",
                confidence=0.9,
            ))
        if re.search(r"(?i)cors.*['\"]\*['\"]", content):
            findings.append(AuditFinding(
                category="misconfig", severity="high", file=file_path,
                line=1, code="CA_MIS_002",
                message="Wildcard CORS origin (*)",
                remediation="Restrict to specific origins",
                confidence=0.85,
            ))
        return findings

    def _find_vulns(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        patterns = [
            ("sql_injection", r"(?i)(execute|query)\s*\(\s*['\"].*\{.*\}.*['\"]", "critical", "CA_VUL_001"),
            ("eval_usage", r"(?i)\beval\s*\(", "high", "CA_VUL_002"),
            ("pickle_load", r"(?i)pickle\.(load|loads)\s*\(", "high", "CA_VUL_003"),
            ("yaml_load_unsafe", r"(?i)yaml\.load\s*\([^)]*(?!SafeLoader)", "medium", "CA_VUL_004"),
        ]
        for name, regex, severity, code in patterns:
            for m in re.finditer(regex, content):
                line_num = content[:m.start()].count("\n") + 1
                findings.append(AuditFinding(
                    category="vulns", severity=severity, file=file_path,
                    line=line_num, code=code,
                    message=f"Potential {name}: {m.group()[:60]}",
                    details={"match": m.group()[:80]},
                    remediation=f"Sanitize inputs, avoid {name}",
                    confidence=0.85,
                ))
        return findings

    def _check_naming_convention(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        # Class naming: should be PascalCase
        for i, line in enumerate(lines, 1):
            m = re.search(r"^\s*class\s+(\w+)", line)
            if m:
                name = m.group(1)
                if not re.match(r"^[A-Z]", name) and not name[0].isupper():
                    findings.append(AuditFinding(
                        category="naming", severity="medium", file=file_path,
                        line=i, code="CA_NAM_001",
                        message=f"Class '{name}' should be PascalCase",
                        details={"class_name": name},
                        remediation=f"Rename to {name[0].upper() + name[1:]}",
                        standard_ref="coding-standard.md §3",
                        confidence=0.9,
                    ))
            # Function naming: should be snake_case for Python
            m2 = re.search(r"^\s*def\s+(\w+)", line)
            if m2:
                name = m2.group(1)
                if re.search(r"[A-Z]", name) and not name.startswith("_"):
                    findings.append(AuditFinding(
                        category="naming", severity="low", file=file_path,
                        line=i, code="CA_NAM_002",
                        message=f"Function '{name}' should be snake_case",
                        details={"function_name": name},
                        remediation=f"Rename to {re.sub(r'([A-Z])', r'_\1', name).lower().lstrip('_')}",
                        standard_ref="coding-standard.md §4",
                        confidence=0.85,
                    ))
        return findings

    def _check_type_hints(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        for i, line in enumerate(lines, 1):
            # Public method without type hints
            m = re.search(r"^\s*def\s+(\w+)\s*\(([^)]*)\)\s*:", line)
            if m and not m.group(1).startswith("_"):
                params = m.group(2)
                args = [a.strip() for a in params.split(",") if a.strip() and "self" not in a.split(":")[0]]
                for arg in args:
                    if ":" not in arg:
                        findings.append(AuditFinding(
                            category="type_hints", severity="medium", file=file_path,
                            line=i, code="CA_TYP_001",
                            message=f"Parameter '{arg.split()[0]}' missing type hint in '{m.group(1)}'",
                            details={"function": m.group(1), "param": arg.split()[0]},
                            remediation=f"Add type hint: {arg.split()[0]}: <type>",
                            standard_ref="coding-standard.md",
                            confidence=0.8,
                        ))
                    break  # one per line
        return findings

    def _check_class_docblock(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        for i, line in enumerate(lines, 1):
            m = re.search(r"^\s*class\s+(\w+)", line)
            if not m:
                continue
            class_name = m.group(1)
            doc_block = self._extract_preceding_docblock(lines, i - 2)
            if doc_block is None:
                findings.append(AuditFinding(
                    category="docblock", severity="medium", file=file_path,
                    line=i, code="CA_DOC_010",
                    message=f"Class '{class_name}' missing DocBlock",
                    details={"class": class_name},
                    remediation=f"Add DocBlock with @package, description, and @method/@property tags",
                    standard_ref="coding-standard.md §1 (Class DocBlock)",
                    confidence=0.9,
                ))
                continue

            tags = ["@package", "@author"]
            for tag in tags:
                if tag not in doc_block:
                    findings.append(AuditFinding(
                        category="docblock", severity="low", file=file_path,
                        line=i, code="CA_DOC_011" if tag == "@package" else "CA_DOC_012",
                        message=f"Class '{class_name}' missing {tag} in DocBlock",
                        details={"class": class_name, "missing": tag},
                        remediation=f"Add '{tag}' to class DocBlock",
                        standard_ref="coding-standard.md §1",
                        confidence=0.85,
                    ))

            has_desc = bool(re.sub(r'^\s*\*\s*|^\s*#\s*|^\s*"""\s*', '', doc_block.strip()))
            has_desc = has_desc and not doc_block.strip().startswith(("@", "*/", '"""'))
            if not has_desc:
                findings.append(AuditFinding(
                    category="docblock", severity="low", file=file_path,
                    line=i, code="CA_DOC_013",
                    message=f"Class '{class_name}' DocBlock missing class description",
                    details={"class": class_name},
                    remediation="Add single-responsibility description for the class",
                    standard_ref="coding-standard.md §1",
                    confidence=0.85,
                ))
        return findings

    def _check_file_structure(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        if not lines:
            return findings

        has_header = any(l.strip().startswith(("# ", "/*", '"""', "/**")) for l in lines[:5])
        if not has_header:
            findings.append(AuditFinding(
                category="file_structure", severity="low", file=file_path,
                line=1, code="CA_STR_001",
                message="File missing file header/DocBlock",
                remediation="Add project header with @project, @package, @author, @copyright",
                standard_ref="coding-standard.md §1",
                confidence=0.95,
            ))
            return findings

        header = self._extract_header_block(content)
        if not header:
            return findings

        required_tags = {
            "@project": ("CA_STR_010", "Missing @project tag in file header"),
            "@package": ("CA_STR_011", "Missing @package tag in file header"),
            "@author": ("CA_STR_012", "Missing @author tag in file header"),
            "@copyright": ("CA_STR_013", "Missing @copyright tag in file header"),
        }
        for tag, (code, msg) in required_tags.items():
            if tag not in header:
                findings.append(AuditFinding(
                    category="file_structure", severity="medium", file=file_path,
                    line=1, code=code,
                    message=msg,
                    remediation=f"Add '{tag}' to file header DocBlock",
                    standard_ref="coding-standard.md §1 (Class DocBlock)",
                    confidence=0.95,
                ))

        if "@package" in header and "@stack" not in header:
            pkg_line = [l for l in lines[:20] if "@package" in l]
            pkg_line = pkg_line[0] if pkg_line else ""
            if "/" in pkg_line or "\\" in pkg_line:
                findings.append(AuditFinding(
                    category="file_structure", severity="low", file=file_path,
                    line=1, code="CA_STR_014",
                    message="Missing @stack tag — required when @package uses nested namespace",
                    remediation="Add @stack <language> (e.g. Python, TypeScript, Go)",
                    standard_ref="coding-standard.md §1",
                    confidence=0.85,
                ))

        class_desc = re.search(r'\* \* (?:Class|Module|Tool|Service)\s+\S+\s+[–-]+\s', header)
        if not class_desc:
            findings.append(AuditFinding(
                category="file_structure", severity="low", file=file_path,
                line=1, code="CA_STR_015",
                message="Missing class description line in file header",
                remediation="Add '* * Class <Name> – single responsibility' line after DocBlock tags",
                standard_ref="coding-standard.md §1",
                confidence=0.8,
            ))

        return findings

    def _extract_header_block(self, content: str) -> str:
        header = ""
        lines = content.splitlines()
        in_block = False
        for line in lines[:30]:
            stripped = line.strip()
            if stripped.startswith("/**") or stripped.startswith('"""'):
                in_block = True
                header += stripped + "\n"
            elif in_block:
                header += stripped + "\n"
                if stripped.endswith("*/") or stripped.endswith('"""'):
                    break
            elif stripped.startswith("# ") or stripped.startswith("// "):
                header += stripped + "\n"
            else:
                break
        return header

    def _check_modular(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        class_count = 0
        for i, line in enumerate(lines, 1):
            if re.search(r"^\s*class\s+\w+", line):
                class_count += 1
        if class_count > 3:
            findings.append(AuditFinding(
                category="modular", severity="medium", file=file_path,
                line=1, code="CA_MOD_001",
                message=f"File contains {class_count} classes — consider splitting",
                details={"class_count": class_count},
                remediation=f"Split into {class_count} separate files per SRP",
                standard_ref="project-structure-modular-standard.md §1",
                confidence=0.7,
            ))

        content_lower = content.lower()
        fp_lower = file_path.lower()

        # Check: direct instantiation across modules (M1)
        if "modules/" in fp_lower or "src/" in fp_lower:
            for i, line in enumerate(lines, 1):
                if re.search(r"new\s+(\w+)", line) and "import" not in line and "require" not in line:
                    class_name = re.search(r"new\s+(\w+)", line).group(1)
                    if class_name[0].isupper() and "Exception" not in class_name:
                        findings.append(AuditFinding(
                            category="modular", severity="medium", file=file_path,
                            line=i, code="CA_MOD_002",
                            message=f"Direct instantiation of '{class_name}' — violates M1 constraint",
                            details={"class_name": class_name},
                            remediation="Inject via constructor or use service container (contract over concretion)",
                            standard_ref="project-structure-modular-standard.md §11.1 (M1)",
                            confidence=0.65,
                        ))

        # Check: interface/contract usage (P2)
        if "service" in fp_lower or "repository" in fp_lower or "handler" in fp_lower:
            has_interface = False
            cs = "".join(lines)
            if re.search(r"class\s+\w+.*:", cs) and not re.search(r"class\s+\w+.*\(.*Interface", cs):
                has_interface_ref = re.search(r"(implements|extends|Interface)\s", cs)
                has_injection = re.search(r"(type_hint|def\s+__init__.*Interface|def\s+__init__.*Repository|def\s+__init__.*Contract)", cs)
                if not has_interface_ref and not has_injection:
                    findings.append(AuditFinding(
                        category="modular", severity="low", file=file_path,
                        line=1, code="CA_MOD_003",
                        message="Service class may lack contract/interface — use contract over concretion",
                        details={"file": file_path},
                        remediation="Create interface in Contracts/ and type-hint against it",
                        standard_ref="project-structure-modular-standard.md §11.3 (P2)",
                        confidence=0.5,
                    ))
        return findings

    def _check_modular_structure(self, root: Path, dirs: Set[Path], files: List[Path]) -> List[AuditFinding]:
        """Validate project structure against project-structure-modular-standard.md §2, §5, §8."""
        findings = []
        dir_names = {d.name.lower(): d for d in dirs}
        file_names = {f.name.lower(): f for f in files}
        rel_dirs = {str(d.relative_to(root)).lower(): d for d in dirs if root in d.parents or d == root}

        # §2: Root-level folder structure
        required_roots = [".agents", "src", "tests", "docs", "config"]
        if any(d.name == "composer.json" for d in files):
            required_roots.extend(["public", "database", "storage"])

        for req in required_roots:
            if req not in dir_names:
                findings.append(AuditFinding(
                    category="modular_structure", severity="medium",
                    file=str(root), line=1, code="CA_MDL_001",
                    message=f"Missing required root folder: '{req}'",
                    details={"missing_dir": req},
                    remediation=f"Create '{req}/' directory at project root",
                    standard_ref="project-structure-modular-standard.md §2",
                    confidence=0.9,
                ))

        # §2: Required root files
        required_root_files = [".gitignore", "README.md"]
        for req in required_root_files:
            if req.lower() not in file_names:
                findings.append(AuditFinding(
                    category="modular_structure", severity="medium",
                    file=str(root), line=1, code="CA_MDL_001",
                    message=f"Missing required root file: '{req}'",
                    details={"missing_file": req},
                    remediation=f"Create '{req}' at project root",
                    standard_ref="project-structure-modular-standard.md §2",
                    confidence=0.95,
                ))

        # §5: Module internal structure
        module_dirs = [d for d in dirs if d.parent.name.lower() in ("modules", "plugins", "widgets")]
        for mod in module_dirs:
            mod_files = [f for f in files if mod in f.parents]
            mod_file_names = {f.name.lower() for f in mod_files}
            mod_dir_names = {str(f.relative_to(mod).parts[0]).lower() for f in mod_files if mod in f.parents}

            # §5: Required module manifest
            if "module.json" not in mod_file_names and "manifest.json" not in mod_file_names and "package.json" not in mod_file_names:
                findings.append(AuditFinding(
                    category="modular_structure", severity="low",
                    file=str(mod), line=1, code="CA_MDL_002",
                    message=f"Module '{mod.name}' missing manifest file (module.json)",
                    details={"module": mod.name},
                    remediation=f"Add module.json to {mod.name}/ with name, namespace, version",
                    standard_ref="project-structure-modular-standard.md §5.1",
                    confidence=0.8,
                ))

            # §5: Required README
            if "readme.md" not in mod_file_names:
                findings.append(AuditFinding(
                    category="modular_structure", severity="low",
                    file=str(mod), line=1, code="CA_MDL_003",
                    message=f"Module '{mod.name}' missing README.md",
                    details={"module": mod.name},
                    remediation=f"Add README.md to {mod.name}/ with description, setup, env vars",
                    standard_ref="project-structure-modular-standard.md §5",
                    confidence=0.85,
                ))

            # §5: Required sub-folders (Controllers, Models, Services)
            required_subdirs = []
            for p in mod_files:
                rel = p.relative_to(mod)
                parts = rel.parts
                if len(parts) > 1:
                    container_name = parts[0]
                    if container_name.lower() in ("controllers", "models", "services", "views", "presenters"):
                        required_subdirs.append(container_name.lower())

            unique_subdirs = set(required_subdirs)
            if len(unique_subdirs) < 2:
                findings.append(AuditFinding(
                    category="modular_structure", severity="low",
                    file=str(mod), line=1, code="CA_MDL_004",
                    message=f"Module '{mod.name}' has limited HMVC-P structure ({unique_subdirs or 'none'})",
                    details={"module": mod.name, "subdirs": list(unique_subdirs)},
                    remediation="Add Controllers/, Models/, Services/ structure per HMVC-P pattern",
                    standard_ref="project-structure-modular-standard.md §5",
                    confidence=0.6,
                ))

        # §8: Container folder naming — must be plural
        plural_containers = {
            "controllers", "services", "models", "views", "presenters",
            "repositories", "entities", "events", "listeners",
            "migrations", "helpers", "libraries", "tests",
        }
        for d in dirs:
            name_lower = d.name.lower()
            if name_lower in plural_containers:
                continue
            # Detect singular version used instead of plural
            singular_map = {
                "controller": "controllers", "service": "services",
                "model": "models", "view": "views", "presenter": "presenters",
                "repository": "repositories", "entity": "entities",
                "event": "events", "listener": "listeners",
                "migration": "migrations", "helper": "helpers",
                "library": "libraries", "test": "tests",
            }
            if name_lower in singular_map:
                expected = singular_map[name_lower]
                findings.append(AuditFinding(
                    category="modular_structure", severity="medium",
                    file=str(d), line=1, code="CA_MDL_005",
                    message=f"Container folder '{d.name}' should be plural: '{expected}'",
                    details={"current": d.name, "expected": expected},
                    remediation=f"Rename '{d.name}' to '{expected}'",
                    standard_ref="project-structure-modular-standard.md §8 (plural containers)",
                    confidence=0.9,
                ))

        # §8.4: Root-level folders naming — consistency
        pascal_root_dirs = {"Modules", "Plugins", "Widgets", "Core", "Contracts", "Controllers"}
        lowercase_root_dirs = {"app", "api", "public", "storage", "database", "config", "tests", "docs", "scripts"}
        for d in dirs:
            if d.parent == root:
                if d.name in pascal_root_dirs:
                    continue
                if d.name in lowercase_root_dirs:
                    continue
                # Check for wrong case
                if d.name[0].isupper() and d.name not in pascal_root_dirs:
                    expected = d.name.lower()
                    if expected in lowercase_root_dirs:
                        findings.append(AuditFinding(
                            category="modular_structure", severity="low",
                            file=str(d), line=1, code="CA_MDL_006",
                            message=f"Root folder '{d.name}' should be lowercase: '{expected}'",
                            details={"current": d.name, "expected": expected},
                            remediation=f"Rename '{d.name}' to '{expected}'",
                            standard_ref="project-structure-modular-standard.md §8.4",
                            confidence=0.85,
                        ))

        return findings

    def _check_error_handling(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        has_try = any("try:" in l or "try {" in l for l in lines)
        has_except = any("except" in l or "catch" in l for l in lines)
        if has_try and not has_except:
            findings.append(AuditFinding(
                category="error_handling", severity="high", file=file_path,
                line=1, code="CA_ERR_001",
                message="try without except/catch — silent failure",
                remediation="Add except clause with structured error handling",
                standard_ref="errors-logs-standard.md §1",
                confidence=0.9,
            ))
        for i, line in enumerate(lines, 1):
            if re.search(r"except\s*:", line) and "Exception" not in line:
                findings.append(AuditFinding(
                    category="error_handling", severity="medium", file=file_path,
                    line=i, code="CA_ERR_002",
                    message="Bare except — catches all exceptions silently",
                    remediation="Use specific exception type: except <SpecificError>:",
                    standard_ref="errors-logs-standard.md §1",
                    confidence=0.85,
                ))
        return findings

    def _check_di_compliance(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        for i, line in enumerate(lines, 1):
            m = re.search(r"^\s*(\w+)\s*=\s*(?:(\w+)\(\)|(\w+)\.\w+\s*=\s*(?:\w+)\(\))", line)
            if m and not line.strip().startswith("#"):
                var_name = m.group(1)
                if any(kw in var_name.lower() for kw in ("service", "repo", "handler", "manager", "client", "db", "cache")):
                    findings.append(AuditFinding(
                        category="di_compliance", severity="medium", file=file_path,
                        line=i, code="CA_DI_001",
                        message=f"Direct instantiation of '{var_name}' — should be injected",
                        details={"variable": var_name},
                        remediation="Inject via constructor instead of direct instantiation",
                        standard_ref="modular-standard.md §3",
                        confidence=0.7,
                    ))
        return findings

    def _check_docblock(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        for i, line in enumerate(lines, 1):
            func_match = re.search(r"^\s*def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*[^:]+)?\s*:", line)
            if not func_match:
                func_match = re.search(r"^\s*(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)", line)
            if not func_match:
                func_match = re.search(r"^\s*(\w+)\s*\([^)]*\)\s*\{", line)
                if func_match and func_match.group(1)[0].islower():
                    func_match = None
                else:
                    func_match = None
            if not func_match:
                continue

            func_name = func_match.group(1)
            if func_name.startswith("_"):
                continue

            doc_block = self._extract_preceding_docblock(lines, i - 2)
            if doc_block is None:
                findings.append(AuditFinding(
                    category="docblock", severity="medium", file=file_path,
                    line=i, code="CA_DOC_001",
                    message=f"Public method '{func_name}' missing docstring",
                    details={"method": func_name},
                    remediation="Add method DocBlock with description, @param, @return",
                    standard_ref="coding-standard.md §1 (Method DocBlock)",
                    confidence=0.9,
                ))
                continue

            has_description = bool(re.sub(r'^\s*\*\s*|^\s*#\s*|^\s*"""\s*|^\s*\'\'\'\s*', '', doc_block.strip()))
            has_description = has_description and not doc_block.strip().startswith(("@" , "*/", '"""', "'''"))
            if not has_description:
                findings.append(AuditFinding(
                    category="docblock", severity="low", file=file_path,
                    line=i, code="CA_DOC_020",
                    message=f"Method '{func_name}' DocBlock missing business logic description",
                    details={"method": func_name},
                    remediation="Add description explaining WHAT this method does (business logic)",
                    standard_ref="coding-standard.md §1 (Method DocBlock)",
                    confidence=0.85,
                ))

            params_str = func_match.group(2) if func_match.lastindex and func_match.lastindex >= 2 else ""
            actual_params = []
            if params_str:
                for p in params_str.split(","):
                    p = p.strip()
                    if p and p not in ("self", "cls", "this"):
                        p_name = p.split(":")[0].split("=")[0].strip()
                        if p_name and not p_name.startswith("*"):
                            actual_params.append(p_name)

            for p_name in actual_params:
                param_pattern = re.compile(rf'@param\s+\S+\s+\b{re.escape(p_name)}\b')
                if not param_pattern.search(doc_block):
                    findings.append(AuditFinding(
                        category="docblock", severity="low", file=file_path,
                        line=i, code="CA_DOC_021",
                        message=f"Parameter '{p_name}' missing @param tag in '{func_name}'",
                        details={"method": func_name, "param": p_name},
                        remediation=f"Add '@param  type  {p_name}  description'",
                        standard_ref="coding-standard.md §1 (Method DocBlock)",
                        confidence=0.85,
                    ))

            if not re.search(r'@return\s', doc_block):
                if func_name not in ("__init__", "__new__", "__post_init__"):
                    not_setter = not func_name.startswith("set_")
                    if not_setter:
                        findings.append(AuditFinding(
                            category="docblock", severity="low", file=file_path,
                            line=i, code="CA_DOC_022",
                            message=f"Method '{func_name}' missing @return tag",
                            details={"method": func_name},
                            remediation="Add '@return <type>' — use 'None' if no return value",
                            standard_ref="coding-standard.md §1 (Method DocBlock)",
                            confidence=0.8,
                        ))

            has_raises = "raise " in content[content.index(line):content.index(line) + 500] if line in content else False
            if has_raises and not re.search(r'@throws?\s', doc_block):
                findings.append(AuditFinding(
                    category="docblock", severity="low", file=file_path,
                    line=i, code="CA_DOC_023",
                    message=f"Method '{func_name}' raises exception but missing @throws tag",
                    details={"method": func_name},
                    remediation="Add '@throws <ExceptionType> <condition>'",
                    standard_ref="coding-standard.md §1 (Method DocBlock)",
                    confidence=0.75,
                ))

        return findings

    def _extract_preceding_docblock(self, lines: List[str], end_line: int) -> Optional[str]:
        if end_line < 0:
            return None
        doc_lines = []
        in_block = False
        found_doc = False
        for i in range(end_line, -1, -1):
            stripped = lines[i].strip()
            if stripped.endswith("*/"):
                in_block = True
                doc_lines.insert(0, stripped)
                found_doc = True
            elif in_block:
                doc_lines.insert(0, stripped)
                if stripped.startswith("/**"):
                    break
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                doc_lines.insert(0, stripped)
                if stripped.count('"""') == 1 and stripped.count("'''") == 1:
                    pass
                found_doc = True
                if stripped.endswith('"""') or stripped.endswith("'''"):
                    break
            elif stripped.startswith("#") or stripped.startswith("//"):
                doc_lines.insert(0, stripped)
                found_doc = True
            else:
                if not found_doc:
                    continue
                break

        if not found_doc:
            return None
        return "\n".join(doc_lines)

    def _check_logging(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        has_structured_logger = "get_logger" in content
        has_raw_logger = "logging.getLogger" in content

        # ─── Import/setup check: should use get_logger (logging-standard §1) ───
        if has_raw_logger and not has_structured_logger:
            findings.append(AuditFinding(
                category="logging", severity="medium", file=file_path,
                line=1, code="CA_LOG_010",
                message="Uses logging.getLogger() instead of get_logger() — violates structured logging standard",
                remediation="Replace with 'get_logger(<domain.path>)' from src.core.logging_config",
                standard_ref="logging-standard.md §1 (structured logging)",
                confidence=0.9,
            ))

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            # ─── CA_LOG_001: print() instead of structured logger ───
            if re.search(r"print\s*\(|console\.log\s*\(", line):
                findings.append(AuditFinding(
                    category="logging", severity="low", file=file_path,
                    line=i, code="CA_LOG_001",
                    message="Raw print/log instead of structured logging",
                    details={"line_content": stripped[:60]},
                    remediation="Replace with logger.info/json structured logging",
                    standard_ref="logging-standard.md §1 (no plain text)",
                    confidence=0.9,
                ))

            # ─── L3: log level check ───
            level_match = re.search(r"logger\.(\w+)\s*\(", line)
            if level_match:
                level = level_match.group(1).lower()
                valid_levels = {"debug", "info", "warning", "error", "critical", "exception", "fatal", "warn", "trace"}
                if level not in valid_levels:
                    findings.append(AuditFinding(
                        category="logging", severity="low", file=file_path,
                        line=i, code="CA_LOG_011",
                        message=f"Invalid log level '{level}' — use: debug, info, warn, error, fatal",
                        details={"invalid_level": level},
                        remediation="Use one of: debug, info, warn, error, fatal",
                        standard_ref="logging-standard.md §2.2 (L3)",
                        confidence=0.85,
                    ))

                # ─── L4/L5: message must be static template, max 120 chars ───
                msg_match = re.search(r"logger\.\w+\(\s*([fF]?['\"])", line)
                if msg_match:
                    quote_char = msg_match.group(1)
                    if quote_char.startswith("f") or "f'" in quote_char or 'f"' in quote_char:
                        findings.append(AuditFinding(
                            category="logging", severity="medium", file=file_path,
                            line=i, code="CA_LOG_012",
                            message="f-string in log message — dynamic data must be in extra dict, not message template",
                            details={"line": stripped[:80]},
                            remediation="Use static message template and pass variables as extra={\"key\": value}",
                            standard_ref="logging-standard.md §5.2 (L4)",
                            confidence=0.8,
                        ))

                # ─── ERR-L1: logger.error() with f-string but no error_code ───
                if level in ("error", "critical", "fatal"):
                    has_error_code = "error_code" in line
                    has_f_string = "f'" in line or 'f"' in line or ".format(" in line or "%" in line
                    if has_f_string and not has_error_code:
                        findings.append(AuditFinding(
                            category="logging", severity="high", file=file_path,
                            line=i, code="CA_LOG_013",
                            message="Error log missing error_code — every error/fatal MUST include error_code",
                            details={"line": stripped[:80]},
                            remediation="Add error_code='XXX_XXX' to the log context dict",
                            standard_ref="logging-standard.md §7.4 (ERR-L1)",
                            confidence=0.85,
                        ))

                # ─── ID-L6: identity fields as null in log ───
                if re.search(r"(user_id|tenant_id|organization_id|workspace_id)\s*=\s*None", line):
                    findings.append(AuditFinding(
                        category="logging", severity="low", file=file_path,
                        line=i, code="CA_LOG_014",
                        message="Identity field set to None — should be omitted if not relevant",
                        details={"line": stripped[:80]},
                        remediation="Omit the field entirely instead of passing None",
                        standard_ref="logging-standard.md §8.2 (ID-L6)",
                        confidence=0.8,
                    ))

                # ─── L2: timestamp format check ───
                if "timestamp" in line and not re.search(r'timestamp.*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})', line):
                    if not re.search(r'utc_now_iso|datetime.*isoformat', line):
                        pass  # skip false positives

            # ─── CA_LOG_002: string-based logging without context dict ───
            if re.search(r"logger\.(info|error|warning|debug|fatal|exception)\(\s*['\"]", line):
                # Check if there's a second positional arg (the context dict)
                has_extra = re.search(r"logger\.\w+\(\s*['\"].*['\"]\s*,\s*\{", line)
                has_format_args = "%s" in line or "{}" in line or "{0}" in line
                if not has_extra and not has_format_args:
                    findings.append(AuditFinding(
                        category="logging", severity="low", file=file_path,
                        line=i, code="CA_LOG_002",
                        message="String-based logging without structured context dict",
                        details={"line": stripped[:80]},
                        remediation="Add context dict as second argument: logger.info('msg', extra={'key': val}) or logger.info('msg', {'key': val})",
                        standard_ref="logging-standard.md §5 (JSON format)",
                        confidence=0.7,
                    ))

        return findings

    def _check_api_response(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        """
        Validate code against ~/.aicoders/ api-standard.md rules.

        Rules checked:
          R1:  All top-level fields present
          R3:  data == null on error
          R4:  success == false on >= 400
          O1:  request_id required
          O3:  error_code required on error
          D1-D4: data type per context
          P1:  links for paginated collections
          ID5: identity fields only when relevant (omit, not null)
          §3:  message max 120 chars
        """
        findings = []
        in_api_response_call = False
        api_response_args = {}
        has_list_data = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # ─── R1: Manual response dict detection ───
            if re.search(r"return\s*\{[\s\S]*?\"success\"[\s\S]*?\"data\"", line):
                if "api_response" not in line and "api_response(" not in line:
                    findings.append(AuditFinding(
                        category="api_response", severity="high", file=file_path,
                        line=i, code="CA_API_001",
                        message="Manual response dict instead of api_response()",
                        details={"line": stripped[:80]},
                        remediation="Replace with api_response(success=..., status_code=..., data=..., request_id=...)",
                        standard_ref="api-standard.md §2 (R1)",
                        confidence=0.85,
                    ))

            # ─── api_response() argument extraction ───
            if "api_response(" in line:
                in_api_response_call = True
                api_response_args = {}
                has_list_data = False
                self._extract_api_args(line, api_response_args)

            if in_api_response_call and ")" in line and not line.strip().endswith("\\"):
                in_api_response_call = False

                # Detect if data is a list (array) — pagination required (P1)
                data_val = str(api_response_args.get("data", ""))
                if data_val and ("[" in data_val or data_val.startswith("[")):
                    has_list_data = True

                # R1: Check required fields
                required = ["success", "status_code", "message", "data", "request_id"]
                for field in required:
                    if field not in api_response_args:
                        findings.append(AuditFinding(
                            category="api_response", severity="high", file=file_path,
                            line=i, code="CA_API_009",
                            message=f"api_response() missing required field '{field}'",
                            details={"missing": field},
                            remediation=f"Add {field}=<value> to api_response() call",
                            standard_ref="api-standard.md §2 (R1)",
                            confidence=0.9,
                        ))

                # R3: data=None when status_code >= 400
                sc = api_response_args.get("status_code", "")
                sc_int = None
                try:
                    sc_int = int(sc) if isinstance(sc, str) and sc.isdigit() else sc
                except (ValueError, TypeError):
                    pass
                if isinstance(sc_int, int) and sc_int >= 400 and data_val not in ("None", "null", ""):
                    findings.append(AuditFinding(
                        category="api_response", severity="high", file=file_path,
                        line=i, code="CA_API_005",
                        message=f"Error response (status_code={sc_int}) should have data=None, got '{data_val}'",
                        details={"status_code": sc_int, "data": data_val},
                        remediation="Set data=None for error responses",
                        standard_ref="api-standard.md §2 (R3)",
                        confidence=0.85,
                    ))

                # R4: success=False when status_code >= 400
                success_val = api_response_args.get("success", "")
                if isinstance(sc_int, int) and sc_int >= 400 and success_val not in ("False", "false", "0"):
                    if success_val not in ("True", "true", "1"):
                        pass  # dynamic, skip
                    else:
                        findings.append(AuditFinding(
                            category="api_response", severity="high", file=file_path,
                            line=i, code="CA_API_005",
                            message=f"Error response should have success=False, got success={success_val}",
                            details={"status_code": sc_int, "success": success_val},
                            remediation="Set success=False for status_code >= 400",
                            standard_ref="api-standard.md §2 (R4)",
                            confidence=0.8,
                        ))

                # O1: check request_id format
                rid = str(api_response_args.get("request_id", ""))
                if rid and not rid.startswith("req_") and not rid.startswith("new_request_id"):
                    findings.append(AuditFinding(
                        category="api_response", severity="medium", file=file_path,
                        line=i, code="CA_API_002",
                        message="request_id should be generated via new_request_id()",
                        details={"request_id": rid[:40]},
                        remediation="Use new_request_id() to generate request_id",
                        standard_ref="api-standard.md §2 (O1)",
                        confidence=0.7,
                    ))

                # O3: error_code required on error
                if isinstance(sc_int, int) and sc_int >= 400:
                    ec = api_response_args.get("error_code", "")
                    if not ec or ec == "None":
                        findings.append(AuditFinding(
                            category="api_response", severity="medium", file=file_path,
                            line=i, code="CA_API_003",
                            message=f"Error response missing error_code (status={sc_int})",
                            details={"status_code": sc_int},
                            remediation="Add error_code='XXX_XXX' to api_response() for error responses",
                            standard_ref="api-standard.md §2 (O3)",
                            confidence=0.9,
                        ))

                # §3: message length
                msg = str(api_response_args.get("message", ""))
                if len(msg) > 120:
                    findings.append(AuditFinding(
                        category="api_response", severity="low", file=file_path,
                        line=i, code="CA_API_010",
                        message=f"message exceeds 120 chars ({len(msg)})",
                        details={"length": len(msg)},
                        remediation="Keep message under 120 characters",
                        standard_ref="api-standard.md §3",
                        confidence=0.8,
                    ))

                # P1: List data without links — pagination required
                if has_list_data and "links" not in api_response_args:
                    findings.append(AuditFinding(
                        category="api_response", severity="medium", file=file_path,
                        line=i, code="CA_API_007",
                        message="List/array data without 'links' — paginated collections MUST include links",
                        details={"line": stripped[:80]},
                        remediation="Add links={...} with self, first, prev, next, last URLs",
                        standard_ref="api-standard.md §4.5 (P1)",
                        confidence=0.7,
                    ))

                # ID5: Identity fields as None — should omit instead
                for id_field in ("user_id", "tenant_id", "organization_id", "workspace_id"):
                    val = api_response_args.get(id_field, "")
                    if val in ("None", "null"):
                        findings.append(AuditFinding(
                            category="api_response", severity="low", file=file_path,
                            line=i, code="CA_API_008",
                            message=f"Identity field '{id_field}' set to None — should be omitted if not relevant",
                            details={"field": id_field},
                            remediation=f"Omit {id_field}=None entirely; only include when relevant",
                            standard_ref="api-standard.md §4.2 (ID5)",
                            confidence=0.85,
                        ))

            # ─── Detect inline dicts with required fields ───
            if re.search(r'\{\s*["\']success["\']\s*:', line):
                if "api_response" not in stripped:
                    findings.append(AuditFinding(
                        category="api_response", severity="medium", file=file_path,
                        line=i, code="CA_API_001",
                        message="Manual response structure detected — use api_response()",
                        details={"line": stripped[:80]},
                        remediation="Replace manual dict with api_response() call",
                        standard_ref="api-standard.md §2 (R1)",
                        confidence=0.7,
                    ))

        return findings

    def _extract_api_args(self, line: str, args: dict) -> None:
        """Extract named arguments from api_response() call."""
        m = re.search(r"api_response\s*\((.+?)\)", line, re.DOTALL)
        if not m:
            return
        inner = m.group(1)
        for pair in re.finditer(r'(\w+)\s*=\s*([^,)]+)', inner):
            key = pair.group(1)
            val = pair.group(2).strip().rstrip(",")
            args[key] = val

    # ═══════════════════════════════════════════════════════════════
    # SEMVER COMPLIANCE — ~/.aicoders/rules/standards/semantic-versioning.md
    # ═══════════════════════════════════════════════════════════════

    def _check_semver_compliance(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        fp = Path(file_path)
        fname = fp.name.lower()

        # ─── Version file format checks (§5.1) ───
        if fname in (".version", "version", "version.txt", "version_current"):
            content_stripped = content.strip()
            # CA_SEM_001: Must match SemVer pattern
            if not re.match(r"^v?\d+\.\d+\.\d+", content_stripped):
                findings.append(AuditFinding(
                    category="semver", severity="high", file=file_path,
                    line=1, code="CA_SEM_001",
                    message=".version file does not contain a valid SemVer string",
                    details={"content": content_stripped[:60]},
                    remediation="Set content to MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD] format, e.g. '1.0.0'",
                    standard_ref="semantic-versioning.md §5.1",
                    confidence=0.95,
                ))
            # CA_SEM_002: Leading zeros check
            if re.search(r"\b0\d+\.", content_stripped):
                findings.append(AuditFinding(
                    category="semver", severity="medium", file=file_path,
                    line=1, code="CA_SEM_002",
                    message="Version number has leading zeros — violates SemVer §2",
                    details={"version": content_stripped[:30]},
                    remediation="Remove leading zeros: '1.2.3' not '01.2.3'",
                    standard_ref="semantic-versioning.md §1",
                    confidence=0.9,
                ))
            # CA_SEM_003: Extra whitespace/newlines in .version file
            if content != content_stripped:
                extra = repr(content[len(content_stripped):])
                findings.append(AuditFinding(
                    category="semver", severity="low", file=file_path,
                    line=1, code="CA_SEM_003",
                    message=f".version file has trailing whitespace or newlines: {extra}",
                    details={"extra": extra},
                    remediation="Keep .version as a single line with no trailing whitespace",
                    standard_ref="semantic-versioning.md §5.1",
                    confidence=0.9,
                ))

        # ─── package.json version sync check ───
        if fname == "package.json":
            try:
                pkg = json.loads(content)
                pkg_version = pkg.get("version", "")
                if pkg_version and not re.match(r"^\d+\.\d+\.\d+", pkg_version):
                    findings.append(AuditFinding(
                        category="semver", severity="medium", file=file_path,
                        line=1, code="CA_SEM_001",
                        message=f"package.json version '{pkg_version}' is not valid SemVer",
                        details={"version": pkg_version},
                        remediation="Update version field to MAJOR.MINOR.PATCH format",
                        standard_ref="semantic-versioning.md §6.2",
                        confidence=0.9,
                    ))
            except json.JSONDecodeError:
                pass

        # ─── pyproject.toml version sync check (dynamic version) ───
        if fname == "pyproject.toml":
            ver_match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            if ver_match:
                ver = ver_match.group(1)
                if not re.match(r"^\d+\.\d+\.\d+", ver):
                    findings.append(AuditFinding(
                        category="semver", severity="medium", file=file_path,
                        line=1, code="CA_SEM_001",
                        message=f"pyproject.toml version '{ver}' is not valid SemVer",
                        details={"version": ver},
                        remediation="Update version field to MAJOR.MINOR.PATCH format",
                        standard_ref="semantic-versioning.md §6.3",
                        confidence=0.9,
                    ))

        # ─── Release artifact naming convention (§7.2) ───
        if "releases" in fp.parts:
            release_exts = {".exe", ".msi", ".apk", ".aab", ".ipa", ".dmg", ".deb", ".rpm", ".AppImage", ".zip", ".tar.gz", ".tar.bz2"}
            if fp.suffix.lower() in release_exts or any(str(fp).endswith(ext) for ext in [".tar.gz", ".tar.bz2"]):
                # Must follow {project-name}_{version}_{platform}_{arch}[_{variant}].{ext}
                release_name = fp.stem if fp.suffix != ".gz" else fp.stem.replace(".tar", "")
                if not re.match(r"^[a-z0-9]+[-_][a-z0-9.]+[-_][a-z]+[-_][a-z0-9]+", release_name.lower()):
                    findings.append(AuditFinding(
                        category="semver", severity="medium", file=file_path,
                        line=1, code="CA_SEM_005",
                        message=f"Release artifact '{fp.name}' does not follow naming convention",
                        details={"filename": fp.name},
                        remediation="Rename to {project-name}_{version}_{platform}_{arch}[_{variant}].{ext} using lowercase, e.g. myapp-v1.2.3-windows-amd64.exe",
                        standard_ref="semantic-versioning.md §7.2",
                        confidence=0.8,
                    ))

                # CA_SEM_006: Special characters in release filenames
                if re.search(r"[^a-z0-9._\-]", fp.stem.lower()):
                    findings.append(AuditFinding(
                        category="semver", severity="low", file=file_path,
                        line=1, code="CA_SEM_006",
                        message=f"Release artifact '{fp.name}' contains special characters",
                        details={"filename": fp.name},
                        remediation="Use only [a-z0-9._-] in release filenames",
                        standard_ref="semantic-versioning.md §7.4 (rule 2)",
                        confidence=0.9,
                    ))

        return findings

    # ═══════════════════════════════════════════════════════════════
    # PWA COMPLIANCE — ~/.aicoders/rules/standards/pwa-standard.md (optional)
    # ═══════════════════════════════════════════════════════════════

    def _check_pwa_compliance(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        fp = Path(file_path)
        fname = fp.name.lower()

        # ─── CA_PWA_001: Service worker registration in JS/TS files ───
        if fp.suffix in (".js", ".ts", ".jsx", ".tsx"):
            has_sw = "serviceWorker" in content and "register" in content
            has_sw = has_sw or "ServiceWorker" in content
            if not has_sw:
                if "navigator" in content or "window" in content:
                    pass  # client-side file that might need SW registration

            # CA_PWA_003: HTTPS enforcement check
            if "location.protocol" in content or "location.href" in content:
                if "https" not in content:
                    findings.append(AuditFinding(
                        category="pwa", severity="high", file=file_path,
                        line=1, code="CA_PWA_003",
                        message="Client-side code references location but missing HTTPS enforcement",
                        details={"file": fname},
                        remediation="Add HTTPS redirect: if (location.protocol !== 'https:' && location.hostname !== 'localhost') location.replace(...)",
                        standard_ref="pwa-standard.md §3.1",
                        confidence=0.7,
                    ))

        # ─── CA_PWA_004: Cache strategy without interface/pattern ───
        if "cache" in content.lower() and ("fetch" in content.lower() or "request" in content.lower()):
            has_strategy = any(kw in content for kw in ("ICacheStrategy", "CacheStrategy", "CacheFirst", "NetworkFirst", "StaleWhileRevalidate", "CacheInterface"))
            if fp.suffix in (".js", ".ts", ".py", ".java", ".kt", ".cs", ".go", ".rs", ".dart") and not has_strategy:
                findings.append(AuditFinding(
                    category="pwa", severity="medium", file=file_path,
                    line=1, code="CA_PWA_004",
                    message="Cache/fetch logic found without strategy pattern interface",
                    details={"file": fname},
                    remediation="Implement ICacheStrategy interface with CacheFirst, NetworkFirst, StaleWhileRevalidate implementations",
                    standard_ref="pwa-standard.md §4.1",
                    confidence=0.65,
                ))

        # ─── CA_PWA_007: Touch targets too small in CSS ───
        if fp.suffix in (".css", ".scss", ".less"):
            for i, line in enumerate(lines, 1):
                if re.search(r"(?:height|width)\s*:\s*\d+px", line):
                    val_match = re.search(r"(?:height|width)\s*:\s*(\d+)px", line)
                    if val_match and int(val_match.group(1)) < 44:
                        findings.append(AuditFinding(
                            category="pwa", severity="medium", file=file_path,
                            line=i, code="CA_PWA_007",
                            message=f"Touch target may be too small: {val_match.group(0)} (< 44px minimum)",
                            details={"rule": val_match.group(0).strip()},
                            remediation="Increase to at least 44px for interactive elements; use 48px for mobile small",
                            standard_ref="pwa-standard.md §5.2",
                            confidence=0.6,
                        ))

            # CA_PWA_008: body font-size < 16px
            if re.search(r"(?:body|html)\s*\{[^}]*font-size\s*:\s*(\d+)px", content):
                size_match = re.search(r"(?:body|html)\s*\{[^}]*font-size\s*:\s*(\d+)px", content)
                if size_match and int(size_match.group(1)) < 16:
                    findings.append(AuditFinding(
                        category="pwa", severity="low", file=file_path,
                        line=1, code="CA_PWA_008",
                        message=f"Base font-size is {size_match.group(1)}px — minimum 16px prevents iOS auto-zoom",
                        details={"font_size": size_match.group(1)},
                        remediation="Set html/body font-size to at least 16px",
                        standard_ref="pwa-standard.md §5.2",
                        confidence=0.85,
                    ))

        # ─── CA_PWA_009: Check for container queries ───
        if fp.suffix in (".css", ".scss", ".less"):
            has_container = "@container" in content
            has_media = "@media" in content
            if has_media and not has_container:
                findings.append(AuditFinding(
                    category="pwa", severity="low", file=file_path,
                    line=1, code="CA_PWA_009",
                    message="Uses @media queries but not @container queries — prefer component-level responsiveness",
                    details={"file": fname},
                    remediation="Replace @media with @container queries for component-scoped responsiveness (2026 standard)",
                    standard_ref="pwa-standard.md §5.1",
                    confidence=0.5,
                ))

        return findings

    # ═══════════════════════════════════════════════════════════════
    # CROSS-PLATFORM COMPLIANCE — ~/.aicoders/rules/standards/cross-platform-standard.md (optional)
    # ═══════════════════════════════════════════════════════════════

    def _check_crossplatform_compliance(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        fp = Path(file_path)
        fname = fp.name.lower()
        fp_lower = str(fp).lower()

        # ─── CA_CRO_001: Business logic importing UI framework ───
        is_service_layer = any(kw in fp_lower for kw in ["/services/", "/repositories/", "/usecases/", "/use_cases/", "/core/", "/domain/"])
        ui_imports = {
            "react", "flutter", "material", "cupertino", "uikit", "swiftui",
            "androidx.compose", "widget", "render", "jsx", "tsx",
        }
        if is_service_layer:
            for i, line in enumerate(lines, 1):
                stripped_lower = line.strip().lower()
                for ui_kw in ui_imports:
                    if ui_kw in stripped_lower and ("import" in stripped_lower or "from" in stripped_lower):
                        findings.append(AuditFinding(
                            category="crossplatform", severity="high", file=file_path,
                            line=i, code="CA_CRO_001",
                            message=f"Service/core layer imports UI framework '{ui_kw}' — violates Shared Business Logic principle",
                            details={"import": line.strip()[:80], "ui_framework": ui_kw},
                            remediation="Move UI import to presentation layer; core logic must be pure and UI-framework-agnostic",
                            standard_ref="cross-platform-standard.md §1",
                            confidence=0.85,
                        ))
                        break

        # ─── CA_CRO_003: Hardcoded screen dimensions ───
        hc_dimensions = re.finditer(r"(?:width|height)\s*[=:]\s*(\d{3,4})\s*(?:px|dp|pt)?", content)
        for m in hc_dimensions:
            val = int(m.group(1))
            if val in (320, 360, 375, 390, 414, 480, 600, 720, 768, 800, 1024, 1080, 1280, 1366, 1440, 1536, 1920):
                line_num = content[:m.start()].count("\n") + 1
                findings.append(AuditFinding(
                    category="crossplatform", severity="medium", file=file_path,
                    line=line_num, code="CA_CRO_003",
                    message=f"Hardcoded screen dimension {m.group(0).strip()} — use responsive units instead",
                    details={"dimension": m.group(0).strip(), "value": val},
                    remediation="Replace with relative units (%, flexbox, clamp(), or responsive breakpoints)",
                    standard_ref="cross-platform-standard.md §6 (rule 2)",
                    confidence=0.7,
                ))

        # ─── CA_CRO_004: Raw HTTP objects in business logic ───
        if is_service_layer or "service" in fp_lower or "use_case" in fp_lower or "usecase" in fp_lower:
            raw_http_indicators = ["HttpRequest", "HttpResponse", "express.Request", "flask.request", "django.http", "requests.Response"]
            for i, line in enumerate(lines, 1):
                for indicator in raw_http_indicators:
                    if indicator in line and "import" not in line:
                        findings.append(AuditFinding(
                            category="crossplatform", severity="high", file=file_path,
                            line=i, code="CA_CRO_004",
                            message=f"Raw HTTP object '{indicator}' used in business logic — must use DTOs at boundaries",
                            details={"http_type": indicator, "line": line.strip()[:80]},
                            remediation="Map to DTO in controller/presenter layer before passing to service",
                            standard_ref="cross-platform-standard.md §4",
                            confidence=0.8,
                        ))
                        break

        # ─── CA_CRO_006: Missing responsive breakpoints in CSS ───
        if fp.suffix in (".css", ".scss", ".less"):
            if not re.search(r"@media|@container", content):
                findings.append(AuditFinding(
                    category="crossplatform", severity="low", file=file_path,
                    line=1, code="CA_CRO_006",
                    message="No responsive breakpoints found — UI should adapt to mobile, tablet, and desktop",
                    details={"file": fname},
                    remediation="Add @media or @container queries for breakpoints: <375px, 375px, 768px, 1024px, 1280px, 1536px, 1920px",
                    standard_ref="cross-platform-standard.md §3.A",
                    confidence=0.6,
                ))

        # ─── CA_CRO_007: Dark mode support ───
        if fp.suffix in (".css", ".scss", ".less", ".html", ".tsx", ".jsx"):
            if "color" in content.lower() and "prefers-color-scheme" not in content:
                if "dark" in content.lower() or "theme" in content.lower():
                    pass  # might have custom dark mode
                else:
                    findings.append(AuditFinding(
                        category="crossplatform", severity="low", file=file_path,
                        line=1, code="CA_CRO_007",
                        message="Color definitions found but missing prefers-color-scheme dark mode support",
                        details={"file": fname},
                        remediation="Add @media (prefers-color-scheme: dark) with dark theme variables",
                        standard_ref="cross-platform-standard.md §6 (rule 4)",
                        confidence=0.5,
                    ))

        # ─── CA_CRO_008: Accessibility (aria / role) ───
        if fp.suffix in (".html", ".tsx", ".jsx", ".vue"):
            if "button" in content or "input" in content or "a " in content:
                if "aria-" not in content and "role=" not in content:
                    findings.append(AuditFinding(
                        category="crossplatform", severity="medium", file=file_path,
                        line=1, code="CA_CRO_008",
                        message="Interactive elements found without aria attributes — missing accessibility support",
                        details={"file": fname},
                        remediation="Add aria-label, role, and other ARIA attributes to interactive elements",
                        standard_ref="cross-platform-standard.md §6 (rule 4)",
                        confidence=0.6,
                    ))

        return findings

    # ═══════════════════════════════════════════════════════════════
    # PROJECT-LEVEL SEMVER CHECKS
    # ═══════════════════════════════════════════════════════════════
    # TEST/DEBUG COMPLIANCE — ~/.aicoders/rules/standards/debug-test-standard.md
    # ═══════════════════════════════════════════════════════════════

    def _check_test_debug(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        fp = Path(file_path)
        fname = fp.name.lower()
        fp_lower = str(fp).lower().replace("\\", "/")
        is_test_file = "/tests/" in fp_lower or fp_lower.startswith("tests/")
        is_test_suffix = fname.startswith("test_") or fname.endswith("_test.py") or fname.endswith(".test.js") or fname.endswith(".spec.js") or fname.endswith("_test.go")

        # ─── TD_TF_001: Test filename naming convention ───
        if is_test_file and not is_test_suffix:
            findings.append(AuditFinding(
                category="test_debug", severity="medium", file=file_path,
                line=1, code="CA_TD_001",
                message=f"Test file '{fp.name}' does not follow naming convention for its language",
                details={"filename": fp.name},
                remediation="Rename to test_<name>.py (Python), <name>.test.js (JS/TS), or <name>_test.go (Go)",
                standard_ref="debug-test-standard.md §3.1",
                confidence=0.85,
            ))

        # ─── TD_TF_002: Test function naming ───
        if is_test_file or is_test_suffix:
            has_test_func = False
            for i, line in enumerate(lines, 1):
                if re.search(r"^\s*(?:async\s+)?def\s+test_", line):
                    has_test_func = True
                elif re.search(r"^\s*(?:async\s+)?function\s+test\b|^\s*test\s*\(", line):
                    has_test_func = True
                elif re.search(r"^\s*it\s*\(", line):
                    has_test_func = True
                elif re.search(r"^\s*func\s+Test\w+", line):
                    has_test_func = True
            if not has_test_func and lines:
                # Only flag if looks like a real test file (has imports common to testing frameworks)
                test_imports = ["pytest", "unittest", "jest", "describe", "testing"] if is_test_file else []
                has_import = any(kw in content for kw in test_imports)
                if has_import or not is_test_file:
                    pass  # Not enough certainty to flag
                elif not has_import:
                    findings.append(AuditFinding(
                        category="test_debug", severity="low", file=file_path,
                        line=1, code="CA_TD_002",
                        message="Test file missing test functions — no test_/Test/ test() pattern found",
                        details={"file": fp.name},
                        remediation="Add test functions following pattern: test_<name> (Python), Test<Name> (Go), test('...') (JS/TS)",
                        standard_ref="debug-test-standard.md §3.1",
                        confidence=0.7,
                    ))

            # ─── TD_TF_003: Debug print in test files ───
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("//"):
                    continue
                if re.search(r"\bprint\s*\(", stripped) or "console.log" in stripped:
                    findings.append(AuditFinding(
                        category="test_debug", severity="low", file=file_path,
                        line=i, code="CA_TD_003",
                        message=f"Debug print/console.log in test file — use logger instead",
                        details={"line": stripped[:80]},
                        remediation="Remove print statements or replace with logger.debug()",
                        standard_ref="debug-test-standard.md §5.3 (no debug print in production)",
                        confidence=0.85,
                    ))

            # ─── TD_TF_004: AAA pattern check (Arrange/Act/Assert) ───
            has_arrange = any("# Arrange" in l or "// Arrange" in l or "/* Arrange" in l for l in lines)
            has_act = any("# Act" in l or "// Act" in l or "/* Act" in l for l in lines)
            has_assert = any("# Assert" in l or "// Assert" in l or "/* Assert" in l for l in lines)
            if has_test_func and not (has_arrange and has_act and has_assert):
                findings.append(AuditFinding(
                    category="test_debug", severity="low", file=file_path,
                    line=1, code="CA_TD_004",
                    message="Test file missing AAA pattern comments (# Arrange / # Act / # Assert)",
                    details={"file": fp.name, "has_arrange": has_arrange, "has_act": has_act, "has_assert": has_assert},
                    remediation="Structure each test with '# Arrange', '# Act', '# Assert' comment sections",
                    standard_ref="debug-test-standard.md §3.2",
                    confidence=0.6,
                ))

        return findings

    # ═══════════════════════════════════════════════════════════════
    # CODIFICATION COMPLIANCE — ~/.aicoders/rules/standards/codification-standard.md
    # ═══════════════════════════════════════════════════════════════

    def _check_codification(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        fp = Path(file_path)
        fname = fp.name.lower()
        fp_lower = str(fp).lower().replace("\\", "/")
        is_model = any(kw in fp_lower for kw in ["/models/", "/entities/", "/dtos/", "/schemas/"])

        # ─── CA_COD_001: Raw UUID v4 in API response / user-facing code ───
        if "uuid4" in content or "uuid.uuid4" in content or "Uuid::uuid4" in content:
            for i, line in enumerate(lines, 1):
                if re.search(r"(uuid4|uuid\.uuid4|Uuid::uuid4)", line):
                    findings.append(AuditFinding(
                        category="codification", severity="high", file=file_path,
                        line=i, code="CA_COD_001",
                        message="Using UUID v4 instead of UUID v7 — v4 causes index fragmentation and lacks timestamp",
                        details={"line": line.strip()[:80]},
                        remediation="Replace uuid4() with uuid7() for time-sortable, index-friendly identifiers (RFC 9562)",
                        standard_ref="codification-standard.md §2.3.4",
                        confidence=0.9,
                    ))
                    break

        # ─── CA_COD_002: Missing _code suffix for entity code fields ───
        if is_model:
            # Look for code-like field names that don't end with `_code`
            for i, line in enumerate(lines, 1):
                code_field_match = re.search(r'(?:code|ref|id)\s*[=:]\s*["\']([^"\']+)["\']', line)
                if code_field_match:
                    val = code_field_match.group(1)
                    # Check if value looks like a human-readable code (has prefixes, separators)
                    if re.match(r"^[A-Z]{2,6}[-_/]", val):
                        # Look for the field name definition
                        field_line = lines[i-2] if i >= 2 else ""
                        field_name_match = re.search(r'(?:private|public|protected|var|let|const|val|var)\s+\$?(\w+)', field_line)
                        if field_name_match:
                            field_name = field_name_match.group(1)
                            if field_name.endswith("_code") or field_name.endswith("Code") or field_name.endswith("Ref"):
                                pass  # already has proper suffix
                            else:
                                findings.append(AuditFinding(
                                    category="codification", severity="low", file=file_path,
                                    line=i, code="CA_COD_002",
                                    message=f"Field storing human-readable code should end with '_code' suffix, got '{field_name}'",
                                    details={"field": field_name, "value": val[:40]},
                                    remediation=f"Rename field to '{field_name}_code' for consistency with codification standard",
                                    standard_ref="codification-standard.md §3",
                                    confidence=0.6,
                                ))

        # ─── CA_COD_003: Code format pattern detection ───
        # Check if human-readable codes follow {PREFIX}-{ADDITIONAL}-{UNIQUE} template
        for i, line in enumerate(lines, 1):
            if "generate" in line.lower() and ("code" in line.lower() or "reference" in line.lower() or "number" in line.lower()):
                stripped = line.strip()
                if "return" in stripped and "f'" in stripped:
                    # Check if returned code follows the template
                    if not re.search(r"\{.*\}[-_]\{", stripped):
                        findings.append(AuditFinding(
                            category="codification", severity="low", file=file_path,
                            line=i, code="CA_COD_003",
                            message=f"Code generation may not follow '{PREFIX}-{ADDITIONAL}-{UNIQUE}' format",
                            details={"line": stripped[:80]},
                            remediation="Use format: {PREFIX}-{ENTITY}/{DEPARTMENT}/{YYYY}/{MM}-{SEQUENCE:04d} per codification standard §3.2",
                            standard_ref="codification-standard.md §3.2",
                            confidence=0.5,
                        ))

        # ─── CA_COD_004: Dual Identity Architecture — check for UUID + code pattern ───
        if is_model or any(kw in fp_lower for kw in ["/repositories/", "/services/"]):
            has_uuid_field = bool(re.search(r"uuid|guid\s*[=:]", content, re.IGNORECASE))
            has_code_field = bool(re.search(r"_code\s*[=:]", content))
            if has_uuid_field and not has_code_field:
                findings.append(AuditFinding(
                    category="codification", severity="medium", file=file_path,
                    line=1, code="CA_COD_004",
                    message=f"Entity has UUID but no human-readable code field — violates Dual Identity Architecture",
                    details={"file": fname},
                    remediation="Add a human-readable code field (e.g., <entity>_code) alongside the UUID system ID",
                    standard_ref="codification-standard.md §1.4 (P1)",
                    confidence=0.7,
                ))

        # ─── CA_COD_005: Auto-increment ID as public ID ───
        if is_model or any(kw in fname for kw in ["migration", "schema", "model", "entity"]):
            for i, line in enumerate(lines, 1):
                if re.search(r"(?:autoIncrement|autoincrement|AUTO_INCREMENT|increments|Serial)\s*[\(\]\s]", line, re.IGNORECASE):
                    findings.append(AuditFinding(
                        category="codification", severity="medium", file=file_path,
                        line=i, code="CA_COD_005",
                        message=f"Auto-increment integer ID detected — security risk (enumeration attack), use UUID v7 instead",
                        details={"line": line.strip()[:80]},
                        remediation="Replace auto-increment PK with UUID v7 primary key; keep auto-increment only as internal row identifier",
                        standard_ref="codification-standard.md §2.3.1",
                        confidence=0.8,
                    ))
                    break

        # ─── CA_COD_006: UUID v7 usage check for entity IDs ───
        if is_model:
            has_id_field = bool(re.search(r"(?:id|Id|ID)\s*[=:]\s*[Uu]uid", content))
            has_uuid_v7 = bool(re.search(r"uuid7|uuid_utils\.uuid7|Uuid::uuid7|uuid_generate_v7", content))
            if has_id_field and not has_uuid_v7 and "uuid4" not in content:
                # ID references UUID but doesn't specify v7 — soft warning
                pass  # too speculative

        return findings

    # ═══════════════════════════════════════════════════════════════
    # CODING NAMING CONVENTION — ~/.aicoders/rules/standards/coding-standard.md §2-5
    # ═══════════════════════════════════════════════════════════════

    def _check_coding_naming(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        findings = []
        fp = Path(file_path)
        fname = fp.name.lower()
        fp_lower = str(fp).lower().replace("\\", "/")

        # Detect stack from file extension and content
        if fp.suffix == ".py":
            stack = "python"
        elif fp.suffix in (".js", ".ts", ".jsx", ".tsx"):
            stack = "typescript"
        elif fp.suffix == ".go":
            stack = "go"
        elif fp.suffix in (".php",):
            stack = "php"
        elif fp.suffix in (".java",):
            stack = "java"
        elif fp.suffix in (".kt", ".kts"):
            stack = "kotlin"
        elif fp.suffix in (".cs",):
            stack = "csharp"
        elif fp.suffix in (".rs",):
            stack = "rust"
        elif fp.suffix in (".dart",):
            stack = "dart"
        elif fp.suffix in (".swift",):
            stack = "swift"
        elif fp.suffix in (".css", ".scss", ".less"):
            stack = "css"
        else:
            stack = "unknown"

        # ─── CA_CNAM_001: Directory naming per stack (§2) ───
        parent_dir = fp.parent.name if fp.parent else ""
        if parent_dir:
            if stack in ("python", "rust", "dart", "go") and parent_dir != parent_dir.lower():
                findings.append(AuditFinding(
                    category="coding_naming", severity="low", file=file_path,
                    line=1, code="CA_CNAM_001",
                    message=f"Directory '{parent_dir}' should be snake_case for {stack} stack (§2)",
                    details={"directory": parent_dir, "expected": parent_dir.lower(), "stack": stack},
                    remediation=f"Rename directory to '{parent_dir.lower()}' to follow {stack} convention",
                    standard_ref="coding-standard.md §2",
                    confidence=0.7,
                ))
            elif stack in ("php", "csharp", "swift") and parent_dir[0].islower():
                findings.append(AuditFinding(
                    category="coding_naming", severity="low", file=file_path,
                    line=1, code="CA_CNAM_001",
                    message=f"Directory '{parent_dir}' should be PascalCase for {stack} stack (§2)",
                    details={"directory": parent_dir, "expected": parent_dir[0].upper() + parent_dir[1:], "stack": stack},
                    remediation=f"Rename directory to '{parent_dir[0].upper() + parent_dir[1:]}' to follow {stack} convention",
                    standard_ref="coding-standard.md §2",
                    confidence=0.7,
                ))
            elif stack in ("typescript",) and "-" not in parent_dir and "_" in parent_dir:
                findings.append(AuditFinding(
                    category="coding_naming", severity="low", file=file_path,
                    line=1, code="CA_CNAM_001",
                    message=f"Directory '{parent_dir}' should be kebab-case for {stack} stack (§2)",
                    details={"directory": parent_dir, "expected": parent_dir.replace("_", "-"), "stack": stack},
                    remediation=f"Rename directory to '{parent_dir.replace('_', '-')}' to follow {stack} convention",
                    standard_ref="coding-standard.md §2",
                    confidence=0.6,
                ))

        # ─── CA_CNAM_002: Interface naming (§3) ───
        has_interface_defs = False
        for i, line in enumerate(lines, 1):
            # Check for interface/abstract class definitions
            if stack in ("python", "typescript", "go", "dart"):
                interface_match = re.search(r"class\s+(\w+Interface)", line)
                if interface_match:
                    has_interface_defs = True
                # Check if interface exists but doesn't follow convention
                proto_match = re.search(r"class\s+(\w+).*\(.*Protocol|class\s+(\w+).*\(.*ABC", line)
                if proto_match:
                    has_interface_defs = True
            elif stack in ("java", "csharp", "kotlin"):
                interface_match = re.search(r"interface\s+(\w+)", line)
                if interface_match:
                    name = interface_match.group(1)
                    if not name.startswith("I") and not name.endswith("Interface"):
                        findings.append(AuditFinding(
                            category="coding_naming", severity="low", file=file_path,
                            line=i, code="CA_CNAM_002",
                            message=f"Interface '{name}' should use 'I' prefix or 'Interface' suffix (§3)",
                            details={"interface": name},
                            remediation=f"Rename to 'I{name}' or '{name}Interface'",
                            standard_ref="coding-standard.md §3",
                            confidence=0.8,
                        ))
                    has_interface_defs = True

        # ─── CA_CNAM_003: Abstract class naming (§3) ───
        for i, line in enumerate(lines, 1):
            abs_match = re.search(r"(?:abstract class|class\s+\w+.*\(.*ABC|class\s+\w+.*\[.*Abstract)", line)
            if abs_match:
                cls_name = abs_match.group(0).replace("abstract class ", "").replace("class ", "").strip()
                cls_name = re.split(r"[\(\[]", cls_name)[0].strip()
                if not cls_name.startswith("Abstract"):
                    findings.append(AuditFinding(
                        category="coding_naming", severity="low", file=file_path,
                        line=i, code="CA_CNAM_003",
                        message=f"Abstract class '{cls_name}' should use 'Abstract' prefix (§3)",
                        details={"class": cls_name},
                        remediation=f"Rename to 'Abstract{cls_name}'",
                        standard_ref="coding-standard.md §3",
                        confidence=0.7,
                    ))

        # ─── CA_CNAM_004: Constants in UPPER_SNAKE_CASE (§5) ───
        for i, line in enumerate(lines, 1):
            if "const" in line or "final" in line or "CONST" in line:
                const_match = re.search(r"(?:const|let|val|final)\s+(\w+)\s*[=:]", line)
                if const_match:
                    name = const_match.group(1)
                    if (fname.endswith((".py", ".js", ".ts", ".rs", ".dart", ".go"))
                            and not re.match(r"^_*[A-Z][A-Z0-9_]*$", name)
                            and name.upper() != name.lower()):
                        # It's a const but not UPPER_SNAKE_CASE — flag it
                        findings.append(AuditFinding(
                            category="coding_naming", severity="low", file=file_path,
                            line=i, code="CA_CNAM_004",
                            message=f"Constant '{name}' should be UPPER_SNAKE_CASE (§5)",
                            details={"constant": name},
                            remediation=f"Rename to '{re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', '_', name).upper()}'",
                            standard_ref="coding-standard.md §5",
                            confidence=0.6,
                        ))

        # ─── CA_CNAM_005: JSON/YAML keys in snake_case (§5) ───
        if fname.endswith((".json", ".yaml", ".yml")):
            try:
                data = json.loads(content) if fname.endswith(".json") else {}
                if isinstance(data, dict):
                    for key in data.keys():
                        if "-" in key and key[0].islower():
                            findings.append(AuditFinding(
                                category="coding_naming", severity="low", file=file_path,
                                line=1, code="CA_CNAM_005",
                                message=f"JSON key '{key}' should be snake_case, not kebab-case (§5)",
                                details={"key": key, "expected": key.replace("-", "_")},
                                remediation=f"Rename key to '{key.replace('-', '_')}'",
                                standard_ref="coding-standard.md §5",
                                confidence=0.85,
                            ))
            except (json.JSONDecodeError, ValueError):
                pass

        # ─── CA_CNAM_006: Private/protected method prefix (§4) ───
        for i, line in enumerate(lines, 1):
            if stack in ("python", "typescript", "dart", "php", "kotlin", "java"):
                # Should use _ prefix for private/protected
                pass  # Complex to detect accurately

        return findings

    # ═══════════════════════════════════════════════════════════════

    def _check_semver_project(self, root: Path, files: List[Path]) -> List[AuditFinding]:
        findings = []
        file_names = {f.name.lower(): f for f in files}

        # CA_SEM_001 (project-level): .version file missing
        version_files = {".version", "version", "version.txt", "version_current"}
        found = version_files & file_names.keys()
        if not found:
            findings.append(AuditFinding(
                category="semver", severity="high", file=str(root),
                line=1, code="CA_SEM_001",
                message="No .version file found at project root — every project MUST have a version file",
                details={"root": str(root)},
                remediation="Create .version file with SemVer string: echo '1.0.0' > .version",
                standard_ref="semantic-versioning.md §5.1",
                confidence=0.95,
            ))

        # CA_SEM_004: Missing checksums (.sha256) for release artifacts
        releases_dir = root / "releases"
        if releases_dir.is_dir():
            release_artifacts = []
            for f in files:
                if releases_dir in f.parents:
                    release_exts = {".exe", ".msi", ".apk", ".aab", ".ipa", ".dmg", ".deb", ".rpm", ".appimage"}
                    if f.suffix.lower() in release_exts or f.name.endswith(".tar.gz") or f.name.endswith(".tar.bz2"):
                        release_artifacts.append(f)

            for artifact in release_artifacts:
                sha_file = artifact.parent / (artifact.name + ".sha256")
                if not sha_file.exists():
                    findings.append(AuditFinding(
                        category="semver", severity="medium", file=str(artifact),
                        line=1, code="CA_SEM_004",
                        message=f"Release artifact '{artifact.name}' missing checksum file (.sha256)",
                        details={"artifact": artifact.name},
                        remediation=f"Generate checksum: certutil -hashfile {artifact.name} SHA256 > {artifact.name}.sha256",
                        standard_ref="semantic-versioning.md §7.4 (rule 6)",
                        confidence=0.9,
                    ))

        return findings

    # ═══════════════════════════════════════════════════════════════
    # PROJECT-LEVEL PWA CHECKS
    # ═══════════════════════════════════════════════════════════════

    def _check_pwa_project(self, root: Path, files: List[Path]) -> List[AuditFinding]:
        findings = []
        file_names = {f.name.lower(): f for f in files}
        dir_paths = {str(f.relative_to(root)).lower().split("\\")[0].split("/")[0] for f in files if root in f.parents}

        # Only run PWA checks if project looks like a web app
        has_web_files = any(
            f.suffix in (".html", ".js", ".ts", ".jsx", ".tsx", ".css")
            for f in files
        )
        if not has_web_files:
            return findings

        # CA_PWA_002: Missing manifest file
        manifest_files = {"manifest.json", "site.webmanifest", "manifest.webmanifest", "pwa.config.ts", "manifest.ts", "manifest.py", "manifest.go", "manifest.java"}
        found_manifest = manifest_files & file_names.keys()
        if not found_manifest:
            findings.append(AuditFinding(
                category="pwa", severity="high", file=str(root),
                line=1, code="CA_PWA_002",
                message="No Web App Manifest file found — PWA requires manifest.json or manifest.webmanifest",
                details={"root": str(root)},
                remediation="Add manifest.json with name, short_name, start_url, display, background_color, theme_color, icons",
                standard_ref="pwa-standard.md §3.2",
                confidence=0.9,
            ))

        # CA_PWA_005: PWA icons directory
        icon_dirs = {"icons", "assets/icons", "static/icons", "public/icons"}
        has_icon_dir = any(
            any(str(f).lower().replace("\\", "/").startswith(d) for d in icon_dirs)
            for f in files
        )
        if not has_icon_dir:
            findings.append(AuditFinding(
                category="pwa", severity="low", file=str(root),
                line=1, code="CA_PWA_005",
                message="No PWA icons directory found — required: 72x72 to 512x512 icon sizes",
                details={"root": str(root)},
                remediation="Create icons/ directory with at least 192x192 and 512x512 PNG icons",
                standard_ref="pwa-standard.md §3.2, §10",
                confidence=0.8,
            ))

        # CA_PWA_010: Offline page
        offline_files = {"offline.html", "offline.tsx", "offline.jsx", "offline.vue"}
        found_offline = offline_files & file_names.keys()
        if not found_offline:
            findings.append(AuditFinding(
                category="pwa", severity="medium", file=str(root),
                line=1, code="CA_PWA_010",
                message="No offline page found — PWA MUST provide offline experience",
                details={"root": str(root)},
                remediation="Create offline.html with offline-friendly UI and register it in service worker cache",
                standard_ref="pwa-standard.md §10",
                confidence=0.75,
            ))

        return findings

    # ═══════════════════════════════════════════════════════════════
    # PROJECT-LEVEL TEST/DEBUG CHECKS
    # ═══════════════════════════════════════════════════════════════

    def _check_test_debug_project(self, root: Path, files: List[Path]) -> List[AuditFinding]:
        findings = []
        dir_names = {d.name.lower(): d for d in root.iterdir() if d.is_dir()} if root.is_dir() else {}
        file_names = {f.name.lower(): f for f in files}
        rel_dirs = {str(d.relative_to(root)).lower().replace("\\", "/"): d for d in root.rglob("*") if d.is_dir()} if root.is_dir() else {}

        # ─── TD_DIR_001: Missing tests/ directory ───
        if "tests" not in dir_names:
            findings.append(AuditFinding(
                category="test_debug", severity="medium", file=str(root),
                line=1, code="CA_TD_005",
                message="Missing 'tests/' directory at project root",
                details={"root": str(root)},
                remediation="Create tests/ directory with unit/, integration/, security/ subdirectories",
                standard_ref="debug-test-standard.md §3.3",
                confidence=0.95,
            ))
        else:
            tests_dir = root / "tests"
            # ─── TD_DIR_004: Test type subdirectories ───
            test_subdirs = {d.name.lower() for d in tests_dir.iterdir() if d.is_dir()}
            required_test_subdirs = ["unit", "integration", "security"]
            for req in required_test_subdirs:
                if req not in test_subdirs:
                    findings.append(AuditFinding(
                        category="test_debug", severity="low", file=str(root),
                        line=1, code="CA_TD_006",
                        message=f"Missing 'tests/{req}/' subdirectory — tests should be organized by type",
                        details={"missing_dir": f"tests/{req}"},
                        remediation=f"Create tests/{req}/ directory and move relevant tests there",
                        standard_ref="debug-test-standard.md §3.3",
                        confidence=0.8,
                    ))

        # ─── TD_DIR_002: Missing outputs/tests/ directory ───
        if "outputs/tests" not in rel_dirs:
            findings.append(AuditFinding(
                category="test_debug", severity="low", file=str(root),
                line=1, code="CA_TD_007",
                message="Missing 'outputs/tests/' directory — test output artifacts must be stored here",
                details={"root": str(root)},
                remediation="Create outputs/tests/ directory for test run artifacts (coverage, reports)",
                standard_ref="debug-test-standard.md §0.1",
                confidence=0.8,
            ))

        # ─── TD_DIR_003: Missing outputs/debugs/ directory ───
        if "outputs/debugs" not in rel_dirs:
            findings.append(AuditFinding(
                category="test_debug", severity="low", file=str(root),
                line=1, code="CA_TD_008",
                message="Missing 'outputs/debugs/' directory — debug artifacts must be stored here",
                details={"root": str(root)},
                remediation="Create outputs/debugs/ directory with memory/, traces/, dumps/ subdirectories",
                standard_ref="debug-test-standard.md §0.1",
                confidence=0.8,
            ))

        return findings

    # ═══════════════════════════════════════════════════════════════
    # COMMENT TAGS
    # ═══════════════════════════════════════════════════════════════

    def _find_comment_tags(self, content: str, file_path: str, lines: Optional[List[str]] = None) -> List[AuditFinding]:
        findings = []
        tag_patterns = [
            (r"(?i)\bTODO\s*:", "high", "CA_CMT_001", "Unfinished task"),
            (r"(?i)\bFIXME\s*:", "critical", "CA_CMT_002", "Known bug"),
            (r"(?i)\bHACK\s*:", "medium", "CA_CMT_003", "Temporary workaround"),
            (r"(?i)\bXXX\s*:", "high", "CA_CMT_004", "Deprecated code"),
            (r"(?i)\bSTUB\s*:", "high", "CA_CMT_005", "Placeholder implementation"),
            (r"(?i)\bWIP\s*:", "medium", "CA_CMT_006", "Work in progress"),
            (r"(?i)\bBUG\s*:", "critical", "CA_CMT_007", "Known bug"),
        ]
        if not content:
            return findings
        if lines is None:
            lines = content.splitlines()
        for pattern, severity, code, desc in tag_patterns:
            for m in re.finditer(pattern, content):
                line_num = content[:m.start()].count("\n") + 1
                findings.append(AuditFinding(
                    category="comments", severity=severity, file=file_path,
                    line=line_num, code=code,
                    message=f"Comment tag {m.group().strip()}: {desc}",
                    details={"tag": m.group().strip()},
                    remediation=f"Address or remove this {m.group().strip()} marker",
                    standard_ref="coding-standard.md (zero-placeholder policy)",
                    confidence=0.95,
                ))

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped in ('"""', "'''", '///') and i > 1:
                prev = lines[i - 2].strip() if i >= 2 else ""
                if not prev.startswith(("def ", "class ", "async ", "function ")):
                    findings.append(AuditFinding(
                        category="comments", severity="medium", file=file_path,
                        line=i, code="CA_CMT_008",
                        message="Empty/placeholder docstring detected",
                        details={"line_content": stripped},
                        remediation="Fill in docstring with description, @param, @return",
                        standard_ref="coding-standard.md §1 (zero-placeholder policy)",
                        confidence=0.9,
                    ))

        return findings

    # ═══════════════════════════════════════════════════════════════
    # ARCHITECTURAL PATTERNS
    # ═══════════════════════════════════════════════════════════════

    def _check_architecture(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        """Detect architectural patterns and anti-patterns."""
        findings = []
        ext = Path(file_path).suffix.lower()

        # Only check relevant file types
        if ext not in (".py", ".js", ".ts", ".java", ".cs"):
            return findings

        # ─── ARCH_001: Circular import detection ───
        if ext == ".py":
            import_patterns = [
                r"^from\s+(\S+)\s+import",
                r"^import\s+(\S+)",
            ]
            imports = []
            for i, line in enumerate(lines, 1):
                for pattern in import_patterns:
                    match = re.search(pattern, line)
                    if match:
                        imports.append((i, match.group(1)))

            # Check for suspicious patterns that might indicate circular deps
            file_module = Path(file_path).stem
            for line_no, imp in imports:
                if file_module in imp or imp in file_module:
                    findings.append(AuditFinding(
                        category="architecture", severity="medium", file=file_path,
                        line=line_no, code="CA_ARCH_001",
                        message=f"Potential circular dependency: importing '{imp}' which may reference this module",
                        details={"import": imp, "file_module": file_module},
                        remediation="Review import structure; consider using dependency injection or moving shared code to a common module",
                        standard_ref="modular-standard.md §2 (Dependency Management)",
                        confidence=0.6,
                    ))

        # ─── ARCH_002: Service Locator pattern detection ───
        service_locator_patterns = [
            r"ServiceLocator\.get",
            r"Container\.resolve",
            r"get_instance\(",
            r"ServiceProvider\.get",
        ]
        for pattern in service_locator_patterns:
            for m in re.finditer(pattern, content):
                line_no = content[:m.start()].count("\n") + 1
                findings.append(AuditFinding(
                    category="architecture", severity="low", file=file_path,
                    line=line_no, code="CA_ARCH_002",
                    message="Service Locator pattern detected — prefer explicit dependency injection",
                    details={"pattern": pattern},
                    remediation="Replace service locator with constructor injection for better testability",
                    standard_ref="modular-standard.md §3 (DI/IoC)",
                    confidence=0.7,
                ))

        # ─── ARCH_003: High coupling indicator — many imports ───
        if ext == ".py":
            import_count = len([l for l in lines if re.match(r"^(import|from)\s+", l.strip())])
            if import_count > 20:
                findings.append(AuditFinding(
                    category="architecture", severity="low", file=file_path,
                    line=1, code="CA_ARCH_003",
                    message=f"High coupling indicator: {import_count} imports detected — consider splitting module",
                    details={"import_count": import_count, "threshold": 20},
                    remediation="Split large module into smaller, focused modules with single responsibility",
                    standard_ref="modular-standard.md §1 (Single Responsibility)",
                    confidence=0.6,
                ))

        # ─── ARCH_004: Framework coupling in domain logic ───
        framework_imports = [
            (r"from\s+django", "Django"),
            (r"from\s+flask", "Flask"),
            (r"from\s+fastapi", "FastAPI"),
            (r"from\s+spring", "Spring"),
            (r"import\s+react", "React"),
        ]
        for pattern, fw in framework_imports:
            if re.search(pattern, content, re.IGNORECASE):
                # Check if file appears to be in domain/service layer
                if any(x in file_path.lower() for x in ["service", "domain", "model", "entity"]):
                    findings.append(AuditFinding(
                        category="architecture", severity="medium", file=file_path,
                        line=1, code="CA_ARCH_004",
                        message=f"Framework coupling in domain layer: {fw} imports detected",
                        details={"framework": fw, "layer": "domain/service"},
                        remediation="Extract framework-agnostic interfaces; move framework code to adapters/infrastructure layer",
                        standard_ref="clean-architecture (Dependency Rule)",
                        confidence=0.75,
                    ))

        # ─── ARCH_005: Repository pattern detection (positive) ───
        repository_pattern = r"class\s+\w+Repository\s*[(:]"
        if re.search(repository_pattern, content):
            findings.append(AuditFinding(
                category="architecture", severity="low", file=file_path,
                line=1, code="CA_ARCH_005",
                message="Repository pattern detected — good data access abstraction",
                details={"pattern": "Repository", "type": "positive"},
                remediation="None required — maintain repository abstraction for data access",
                standard_ref="repository-pattern (Domain-Driven Design)",
                confidence=0.8,
            ))

        # ─── ARCH_006: Service layer pattern detection (positive) ───
        service_pattern = r"class\s+\w+Service\s*[(:]"
        if re.search(service_pattern, content):
            findings.append(AuditFinding(
                category="architecture", severity="low", file=file_path,
                line=1, code="CA_ARCH_006",
                message="Service pattern detected — good use case encapsulation",
                details={"pattern": "Service", "type": "positive"},
                remediation="None required — maintain service layer for business logic",
                standard_ref="service-layer-pattern (Domain-Driven Design)",
                confidence=0.8,
            ))

        return findings

    # ═══════════════════════════════════════════════════════════════
    # SYNTAX ERROR DETECTION (NEW - 10/10 AI Coder Impact)
    # ═══════════════════════════════════════════════════════════════

    def _check_syntax(self, content: str, file_path: str, lines: List[str]) -> List[AuditFinding]:
        """Detect syntax errors: unclosed brackets, bad indent, missing semicolons, etc."""
        findings = []
        ext = Path(file_path).suffix.lower()

        # Skip binary or non-code files
        if ext not in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".cs", ".go", ".rs", ".rb", ".php"):
            return findings

        # ─── SYNTAX_001: Unclosed brackets ───
        bracket_pairs = {
            '{': '}', '[': ']', '(': ')', '<': '>'
        }
        closing_brackets = set(bracket_pairs.values())

        stack = []
        in_string = False
        string_char = None

        for line_no, line in enumerate(lines, 1):


            for i, char in enumerate(line):
                # Handle strings
                if char in ('"', "'", '`') and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
                    continue

                if in_string:
                    continue

                # Track brackets
                if char in bracket_pairs:
                    stack.append((char, line_no, i))
                elif char in closing_brackets:
                    if stack:
                        last_open, _, _ = stack[-1]
                        if bracket_pairs.get(last_open) == char:
                            stack.pop()
                        else:
                            # Mismatched bracket
                            findings.append(AuditFinding(
                                category="syntax", severity="critical", file=file_path,
                                line=line_no, column=i, code="CA_SYN_001",
                                message=f"Mismatched bracket: expected '{bracket_pairs.get(last_open, '?')}' but found '{char}'",
                                details={"expected": bracket_pairs.get(last_open), "found": char, "line_content": line.strip()},
                                remediation=f"Fix the bracket mismatch on line {line_no}",
                                standard_ref="syntax-standard (Bracket Matching)",
                                confidence=0.95,
                                auto_fix_available=False,  # Complex to auto-fix
                            ))
                    else:
                        # Unmatched closing bracket
                        findings.append(AuditFinding(
                            category="syntax", severity="critical", file=file_path,
                            line=line_no, column=i, code="CA_SYN_002",
                            message=f"Unmatched closing bracket '{char}'",
                            details={"bracket": char, "line_content": line.strip()},
                            remediation=f"Remove extra '{char}' or add matching opening bracket",
                            standard_ref="syntax-standard (Bracket Matching)",
                            confidence=0.95,
                        ))

        # Report unclosed brackets at end of file
        for open_bracket, open_line, open_col in stack:
            findings.append(AuditFinding(
                category="syntax", severity="critical", file=file_path,
                line=open_line, column=open_col, code="CA_SYN_003",
                message=f"Unclosed bracket '{open_bracket}' - missing '{bracket_pairs[open_bracket]}'",
                details={"open_bracket": open_bracket, "expected_close": bracket_pairs[open_bracket], "opened_at_line": open_line},
                remediation=f"Add missing '{bracket_pairs[open_bracket]}' to close the bracket opened on line {open_line}",
                standard_ref="syntax-standard (Bracket Matching)",
                confidence=0.95,
                auto_fix_available=True,
                auto_fix_code=f"{open_bracket}...{bracket_pairs[open_bracket]}",
                auto_fix_description=f"Add missing closing '{bracket_pairs[open_bracket]}'",
            ))

        # ─── SYNTAX_002: Mixed indentation (tabs and spaces) ───
        if ext == ".py":
            has_tabs = False
            has_spaces = False
            for line_no, line in enumerate(lines, 1):
                if line.startswith('\t'):
                    has_tabs = True
                elif line.startswith(' '):
                    has_spaces = True

                if has_tabs and has_spaces:
                    findings.append(AuditFinding(
                        category="syntax", severity="high", file=file_path,
                        line=line_no, column=0, code="CA_SYN_004",
                        message="Mixed indentation detected: file uses both tabs and spaces",
                        details={"issue": "mixed_indentation", "recommendation": "Use 4 spaces for Python"},
                        remediation="Convert all indentation to spaces (PEP 8 recommends 4 spaces)",
                        standard_ref="pep8 (Indentation)",
                        confidence=0.9,
                    ))
                    break

        # ─── SYNTAX_003: Trailing whitespace ───
        for line_no, line in enumerate(lines, 1):
            if line.rstrip() != line:
                findings.append(AuditFinding(
                    category="syntax", severity="low", file=file_path,
                    line=line_no, column=len(line.rstrip()), code="CA_SYN_005",
                    message="Trailing whitespace detected",
                    details={"trailing_chars": repr(line[len(line.rstrip()):])},
                    remediation="Remove trailing whitespace",
                    standard_ref="coding-standard (Whitespace)",
                    confidence=0.99,
                    auto_fix_available=True,
                    auto_fix_code=line.rstrip(),
                    auto_fix_description="Remove trailing whitespace from line",
                ))

        # ─── SYNTAX_004: Missing semicolons (JS/C-like) ───
        if ext in (".js", ".ts", ".jsx", ".tsx", ".c", ".cpp", ".java", ".cs"):
            for line_no, line in enumerate(lines, 1):
                stripped = line.strip()
                # Check lines that look like statements but missing semicolon
                if (stripped and
                    not stripped.startswith(('//', '/*', '*', '#', '{', '}', 'if', 'for', 'while', 'switch', 'class', 'function', 'return')) and
                    not stripped.endswith((';', '{', '}', '//', '/*', '*/')) and
                    not stripped.startswith('//')):

                    # Check if it's likely a statement needing semicolon
                    statement_patterns = [
                        r'^\s*\w+\s*=\s*.+[^;{*/\]]$',  # Assignment
                        r'^\s*\w+\([^)]*\)[^{;]*$',      # Function call
                        r'^\s*\w+\s+\w+\s*[^;{(]*$',    # Declaration
                    ]

                    for pattern in statement_patterns:
                        if re.match(pattern, stripped):
                            findings.append(AuditFinding(
                                category="syntax", severity="medium", file=file_path,
                                line=line_no, column=len(stripped), code="CA_SYN_006",
                                message="Potentially missing semicolon",
                                details={"line_content": stripped[:50]},
                                remediation="Add semicolon at end of statement",
                                standard_ref="javascript-standard / c-standard (Statements)",
                                confidence=0.7,
                                auto_fix_available=True,
                                auto_fix_code=f"{stripped};",
                                auto_fix_description="Add semicolon at end of line",
                            ))
                            break

        # ─── SYNTAX_005: Unclosed quotes/strings ───
        for line_no, line in enumerate(lines, 1):
            for quote in ('"', "'"):
                count = line.count(quote)
                # Simple check: odd number of unescaped quotes
                escaped_count = line.count(f'\\{quote}')
                actual_count = count - escaped_count
                if actual_count % 2 != 0:
                    findings.append(AuditFinding(
                        category="syntax", severity="critical", file=file_path,
                        line=line_no, column=line.find(quote), code="CA_SYN_007",
                        message=f"Potentially unclosed string quote ({quote})",
                        details={"quote": quote, "count": actual_count, "line_content": line.strip()[:50]},
                        remediation=f"Close the string with matching {quote} or escape with \\\\{quote}",
                        standard_ref="syntax-standard (String Literals)",
                        confidence=0.85,
                    ))

        # ─── SYNTAX_006: Blank lines with whitespace ───
        for line_no, line in enumerate(lines, 1):
            if line.strip() == '' and line != '':
                findings.append(AuditFinding(
                    category="syntax", severity="low", file=file_path,
                    line=line_no, column=0, code="CA_SYN_008",
                    message="Blank line contains whitespace",
                    details={"whitespace": repr(line)},
                    remediation="Remove whitespace from blank line",
                    standard_ref="coding-standard (Whitespace)",
                    confidence=0.99,
                    auto_fix_available=True,
                    auto_fix_code="",
                    auto_fix_description="Remove all whitespace from blank line",
                ))

        return findings

    # ═══════════════════════════════════════════════════════════════
    # SUMMARY & SCORING
    # ═══════════════════════════════════════════════════════════════

    def _build_summary(self, findings: List[AuditFinding]) -> Dict[str, int]:
        summary = {}
        for f in findings:
            sev = f.severity
            summary[sev] = summary.get(sev, 0) + 1
        return summary

    def _calc_compliance_score(self, summary: Dict[str, int], findings: List[AuditFinding]) -> int:
        score = 100
        score -= summary.get("critical", 0) * 15
        score -= summary.get("high", 0) * 10
        score -= summary.get("medium", 0) * 5
        score -= summary.get("low", 0) * 2
        return max(0, min(100, score))

    def _build_recommendations(self, findings: List[AuditFinding]) -> Dict[str, Any]:
        gitignore = set()
        rotate = set()
        for f in findings:
            if f.severity in ("critical", "high"):
                if f.category == "secrets":
                    rotate.add(f.file)
                gitignore.add(Path(f.file).name)
        return {
            "gitignore_entries": sorted(gitignore),
            "secrets_to_rotate": list(rotate),
        }

    def _generate_auto_fixes(self, findings: List[AuditFinding]) -> List[AuditFinding]:
        """Generate auto-fix suggestions for applicable findings (10/10 AI coder impact)."""
        for finding in findings:
            # Auto-fix for simple naming convention issues
            if finding.category == "naming" and finding.code == "CA_NAM_001":
                # PascalCase violation - suggest fix
                old_name = finding.details.get("name", "")
                if old_name:
                    new_name = self._to_pascal_case(old_name)
                    finding.auto_fix_available = True
                    finding.auto_fix_code = new_name
                    finding.auto_fix_description = f"Rename '{old_name}' to '{new_name}'"

            # Auto-fix for missing type hints
            elif finding.category == "type_hints" and "Missing type hint" in finding.message:
                func_name = finding.details.get("function", "")
                if func_name:
                    finding.auto_fix_available = True
                    finding.auto_fix_code = f"def {func_name}(...) -> Any:"
                    finding.auto_fix_description = "Add '-> Any' return type annotation"

            # Auto-fix for bare except
            elif finding.category == "error_handling" and finding.code == "CA_ERR_001":
                finding.auto_fix_available = True
                finding.auto_fix_code = "except Exception:"
                finding.auto_fix_description = "Replace 'except:' with 'except Exception:'"

            # Auto-fix for debug mode
            elif finding.category == "misconfig" and "DEBUG = True" in finding.message:
                finding.auto_fix_available = True
                finding.auto_fix_code = "DEBUG = False"
                finding.auto_fix_description = "Set DEBUG to False for production"

            # Generate diff preview
            if finding.auto_fix_available and finding.auto_fix_code:
                finding.fix_diff = self._generate_fix_diff(finding)

        return findings

    def _to_pascal_case(self, name: str) -> str:
        """Convert snake_case or camelCase to PascalCase."""
        if "_" in name:
            return "".join(word.capitalize() for word in name.split("_"))
        elif name[0].islower():
            return name[0].upper() + name[1:]
        return name

    def _generate_fix_diff(self, finding: AuditFinding) -> str:
        """Generate a unified diff preview of the fix."""
        try:
            if not finding.auto_fix_code:
                return ""

            # Simple diff generation for demonstration
            old_line = finding.context if finding.context else ""
            new_line = finding.auto_fix_code

            return f"--- {finding.file}\n+++ {finding.file}\n@@ -{finding.line},1 +{finding.line},1 @@\n-{old_line}\n+{new_line}"
        except Exception:
            return ""

    def _apply_auto_fixes(self, findings: List[AuditFinding]) -> int:
        """Apply auto-fixes to files. Returns count of applied fixes."""
        applied = 0
        for finding in findings:
            if not finding.auto_fix_available or not finding.auto_fix_code:
                continue

            try:
                file_path = Path(finding.file)
                if not file_path.exists():
                    continue

                content = file_path.read_text(encoding="utf-8")
                lines = content.splitlines()

                if finding.line < 1 or finding.line > len(lines):
                    continue

                # Apply the fix
                line_idx = finding.line - 1
                old_line = lines[line_idx]

                # Simple replacement strategy
                if finding.category == "error_handling":
                    lines[line_idx] = old_line.replace("except:", "except Exception:")
                elif finding.category == "misconfig":
                    lines[line_idx] = old_line.replace("DEBUG = True", "DEBUG = False")

                # Write back
                file_path.write_text("\n".join(lines), encoding="utf-8")
                finding.fix_applied = True
                applied += 1
                logger.info(f"Applied fix to {finding.file}:{finding.line}")

            except Exception as e:
                logger.warning(f"Failed to apply fix to {finding.file}: {e}")

        return applied
