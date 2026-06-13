"""
Knowledge Extraction Engine — extracts 8 types of engineering knowledge from documents.

Input formats (normalized to markdown-like text via FormatParser):
  .md, .rst, .txt, .adoc          → Native text/markup
  .csv, .json, .log               → Structured text (normalized)
  .docx                           → Word (via python-docx)
  .pdf                            → PDF (via pypdf)
  .xlsx, .xls                     → Excel (via openpyxl)
  .pptx, .ppt                     → PowerPoint (via python-pptx)

Extracted knowledge types:
  concept      → Engineering concept or domain term
  constraint   → Constraint, rule, or invariant
  decision     → Architectural decision with rationale
  flow         → Process flow or lifecycle
  risk         → Risk, hotspot, or fragility
  invariant    → Business invariant or integrity rule
  anti_pattern → Anti-pattern or practice to avoid
  principle    → Engineering principle or standard

Extraction strategy: regex pattern-based (no LLM dependency).

Standards:
    - CODDY-Architecture-v1.0    → Pattern-based extraction (no LLM)
    - CODDY-ProjectStructure-v1.0 → core/ logic, testable without MCP/CLI
"""

from __future__ import annotations

__all__ = ["KnowledgeExtractor", "ALL_EXTRACTORS"]

import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Set, Tuple

from src.modules.knowledgegraph.models.chunk import KnowledgeChunk

# ── Extraction patterns per knowledge type ────────────────

CONCEPT_PATTERNS = [
    # **Concept:** or **Term:** patterns
    (re.compile(r"\*\*(?:Concept|Term|Entity|Domain)\s*\*{0,2}:\s*\*{0,2}(.+?)(?:\n|$)", re.I | re.M), 1.0),
    # Bullet with definition: - Term: definition
    (re.compile(r"^[-*]\s+\*\*(.+?)\*\*\s*[—–\-:]\s*(.+?)$", re.M), 0.6),
    # Table rows with concept name
    (re.compile(r"^\|\s*`(.+?)`\s*\|\s*(.+?)\s*\|", re.M), 0.5),
]

CONSTRAINT_PATTERNS = [
    (re.compile(r"\*\*(?:Constraint|Rule|Must|Required)\*\*:?\s*(.+?)(?:\n|$)", re.I | re.M), 1.0),
    (re.compile(r"(?:^|\n)\s*[-*]\s*(?:MUST|SHOULD|MUST NOT|SHALL|REQUIRED)\s+(.+?)(?=\n|$)", re.M), 0.9),
    (re.compile(r"(?:cannot|can't|must not|may not|should not)\s+(.+?)[,.\n]", re.I), 0.7),
    (re.compile(r"(?:is|are)\s+(?:always|never|required|mandatory)\s+(?:to|for|that)\s+(.+?)[,.\n]", re.I), 0.6),
    # "No direct DB access" type constraints
    (re.compile(r"No\s+(?:direct\s+)?(?:access|modification|deletion)\s+(?:to|of|from)\s+(.+?)[,.\n]", re.I), 0.7),
]

DECISION_PATTERNS = [
    (re.compile(r"##+\s*(?:Decision|Approach|Solution|Chosen)\s*\n(.+?)(?=\n##+\s|\Z)", re.I | re.M | re.DOTALL), 0.9),
    (re.compile(r"\*\*(?:Decision|Approach|Solution)\*\*:?\s*(.+?)(?:\n|$)", re.I | re.M), 0.8),
    (re.compile(r"We\s+(?:chose|adopted|selected|decided|implemented|migrated)\s+(.+?)[,.\n]", re.I), 0.7),
    (re.compile(r"(?:was|were)\s+(?:chosen|adopted|selected)\s+(?:due to|because of|for)\s+(.+?)[,.\n]", re.I), 0.6),
]

FLOW_PATTERNS = [
    (re.compile(r"##+\s*(?:Flow|Process|Lifecycle|Pipeline)\s*\n(.+?)(?=\n##+\s|\Z)", re.I | re.M | re.DOTALL), 0.9),
    (re.compile(r"\d+\.\s+(.+?)(?=\n\d+\.|\n\n|\Z)", re.M), 0.7),
    (re.compile(r"Step\s+\d+[:\s]+(.+?)(?:\n|$)", re.I), 0.7),
    (re.compile(r"(?:flow|process|lifecycle|pipeline)[:\s]+(.+?)(?:\n\n|\Z)", re.I | re.M | re.DOTALL), 0.6),
]

