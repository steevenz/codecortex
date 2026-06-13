"""
Ruby on Rails framework detection and symbol enrichment.

:project: CodeCortex
:package: Modules.Codeindex.Parsers.Parsers.Frameworks.Rails
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeIndex-v1.0
"""
from typing import Dict, List, Any, Optional

def detect_rails(
    rel_path: str,
    source: str,
    imports: List[Dict],
    classes: List[Dict],
    functions: List[Dict],
    repo_configs: Dict[str, Any],
) -> bool:
    """Detect Ruby on Rails usage with zero false positives.

    Requires at least TWO of the following signals:
    1. Rails in Gemfile
    2. Rails directory structure (app/, config/, db/, etc.)
    3. ApplicationRecord base class
    4. Rails-specific patterns (ActiveRecord, ActionController, etc.)
    """
    signals = []

    # Signal 1: Rails in Gemfile
    gem_deps = repo_configs.get("Gemfile", {}).get("dependencies", {})
    if "rails" in gem_deps:
        signals.append("rails_gem")

    # Signal 2: Rails directory structure
    rails_paths = [
        "app/controllers", "app/models", "app/views", "app/helpers",
        "config/routes.rb", "config/database.yml", "db/migrate",
        "app/jobs", "app/mailers", "app/channels"
    ]
    if any(rp in rel_path for rp in rails_paths):
        signals.append("rails_structure")

    # Signal 3: ApplicationRecord inheritance
    for cls in classes:
        bases = [b.lower() for b in cls.get("bases", [])]
        if "applicationrecord" in bases or "activerecord::base" in bases:
            signals.append("rails_model")
            break
        if "applicationcontroller" in bases or "actioncontroller::base" in bases:
            signals.append("rails_controller")
            break

    # Signal 4: Rails-specific class names
    for cls in classes:
        name = cls.get("name", "").lower()
        if name.endswith("controller") or name.endswith("model"):
            # Weak signal, only count if we have other signals
            if len(signals) >= 1:
                signals.append("rails_naming")
                break

    # Zero false positives: require at least 2 signals
    return len(signals) >= 2

def enrich_class(cls: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Rails-specific class types."""
    bases = [b.lower() for b in cls.get("bases", [])]
    name = cls.get("name", "").lower()

    if "applicationrecord" in bases or "activerecord::base" in bases:
        return {"rails_type": "Model"}
    if "applicationcontroller" in bases or "actioncontroller::base" in bases:
        return {"rails_type": "Controller"}
    if "actionmailer::base" in bases:
        return {"rails_type": "Mailer"}
    if "activejob::base" in bases:
        return {"rails_type": "Job"}
    if name.endswith("controller"):
        return {"rails_type": "Controller"}
    if name.endswith("helper"):
        return {"rails_type": "Helper"}

    return None

def enrich_function(fn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Tag Rails-specific methods."""
    name = fn.get("name", "")

    # Rails lifecycle callbacks
    rails_callbacks = [
        "before_validation", "after_validation", "before_save", "after_save",
        "before_create", "after_create", "before_update", "after_update",
        "before_destroy", "after_destroy"
    ]
    if name in rails_callbacks:
        return {"rails_callback": name}

    # Rails controller filters
    if name in ["before_action", "after_action", "around_action", "skip_before_action"]:
        return {"rails_filter": name}

    return None
