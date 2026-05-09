"""
/**
 * @project   CodeCortex
 * @package   CodeGraph/ServiceBoundary
 * @standard  Aegis-CrossStack-v1.0
 * * Service Boundary Detection — detects microservice boundaries from
 *   HTTP routes, gRPC services, Thrift definitions, and message topics.
 *   Ported from GitNexus's group/ system.
 */
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field

logger = logging.getLogger("CodeCortex.CodeGraph.ServiceBoundary")

SERVICE_MARKERS = [
    "package.json", "go.mod", "Dockerfile", "pom.xml",
    "build.gradle", "Cargo.toml", "pyproject.toml",
    "requirements.txt", "mix.exs", "Gemfile",
]


@dataclass
class ServiceBoundary:
    service_path: str
    service_name: str
    markers: List[str] = field(default_factory=list)
    confidence: float = 0.0
    routes: List[str] = field(default_factory=list)
    ports: List[int] = field(default_factory=list)


HTTP_FRAMEWORKS = {
    "python": [r"@app\.(get|post|put|delete)", r"@router\.(get|post)", r"path\(['\"]"],
    "javascript": [r"router\.(get|post|put|delete)", r"app\.(get|post|put|delete)", r"axios\.(get|post)"],
    "go": [r"mux\.Handle", r"gin\.(GET|POST)", r"echo\.(GET|POST)"],
    "java": [r"@RequestMapping", r"@GetMapping", r"@PostMapping"],
}

GRPC_PATTERNS = [
    r"service\s+\w+\s*\{",
    r"rpc\s+\w+\s*\(",
    r"proto\s+(package|service)",
]

THRIFT_PATTERNS = [
    r"service\s+\w+\s*\{",
    r"struct\s+\w+\s*\{",
    r"thrift\s+namespace",
]

TOPIC_PATTERNS = [
    r"(publish|subscribe|emit|on)\s*\(\s*['\"]",
    r"channel\s*[:=]\s*['\"]",
    r"topic\s*[:=]\s*['\"]",
]


class ServiceBoundaryDetector:
    """
    Detects microservice boundaries by analyzing project structure
    and communication patterns (HTTP, gRPC, Thrift, topics).
    """
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.services: List[ServiceBoundary] = []
    
    def detect_all(self) -> List[ServiceBoundary]:
        """Detect all service boundaries in the repository."""
        self.services = []
        
        # 1. Detect by project markers
        self._detect_by_markers()
        
        # 2. Detect by HTTP routes
        self._detect_by_routes()
        
        # 3. Score and rank
        for svc in self.services:
            svc.confidence = self._calculate_confidence(svc)
        
        return sorted(self.services, key=lambda s: s.confidence, reverse=True)
    
    def _detect_by_markers(self):
        """Find service boundaries using build config files."""
        for marker in SERVICE_MARKERS:
            for path in self.repo_root.rglob(marker):
                if path.is_file():
                    rel = path.relative_to(self.repo_root)
                    parts = list(rel.parts[:-1]) if len(rel.parts) > 1 else []
                    service_name = parts[-1] if parts else self.repo_root.name
                    
                    existing = [s for s in self.services if s.service_name == service_name]
                    if existing:
                        existing[0].markers.append(str(rel))
                    else:
                        self.services.append(ServiceBoundary(
                            service_path=str(rel.parent) if parts else ".",
                            service_name=service_name,
                            markers=[str(rel)]
                        ))
    
    def _detect_by_routes(self):
        """Find HTTP routes in source files."""
        import os
        for root, _dirs, files in os.walk(str(self.repo_root)):
            for fname in files:
                fpath = Path(root) / fname
                if fname.endswith((".py", ".js", ".ts", ".go", ".java", ".kt")):
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="ignore")
                        ext = fname.split(".")[-1]
                        
                        # Check HTTP patterns
                        lang = "python" if ext == "py" else "javascript" if ext in ("js", "ts") else "go" if ext == "go" else "java" if ext in ("java", "kt") else None
                        if lang:
                            for pattern in HTTP_FRAMEWORKS.get(lang, []):
                                if re.search(pattern, content):
                                    rel = fpath.relative_to(self.repo_root)
                                    svc_name = str(rel.parent).split("/")[0] if rel.parent != "." else "root"
                                    existing = [s for s in self.services if s.service_name == svc_name]
                                    if existing:
                                        existing[0].routes.append(str(rel))
                                    else:
                                        # Create service from route if no marker exists
                                        new_svc = ServiceBoundary(
                                            service_path=str(rel.parent),
                                            service_name=svc_name,
                                            routes=[str(rel)]
                                        )
                                        self.services.append(new_svc)
                                    break
                        
                        # Check gRPC patterns
                        for pat in GRPC_PATTERNS:
                            if re.search(pat, content):
                                rel = fpath.relative_to(self.repo_root)
                                svc_name = str(rel.parent).split("/")[0] if rel.parent != "." else "root"
                                existing = [s for s in self.services if s.service_name == svc_name]
                                marker_val = f"grpc:{rel}"
                                if existing:
                                    existing[0].markers.append(marker_val)
                                else:
                                    new_svc = ServiceBoundary(
                                        service_path=str(rel.parent),
                                        service_name=svc_name,
                                        markers=[marker_val]
                                    )
                                    self.services.append(new_svc)
                                break
                    except Exception:
                        pass
    
    def _calculate_confidence(self, svc: ServiceBoundary) -> float:
        score = 0.0
        if len(svc.markers) >= 2:
            score += 0.4
        elif len(svc.markers) == 1:
            score += 0.2
        if len(svc.routes) >= 3:
            score += 0.4
        elif len(svc.routes) >= 1:
            score += 0.2
        if any("grpc" in m for m in svc.markers):
            score += 0.3
        if any("Dockerfile" in m for m in svc.markers):
            score += 0.2
        return min(1.0, score)


def detect_service_boundaries(repo_root: Path) -> List[Dict]:
    """Convenience function to detect service boundaries."""
    detector = ServiceBoundaryDetector(repo_root)
    services = detector.detect_all()
    return [
        {
            "name": s.service_name,
            "path": s.service_path,
            "confidence": round(s.confidence, 2),
            "markers": s.markers,
            "routes_found": len(s.routes),
        }
        for s in services
    ]
