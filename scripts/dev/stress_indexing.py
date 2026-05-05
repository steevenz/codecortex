import json
import os
import time
from pathlib import Path

from src.main import index_codebase, reindex_codebase


def main() -> None:
    root = Path(os.getenv("CODECORTEX_STRESS_ROOT") or ".").resolve()
    runs_raw = (os.getenv("CODECORTEX_STRESS_RUNS") or "3").strip()
    runs = int(runs_raw) if runs_raw.isdigit() else 3

    t0 = time.perf_counter()
    first = index_codebase(str(root))
    t1 = time.perf_counter()

    results = {
        "root": str(root),
        "initial_seconds": round(t1 - t0, 3),
        "initial_success": bool(first.get("success")),
        "reindex_runs": [],
    }

    for _ in range(runs):
        s0 = time.perf_counter()
        r = reindex_codebase(str(root))
        s1 = time.perf_counter()
        results["reindex_runs"].append(
            {
                "seconds": round(s1 - s0, 3),
                "success": bool(r.get("success")),
                "skipped": bool((r.get("data") or {}).get("skipped")),
                "changed_files": int((r.get("data") or {}).get("changed_files") or 0),
            }
        )

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

