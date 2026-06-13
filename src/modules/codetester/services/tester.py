"""
Tester - Orchestrates test run, coverage, discover, generate, and diagnose actions.

:project: CodeCortex
:package: Modules.Codetester.Services.Tester
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeTester-v1.0
"""

import os
import re
import uuid
import json
import time
import ast
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from src.core.logging import get_logger
from src.core.logging.event_logger import log_event
from src.core.database import DatabaseManager
from src.modules.codetester.core.dtos import (
    CodeTesterRequest,
    FrameworkDetection,
    TestRunData,
    CoverageData,
    DiscoveryData,
    GenerateData,
    DiagnoseData,
)
from src.modules.codetester.core.framework import detect_framework, get_run_command
from src.modules.codetester.test_adapters.pytest import Pytest
from src.modules.codetester.test_adapters.flake8 import Flake8
from src.modules.codetester.test_adapters.unittest import Unittest
from src.modules.codetester.test_adapters.jest import Jest
from src.modules.codetester.test_adapters.phpunit import PHPUnit
from src.modules.codetester.test_adapters.npm import Npm
from src.modules.codetester.test_adapters.pnpm import Pnpm
from src.modules.codetester.test_adapters.vitest import Vitest
from src.modules.codetester.test_adapters.yarn import Yarn
from src.modules.codetester.test_adapters.go_test import GoTest
from src.modules.codetester.test_adapters.cargo_test import CargoTest
from src.modules.codetester.test_adapters.swift_test import SwiftTest
from src.modules.codetester.test_adapters.kotlin_test import KotlinTest
from src.modules.codetester.test_adapters.sbt_test import SbtTest
from src.modules.codetester.test_adapters.maven_test import MavenTest
from src.modules.codetester.test_adapters.ruby_test import RubyTest
from src.modules.codetester.test_adapters.flutter_test import FlutterTest
from src.modules.codetester.test_adapters.dart_test import DartTest
from src.modules.codetester.test_adapters.haskell_test import HaskellTest
from src.modules.codetester.test_adapters.elixir_test import ElixirTest
from src.modules.codetester.test_adapters.dotnet_test import DotNetTest
from src.modules.codetester.test_adapters.perl_test import PerlTest
from src.modules.codetester.test_adapters.stylelint import Stylelint
from src.modules.codetester.test_adapters.ctest import Ctest

logger = get_logger("CodeCortex.Domain.CodeTester")

