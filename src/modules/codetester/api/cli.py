"""
CodeTester CLI — QA test execution and analysis commands.

:project: CodeCortex
:package: Modules.Codetester.Api.Cli
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CrossStack-v1.0
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

DOMAIN = "codetester"
ALIASES = ["qa", "tester"]


def output(data: Any, pretty: bool = True) -> None:
    """Print JSON to stdout as UTF-8 bytes (avoids Windows cp1252 issues)."""
    kwargs: Dict[str, Any] = {"ensure_ascii": False}
    if pretty:
        kwargs["indent"] = 2
    text = json.dumps(data, **kwargs, default=str)
    buf = sys.stdout.buffer
    buf.write(text.encode("utf-8", errors="replace"))
    buf.write(b"\n")
    buf.flush()


def ok(message: str, data: Any = None) -> Dict[str, Any]:
    return {"success": True, "status_code": 200, "message": message, "data": data}


def err(message: str, code: str = "CLI_ERROR", status: int = 400) -> Dict[str, Any]:
    return {"success": False, "status_code": status, "message": message, "data": {"explanation": f"No relevant data is available because an error occurred: {message}"}, "error_code": code}


def run_async(coro):
    """Safely run a coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)


# ══════════════════════════════════════════════════════════════
# CODETESTER (6 actions)
# ══════════════════════════════════════════════════════════════


def cmd_qa_run(args_ns: argparse.Namespace) -> Dict:
    """Run tests with auto-detected or specified framework."""
    from src.modules.codetester.services.tester import Tester
    from src.modules.codetester.core.dtos import CodeTesterRequest
    from src.main import create_orchestrator

    orch = create_orchestrator()
    try:
        service = Tester(db=orch.db)
        request = CodeTesterRequest(
            action="run",
            target_path=args_ns.target,
            test_framework=getattr(args_ns, "framework", "auto"),
            test_filter=getattr(args_ns, "filter", None),
            test_names=getattr(args_ns, "names", None),
            categories=getattr(args_ns, "categories", None),
            max_duration=getattr(args_ns, "max_duration", 300),
        )
        result = service.run_tests(request)
        return ok(
            f"Tests completed: {result.summary.get('passed', 0)} passed, "
            f"{result.summary.get('failed', 0)} failed, "
            f"{result.summary.get('skipped', 0)} skipped",
            {"framework": result.framework, "summary": result.summary, "results": result.results, "duration": result.duration_seconds},
        )
    except FileNotFoundError as e:
        return err(str(e), "CT_404", 404)
    except ValueError as e:
        return err(str(e), "CT_400", 400)
    except Exception as e:
        return err(f"Test run failed: {e}", "CT_500", 500)
    finally:
        orch.db.close()


def cmd_qa_coverage(args_ns: argparse.Namespace) -> Dict:
    """Generate coverage analysis with recommendations."""
    from src.modules.codetester.services.tester import Tester
    from src.modules.codetester.core.dtos import CodeTesterRequest
    from src.main import create_orchestrator

    orch = create_orchestrator()
    try:
        service = Tester(db=orch.db)
        request = CodeTesterRequest(
            action="coverage",
            target_path=args_ns.target,
            test_framework=getattr(args_ns, "framework", "auto"),
            coverage_format=getattr(args_ns, "format", "summary"),
        )
        result = service.run_coverage(request)
        return ok(
            f"Coverage: {result.overall_coverage:.1f}% overall",
            {"overall_coverage": result.overall_coverage, "files": result.files, "recommendations": result.recommendations},
        )
    except FileNotFoundError as e:
        return err(str(e), "CT_404", 404)
    except Exception as e:
        return err(f"Coverage failed: {e}", "CT_500", 500)
    finally:
        orch.db.close()


def cmd_qa_discover(args_ns: argparse.Namespace) -> Dict:
    """Discover all tests in a project with markers and categories."""
    from src.modules.codetester.services.tester import Tester
    from src.modules.codetester.core.dtos import CodeTesterRequest
    from src.main import create_orchestrator

    orch = create_orchestrator()
    try:
        service = Tester(db=orch.db)
        request = CodeTesterRequest(
            action="discover",
            target_path=args_ns.target,
            test_framework=getattr(args_ns, "framework", "auto"),
        )
        result = service.discover_tests(request)
        return ok(
            f"Discovered {len(result.tests)} tests (framework: {result.framework})",
            {"framework": result.framework, "test_files": result.test_files, "tests": result.tests, "markers": result.markers, "categories": result.categories},
        )
    except FileNotFoundError as e:
        return err(str(e), "CT_404", 404)
    except Exception as e:
        return err(f"Discover failed: {e}", "CT_500", 500)
    finally:
        orch.db.close()


