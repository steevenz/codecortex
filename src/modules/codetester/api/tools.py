"""
Module tools – Single Responsibility: Register code_tester MCP tool with 5 actions.
Actions: run, coverage, discover, generate, diagnose.

:project: CodeCortex
:package: Modules.Codetester.Api.Tools
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeTester-v1.0
"""
from __future__ import annotations
import dataclasses
import time
from typing import Optional, List, Dict, Any, Callable
from mcp.server.fastmcp import FastMCP
from src.core import api_response, new_request_id
from src.core.utils.serialization import to_dict
from src.modules.codetester.core.dtos import CodeTesterRequest

def register_tools(mcp: FastMCP, orchestrator_factory: Callable[..., Any]) -> None:
    """
    Register consolidated code_tester tool with 5 standard actions.
    """

    @mcp.tool()
    async def qa_status(
        task_id: str,
    ) -> Dict[str, Any]:
        """
        Poll the status and results of a background QA task.

        @param task_id: UUID of the background task returned by code_tester async_mode.
        @return: Task status and result (pending | running | completed | failed).
        """
        from src.modules.codetester.services.qa import QA
        orchestrator = orchestrator_factory()
        service = QA(db=orchestrator.db)
        request_id = new_request_id()

        try:
            result = service.get_task_status(task_id)
            return api_response(success=True, insight="qa_status", status_code=200,
                message=f"Task status: {result.get('status', 'unknown')}",
                data=result, request_id=request_id)
        except ValueError as e:
            return api_response(success=False, status_code=404,
                message=str(e), data=None,
                request_id=request_id, error_code="CT_404")
        except Exception as e:
            return api_response(success=False, status_code=500,
                message=f"qa_status failed: {e}", data=None,
                request_id=request_id, error_code="CT_500")

    @mcp.tool()
    async def code_tester(
        action: str,
        target_path: str,
        test_framework: str = "auto",
        test_filter: Optional[str] = None,
        test_names: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        coverage_format: str = "summary",
        target_symbol: Optional[str] = None,
        max_duration: int = 300,
        async_mode: bool = False,
        follow: bool = False,
    ) -> Dict[str, Any]:
        """
        Comprehensive test assistant: run, analyze coverage, discover tests, generate tests, diagnose failures.

        @param action: "run" | "coverage" | "discover" | "generate" | "diagnose"
        @param target_path: Path ke direktori proyek atau file test/source (wajib).
        @param test_framework: "auto" | "pytest" | "jest" | "go_test" | "cargo_test" | "vitest" | ...
        @param test_filter: Filter test (marker, file pattern, test name expression).
        @param test_names: Daftar test name spesifik untuk dijalankan.
        @param categories: Kategori test ("unit", "integration", "e2e").
        @param coverage_format: "summary" | "detailed" | "json".
        @param target_symbol: Symbol/function untuk generate test (action "generate").
        @param max_duration: Batas waktu eksekusi (detik, max 600).
        @param async_mode: Jalankan secara async (return task_id).
        @param follow: Tunggu hasil async hingga selesai.
        @return: Structured JSON response sesuai action.
        """
        from src.modules.codetester.services.tester import Tester
        orchestrator = orchestrator_factory()
        service = Tester(db=orchestrator.db)

        request_id = new_request_id()
        start_time = time.time()

        if not target_path:
            return api_response(success=False, status_code=400,
                message="target_path is required", data=None,
                request_id=request_id, error_code="CT_001")

        allowed_actions = ["run", "coverage", "discover", "generate", "diagnose"]
        if action not in allowed_actions:
            return api_response(success=False, status_code=400,
                message=f"action must be one of {allowed_actions}", data=None,
                request_id=request_id, error_code="CT_002")

        max_duration = min(max(max_duration, 10), 600)

        request = CodeTesterRequest(
            action=action,
            target_path=target_path,
            test_framework=test_framework,
            test_filter=test_filter,
            test_names=test_names,
            categories=categories,
            coverage_format=coverage_format,
            target_symbol=target_symbol,
            max_duration=max_duration,
            async_mode=async_mode,
            follow=follow,
        )

        try:
            if async_mode and not follow:
                task = service.run_async_task(request)
                return api_response(success=True, insight="code_tester", status_code=202,
                    message="Task started in background",
                    data=task, request_id=request_id)

            result = None
            if action == "run":
                result = service.run_tests(request)
            elif action == "coverage":
                result = service.run_coverage(request)
            elif action == "discover":
                result = service.discover_tests(request)
            elif action == "generate":
                result = service.generate_test(request)
            elif action == "diagnose":
                result = service.diagnose_failure(request)

            elapsed = time.time() - start_time
            message = _build_message(action, result, elapsed)
            data = _build_data(result)

            # Mark test as synced
            repo_id_effective = target_path or ""
            try:
                from src.core.database.integrity import FileIntegrity
                resolved_id = orchestrator.get_repo_id(repo_id_effective) if repo_id_effective else None
                if resolved_id:
                    FileIntegrity(orchestrator.db).mark_synced(resolved_id, "test")
            except Exception:
                pass

            return api_response(success=True, insight="code_tester", status_code=200,
                message=message, data=data, request_id=request_id)

        except FileNotFoundError as e:
            return api_response(success=False, status_code=404,
                message=str(e), data=None,
                request_id=request_id, error_code="CT_404")
        except ValueError as e:
            return api_response(success=False, status_code=400,
                message=str(e), data=None,
                request_id=request_id, error_code="CT_400")
        except Exception as e:
            return api_response(success=False, status_code=500,
                message=f"code_tester failed: {e}", data=None,
                request_id=request_id, error_code="CT_500")

def _build_message(action: str, result, elapsed: float) -> str:
    summary = getattr(result, "summary", None)
    framework = getattr(result, "framework", None)

    if action == "run" and summary:
        return (
            f"Test run completed: {summary.get('passed', 0)} passed, "
            f"{summary.get('failed', 0)} failed, {summary.get('skipped', 0)} skipped "
            f"({elapsed:.1f}s)"
        )
    if action == "coverage":
        cov = getattr(result, "overall_coverage", 0)
        return f"Coverage analysis completed: {cov:.1f}% overall coverage"
    if action == "discover":
        tests = getattr(result, "tests", [])
        return f"Discovered {len(tests)} tests (framework: {framework})"
    if action == "generate":
        tf = getattr(result, "test_file", "")
        ts = getattr(result, "target_symbol", "")
        return f"Test generated for '{ts}' and saved to {tf}"
    if action == "diagnose":
        failure_dict = getattr(result, "failure", {}) or {}
        fname = failure_dict.get("name", "none") if isinstance(failure_dict, dict) else "none"
        if fname == "none":
            return "No failures found to diagnose"
        return f"Diagnosis completed for failure: {fname}"
    return f"{action} completed ({elapsed:.1f}s)"

def _build_data(result) -> Dict[str, Any]:
    if result is None:
        return {}
    return to_dict(result)
