"""
ORM Dataflow Analysis — extracts model-database relationships from ORM definitions.
Ported from GitNexus's orm.ts and orm-extraction.ts pipeline phases.

:project: CodeCortex
:package: Modules.Codegraph.Core.Orm
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeGraph-v1.0
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("CodeCortex.CodeGraph.ORM")

@dataclass
class ORMModel:
    name: str
    table: Optional[str]
    fields: List[Dict] = field(default_factory=list)
    framework: str = ""
    file: str = ""
    line: int = 0

@dataclass
class ORMQuery:
    source: str  # The code making the query
    model: str  # The model being queried
    operation: str  # CREATE, READ, UPDATE, DELETE
    file: str = ""
    line: int = 0

class ORMExtractor:
    """
    Extracts ORM model definitions and query patterns from code.

    Supports:
    - SQLAlchemy: class User(Base), session.query(User)
    - Django: class User(models.Model), User.objects.filter()
    - Prisma: model User { ... }
    """

    # SQLAlchemy patterns
    SA_BASE = re.compile(r"class\s+\w+\s*\(\s*(?:db\.)?(?:Model|DeclarativeBase)\s*\)")
    SA_MODEL = re.compile(r"class\s+(\w+)\s*\(.*?\)\s*:")
    SA_TABLE = re.compile(r"__tablename__\s*=\s*['\"](\w+)['\"]")
    SA_COLUMN = re.compile(r"(\w+)\s*=\s*(?:db\.)?Column\s*\(([^)]*)\)")
    SA_QUERY = re.compile(r"(?:session|db)\.(?:query|execute|get|find)\s*\(\s*(\w+)")

    # Django patterns
    DJ_MODEL = re.compile(r"class\s+(\w+)\s*\(\s*models?\.Model\s*\)")
    DJ_FIELD = re.compile(r"(\w+)\s*=\s*models?\.(\w+)Field\s*\(([^)]*)\)")
    DJ_QUERY = re.compile(r"(\w+)\.objects\.(?:filter|get|create|update|delete|all|first)\s*\(")

    # Prisma pattern
    PRISMA_MODEL = re.compile(r"^\s*model\s+(\w+)\s*\{")
    PRISMA_FIELD = re.compile(r"^\s*(\w+)\s+(\w+)")

    def extract_models_from_file(self, content: str, file_path: str, language: str) -> List[ORMModel]:
        models: List[ORMModel] = []

        if language == "python":
            models.extend(self._extract_sqlalchemy(content, file_path))
            models.extend(self._extract_django(content, file_path))
        elif language == "prisma" or file_path.endswith("schema.prisma"):
            models.extend(self._extract_prisma(content, file_path))

        return models

    def _extract_sqlalchemy(self, content: str, file_path: str) -> List[ORMModel]:
        if not self.SA_BASE.search(content):
            return []
        models = []
        lines = content.split("\n")
        current_model = None

        for i, line in enumerate(lines, 1):
            m = self.SA_MODEL.search(line)
            if m and not m.group(1) == "Base":
                if current_model:
                    models.append(current_model)
                current_model = ORMModel(
                    name=m.group(1),
                    table=m.group(1).lower(),
                    framework="sqlalchemy",
                    file=file_path,
                    line=i,
                )
                # Look ahead for __tablename__ and columns (up to 50 lines)
                for j in range(i, min(i + 50, len(lines))):
                    nl = lines[j - 1]
                    t = self.SA_TABLE.search(nl)
                    if t and current_model:
                        current_model.table = t.group(1)
                    c = self.SA_COLUMN.search(nl)
                    if c and current_model:
                        current_model.fields.append({
                            "name": c.group(1),
                            "type": c.group(2).split(",")[0].strip() if c.group(2) else "unknown"
                        })
            elif current_model and line.strip() == "" and i > current_model.line + 1:
                if any(f.get("name") for f in current_model.fields):
                    models.append(current_model)
                current_model = None

        if current_model and current_model.fields:
            models.append(current_model)
        return models

    def _extract_django(self, content: str, file_path: str) -> List[ORMModel]:
        models = []
        for i, line in enumerate(content.split("\n"), 1):
            m = self.DJ_MODEL.search(line)
            if m:
                model = ORMModel(
                    name=m.group(1),
                    table=None,  # Django auto-generates
                    framework="django",
                    file=file_path,
                    line=i,
                )
                # Look ahead for fields
                for j in range(i + 1, min(i + 50, len(content.split("\n")))):
                    next_line = content.split("\n")[j - 1]
                    f = self.DJ_FIELD.search(next_line)
                    if f:
                        model.fields.append({"name": f.group(1), "type": f.group(2)})
                models.append(model)
        return models

    def _extract_prisma(self, content: str, file_path: str) -> List[ORMModel]:
        models = []
        lines = content.split("\n")
        current_model = None
        in_model = False
        brace_depth = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("#"):
                continue

            m = self.PRISMA_MODEL.search(line)
            if m:
                if current_model:
                    models.append(current_model)
                current_model = ORMModel(
                    name=m.group(1),
                    table=m.group(1).lower(),
                    framework="prisma",
                    file=file_path,
                    line=i,
                )
                in_model = True
                brace_depth = stripped.count("{")
                continue

            if in_model and current_model:
                brace_depth += stripped.count("{") - stripped.count("}")

                # Parse field: `fieldName  FieldType  @attribute`
                # Prisma uses space separation, no colons
                field_m = self.PRISMA_FIELD.match(stripped)
                if field_m and not stripped.startswith("@"):
                    field_name = field_m.group(1)
                    field_type = field_m.group(2)
                    if field_name not in ("model", "enum", "datasource", "generator"):
                        current_model.fields.append({"name": field_name, "type": field_type})

                if brace_depth <= 0:
                    if current_model.fields:
                        models.append(current_model)
                    current_model = None
                    in_model = False

        if current_model and current_model.fields:
            models.append(current_model)
        return models

    def extract_queries_from_file(self, content: str, file_path: str, language: str) -> List[ORMQuery]:
        queries = []
        for i, line in enumerate(content.split("\n"), 1):
            if language == "python":
                for p in (self.SA_QUERY, self.DJ_QUERY):
                    m = p.search(line)
                    if m:
                        operation = self._infer_operation(line, p)
                        queries.append(ORMQuery(
                            source=file_path,
                            model=m.group(1),
                            operation=operation,
                            file=file_path,
                            line=i,
                        ))
        return queries

    def _infer_operation(self, line: str, pattern: re.Pattern) -> str:
        if ".create" in line or "add(" in line:
            return "CREATE"
        elif ".update" in line:
            return "UPDATE"
        elif ".delete" in line:
            return "DELETE"
        elif ".filter" in line or ".get" in line or ".all" in line or ".first" in line:
            return "READ"
        elif "query" in line or "execute" in line:
            return "READ"
        return "READ"

def extract_orm_from_files(files: List[Dict[str, str]]) -> Dict:
    """Bulk extract ORM models and queries from multiple files."""
    extractor = ORMExtractor()
    all_models = []
    all_queries = []

    for f in files:
        lang = f.get("language", "python")
        try:
            models = extractor.extract_models_from_file(f.get("content", ""), f.get("path", ""), lang)
            queries = extractor.extract_queries_from_file(f.get("content", ""), f.get("path", ""), lang)
            all_models.extend(models)
            all_queries.extend(queries)
        except Exception as e:
            logger.debug(f"ORM extraction failed for {f.get('path')}: {e}")

    return {
        "models": [{"name": m.name, "table": m.table, "fields": m.fields, "framework": m.framework, "file": m.file} for m in all_models],
        "queries": [{"source": q.source, "model": q.model, "operation": q.operation} for q in all_queries],
        "model_count": len(all_models),
        "query_count": len(all_queries),
    }
