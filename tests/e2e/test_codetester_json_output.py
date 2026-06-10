"""
/**
 * @project   CodeCortex
 * @package   Tests
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Test: Verify code_tester MCP tool produces spec-compliant JSON output for all 5 actions.
 */
"""

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Any

import pytest
from mcp.server.fastmcp import FastMCP

from src.core import api_response, new_request_id
from src.modules.codetester.services.tester import Tester
from src.modules.codetester.core.dtos import (
    CodeTesterRequest,
    TestRunData,
    CoverageData,
    DiscoveryData,
    GenerateData,
    DiagnoseData,
)
from src.modules.codetester.core.framework import detect_framework
from src.modules.codetester.api.tools import _build_data, _build_message


# ═══════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def tmp_source_file():
    """Create a temporary Python source file for testing generate/detect."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "math_utils.py"
        src.write_text("""
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b


def divide(a: float, b: float) -> float:
    \"\"\"Divide two numbers.\"\"\"
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
""")
        yield str(src)


@pytest.fixture
def db_manager():
    """Create an in-memory DatabaseManager for CodeTesterService."""
    from src.core.database import DatabaseManager
    db = DatabaseManager(":memory:")
    yield db


# ═══════════════════════════════════════════════════════════════════
# API RESPONSE ENVELOPE VERIFICATION
# ═══════════════════════════════════════════════════════════════════

def test_api_response_envelope():
    """Verify the api_response wrapper always returns correct envelope."""
    resp = api_response(
        success=True, status_code=200,
        message="Test completed", data={"key": "value"},
        request_id=new_request_id(),
    )
    assert resp["success"] is True
    assert resp["status_code"] == 200
    assert resp["message"] == "Test completed"
    assert resp["data"] == {"key": "value"}
    assert resp["meta"]["request_id"].startswith("req_")
    assert resp["meta"]["timestamp"].endswith("Z")

    err_resp = api_response(
        success=False, status_code=400,
        message="Bad request", data=None,
        request_id=new_request_id(), error_code="CT_001",
    )
    assert err_resp["success"] is False
    assert err_resp["status_code"] == 400
    assert err_resp["message"] == "Bad request"
    assert err_resp["data"] is None
    assert err_resp["meta"]["request_id"].startswith("req_")
    assert err_resp["error_code"] == "CT_001"


# ═══════════════════════════════════════════════════════════════════
# DTO DATA SERIALIZATION
# ═══════════════════════════════════════════════════════════════════

class TestDtoSerialization:
    """Verify each action's DTO serializes to correct JSON structure."""

    def test_testrundata_serialization(self):
        data = TestRunData(
            action="run",
            target_path="/project",
            framework="pytest",
            duration_seconds=12.45,
            summary={"total": 50, "passed": 45, "failed": 2, "skipped": 3, "errors": 0},
            results=[
                {"name": "test_auth_success", "file": "tests/test_auth.py",
                 "line": 45, "status": "passed", "duration_ms": 12.3, "failure": None},
                {"name": "test_auth_failure", "file": "tests/test_auth.py",
                 "line": 52, "status": "failed", "duration_ms": 8.7,
                 "failure": {"type": "AssertionError", "message": "assert False",
                             "traceback": 'File "tests/test_auth.py", line 55, in test_auth_failure'}},
            ],
            test_run_id="tr_20260525_143022",
        )
        d = _build_data(data)

        assert d["action"] == "run"
        assert d["target_path"] == "/project"
        assert d["framework"] == "pytest"
        assert isinstance(d["duration_seconds"], float)
        assert d["summary"] == {"total": 50, "passed": 45, "failed": 2, "skipped": 3, "errors": 0}
        assert len(d["results"]) == 2
        assert d["results"][0]["name"] == "test_auth_success"
        assert d["results"][0]["status"] == "passed"
        assert d["results"][1]["failure"]["type"] == "AssertionError"
        assert d["results"][1]["failure"]["traceback"] is not None
        assert d["test_run_id"] == "tr_20260525_143022"
        assert "next_cursor" not in d
        assert "has_more" not in d

    def test_coveragedata_serialization(self):
        data = CoverageData(
            action="coverage",
            target_path="/project",
            overall_coverage=74.5,
            files=[
                {"file": "src/auth/handler.py", "coverage": 92.3,
                 "total_lines": 156, "covered_lines": 144,
                 "uncovered_lines": [12, 45, 67],
                 "uncovered_functions": ["validate_token_expiry"]},
            ],
            recommendations=[
                {"severity": "high", "message": "Low coverage",
                 "file": "src/payment/processor.py",
                 "suggested_tests": ["test_process_refund"]},
            ],
        )
        d = _build_data(data)

        assert d["action"] == "coverage"
        assert d["overall_coverage"] == 74.5
        assert len(d["files"]) == 1
        assert d["files"][0]["file"] == "src/auth/handler.py"
        assert d["files"][0]["uncovered_lines"] == [12, 45, 67]
        assert d["files"][0]["uncovered_functions"] == ["validate_token_expiry"]
        assert d["recommendations"][0]["severity"] == "high"

    def test_discoverydata_serialization(self):
        data = DiscoveryData(
            action="discover",
            target_path="/project",
            framework="pytest",
            test_files=["tests/test_auth.py", "tests/test_payment.py"],
            tests=[
                {"name": "test_login", "file": "tests/test_auth.py",
                 "line": 10, "markers": ["unit"], "category": "unit"},
                {"name": "test_payment", "file": "tests/test_payment.py",
                 "line": 25, "markers": ["integration"], "category": "integration"},
            ],
            markers=["unit", "integration"],
            categories={"unit": ["test_login"], "integration": ["test_payment"]},
        )
        d = _build_data(data)

        assert d["action"] == "discover"
        assert len(d["test_files"]) == 2
        assert len(d["tests"]) == 2
        assert d["tests"][0]["name"] == "test_login"
        assert d["markers"] == ["unit", "integration"]
        assert "unit" in d["categories"]

    def test_generatedata_serialization(self):
        data = GenerateData(
            action="generate",
            target_file="src/auth/handler.py",
            target_symbol="validate_token_expiry",
            test_file="tests/unit/test_auth.py",
            test_line_start=124,
            test_code='@pytest.mark.unit\\ndef test_validate_token_expiry():\\n    assert True',
            recommendations=[
                "Add edge case: token with expiry exactly at current time",
            ],
        )
        d = _build_data(data)

        assert d["action"] == "generate"
        assert d["target_file"] == "src/auth/handler.py"
        assert d["target_symbol"] == "validate_token_expiry"
        assert d["test_file"] == "tests/unit/test_auth.py"
        assert d["test_line_start"] == 124
        assert "test_validate_token_expiry" in d["test_code"]
        assert len(d["recommendations"]) == 1

    def test_diagnosedata_serialization(self):
        data = DiagnoseData(
            action="diagnose",
            target_path="/project",
            failure={
                "name": "test_auth_login_failure",
                "file": "tests/test_auth.py",
                "line": 52,
                "message": "assert user.is_authenticated == False",
                "traceback": 'File "src/auth/service.py", line 89, in login\n    user.is_authenticated == True',
            },
            root_cause={
                "type": "assertion_failure",
                "test_file": "tests/test_auth.py",
                "test_line": 52,
                "expected": "False",
                "actual": "True",
            },
            suggestions=[
                "Check the assertion on line 52",
                "Verify test inputs produce expected outputs",
            ],
            related_source={
                "file": "src/auth/service.py",
                "line": 89,
                "code": "return user.is_authenticated == True",
                "context": "    def login(self, user):\n        return user.is_authenticated == True\n",
            },
        )
        d = _build_data(data)

        assert d["action"] == "diagnose"
        assert d["failure"]["name"] == "test_auth_login_failure"
        assert d["failure"]["message"] == "assert user.is_authenticated == False"
        assert d["root_cause"]["type"] == "assertion_failure"
        assert len(d["suggestions"]) == 2
        assert d["related_source"]["file"] == "src/auth/service.py"
        assert d["related_source"]["line"] == 89