RISK_PATTERNS = [
    (re.compile(r"\*\*(?:Risk|Warning|Caution|Concern)\*\*:?\s*(.+?)(?:\n|$)", re.I | re.M), 1.0),
    (re.compile(r"(?:risk|risk of|risk that|danger|pitfall|drawback)[:\s]+(.+?)(?:\n|$)", re.I), 0.8),
    (re.compile(r"(?:tightly coupled|high coupling|fragile|brittle|unstable|bottleneck)\s+(.+?)[,.\n]", re.I), 0.7),
    (re.compile(r"(?:single point of failure|SPOF|no fallback|no backup)\s*(.+?)[,.\n]", re.I), 0.9),
]

INVARIANT_PATTERNS = [
    (re.compile(r"\*\*(?:Invariant|Integrity)\*\*:?\s*(.+?)(?:\n|$)", re.I | re.M), 1.0),
    (re.compile(r"(?:must always|must never|always must|must remain|must be unique)\s+(.+?)[,.\n]", re.I), 0.9),
    (re.compile(r"(?:invariant|integrity rule|business rule)[:\s]+(.+?)(?:\n|$)", re.I), 0.8),
    (re.compile(r"Each\s+\w+\s+(?:must|shall|should)\s+(?:have|be|belong|contain)\s+(.+?)[,.\n]", re.I), 0.7),
    (re.compile(r"(?:unique|distinct|cannot duplicate)\s+(.+?)[,.\n]", re.I), 0.6),
]

ANTI_PATTERN_PATTERNS = [
    (re.compile(r"\*\*(?:Anti-pattern|Anti pattern|Avoid|Do not)\*\*:?\s*(.+?)(?:\n|$)", re.I | re.M), 1.0),
    (re.compile(r"(?:anti-pattern|bad practice|common mistake|code smell)[:\s]+(.+?)(?:\n|$)", re.I), 0.8),
    (re.compile(r"Don't\s+(.+?)[,.\n]", re.I), 0.7),
    (re.compile(r"avoid\s+(?:using|doing|creating|making)\s+(.+?)[,.\n]", re.I), 0.7),
]

PRINCIPLE_PATTERNS = [
    (re.compile(r"\*\*(?:Principle|Standard|Guideline)\*\*:?\s*(.+?)(?:\n|$)", re.I | re.M), 1.0),
    (re.compile(r"##+\s*(?:Principles?|Standards?)\s*\n(.+?)(?=\n##+\s|\Z)", re.I | re.M | re.DOTALL), 0.9),
    (re.compile(r"(?:principle|our philosophy|we believe|we follow)[:\s]+(.+?)(?:\n|$)", re.I), 0.7),
    (re.compile(r"modular[-_](?:first|by.design)|loose.coupling|high.cohesion|single.responsibility", re.I), 0.6),
]

ALL_EXTRACTORS: Dict[str, Tuple[List[Tuple[re.Pattern, float]], str]] = {
    "concept": (CONCEPT_PATTERNS, "concept"),
    "constraint": (CONSTRAINT_PATTERNS, "constraint"),
    "decision": (DECISION_PATTERNS, "decision"),
    "flow": (FLOW_PATTERNS, "flow"),
    "risk": (RISK_PATTERNS, "risk"),
    "invariant": (INVARIANT_PATTERNS, "invariant"),
    "anti_pattern": (ANTI_PATTERN_PATTERNS, "anti_pattern"),
    "principle": (PRINCIPLE_PATTERNS, "principle"),
}


