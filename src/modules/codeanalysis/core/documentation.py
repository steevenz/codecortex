"""
Document Intelligence — parses PRDs, ADRs, specs, standards, and implementation plans.

Detects document types from path conventions and content patterns.
Extracts structured metadata: title, sections, requirements, decisions,
referenced files, and version info.

:project: CodeCortex
:package: Modules.Codeanalysis.Core.Documentation
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeAnalysis-v1.0
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("CodeCortex.CodeAnalysis.Documentation")

# ── Document type detection rules ─────────────────────────

DOC_PATTERNS: Dict[str, List[str]] = {
    "prd": [
        r"docs?/prd/", r"\bPRD\.md$", r"\bprd[-_]",
        r"implementation.plan", r"implementation_plan",
        r"feature.requirements", r"requirements\.md$",
    ],
    "adr": [
        r"docs?/adr/", r"\bADR-\d", r"adr[-_]\d",
        r"architecture.decision", r"architectural.decision",
    ],
    "spec": [
        r"docs?/spec/", r"\bspec[-_]", r"\bSPEC-",
        r"specification", r"functional.spec",
    ],
    "standard": [
        r"standard", r"\bSTANDARD", r"guideline",
        r"\bcoding[-_]standard", r"\bapi[-_]standard",
    ],
    "changelog": [
        r"changelog", r"change.log", r"change_log",
        r"whatsnew", r"release.notes",
    ],
    "walkthrough": [
        r"walkthrough", r"walk.through", r"walk_through",
        r"tutorial", r"howto",
    ],
}

# Requirement extraction patterns
REQUIREMENT_PATTERNS = [
    re.compile(r"(?:^|\n)\s*\*\*(?:Requirement|Must|Should|Need)\*\*:\s*(.+?)(?=\n|$)", re.I | re.M),
    re.compile(r"(?:^|\n)\s*[-*]\s*\*\*(?:Requirement|Must|Should|Need)\*\*:\s*(.+?)(?=\n|$)", re.I | re.M),
    re.compile(r"(?:^|\n)\s*\d+\.\s*\*\*(?:Requirement|Must|Should|Need)\*\*:\s*(.+?)(?=\n|$)", re.I | re.M),
    re.compile(r"(?:^|\n)\s*[-*]\s*(?:MUST|SHOULD|REQUIRED)\s+[-–]\s+(.+?)(?=\n|$)", re.M),
    re.compile(r"(?:^|\n)\s*(?:Requirement|Prerequisite)s?:\s*\n((?:\s*[-*]\s*.+\n?)+)", re.I | re.M),
]

# Decision extraction patterns
DECISION_PATTERNS = [
    re.compile(r"(?:^|\n)#+\s*(?:Context|Background)\s*\n(.+?)(?=\n#+\s*(?:Decision|Approach|Solution)\s*\n)", re.I | re.M | re.DOTALL),
    re.compile(r"(?:^|\n)#+\s*(?:Decision|Approach|Solution|Chosen)\s*\n(.+?)(?=\n#+\s*(?:Consequence|Result|Impact|Rationale)\s*\n|\Z)", re.I | re.M | re.DOTALL),
    re.compile(r"(?:^|\n)#+\s*(?:Consequence|Result|Impact|Rationale|Risks?)\s*\n(.+?)(?=\n#+\s|\Z)", re.I | re.M | re.DOTALL),
]

# File reference patterns
FILE_REF_PATTERN = re.compile(r"`([^`]+\.(?:py|js|ts|go|rs|java|kt|cs|rb|php|swift|vue|tsx|jsx|md|yaml|yml|json|toml|cfg|conf|sh|bat|ps1))`")

# Version pattern
VERSION_PATTERN = re.compile(r"\b(\d+\.\d+\.\d+(?:[-_][a-zA-Z0-9]+)?)\b")

# Section heading pattern
SECTION_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)$", re.M)


@dataclass
class DocSection:
    """A single section extracted from a document."""
    heading: str
    level: int
    content: str
    subsections: List["DocSection"] = field(default_factory=list)


@dataclass
class DocRequirement:
    """A requirement extracted from a document."""
    text: str
    source_section: str
    priority: str = "medium"  # high, medium, low, must, should


@dataclass
class DocDecision:
    """An architectural decision extracted from a document."""
    context: str
    decision: str
    consequence: str = ""
    source_section: str = ""


@dataclass
class DocFileRef:
    """A reference to a source code file in documentation."""
    path: str
    context: str = ""


@dataclass
class DocumentArtifact:
    """Complete parsed document with all extracted intelligence."""
    path: str
    title: str
    doc_type: str  # prd, adr, spec, standard, changelog, walkthrough, unknown
    sections: List[DocSection] = field(default_factory=list)
    requirements: List[DocRequirement] = field(default_factory=list)
    decisions: List[DocDecision] = field(default_factory=list)
    referenced_files: List[DocFileRef] = field(default_factory=list)
    version: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "title": self.title,
            "doc_type": self.doc_type,
            "section_count": len(self.sections),
            "requirement_count": len(self.requirements),
            "decision_count": len(self.decisions),
            "referenced_files": [r.path for r in self.referenced_files[:20]],
            "version": self.version,
            "metadata": self.metadata,
        }

    def to_detail_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "title": self.title,
            "doc_type": self.doc_type,
            "sections": [
                {"heading": s.heading, "level": s.level,
                 "content_preview": s.content[:200]}
                for s in self.sections
            ],
            "requirements": [
                {"text": r.text[:200], "priority": r.priority,
                 "source": r.source_section}
                for r in self.requirements
            ],
            "decisions": [
                {"context": d.context[:200], "decision": d.decision[:200],
                 "consequence": d.consequence[:200]}
                for d in self.decisions
            ],
            "referenced_files": [r.path for r in self.referenced_files],
            "version": self.version,
            "metadata": self.metadata,
        }


class DocumentParser:
    """Parses project documentation into structured intelligence.

    Handles: PRDs, ADRs, specs, standards, changelogs, walkthroughs.
    Detects document type by path, extracts sections, requirements,
    decisions, and file references.
    """

    @classmethod
    def parse_file(cls, file_path: str) -> DocumentArtifact:
        """Parse a single document file."""
        path = Path(file_path)
        if not path.exists():
            return DocumentArtifact(
                path=file_path, title="", doc_type="unknown",
                error=f"File not found: {file_path}",
            )

        # Use FormatParser for all supported formats (including binary docs)
        from src.modules.knowledgegraph.adapters.format_parser import FormatParser
        if FormatParser.can_parse(str(path)):
            content, parse_error = FormatParser.extract(str(path))
            if parse_error:
                return DocumentArtifact(
                    path=file_path, title="", doc_type="unknown",
                    error=f"Parse error: {parse_error}",
                )
        else:
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                return DocumentArtifact(
                    path=file_path, title="", doc_type="unknown",
                    error=f"Read error: {e}",
                )

        title = cls._extract_title(content, path)
        doc_type = cls._detect_type(content, str(path))
        sections = cls._extract_sections(content)
        requirements = cls._extract_requirements(content, sections)
        decisions = cls._extract_decisions(content)
        refs = cls._extract_file_refs(content)
        version = cls._extract_version(content)
        metadata = cls._extract_metadata(content, path)

        return DocumentArtifact(
            path=str(path.resolve()),
            title=title,
            doc_type=doc_type,
            sections=sections,
            requirements=requirements,
            decisions=decisions,
            referenced_files=refs,
            version=version,
            metadata=metadata,
        )

    @classmethod
    def scan_directory(
        cls,
        root_path: str,
        max_depth: int = 5,
        include_dirs: Optional[List[str]] = None,
    ) -> Dict[str, List[DocumentArtifact]]:
        """Scan a directory for documentation files.

        Args:
            root_path: Root directory to scan.
            max_depth: Maximum directory depth.
            include_dirs: Specific subdirectories to include (e.g. ["docs", "adr"]).

        Returns:
            Dict of doc_type → [DocumentArtifact, ...]
        """
        root = Path(root_path)
        if not root.exists():
            return {}

        results: Dict[str, List[DocumentArtifact]] = {}
        doc_extensions = {
            ".md", ".rst", ".txt", ".adoc",       # text/markup
            ".csv", ".json", ".log",              # structured text
            ".docx",                               # Word
            ".pdf",                                # PDF
            ".xlsx", ".xls",                      # Excel
            ".pptx", ".ppt",                       # PowerPoint
        }

        # Define search paths
        search_dirs: List[Path] = []
        if include_dirs:
            for d in include_dirs:
                target = root / d
                if target.exists() and target.is_dir():
                    search_dirs.append(target)
        else:
            # Auto-detect common doc directories
            for candidate in [
                "docs", "doc", "documentation", "adr", "specs",
                "proposals", "rfcs", "design", "wiki",
            ]:
                target = root / candidate
                if target.exists() and target.is_dir():
                    search_dirs.append(target)
            search_dirs.append(root)

        for search_root in search_dirs:
            if not search_root.exists():
                continue
            for fp in search_root.rglob("*"):
                if fp.suffix.lower() not in doc_extensions:
                    continue
                if not fp.is_file():
                    continue
                # Skip hidden files
                if any(p.startswith(".") for p in fp.relative_to(root).parts):
                    continue
                try:
                    artifact = cls.parse_file(str(fp))
                    if artifact.doc_type not in results:
                        results[artifact.doc_type] = []
                    results[artifact.doc_type].append(artifact)
                except Exception as e:
                    logger.debug(f"Failed to parse {fp}: {e}")

        # Sort results by title within each type
        for docs in results.values():
            docs.sort(key=lambda d: d.title)

        return results

    @classmethod
    def get_summary(cls, artifacts: Dict[str, List[DocumentArtifact]]) -> Dict[str, Any]:
        """Get summary statistics for scanned documentation."""
        total = 0
        by_type: Dict[str, int] = {}
        all_refs: Set[str] = set()
        all_reqs = 0
        all_decisions = 0

        for doc_type, docs in artifacts.items():
            by_type[doc_type] = len(docs)
            total += len(docs)
            for d in docs:
                all_refs.update(r.path for r in d.referenced_files)
                all_reqs += len(d.requirements)
                all_decisions += len(d.decisions)

        return {
            "total_documents": total,
            "by_type": by_type,
            "total_requirements": all_reqs,
            "total_decisions": all_decisions,
            "total_referenced_files": len(all_refs),
            "referenced_files": sorted(all_refs)[:30],
            "documents": [
                {"path": d.path, "title": d.title, "doc_type": d.doc_type,
                 "requirements": len(d.requirements), "decisions": len(d.decisions)}
                for docs in artifacts.values() for d in docs
            ],
        }

    # ── Internal helpers ──────────────────────────────────

    @staticmethod
    def _extract_title(content: str, path: Path) -> str:
        """Extract document title from first H1 or filename."""
        m = re.search(r"^#\s+(.+)$", content, re.M)
        if m:
            return m.group(1).strip()
        return path.stem.replace("-", " ").replace("_", " ").title()

    @staticmethod
    def _detect_type(content: str, path: str) -> str:
        """Detect document type from path and content patterns."""
        path_lower = path.lower()

        # Check path patterns first
        for doc_type, patterns in DOC_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, path_lower):
                    return doc_type

        # Fallback: content-based detection
        content_lower = content.lower()
        if any(kw in content_lower for kw in ["architecture decision", "adr "]):
            return "adr"
        if any(kw in content_lower for kw in ["product requirement", "prd "]):
            return "prd"
        if any(kw in content_lower for kw in ["implementation plan", "objective"]):
            return "prd"
        if any(kw in content_lower for kw in ["standard", "compliance"]):
            return "standard"
        if any(kw in content_lower for kw in ["changelog", "change log"]):
            return "changelog"
        return "unknown"

    @staticmethod
    def _extract_sections(content: str) -> List[DocSection]:
        """Extract hierarchical sections from markdown content."""
        sections: List[DocSection] = []
        stack: List[DocSection] = []
        current_section: Optional[DocSection] = None
        current_content: List[str] = []

        for line in content.split("\n"):
            m = SECTION_PATTERN.match(line)
            if m:
                # Save previous section
                if current_section is not None:
                    current_section.content = "\n".join(current_content).strip()

                level = len(m.group(1))
                heading = m.group(2).strip()
                new_section = DocSection(heading=heading, level=level, content="")
                sections.append(new_section)

                # Pop stack until we find the parent
                while stack and stack[-1].level >= level:
                    stack.pop()
                if stack:
                    stack[-1].subsections.append(new_section)
                stack.append(new_section)

                current_section = new_section
                current_content = []
            else:
                current_content.append(line)

        if current_section is not None:
            current_section.content = "\n".join(current_content).strip()

        return sections

    @staticmethod
    def _extract_requirements(content: str, sections: List[DocSection]) -> List[DocRequirement]:
        """Extract requirements from document.

        Looks for: "Must:", "Should:", "Requirement:", bullet-point requirements,
        and structured requirement sections.
        """
        requirements: List[DocRequirement] = []
        seen: Set[str] = set()

        # Pattern-based extraction
        for pattern in REQUIREMENT_PATTERNS:
            for m in pattern.finditer(content):
                text = m.group(1).strip()
                # Clean up bullet points
                text = re.sub(r"^\s*[-*]\s*", "", text, flags=re.M)
                text = re.sub(r"\s+", " ", text).strip()
                if text and text not in seen and len(text) > 10:
                    seen.add(text)

                    # Determine priority
                    priority = "medium"
                    lower = text.lower()
                    if any(kw in lower for kw in ["must", "required", "critical", "blocker"]):
                        priority = "high"
                    elif any(kw in lower for kw in ["should", "recommended", "nice"]):
                        priority = "medium"
                    else:
                        priority = "low"

                    # Find source section
                    source = ""
                    for s in sections:
                        if text in s.content or s.heading in content[:content.index(m.group(0))]:
                            source = s.heading
                            break

                    requirements.append(DocRequirement(
                        text=text[:500], priority=priority, source_section=source,
                    ))

        return requirements

    @staticmethod
    def _extract_decisions(content: str) -> List[DocDecision]:
        """Extract architectural decisions (context → decision → consequence)."""
        decisions: List[DocDecision] = []

        # Try ADR format: ## Context → ## Decision → ## Consequence
        matches = DECISION_PATTERNS
        ctx_m = matches[0].search(content)
        dec_m = matches[1].search(content)
        cons_m = matches[2].search(content)

        if ctx_m and dec_m:
            context = " ".join(ctx_m.group(1).strip().split())[:500]
            decision = " ".join(dec_m.group(1).strip().split())[:500]
            consequence = ""
            if cons_m:
                consequence = " ".join(cons_m.group(1).strip().split())[:500]
            decisions.append(DocDecision(
                context=context, decision=decision, consequence=consequence,
            ))

        return decisions

    @staticmethod
    def _extract_file_refs(content: str) -> List[DocFileRef]:
        """Extract file references from inline code backticks."""
        refs: List[DocFileRef] = []
        seen: Set[str] = set()
        for m in FILE_REF_PATTERN.finditer(content):
            path = m.group(1)
            if path not in seen:
                seen.add(path)
                refs.append(DocFileRef(path=path))
        return refs

    @staticmethod
    def _extract_version(content: str) -> Optional[str]:
        """Extract version number from document."""
        m = VERSION_PATTERN.search(content)
        return m.group(1) if m else None

    @staticmethod
    def _extract_metadata(content: str, path: Path) -> Dict[str, str]:
        """Extract metadata fields from document."""
        meta: Dict[str, str] = {}
        patterns = [
            (r"\*\*Status:\*\*\s*(.+)", "status"),
            (r"\*\*Version:\*\*\s*(.+)", "version"),
            (r"\*\*Applies to:\*\*\s*(.+)", "applies_to"),
            (r"\*\*Patch ID:\*\*\s*(.+)", "patch_id"),
            (r"\*\*Date:\*\*\s*(.+)", "date"),
            (r"^## (?:Patch ID|Date|Status)", None),
        ]

        for pat, key in patterns:
            m = re.search(pat, content, re.I | re.M)
            if m and key:
                meta[key] = m.group(1).strip()

        meta["file_size"] = str(path.stat().st_size) if path.exists() else "0"
        meta["last_modified"] = str(path.stat().st_mtime) if path.exists() else ""
        return meta


class ReadmeParser:
    """Parses README.md files into structured project overview.

    Extracts: project name, description, tech stack, install steps,
    usage examples, API endpoints, architecture overview.
    """

    @classmethod
    def parse(cls, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"error": "README not found", "path": file_path}

        content = path.read_text(encoding="utf-8", errors="replace")
        sections = DocumentParser._extract_sections(content)

        return {
            "path": str(path.resolve()),
            "project_name": cls._extract_project_name(content, path),
            "description": cls._extract_description(content),
            "tech_stack": cls._extract_tech_stack(content),
            "install_steps": cls._extract_section(content, "install"),
            "usage": cls._extract_section(content, "usage"),
            "api_endpoints": cls._extract_api_endpoints(content),
            "architecture": cls._extract_section(content, "architect"),
            "license": cls._extract_license(content),
            "contributors": cls._extract_contributors(content),
            "badges": cls._extract_badges(content),
        }

    @staticmethod
    def _extract_project_name(content: str, path: Path) -> str:
        m = re.search(r"^#\s+(.+)$", content, re.M)
        return m.group(1).strip() if m else path.parent.name.replace("-", " ").title()

    @staticmethod
    def _extract_description(content: str) -> str:
        lines = content.split("\n")
        desc_lines = []
        in_desc = False
        for line in lines:
            if line.startswith("# ") or line.startswith("<h1"):
                in_desc = True
                continue
            if in_desc:
                if line.startswith("#") or line.startswith("---"):
                    break
                stripped = line.strip()
                if stripped and not stripped.startswith("!"):
                    desc_lines.append(stripped)
        return " ".join(desc_lines)[:500]

    @staticmethod
    def _extract_tech_stack(content: str) -> List[str]:
        stack = []
        patterns = [
            r"```(?:toml|yaml|json)\s*\n(?:.*\n)*?(language|python|node|golang|rust)\s*[:=]",
            r"\b(Python|TypeScript|JavaScript|Go|Rust|Java|Kotlin|Swift|PHP|Ruby)\b",
            r"\b(FastAPI|Flask|Django|Express|Next\.?js|React|Vue|Spring|Laravel|Rails)\b",
            r"\b(Docker|Kubernetes|PostgreSQL|MySQL|MongoDB|Redis|Kafka|RabbitMQ)\b",
        ]
        for pat in patterns:
            for m in re.finditer(pat, content, re.I):
                tech = m.group(1) if m.lastindex else m.group(0)
                if tech not in stack:
                    stack.append(tech)
        return stack[:15]

    @staticmethod
    def _extract_section(content: str, section_name: str) -> str:
        pat = re.compile(
            r"(?:^|\n)#{2,3}\s+" + re.escape(section_name) + r".*?\n(.+?)(?=\n#{2,3}\s|\Z)",
            re.I | re.M | re.DOTALL,
        )
        m = pat.search(content)
        return m.group(1).strip()[:500] if m else ""

    @staticmethod
    def _extract_api_endpoints(content: str) -> List[Dict[str, str]]:
        endpoints = []
        pat = re.compile(r"`(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/\S+)`", re.I)
        for m in pat.finditer(content):
            endpoints.append({"method": m.group(1).upper(), "path": m.group(2)})
        return endpoints

    @staticmethod
    def _extract_license(content: str) -> Optional[str]:
        m = re.search(r"\b(MIT|Apache-2\.0|GPL-3\.0|BSD|MPL-2\.0|LGPL)\b", content)
        return m.group(1) if m else None

    @staticmethod
    def _extract_contributors(content: str) -> List[str]:
        pat = re.compile(r"\*\*(?:Author|Authors?|Contributors?|Team)\*\*:?\s*(.+?)(?=\n|$)", re.I)
        m = pat.search(content)
        if m:
            return [c.strip() for c in m.group(1).split(",")]
        return []

    @staticmethod
    def _extract_badges(content: str) -> List[str]:
        return re.findall(r"!\[[^\]]*\]\([^)]+\.(?:svg|png)\)", content)


class ApiContractExtractor:
    """Extracts API contracts from OpenAPI, gRPC, and GraphQL definitions.

    Handles:
    - OpenAPI 2.0/3.0 (swagger.json, openapi.yaml)
    - gRPC protobuf definitions
    - GraphQL schemas
    """

    @classmethod
    def extract_openapi(cls, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found", "path": file_path}

        content = path.read_text(encoding="utf-8", errors="replace")
        result: Dict[str, Any] = {"source": str(path.resolve()), "endpoints": [], "schemas": []}

        try:
            import json
            import yaml

            if path.suffix in (".json",):
                spec = json.loads(content)
            else:
                spec = yaml.safe_load(content)

            if not isinstance(spec, dict):
                return {**result, "error": "Invalid OpenAPI spec format"}

            result["title"] = spec.get("info", {}).get("title", "")
            result["version"] = spec.get("info", {}).get("version", "")
            result["description"] = (spec.get("info", {}) or {}).get("description", "")[:200]

            # Extract paths/endpoints
            paths = spec.get("paths", {}) or {}
            for path_name, methods in paths.items():
                if not isinstance(methods, dict):
                    continue
                for method, details in methods.items():
                    if not isinstance(details, dict):
                        continue
                    result["endpoints"].append({
                        "path": path_name,
                        "method": method.upper(),
                        "summary": details.get("summary", ""),
                        "operation_id": details.get("operationId", ""),
                        "tags": details.get("tags", []),
                        "parameters": len(details.get("parameters", [])),
                    })

            # Extract schemas
            schemas = (spec.get("components", {}) or {}).get("schemas", {}) or {}
            if not schemas:
                schemas = (spec.get("definitions", {}) or {})
            for name, schema in schemas.items():
                if isinstance(schema, dict):
                    result["schemas"].append({
                        "name": name,
                        "type": schema.get("type", "object"),
                        "properties": list((schema.get("properties", {}) or {}).keys())[:20],
                        "required": schema.get("required", []),
                    })

        except ImportError:
            result["error"] = "PyYAML required for OpenAPI parsing"
        except Exception as e:
            result["error"] = str(e)

        return result

    @classmethod
    def extract_grpc(cls, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found", "path": file_path}

        content = path.read_text(encoding="utf-8", errors="replace")
        result: Dict[str, Any] = {"source": str(path.resolve()), "services": [], "messages": []}

        # Extract service definitions
        for m in re.finditer(r"service\s+(\w+)\s*\{([^}]+)\}", content, re.DOTALL):
            service_name = m.group(1)
            body = m.group(2)
            methods = []
            for rm in re.finditer(r"rpc\s+(\w+)\s*\(\s*(\w+)\s*\)\s*returns\s*\(\s*(\w+)\s*\)", body):
                methods.append({
                    "name": rm.group(1),
                    "input_type": rm.group(2),
                    "output_type": rm.group(3),
                })
            result["services"].append({"name": service_name, "methods": methods})

        # Extract message definitions
        for m in re.finditer(r"message\s+(\w+)\s*\{([^}]+)\}", content, re.DOTALL):
            msg_name = m.group(1)
            body = m.group(2)
            fields = []
            for fm in re.finditer(r"(?:repeated\s+)?(\w+)\s+(\w+)\s*=\s*(\d+)", body):
                fields.append({"type": fm.group(1), "name": fm.group(2), "tag": int(fm.group(3))})
            result["messages"].append({"name": msg_name, "fields": fields})

        return result

    @classmethod
    def extract_graphql(cls, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found", "path": file_path}

        content = path.read_text(encoding="utf-8", errors="replace")
        result: Dict[str, Any] = {"source": str(path.resolve()), "types": [], "queries": [], "mutations": []}

        # Extract type definitions
        for m in re.finditer(r"(?:type|interface|input|enum)\s+(\w+)\s*\{([^}]+)\}", content, re.DOTALL):
            type_name = m.group(1)
            body = m.group(2)
            fields = re.findall(r"(\w+(?:\(\s*[^)]*\s*\))?)\s*:\s*(\w[!]?)", body)
            result["types"].append({"name": type_name, "fields": [{"name": f[0], "type": f[1]} for f in fields]})

        # Extract Query type fields
        for m in re.finditer(r"type\s+Query\s*\{([^}]+)\}", content, re.DOTALL):
            for fm in re.finditer(r"(\w+)\(([^)]*)\)\s*:\s*(\w[!]?)", m.group(1)):
                result["queries"].append({"name": fm.group(1), "args": fm.group(2), "return_type": fm.group(3)})

        # Extract Mutation type fields
        for m in re.finditer(r"type\s+Mutation\s*\{([^}]+)\}", content, re.DOTALL):
            for fm in re.finditer(r"(\w+)\(([^)]*)\)\s*:\s*(\w[!]?)", m.group(1)):
                result["mutations"].append({"name": fm.group(1), "args": fm.group(2), "return_type": fm.group(3)})

        return result
