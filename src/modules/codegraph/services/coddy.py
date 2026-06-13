"""
CODDY Graph Builder – Modular Detection & Dependency Graph Construction
Based on CODDY Codework Project Structure & Modular Standard.

:project: CodeCortex
:package: Modules.Codegraph.Services.CODDY
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeGraph-v1.0
"""

import json
import hashlib
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from dataclasses import dataclass, field, asdict

import networkx as nx

from src.core.database import DatabaseManager
from src.core.graph import GraphManager
from src.core.logging import get_logger
from src.core import ApiError

logger = get_logger("CodeCortex.Domain.CodeGraph.CODDY")

# ---------------------------------------------------------------------------
# Constants & Type Definitions
# ---------------------------------------------------------------------------

MODULE_DIRECTORIES = {
    "Modules": "module",
    "Plugins": "plugin",
    "Widgets": "widget",
    "Components": "component",
    "Services": "service",
    "Core": "core",
}

HMVC_P_FOLDERS = [
    "Controllers", "Presenters", "ViewModels", "Views", "Models",
    "Services", "DTOs", "Events", "Listeners", "Migrations",
    "Languages", "Helpers", "Libraries", "Entities", "ValueObjects",
    "Aggregates", "Repositories", "Interfaces", "Exceptions",
]

MANIFEST_FILES = {
    "module": "module.json",
    "plugin": "plugin.json",
    "widget": "widget.json",
    "component": "component.json",
}

@dataclass
class HMVCPStructure:
    has_controllers: bool = False
    has_presenters: bool = False
    has_view_models: bool = False
    has_views: bool = False
    has_models: bool = False
    controller_count: int = 0
    presenter_count: int = 0
    view_model_count: int = 0
    model_count: int = 0
    service_count: int = 0
    dto_count: int = 0

@dataclass
class ModuleInfo:
    name: str
    type: str
    path: str
    namespace: str
    version: str = "1.0.0"
    bounded_context: str = ""
    hmvc_p: Optional[Dict[str, Any]] = None
    requires: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    hooks: Dict[str, List[str]] = field(default_factory=dict)
    services_registered: List[str] = field(default_factory=list)
    submodules: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class PluginInfo:
    name: str
    type: str
    path: str
    version: str = "1.0.0"
    hooks_subscribed: List[str] = field(default_factory=list)

@dataclass
class WidgetInfo:
    name: str
    type: str
    path: str
    renders: str = ""
    data_source: str = ""

@dataclass
class ComponentInfo:
    name: str
    type: str
    path: str
    ui_framework: str = ""
    props: List[str] = field(default_factory=list)

@dataclass
class CoreContractInfo:
    name: str
    path: str
    namespace: str = ""

@dataclass
class DependencyGraph:
    nodes: List[Dict[str, str]] = field(default_factory=list)
    edges: List[Dict[str, str]] = field(default_factory=list)
    circular_dependencies_detected: bool = False
    god_modules: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class Metrics:
    total_controllers: int = 0
    total_presenters: int = 0
    total_view_models: int = 0
    total_models: int = 0
    total_services: int = 0
    total_dtos: int = 0
    average_complexity_per_module: float = 0.0

@dataclass
class AIRecommendation:
    severity: str
    message: str

# ---------------------------------------------------------------------------
# CODDY Graph Builder Class
# ---------------------------------------------------------------------------