class KnowledgeExtractor:
    """Extracts structured engineering knowledge from markdown content.

    Usage:
        extractor = KnowledgeExtractor()
        chunks = extractor.extract_all(content, source_file="docs/arch.md")
    """

    def extract_all(
        self,
        content: str,
        source_file: str,
        doc_type: str = "unknown",
        section_path: str = "",
        types: Optional[List[str]] = None,
        repo_id: str = "",
    ) -> List[KnowledgeChunk]:
        """Run all (or specified) extractors on content.

        Args:
            content: Raw markdown content.
            source_file: Source file path (for attribution).
            doc_type: Document type (prd, adr, readme, etc.).
            section_path: Section path within the document.
            types: Knowledge types to extract. None = all 8.

        Returns:
            List of extracted KnowledgeChunk objects.
        """
        active_types = types or list(ALL_EXTRACTORS.keys())
        chunks: List[KnowledgeChunk] = []
        seen_contents: Set[str] = set()

        for ktype in active_types:
            if ktype not in ALL_EXTRACTORS:
                continue
            patterns, _ = ALL_EXTRACTORS[ktype]
            for pattern, confidence in patterns:
                for m in pattern.finditer(content):
                    raw = m.group(1).strip() if m.lastindex and m.group(1) else m.group(0).strip()
                    raw = self._clean(raw)
                    # Dedup
                    key = raw[:100].lower()
                    if key in seen_contents or len(raw) < 15:
                        continue
                    seen_contents.add(key)

                    chunk = KnowledgeChunk(
                        knowledge_type=ktype,
                        title=self._make_title(ktype, raw),
                        content=raw[:1000],
                        summary=self._make_summary(raw),
                        source_file=source_file,
                        doc_type=doc_type,
                        section_path=section_path,
                        importance_score=confidence,
                        confidence_score=confidence,
                        criticality=self._classify_criticality(ktype, raw),
                        concept=self._extract_concepts(raw, ktype),
                        related_module=self._extract_modules(raw),
                        architecture_tag=self._extract_tags(raw),
                        repo_id=repo_id,
                    )
                    chunks.append(chunk)

        return chunks

    # ── Helpers ───────────────────────────────────────────

    @staticmethod
    def _clean(text: str) -> str:
        """Clean extracted text: remove extra whitespace, markdown artifacts."""
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\*\*", "", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        return text[:800]

    @staticmethod
    def _make_title(ktype: str, raw: str) -> str:
        prefix = {
            "concept": "Concept",
            "constraint": "Constraint",
            "decision": "Decision",
            "flow": "Flow",
            "risk": "Risk",
            "invariant": "Invariant",
            "anti_pattern": "Anti-Pattern",
            "principle": "Principle",
        }
        short = raw[:80].rstrip(".,:;")
        return f"{prefix.get(ktype, 'Knowledge')}: {short}"

    @staticmethod
    def _make_summary(raw: str) -> str:
        return raw[:200].rstrip(".,:;") + "."

    @staticmethod
    def _classify_criticality(ktype: str, raw: str) -> str:
        lower = raw.lower()
        high_keywords = ["critical", "blocker", "must", "never", "always", "required",
                         "vital", "essential", "mandatory", "security", "integrity"]
        if any(kw in lower for kw in high_keywords):
            return "high"
        if ktype in ("risk", "constraint", "invariant"):
            return "high" if any(kw in lower for kw in ["high", "significant", "severe"]) else "medium"
        if ktype in ("principle", "decision"):
            return "medium"
        return "low"

    @staticmethod
    def _extract_concepts(raw: str, ktype: str) -> List[str]:
        words = re.findall(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", raw)  # PascalCase
        words += re.findall(r"\b([A-Z]{2,})\b", raw)  # ALL CAPS
        return words[:5]

    @staticmethod
    def _extract_modules(raw: str) -> List[str]:
        paths = re.findall(r"\b(?:src|app|lib|packages)/[\w/.-]+", raw)
        return paths[:3]

    @staticmethod
    def _extract_tags(raw: str) -> List[str]:
        tags = []
        if any(w in raw.lower() for w in ["security", "auth", "permission"]):
            tags.append("security")
        if any(w in raw.lower() for w in ["perform", "scale", "latency", "cache"]):
            tags.append("performance")
        if any(w in raw.lower() for w in ["database", "sql", "orm", "query", "store"]):
            tags.append("data")
        if any(w in raw.lower() for w in ["api", "endpoint", "route", "rest"]):
            tags.append("api")
        if any(w in raw.lower() for w in ["test", "coverage", "qa"]):
            tags.append("testing")
        return tags

    @staticmethod
    def compute_file_hash(content: str) -> str:
        """Compute SHA-256 hash of content for incremental extraction tracking."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]

    def extract_batch(
        self,
        documents: List[Dict[str, str]],
        types: Optional[List[str]] = None,
        repo_id: str = "",
        max_workers: int = 4,
    ) -> List[KnowledgeChunk]:
        """Extract knowledge from multiple documents in parallel.

        Args:
            documents: List of {"source_file": str, "content": str, "doc_type": str}
            types: Knowledge types to extract.
            repo_id: Repository identifier.
            max_workers: Max parallel workers.

        Returns:
            List of extracted KnowledgeChunk objects.
        """
        all_chunks: List[KnowledgeChunk] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    self.extract_all,
                    doc["content"],
                    doc["source_file"],
                    doc.get("doc_type", "unknown"),
                    "",
                    types,
                    repo_id,
                )
                for doc in documents
            ]
            for future in futures:
                try:
                    chunks = future.result()
                    all_chunks.extend(chunks)
                except Exception:
                    continue
        return all_chunks
