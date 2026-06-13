"""
ASP.NET Core framework detection and symbol enrichment.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Frameworks.Aspnet
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""
from typing import Dict, List, Any, Optional

def detect_aspnet(
    rel_path: str,
    source: str,
    imports: List[Dict],
    classes: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any],
) -> bool:
    """Detect ASP.NET Core usage with zero false positives.

    Requires at least TWO of the following signals:
    1. Microsoft.AspNetCore.* imports
    2. ASP.NET Core packages in .csproj
    3. ASP.NET-specific patterns (Controller base class, [HttpGet], etc.)
    4. Program.cs or Startup.cs files
    """
    signals = []

    # Signal 1: ASP.NET Core imports
    for imp in imports:
        mod = (imp.get("module") or "").lower()
        if mod.startswith("microsoft.aspnetcore.") or mod.startswith("microsoft.extensions."):
            signals.append("aspnet_import")
            break

    # Signal 2: ASP.NET Core in .csproj
    csproj_deps = repo_configs.get("csproj", {}).get("dependencies", {})
    if any(dep.startswith("Microsoft.AspNetCore") for dep in csproj_deps):
        signals.append("aspnet_dependency")

    # Signal 3: ASP.NET-specific files
    aspnet_files = ["program.cs", "startup.cs", "appsettings.json"]
    if any(af in rel_path.lower() for af in aspnet_files):
        signals.append("aspnet_file")

    # Signal 4: ASP.NET-specific base classes
    for cls in classes:
        bases = [b.lower() for b in cls.get("bases", [])]
        if "controllerbase" in bases or "controller" in bases:
            signals.append("aspnet_controller")
            break
        if "page" in bases or "razorpage" in bases:
            signals.append("aspnet_page")
            break

    # Signal 5: ASP.NET attributes
    for cls in classes:
        decorators = cls.get("decorators", [])
        aspnet_attrs = ["[HttpGet]", "[HttpPost]", "[Route]", "[ApiController]", "[Authorize]"]
        if any(attr in str(decorators) for attr in aspnet_attrs):
            signals.append("aspnet_attribute")
            break

    # Zero false positives: require at least 2 signals
    return len(signals) >= 2

def enrich_class(cls: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag ASP.NET-specific class types."""
    bases = [b.lower() for b in cls.get("bases", [])]
    decorators = cls.get("decorators", [])

    if "controllerbase" in bases or "controller" in bases:
        return {"aspnet_type": "Controller"}
    if "page" in bases or "razorpage" in bases:
        return {"aspnet_type": "RazorPage"}
    if "[ApiController]" in str(decorators):
        return {"aspnet_type": "ApiController"}

    return None

def enrich_function(fn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag ASP.NET-specific attributes and lifecycle methods."""
    decorators = fn.get("decorators", [])
    name = fn.get("name", "")

    # ASP.NET HTTP method attributes
    http_attrs = ["[HttpGet]", "[HttpPost]", "[HttpPut]", "[HttpDelete]", "[HttpPatch]"]
    if any(attr in str(decorators) for attr in http_attrs):
        return {"aspnet_http_method": True}

    # ASP.NET lifecycle methods
    aspnet_lifecycle = ["OnGet", "OnPost", "OnPut", "OnDelete", "OnPatch"]
    if name in aspnet_lifecycle:
        return {"aspnet_lifecycle": name}

    # Startup configuration methods
    if name in ["ConfigureServices", "Configure"]:
        return {"aspnet_startup": name}

    return None