def cmd_qa_generate(args_ns: argparse.Namespace) -> Dict:
    """Generate test code for a specific function or symbol."""
    from src.modules.codetester.services.tester import Tester
    from src.modules.codetester.core.dtos import CodeTesterRequest
    from src.main import create_orchestrator

    orch = create_orchestrator()
    try:
        service = Tester(db=orch.db)
        request = CodeTesterRequest(
            action="generate",
            target_path=args_ns.target,
            target_symbol=getattr(args_ns, "symbol", None),
        )
        result = service.generate_test(request)
        return ok(
            f"Test generated for '{result.target_symbol}' in {result.test_file}",
            {"target_file": result.target_file, "test_file": result.test_file, "test_code": result.test_code, "recommendations": result.recommendations},
        )
    except FileNotFoundError as e:
        return err(str(e), "CT_404", 404)
    except Exception as e:
        return err(f"Generate failed: {e}", "CT_500", 500)
    finally:
        orch.db.close()


def cmd_qa_diagnose(args_ns: argparse.Namespace) -> Dict:
    """Analyze test failures with root cause and suggestions."""
    from src.modules.codetester.services.tester import Tester
    from src.modules.codetester.core.dtos import CodeTesterRequest
    from src.main import create_orchestrator

    orch = create_orchestrator()
    try:
        service = Tester(db=orch.db)
        request = CodeTesterRequest(
            action="diagnose",
            target_path=args_ns.target,
            test_framework=getattr(args_ns, "framework", "auto"),
        )
        result = service.diagnose_failure(request)
        failure_name = result.failure.get("name", "none") if result.failure else "none"
        if failure_name == "none":
            return ok("No failures found to diagnose", {"failure": {}, "suggestions": []})
        return ok(
            f"Diagnosis for failure: {failure_name}",
            {"failure": result.failure, "root_cause": result.root_cause, "suggestions": result.suggestions, "related_source": result.related_source},
        )
    except FileNotFoundError as e:
        return err(str(e), "CT_404", 404)
    except Exception as e:
        return err(f"Diagnose failed: {e}", "CT_500", 500)
    finally:
        orch.db.close()


def cmd_qa_status(args_ns: argparse.Namespace) -> Dict:
    """Poll the status and results of a background QA task."""
    from src.modules.codetester.services.qa import QA
    from src.main import create_orchestrator

    orch = create_orchestrator()
    try:
        service = QA(db=orch.db)
        result = service.get_task_status(args_ns.task_id)
        status = result.get("status", "unknown")
        if status == "completed":
            return ok(f"Task {args_ns.task_id} completed", result)
        elif status == "failed":
            return err(f"Task {args_ns.task_id} failed", "CT_TASK_FAILED", 500)
        elif status == "running":
            return ok(f"Task {args_ns.task_id} is running", result)
        else:
            return ok(f"Task {args_ns.task_id} status: {status}", result)
    except ValueError as e:
        return err(str(e), "CT_404", 404)
    except Exception as e:
        return err(f"Status check failed: {e}", "CT_500", 500)
    finally:
        orch.db.close()


# ══════════════════════════════════════════════════════════════
# COMMAND REGISTRY
# ══════════════════════════════════════════════════════════════

QA_COMMANDS = {
    "run": cmd_qa_run,
    "coverage": cmd_qa_coverage,
    "discover": cmd_qa_discover,
    "generate": cmd_qa_generate,
    "diagnose": cmd_qa_diagnose,
    "status": cmd_qa_status,
}


def build_parser(subparsers) -> None:
    p = subparsers.add_parser("codetester", aliases=["qa", "tester"], help="QA test execution and analysis")
    sp = p.add_subparsers(dest="qa_action", required=True)

    # run
    r = sp.add_parser("run", help="Run tests with auto-detected or specified framework")
    r.add_argument("target", help="Path to project or test directory/file")
    r.add_argument("--framework", default="auto", help="Test framework (auto, pytest, jest, go_test, cargo_test, etc.)")
    r.add_argument("--filter", help="Filter expression (marker, file pattern, test name)")
    r.add_argument("--names", nargs="+", help="List of specific test names to run")
    r.add_argument("--categories", nargs="+", help="Test categories (unit, integration, e2e)")
    r.add_argument("--max-duration", type=int, default=300, help="Max execution time in seconds (10-600)")

    # coverage
    c = sp.add_parser("coverage", help="Generate coverage analysis")
    c.add_argument("target", help="Path to project directory")
    c.add_argument("--framework", default="auto", help="Test framework")
    c.add_argument("--format", choices=["summary", "detailed", "json"], default="summary", help="Coverage output format")

    # discover
    d = sp.add_parser("discover", help="Discover all tests in a project")
    d.add_argument("target", help="Path to project directory")
    d.add_argument("--framework", default="auto", help="Test framework")

    # generate
    g = sp.add_parser("generate", help="Generate test code for a function")
    g.add_argument("target", help="Path to source file")
    g.add_argument("--symbol", help="Function/symbol name to generate tests for")

    # diagnose
    diag = sp.add_parser("diagnose", help="Diagnose test failures")
    diag.add_argument("target", help="Path to project or test directory")
    diag.add_argument("--framework", default="auto", help="Test framework")

    # status
    s = sp.add_parser("status", help="Check background task status")
    s.add_argument("task_id", help="Background task UUID")