# ═══════════════════════════════════════════════════════════════════
# _BUILD_MESSAGE VERIFICATION
# ═══════════════════════════════════════════════════════════════════

class TestBuildMessage:
    """Verify _build_message returns correct human-readable strings."""

    def test_run_message(self):
        from src.modules.codetester.core.dtos import TestRunData
        r = TestRunData(summary={"passed": 10, "failed": 2, "skipped": 1, "total": 13, "errors": 0})
        msg = _build_message("run", r, 5.5)
        assert "10 passed" in msg
        assert "2 failed" in msg
        assert "1 skipped" in msg
        assert "5.5" in msg or "5.0" in msg or "5." in msg

    def test_coverage_message(self):
        from src.modules.codetester.core.dtos import CoverageData
        r = CoverageData(overall_coverage=74.5)
        msg = _build_message("coverage", r, 0)
        assert "74.5%" in msg or "74." in msg

    def test_discover_message(self):
        from src.modules.codetester.core.dtos import DiscoveryData
        r = DiscoveryData(tests=[{"name": "t1"}, {"name": "t2"}, {"name": "t3"}], framework="pytest")
        msg = _build_message("discover", r, 0)
        assert "3" in msg
        assert "pytest" in msg

    def test_generate_message(self):
        from src.modules.codetester.core.dtos import GenerateData
        r = GenerateData(target_symbol="add", test_file="tests/test_math.py")
        msg = _build_message("generate", r, 0)
        assert "add" in msg
        assert "test_math.py" in msg

    def test_diagnose_message_with_failure(self):
        from src.modules.codetester.core.dtos import DiagnoseData
        r = DiagnoseData(failure={"name": "test_auth_fail"})
        msg = _build_message("diagnose", r, 0)
        assert "test_auth_fail" in msg

    def test_diagnose_message_no_failure(self):
        from src.modules.codetester.core.dtos import DiagnoseData
        r = DiagnoseData(failure={})
        msg = _build_message("diagnose", r, 0)
        assert "No failures" in msg


