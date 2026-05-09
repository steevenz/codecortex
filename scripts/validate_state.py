"""
Validate .agents/state.yaml schema compliance for production safety.
"""
import yaml
from pathlib import Path
import sys

SCHEMA = {
    "type": "object",
    "properties": {
        "schema_version": {"type": "string"},
        "active_domain": {"type": "string"},
        "repo_id": {"type": "string"},
        "pending_todos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"]},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]}
                },
                "required": ["content", "status"]
            }
        }
    },
    "required": ["schema_version", "active_domain", "pending_todos"]
}

def validate():
    state_path = Path(__file__).resolve().parents[1] / ".agents" / "state.yaml"
    if not state_path.exists():
        print(f"FAILED: state.yaml not found at {state_path}")
        sys.exit(1)

    with open(state_path, "r") as f:
        data = yaml.safe_load(f) or {}

    required = SCHEMA["required"]
    missing = [k for k in required if k not in data]
    if missing:
        print(f"FAILED: Missing required keys: {missing}")
        sys.exit(1)

    todos = data.get("pending_todos", [])
    for t in todos:
        if t.get("status") not in ("pending", "in_progress", "completed", "cancelled"):
            print(f"FAILED: Invalid status '{t.get('status')}' in todo: {t.get('content')}")
            sys.exit(1)
        if t.get("priority") and t["priority"] not in ("high", "medium", "low"):
            print(f"FAILED: Invalid priority '{t.get('priority')}' in todo: {t.get('content')}")
            sys.exit(1)

    print(f"VALID: state.yaml schema compliant (version={data.get('schema_version')}, todos={len(todos)})")

if __name__ == "__main__":
    validate()