class CODDY:
    """
    Builds modular dependency graphs following CODDY standard.
    Supports Modules, Plugins, Widgets, Components, Core, and Services.
    """

    def __init__(self, db: DatabaseManager, graph_manager: Optional[GraphManager] = None):
        self.db = db
        self.graph_manager = graph_manager
        self._modules: List[ModuleInfo] = []
        self._plugins: List[PluginInfo] = []
        self._widgets: List[WidgetInfo] = []
        self._components: List[ComponentInfo] = []
        self._core_contracts: List[CoreContractInfo] = []
        self._dependency_graph = DependencyGraph()
        self._metrics = Metrics()
        self._recommendations: List[AIRecommendation] = []

    async def build(
        self,
        repo_path: str,
        repo_id: Optional[str] = None,
        detect_modular: bool = True,
        build_dependency_graph: bool = True,
        include_core_contracts: bool = True,
        scan_hmvc_p: bool = True,
        max_depth: int = 5,
        use_cache: bool = True,
        incremental: bool = True,
    ) -> Dict[str, Any]:
        """
        Main entry point for CODDY graph building.

        Supports incremental builds: if incremental=True (default), the repo
        content hash is checked before rebuilding. If files have not changed
        since the last build, the cached result is returned instantly.
        Set use_cache=False or incremental=False to force a full rebuild.
        """
        start_time = datetime.now()
        request_id = f"graph_build_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        repo_path_obj = Path(repo_path).resolve()
        if not repo_path_obj.exists():
            raise ApiError(f"Path not found: {repo_path}", status_code=400, error_code="GRPH_004")

        if not repo_id:
            repo_id = await self._resolve_or_create_repo_id(repo_path_obj)

        # --- Incremental / auto-invalidation logic ---
        current_hash = self._compute_repo_hash(repo_path_obj)
        if use_cache and incremental:
            cached = await self._try_load_cache_with_hash(repo_id, current_hash)
            if cached:
                cached["build_mode"] = "incremental_cache_hit"
                return cached
        elif use_cache and not incremental:
            # Legacy: time-only cache check (ignore hash)
            cached = await self._try_load_cache(repo_id)
            if cached:
                cached["build_mode"] = "time_cache_hit"
                return cached

        if detect_modular:
            await self._detect_modular_structure(repo_path_obj)

        if include_core_contracts:
            await self._detect_core_contracts(repo_path_obj)

        if scan_hmvc_p:
            await self._scan_hmvc_p(repo_path_obj)

        if build_dependency_graph:
            await self._build_dependency_graph()

        await self._calculate_metrics()
        await self._generate_recommendations()

        result = self._build_output(repo_id, repo_path_obj, start_time)
        result["build_mode"] = "full_build"
        result["repo_hash"] = current_hash

        if use_cache:
            await self._save_cache_with_hash(repo_id, result, current_hash)

        # Mark graph as synced
        try:
            from src.core.database.integrity import FileIntegrity
            FileIntegrity(self.db).mark_synced(repo_id, "graph")
        except Exception:
            pass

        result["sync_at"] = datetime.now().isoformat()
        return result

    async def _resolve_or_create_repo_id(self, repo_path: Path) -> str:
        cursor = self.db.conn.execute(
            "SELECT id FROM repositories WHERE root_path = ?",
            (str(repo_path),)
        )
        row = cursor.fetchone()
        if row:
            return row["id"]
        import uuid
        new_id = str(uuid.uuid4())
        self.db.conn.execute(
            "INSERT INTO repositories (id, name, root_path, created_at, vcs_type, total_files, total_symbols, total_edges) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id, repo_path.name, str(repo_path), datetime.now().isoformat(), "git", 0, 0, 0)
        )
        self.db.conn.commit()
        return new_id

    def _compute_repo_hash(self, repo_path: Path) -> str:
        """Compute a lightweight hash of all source files to detect changes."""
        hasher = hashlib.sha1()
        try:
            for root, dirs, files in os.walk(str(repo_path)):
                # Skip hidden dirs, __pycache__, node_modules, .git
                dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "node_modules", "dist", "build"))
                for fname in sorted(files):
                    if fname.endswith((".py", ".ts", ".js", ".php", ".rb", ".java", ".go", ".cs", ".json")):
                        fpath = Path(root) / fname
                        try:
                            stat = fpath.stat()
                            hasher.update(f"{fpath}:{stat.st_mtime}:{stat.st_size}".encode())
                        except OSError:
                            pass
        except Exception:
            pass
        return hasher.hexdigest()[:16]

    async def _try_load_cache(self, repo_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.db.conn.execute(
            "SELECT data FROM graph_cache WHERE repository_id = ? AND created_at > datetime('now', '-1 hour')",
            (repo_id,)
        )
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row["data"])
            except Exception:
                return None
        return None

    async def _try_load_cache_with_hash(self, repo_id: str, current_hash: str) -> Optional[Dict[str, Any]]:
        """Return cached data only if the repo hash matches (auto-invalidation on file changes)."""
        cursor = self.db.conn.execute(
            "SELECT data, repo_hash FROM graph_cache WHERE repository_id = ?",
            (repo_id,)
        )
        row = cursor.fetchone()
        if row:
            stored_hash = row["repo_hash"] if "repo_hash" in row.keys() else None
            if stored_hash and stored_hash == current_hash:
                try:
                    return json.loads(row["data"])
                except Exception:
                    return None
        return None

    async def _save_cache(self, repo_id: str, data: Dict[str, Any]) -> None:
        self.db.conn.execute(
            "INSERT OR REPLACE INTO graph_cache (id, repository_id, data, created_at) VALUES (?, ?, ?, ?)",
            (repo_id, repo_id, json.dumps(data, default=str), datetime.now().isoformat())
        )
        self.db.conn.commit()

    async def _save_cache_with_hash(self, repo_id: str, data: Dict[str, Any], repo_hash: str) -> None:
        """Persist cache with repo hash for auto-invalidation support."""
        try:
            self.db.conn.execute(
                "INSERT OR REPLACE INTO graph_cache (id, repository_id, data, repo_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (repo_id, repo_id, json.dumps(data, default=str), repo_hash, datetime.now().isoformat())
            )
            self.db.conn.commit()
        except Exception:
            # Fallback: column may not exist yet, use legacy save
            await self._save_cache(repo_id, data)

    async def _detect_modular_structure(self, repo_path: Path) -> None:
        for dir_name, module_type in MODULE_DIRECTORIES.items():
            module_dir = repo_path / "src" / dir_name
            if not module_dir.exists():
                continue

            for item in module_dir.iterdir():
                if item.is_dir():
                    await self._process_module_item(item, module_type)

    async def _process_module_item(self, item: Path, module_type: str) -> None:
        manifest_file = item / MANIFEST_FILES.get(module_type, f"{module_type}.json")
        manifest = {}
        if manifest_file.exists():
            try:
                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            except Exception:
                manifest = {}

        name = manifest.get("name", item.name)
        version = manifest.get("version", "1.0.0")
        namespace = manifest.get("namespace", f"{module_type.capitalize()}__{name}")
        requires = manifest.get("requires", [])
        provides = manifest.get("provides", [])
        hooks = manifest.get("hooks", {})
        services = manifest.get("services_registered", [])

        if module_type == "module":
            hmvc_p = await self._scan_hmvc_p(item) if True else None
            submodules = await self._scan_submodules(item)

            module = ModuleInfo(
                name=name,
                type=module_type,
                path=str(item),
                namespace=namespace,
                version=version,
                bounded_context=namespace.split("\\")[-1] if "\\" in namespace else namespace,
                hmvc_p=hmvc_p,
                requires=requires,
                provides=provides,
                hooks=hooks,
                services_registered=services,
                submodules=submodules,
            )
            self._modules.append(module)
        else:
            info = self._create_type_info(item, module_type, name, version, manifest)
            if module_type == "plugin":
                self._plugins.append(info)
            elif module_type == "widget":
                self._widgets.append(info)
            elif module_type == "component":
                self._components.append(info)

    def _create_type_info(self, item: Path, module_type: str, name: str, version: str, manifest: Dict) -> Any:
        if module_type == "plugin":
            return PluginInfo(
                name=name,
                type=module_type,
                path=str(item),
                version=version,
                hooks_subscribed=manifest.get("hooks_subscribed", manifest.get("hooks", {}).get("filters", [])),
            )
        elif module_type == "widget":
            return WidgetInfo(
                name=name,
                type=module_type,
                path=str(item),
                renders=manifest.get("renders", ""),
                data_source=manifest.get("data_source", ""),
            )
        else:
            return ComponentInfo(
                name=name,
                type=module_type,
                path=str(item),
                ui_framework=manifest.get("ui_framework", ""),
                props=manifest.get("props", []),
            )

    async def _scan_hmvc_p(self, module_path: Path) -> Dict[str, Any]:
        hmvc_p = HMVCPStructure()
        folder_counts = {}

        for folder in HMVC_P_FOLDERS:
            folder_path = module_path / folder
            if folder_path.exists() and folder_path.is_dir():
                count = len([f for f in folder_path.rglob("*") if f.is_file()])
                folder_counts[folder] = count

        hmvc_p.has_controllers = folder_counts.get("Controllers", 0) > 0
        hmvc_p.has_presenters = folder_counts.get("Presenters", 0) > 0
        hmvc_p.has_view_models = folder_counts.get("ViewModels", 0) > 0
        hmvc_p.has_views = folder_counts.get("Views", 0) > 0
        hmvc_p.has_models = folder_counts.get("Models", 0) > 0
        hmvc_p.controller_count = folder_counts.get("Controllers", 0)
        hmvc_p.presenter_count = folder_counts.get("Presenters", 0)
        hmvc_p.view_model_count = folder_counts.get("ViewModels", 0)
        hmvc_p.model_count = folder_counts.get("Models", 0)
        hmvc_p.service_count = folder_counts.get("Services", 0)
        hmvc_p.dto_count = folder_counts.get("DTOs", 0)

        return asdict(hmvc_p)

    async def _scan_submodules(self, module_path: Path) -> List[Dict[str, Any]]:
        submodules = []
        for item in module_path.iterdir():
            if item.is_dir() and item.name not in HMVC_P_FOLDERS and item.name not in MANIFEST_FILES.values():
                hmvc_p = await self._scan_hmvc_p(item)
                submodules.append({
                    "name": item.name,
                    "type": "submodule",
                    "path": str(item),
                    "hmvc_p": hmvc_p,
                })
        return submodules

    async def _detect_core_contracts(self, repo_path: Path) -> None:
        core_path = repo_path / "src" / "core" / "Contracts"
        if not core_path.exists():
            return

        for item in core_path.rglob("*"):
            if item.is_file() and item.suffix in {".py", ".php", ".ts", ".go"}:
                namespace = str(item.relative_to(core_path).parent).replace("/", "\\")
                self._core_contracts.append(CoreContractInfo(
                    name=item.stem,
                    path=str(item),
                    namespace=namespace,
                ))

    async def _build_dependency_graph(self) -> None:
        nodes = []
        edges = []
        in_degree = {}

        for module in self._modules:
            node_id = f"mod_{module.name.lower()}"
            nodes.append({"id": node_id, "type": "module", "name": module.name})
            in_degree[node_id] = 0

        for module in self._modules:
            from_id = f"mod_{module.name.lower()}"
            for req in module.requires:
                to_id = f"mod_{req.lower()}"
                edges.append({"from": from_id, "to": to_id, "relation": "requires"})
                in_degree[to_id] = in_degree.get(to_id, 0) + 1

        G = nx.DiGraph()
        for node in nodes:
            G.add_node(node["id"])
        for edge in edges:
            G.add_edge(edge["from"], edge["to"])

        self._dependency_graph.nodes = nodes
        self._dependency_graph.edges = edges
        self._dependency_graph.circular_dependencies_detected = not nx.is_directed_acyclic_graph(G)

        god_modules = []
        for node_id, degree in in_degree.items():
            if degree >= 5:
                node_data = next((n for n in nodes if n["id"] == node_id), None)
                if node_data:
                    risk = "high" if degree >= 8 else "medium"
                    god_modules.append({"name": node_data["name"], "inbound_dependencies": degree, "risk": risk})
        self._dependency_graph.god_modules = god_modules

    async def _calculate_metrics(self) -> None:
        total_controllers = 0
        total_presenters = 0
        total_view_models = 0
        total_models = 0
        total_services = 0
        total_dtos = 0

        for module in self._modules:
            if module.hmvc_p:
                hmvc_p = module.hmvc_p
                total_controllers += hmvc_p.get("controller_count", 0)
                total_presenters += hmvc_p.get("presenter_count", 0)
                total_view_models += hmvc_p.get("view_model_count", 0)
                total_models += hmvc_p.get("model_count", 0)
                total_services += hmvc_p.get("service_count", 0)
                total_dtos += hmvc_p.get("dto_count", 0)

        self._metrics = Metrics(
            total_controllers=total_controllers,
            total_presenters=total_presenters,
            total_view_models=total_view_models,
            total_models=total_models,
            total_services=total_services,
            total_dtos=total_dtos,
            average_complexity_per_module=round(len(self._modules) / max(1, len(self._modules)), 2) if self._modules else 0.0,
        )

    async def _generate_recommendations(self) -> None:
        for module in self._modules:
            if len(module.requires) >= 3:
                self._recommendations.append(AIRecommendation(
                    severity="info",
                    message=f"Module '{module.name}' depends on {len(module.requires)} modules. Ensure contracts are stable.",
                ))

        for god in self._dependency_graph.god_modules:
            self._recommendations.append(AIRecommendation(
                severity="warning",
                message=f"Module '{god['name']}' has {god['inbound_dependencies']} inbound dependencies. Consider splitting into submodules.",
            ))

        if self._dependency_graph.circular_dependencies_detected:
            self._recommendations.append(AIRecommendation(
                severity="critical",
                message="Circular dependencies detected in the dependency graph. Refactor to break cycles.",
            ))

    def _build_output(self, repo_id: str, repo_path: Path, start_time: datetime) -> Dict[str, Any]:
        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        modules_data = []
        for m in self._modules:
            modules_data.append({
                "name": m.name,
                "type": m.type,
                "path": m.path,
                "namespace": m.namespace,
                "version": m.version,
                "bounded_context": m.bounded_context,
                "hmvc_p": m.hmvc_p,
                "requires": m.requires,
                "provides": m.provides,
                "hooks": m.hooks,
                "services_registered": m.services_registered,
                "submodules": m.submodules,
            })

        plugins_data = [{"name": p.name, "type": p.type, "path": p.path, "version": p.version, "hooks_subscribed": p.hooks_subscribed} for p in self._plugins]
        widgets_data = [{"name": w.name, "type": w.type, "path": w.path, "renders": w.renders, "data_source": w.data_source} for w in self._widgets]
        components_data = [{"name": c.name, "type": c.type, "path": c.path, "ui_framework": c.ui_framework, "props": c.props} for c in self._components]
        core_data = [{"name": c.name, "path": c.path, "namespace": c.namespace} for c in self._core_contracts]

        return {
            "repo_id": repo_id,
            "repo_path": str(repo_path),
            "detected_structure": "CODDY_v1.1",
            "modular_summary": {
                "total_modules": len(self._modules),
                "total_plugins": len(self._plugins),
                "total_widgets": len(self._widgets),
                "total_components": len(self._components),
                "total_services": len(self._modules),
                "core_contracts": len(self._core_contracts),
                "applications": ["app", "api"],
            },
            "modules": modules_data,
            "plugins": plugins_data,
            "widgets": widgets_data,
            "components": components_data,
            "core_contracts": core_data,
            "dependency_graph": asdict(self._dependency_graph),
            "metrics": asdict(self._metrics),
            "ai_recommendations": [{"severity": r.severity, "message": r.message} for r in self._recommendations],
            "duration_ms": duration_ms,
        }

    def _error_response(self, message: str, request_id: str) -> Dict[str, Any]:
        return {
            "success": False,
            "status_code": 400,
            "message": message,
            "data": None,
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
            },
        }