class Tester:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self._adapters: Dict[str, Any] = {}
        self._init_adapters()
        self._task_store: Dict[str, Dict[str, Any]] = {}

    def _init_adapters(self):
        adapters = [
            Pytest(),
            Flake8(),
            Unittest(),
            Jest(),
            PHPUnit(),
            Npm(),
            Pnpm(),
            Vitest(),
            Yarn(),
            GoTest(),
            CargoTest(),
            SwiftTest(),
            KotlinTest(),
            SbtTest(),
            MavenTest(),
            RubyTest(),
            FlutterTest(),
            DartTest(),
            HaskellTest(),
            ElixirTest(),
            DotNetTest(),
            PerlTest(),
            Stylelint(),
            Ctest(),
        ]
        for a in adapters:
            self._adapters[a.get_name()] = a

    def _get_adapter(self, adapter_key: str):
        adapter = self._adapters.get(adapter_key)
        if not adapter:
            raise ValueError(f"Unsupported test framework: {adapter_key}")
        return adapter

    def _log_event(self, level: str, event_code: str, context: Dict, request_id: Optional[str] = None):
        log_event(level, event_code, context, request_id=request_id, logger=getattr(self, 'logger', None))

    def run_tests(self, request: CodeTesterRequest) -> TestRunData:
        start = time.time()
        abs_path = os.path.abspath(request.target_path)
        detection = detect_framework(abs_path, request.test_framework if request.test_framework != "auto" else None)
        adapter = self._get_adapter(detection.adapter_key)

        extra_args = None
        if request.test_filter:
            extra_args = f"-k {request.test_filter}"
        if request.test_names:
            names_filter = " or ".join(request.test_names)
            extra_args = f"-k '{names_filter}'" if extra_args is None else f"{extra_args} or {names_filter}"
        if request.categories:
            cat_filter = " or ".join(f"markers[{c}]" for c in request.categories)
            extra_args = f"-m '{cat_filter}'" if extra_args is None else f"{extra_args} and -m '{cat_filter}'"

        raw = adapter.run(abs_path, None, extra_args)
        parsed = adapter.parse_results(raw)

        test_run_id = f"tr_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        return TestRunData(
            action="run",
            target_path=request.target_path,
            framework=detection.framework,
            duration_seconds=time.time() - start,
            summary=parsed.get("summary", {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0}),
            results=parsed.get("results", []),
            test_run_id=test_run_id,
        )

    def run_coverage(self, request: CodeTesterRequest) -> CoverageData:
        abs_path = os.path.abspath(request.target_path)
        detection = detect_framework(abs_path, request.test_framework if request.test_framework != "auto" else None)
        adapter = self._get_adapter(detection.adapter_key)
        raw = adapter.run_with_coverage(abs_path)
        cov = raw.get("coverage", {})
        return CoverageData(
            action="coverage",
            target_path=request.target_path,
            overall_coverage=cov.get("overall_coverage", 0.0),
            files=cov.get("files", []),
            recommendations=cov.get("recommendations", []),
        )

    def discover_tests(self, request: CodeTesterRequest) -> DiscoveryData:
        abs_path = os.path.abspath(request.target_path)
        detection = detect_framework(abs_path, request.test_framework if request.test_framework != "auto" else None)
        adapter = self._get_adapter(detection.adapter_key)
        discovered = adapter.discover(abs_path)

        return DiscoveryData(
            action="discover",
            target_path=request.target_path,
            framework=detection.framework,
            test_files=discovered.get("test_files", []),
            tests=discovered.get("tests", []),
            markers=discovered.get("markers", []),
            categories=discovered.get("categories", {}),
        )

    def generate_test(self, request: CodeTesterRequest) -> GenerateData:
        abs_path = os.path.abspath(request.target_path)
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(f"Target file not found: {abs_path}")

        source_code = Path(abs_path).read_text(encoding="utf-8")
        symbol = request.target_symbol or Path(abs_path).stem

        tree = ast.parse(source_code)
        func_body = self._extract_function_source(source_code, tree, symbol)
        test_code = self._generate_test_code(symbol, func_body)

        test_dir = self._find_test_dir(abs_path)
        os.makedirs(test_dir, exist_ok=True)
        test_filename = f"test_{Path(abs_path).name}"
        test_path = os.path.join(test_dir, test_filename)

        existing_lines = 0
        if os.path.exists(test_path):
            with open(test_path, "r", encoding="utf-8") as f:
                existing_lines = len(f.readlines())

        with open(test_path, "a", encoding="utf-8") as f:
            if existing_lines > 0:
                f.write("\n\n")
            f.write(test_code)

        test_line_start = existing_lines + 1
        first_test_line = test_code.split("\n")[0] if test_code else ""

        return GenerateData(
            action="generate",
            target_file=abs_path,
            target_symbol=symbol,
            test_file=test_path,
            test_line_start=test_line_start,
            test_code=test_code,
            recommendations=[
                f"Verify test file at {test_path}",
                f"Run: pytest {test_path} -k {symbol}",
            ],
        )

    def diagnose_failure(self, request: CodeTesterRequest) -> DiagnoseData:
        abs_path = os.path.abspath(request.target_path)
        detection = detect_framework(abs_path, request.test_framework if request.test_framework != "auto" else None)
        adapter = self._get_adapter(detection.adapter_key)

        raw = adapter.run(abs_path)
        parsed = adapter.parse_results(raw)

        failures = [r for r in parsed.get("results", []) if r.get("status") in ("failed", "error")]
        failure_data = {}
        root_cause = {}
        suggestions = []
        related_source = None

        if failures:
            f = failures[0]
            failure_data = {
                "name": f.get("name", ""),
                "file": f.get("file", ""),
                "line": f.get("line", 0),
                "message": (f.get("failure") or {}).get("message", ""),
                "traceback": (f.get("failure") or {}).get("traceback", ""),
            }

            tb = failure_data.get("traceback", "")
            source_match = re.search(r'File "([^"]+)", line (\d+)', tb)
            if source_match:
                related_source = {
                    "file": source_match.group(1),
                    "line": int(source_match.group(2)),
                }
                error_line = related_source["line"]
                sf = related_source["file"]
                if os.path.exists(sf):
                    with open(sf, "r", encoding="utf-8") as sfh:
                        lines = sfh.readlines()
                    if 0 <= error_line - 1 < len(lines):
                        related_source["code"] = lines[error_line - 1].strip()
                    start = max(0, error_line - 3)
                    end = min(len(lines), error_line + 2)
                    related_source["context"] = "".join(lines[start:end])

            root_cause = {
                "type": "assertion_failure",
                "test_file": f.get("file", ""),
                "test_line": f.get("line", 0),
                "expected": "",
                "actual": "",
            }
            suggestions.append("Check the assertion on line " + str(f.get("line", 0)))
            suggestions.append("Verify test inputs produce expected outputs")

        return DiagnoseData(
            action="diagnose",
            target_path=request.target_path,
            failure=failure_data,
            root_cause=root_cause,
            suggestions=suggestions,
            related_source=related_source,
        )

    def run_async_task(self, request: CodeTesterRequest) -> Dict[str, Any]:
        task_id = str(uuid.uuid4())
        self._task_store[task_id] = {"status": "pending", "result": None}

        import threading
        thread = threading.Thread(
            target=self._execute_async,
            args=(task_id, request),
        )
        thread.start()

        return {"status": "accepted", "task_id": task_id, "message": "Task started in background."}

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        task = self._task_store.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        return task

    def _execute_async(self, task_id: str, request: CodeTesterRequest):
        try:
            self._task_store[task_id]["status"] = "running"
            if request.action == "run":
                result = self.run_tests(request)
            elif request.action == "coverage":
                result = self.run_coverage(request)
            elif request.action == "discover":
                result = self.discover_tests(request)
            elif request.action == "generate":
                result = self.generate_test(request)
            elif request.action == "diagnose":
                result = self.diagnose_failure(request)
            else:
                raise ValueError(f"Unknown action: {request.action}")
            self._task_store[task_id]["status"] = "completed"
            self._task_store[task_id]["result"] = result
        except Exception as e:
            self._task_store[task_id]["status"] = "failed"
            self._task_store[task_id]["result"] = {"error": str(e)}

    def _extract_function_source(self, source_code: str, tree: ast.AST, symbol: str) -> Optional[str]:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
                lines = source_code.splitlines()
                start_line = node.lineno - 1
                end_line = node.end_lineno if hasattr(node, "end_lineno") and node.end_lineno else start_line + 1
                return "\n".join(lines[start_line:end_line])
        return None

    def _generate_test_code(self, symbol: str, func_body: Optional[str]) -> str:
        params = []
        has_return = False
        if func_body:
            try:
                tree = ast.parse(func_body)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        for arg in node.args.args:
                            if arg.arg != "self":
                                params.append(arg.arg)
                    if isinstance(node, ast.Return):
                        has_return = True
            except SyntaxError:
                pass

        param_assignments = "\n    ".join(
            f"{p} = None  # Parameter initialized with None, update as needed" for p in params
        ) if params else "    pass"

        test_lines = [
            f"def test_{symbol}_success():",
        ]
        if param_assignments != "    pass":
            test_lines.append(f"    {param_assignments}")
        if has_return:
            test_lines.append(f"    result = {symbol}({', '.join(params)})")
            test_lines.append("    assert result is not None")
        else:
            if params:
                test_lines.append(f"    {symbol}({', '.join(params)})")
            test_lines.append("    assert True")

        test_lines.extend([
            "",
            "",
            f"def test_{symbol}_edge_case():",
        ])
        if param_assignments != "    pass":
            test_lines.append(f"    {param_assignments}")
        if has_return:
            if params:
                test_lines.append(f"    result = {symbol}({', '.join(params)})")
            else:
                test_lines.append(f"    result = {symbol}()")
            test_lines.append("    assert result is not None")
        else:
            if params:
                test_lines.append(f"    {symbol}({', '.join(params)})")
            else:
                test_lines.append(f"    {symbol}()")
            test_lines.append("    assert True")

        return "\n".join(test_lines)

    def _find_test_dir(self, source_path: str) -> str:
        source_dir = os.path.dirname(source_path)
        candidates = [
            os.path.join(source_dir, "tests"),
            os.path.join(source_dir, "..", "tests"),
            os.path.join(os.path.dirname(source_dir), "tests"),
        ]
        for c in candidates:
            resolved = os.path.abspath(c)
            if os.path.isdir(resolved):
                return resolved
        tests_dir = os.path.join(source_dir, "tests")
        os.makedirs(tests_dir, exist_ok=True)
        return tests_dir