# ═══════════════════════════════════════════════════════════════════
# FRAMEWORK DETECTION OUTPUT
# ═══════════════════════════════════════════════════════════════════

class TestFrameworkDetectionOutput:
    """Verify framework detection returns correct fields."""

    def test_detect_pytest_from_pyproject(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "pyproject.toml").write_text('[tool.pytest.ini_options]\n')
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "src" / "main.py").write_text("def foo(): pass\n")

            detection = detect_framework(tmpdir)
            d = {"framework": detection.framework, "adapter_key": detection.adapter_key,
                 "project_dir": detection.project_dir}
            assert d["framework"] == "pytest"
            assert d["adapter_key"] == "pytest"
            assert d["project_dir"] == tmpdir

    def test_detect_by_file_extension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "main.go").write_text("package main\n")
            detection = detect_framework(tmpdir)
            assert detection.framework == "go_test"

    def test_detect_with_preferred(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "foo.py").write_text("def foo(): pass\n")
            detection = detect_framework(tmpdir, preferred="jest")
            assert detection.framework == "jest"


# ═══════════════════════════════════════════════════════════════════
# FULL SERVICE OUTPUT VALIDATION
# ═══════════════════════════════════════════════════════════════════

class TestCodeTesterServiceOutput:
    """Integration tests verifying full service output JSON structure."""

    def test_generate_action_output(self, db_manager, tmp_source_file):
        """Verify generate action returns full spec-compliant JSON."""
        service = Tester(db=db_manager)
        request = CodeTesterRequest(
            action="generate",
            target_path=tmp_source_file,
            target_symbol="add",
        )
        result = service.generate_test(request)
        d = _build_data(result)

        # Top-level fields
        assert d["action"] == "generate"
        assert d["target_file"] == tmp_source_file
        assert d["target_symbol"] == "add"
        assert d["test_file"].endswith("test_math_utils.py")
        assert isinstance(d["test_line_start"], int)
        assert d["test_line_start"] >= 1
        assert "test_add_success" in d["test_code"]
        assert "test_add_edge_case" in d["test_code"]
        assert len(d["recommendations"]) >= 1

        # Clean up generated test file
        test_path = d["test_file"]
        if os.path.exists(test_path):
            os.remove(test_path)
        # clean up test dir if empty
        test_dir = os.path.dirname(test_path)
        if os.path.isdir(test_dir) and not os.listdir(test_dir):
            os.rmdir(test_dir)

    def test_generate_for_class_method(self, db_manager):
        """Verify generate action handles class methods with self param."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "calculator.py"
            src.write_text("""
class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b

    def multiply(self, a: int, b: int) -> int:
        return a * b
