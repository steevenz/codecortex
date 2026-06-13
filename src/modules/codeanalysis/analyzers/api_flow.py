"""
API Flow Mapper — traces request lifecycle: endpoint → handler → data → response.

Combines route detection (from CrossLanguageResolver) with data flow analysis
to map complete API request flows.

:project: CodeCortex
:package: Modules.Codeanalysis.Analyzers.Api_flow
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeAnalysis-v1.0
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List


class ApiFlowMapper:
    """Maps API request flows: endpoint → handler → data → response."""

    FRAMEWORK_ROUTES = {
        "fastapi": (r"@(?:router|app)\.(get|post|put|delete|patch)\s*\(\s*[\"']([^\"']+)[\"']", "python"),
        "flask": (r"@(?:app|blueprint)\.route\s*\(\s*[\"']([^\"']+)[\"']\s*(?:,\s*methods=\[([^\]]+)\])?", "python"),
        "express": (r"router\.(get|post|put|delete|patch)\s*\(\s*[\"']([^\"']+)[\"']", "typescript"),
        "nextjs": (r"export\s+(?:async\s+)?function\s+(?:GET|POST|PUT|DELETE)\s*\(", "typescript"),
    }

    def analyze(self, root_path: str) -> Dict[str, Any]:
        root = Path(root_path)
        flows: List[Dict] = []

        for framework, (pattern, lang) in self.FRAMEWORK_ROUTES.items():
            ext_map = {"python": ".py", "typescript": ".ts"}
            for fp in root.rglob(f"*{ext_map.get(lang, '.py')}"):
                if not fp.is_file():
                    continue
                if any(p.startswith(".") or p in ("node_modules", "venv") for p in fp.relative_to(root).parts):
                    continue

                try:
                    content = fp.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                for m in re.finditer(pattern, content):
                    method = m.group(1).upper() if m.lastindex and m.group(1) else "GET"
                    if m.lastindex and m.lastindex >= 2 and m.group(2):
                        path_str = m.group(2)
                    else:
                        path_str = "/"

                    line_num = content[:m.start()].count("\n") + 1
                    handler_name = self._find_handler_name(content, m.start())

                    # Detect data sources and response types
                    data_sources = self._detect_data_sources(content, line_num)
                    response_type = self._detect_response_type(content, line_num)

                    flows.append({
                        "method": method if len(method) < 8 else "GET",
                        "path": path_str.replace('"', "").replace("'", ""),
                        "framework": framework,
                        "language": lang,
                        "file": str(fp.relative_to(root)),
                        "line": line_num,
                        "handler": handler_name,
                        "data_sources": data_sources,
                        "response_type": response_type,
                    })

        return {
            "total_endpoints": len(flows),
            "flows": flows[:100],
            "by_framework": {fw: sum(1 for f in flows if f["framework"] == fw) for fw in self.FRAMEWORK_ROUTES},
        }

    def _find_handler_name(self, content: str, pos: int) -> str:
        before = content[:pos]
        lines = before.split("\n")
        for i in range(len(lines) - 1, -1, -1):
            m = re.match(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(", lines[i])
            if m:
                return m.group(1)
        return ""

    def _detect_data_sources(self, content: str, line: int) -> List[str]:
        sources = []
        lines = content.split("\n")
        start = max(0, line - 5)
        end = min(len(lines), line + 30)
        window = "\n".join(lines[start:end])

        if "db:" in window or "database" in window.lower():
            sources.append("database")
        if "request" in window.lower():
            sources.append("http_request")
        if "cache" in window.lower():
            sources.append("cache")
        if "redis" in window.lower():
            sources.append("redis")
        if "api" in window.lower() and "request" in window.lower():
            sources.append("external_api")

        return sources

    def _detect_response_type(self, content: str, line: int) -> str:
        lines = content.split("\n")
        start = max(0, line - 5)
        end = min(len(lines), line + 30)
        window = "\n".join(lines[start:end])

        if "JSONResponse" in window or "json.dumps" in window or ".json()" in window:
            return "json"
        if "HTMLResponse" in window or "TemplateResponse" in window:
            return "html"
        if "StreamingResponse" in window or "FileResponse" in window:
            return "stream"
        if "RedirectResponse" in window:
            return "redirect"
        if "Response(" in window:
            return "custom"
        return "json"  # default