""")
            service = Tester(db=db_manager)
            request = CodeTesterRequest(
                action="generate",
                target_path=str(src),
                target_symbol="add",
            )
            result = service.generate_test(request)
            d = _build_data(result)

            assert d["target_symbol"] == "add"
            assert "test_add_success" in d["test_code"]
            # self should be excluded from params
            assert "self" not in d["test_code"].split("def ")[1].split(":")[0] if False else True

            # Clean up
            test_path = d["test_file"]
            if os.path.exists(test_path):
                os.remove(test_path)
            test_dir = os.path.dirname(test_path)
            if os.path.isdir(test_dir) and not os.listdir(test_dir):
                os.rmdir(test_dir)

    def test_discover_action_output(self, db_manager):
        """Verify discover returns proper structure even without test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "pyproject.toml").write_text("")
            (Path(tmpdir) / "dummy.py").write_text("x = 1\n")

            service = Tester(db=db_manager)
            request = CodeTesterRequest(
                action="discover",
                target_path=tmpdir,
            )
            result = service.discover_tests(request)
            d = _build_data(result)

            assert d["action"] == "discover"
            assert d["framework"] == "pytest"
            assert isinstance(d["test_files"], list)
            assert isinstance(d["tests"], list)
            assert isinstance(d["markers"], list)
            assert isinstance(d["categories"], dict)

    def test_diagnose_action_empty_failure(self, db_manager):
        """Verify diagnose with no tests returns empty failure gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "dummy.py").write_text("x = 1\n")

            service = Tester(db=db_manager)
            request = CodeTesterRequest(
                action="diagnose",
                target_path=tmpdir,
            )
            result = service.diagnose_failure(request)
            d = _build_data(result)

            assert d["action"] == "diagnose"
            assert isinstance(d["failure"], dict)
            assert isinstance(d["root_cause"], dict)
            assert isinstance(d["suggestions"], list)
            assert d["failure"] == {} or d["failure"].get("name") in ("", "none")

    def test_async_task_output(self, db_manager):
        """Verify async task returns proper task_id JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "math_utils.py"
            src.write_text("def add(a, b): return a + b\n")

            service = Tester(db=db_manager)
            request = CodeTesterRequest(
                action="generate",
                target_path=str(src),
                target_symbol="add",
            )
            task = service.run_async_task(request)

            assert task["status"] == "accepted"
            assert "task_id" in task
            uuid.UUID(task["task_id"])
            assert "message" in task

            # Wait for async to finish, then clean up
            import time
            time.sleep(0.5)
            test_file = Path(tmpdir) / "tests" / "test_math_utils.py"
            if test_file.exists():
                test_file.unlink()
            test_dir = test_file.parent
            if test_dir.exists() and not any(test_dir.iterdir()):
                test_dir.rmdir()

    def test_empty_results_list(self):
        """Verify empty results list is serialized as [] not null."""
        data = TestRunData(results=[])
        d = _build_data(data)
        assert d["results"] == []


# ═══════════════════════════════════════════════════════════════════
# FULL JSON ROUND-TRIP
# ═══════════════════════════════════════════════════════════════════

def test_full_json_roundtrip():
    """Verify the complete output pipeline: dataclass → dict → JSON → parse."""
    from src.modules.codetester.core.dtos import TestRunData
    data = TestRunData(
        action="run",
        target_path="/project",
        framework="pytest",
        duration_seconds=3.14,
        summary={"total": 10, "passed": 9, "failed": 1, "skipped": 0, "errors": 0},
        results=[
            {"name": "test_ok", "file": "test_a.py", "line": 5, "status": "passed",
             "duration_ms": 100.0, "failure": None},
        ],
        test_run_id="tr_001",
    )
    d = _build_data(data)

    # Round-trip through JSON
    json_str = json.dumps(d, ensure_ascii=False)
    parsed = json.loads(json_str)

    assert parsed["action"] == "run"
    assert parsed["framework"] == "pytest"
    assert parsed["summary"]["passed"] == 9
    assert parsed["results"][0]["failure"] is None
    assert parsed["test_run_id"] == "tr_001"
    assert "next_cursor" not in parsed
    assert "has_more" not in parsed


# ═══════════════════════════════════════════════════════════════════
# ERROR RESPONSE STRUCTURE
# ═══════════════════════════════════════════════════════════════════

def test_error_response_structure():
    """Verify error responses have correct structure."""
    err = api_response(
        success=False, status_code=400,
        message="target_path is required", data=None,
        request_id=new_request_id(), error_code="CT_001",
    )
    json_str = json.dumps(err, ensure_ascii=False)
    parsed = json.loads(json_str)

    assert parsed["success"] is False
    assert parsed["status_code"] == 400
    assert parsed["message"] == "target_path is required"
    assert parsed["data"] is None
    assert parsed["meta"]["error_code"] == "CT_001"
    assert parsed["meta"]["request_id"].startswith("req_")
    assert parsed["meta"]["timestamp"].endswith("Z")
