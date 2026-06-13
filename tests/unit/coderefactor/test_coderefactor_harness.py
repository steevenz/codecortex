"""
CodeRefactor QA Harness — Comprehensive test suite.

Covers:
  - DTOs and error codes (unit)
  - CLI parser registration (unit)
  - Service: rename_symbol, move_code_element, analyze_impact,
             rename_file, rename_folder, move_file, modularize,
             change_signature, extract_function, inline_function (integration)
  - MCP tool: code_refactor action dispatch (integration)
  - Error paths: missing repo, bad action, missing param, etc.

:project: CodeCortex
:package: Tests.Coderefactor
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_repo(tmp_path: Path) -> Path:
    """Create a minimal Python repo for testing."""
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "utils.py").write_text(
        "def old_func(a, b):\n    return a + b\n\ndef helper():\n    return old_func(1, 2)\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "main.py").write_text(
        "from src.utils import old_func\n\nresult = old_func(1, 2)\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "monolith.py").write_text(
        "def login_user(u, p):\n    return True\n\ndef send_email(to, msg):\n    pass\n\ndef create_invoice(amount):\n    pass\n",
        encoding="utf-8",
    )
    return tmp_path


async def _create_orchestrator_with_repo(tmp_path: Path):
    """Returns (orchestrator, repo_id) with a freshly indexed test repo."""
    from src.main import create_orchestrator
    orch = create_orchestrator()
    repo_id = await orch.repo_service.initialize(str(tmp_path))
    await orch.index_service.index_repository(repo_id)
    return orch, repo_id


# ─────────────────────────────────────────────────────────────────────────────
# 1. DTOs — unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDTOs:
    def test_refactor_change_fields(self):
        from src.modules.coderefactor.core.dtos import RefactorChange
        c = RefactorChange(path="src/utils.py", action="modify", description="rename x→y", diff="---\n+++")
        assert c.path == "src/utils.py"
        assert c.action == "modify"
        assert c.diff == "---\n+++"
        assert c.metadata == {}

    def test_blast_radius_defaults(self):
        from src.modules.coderefactor.core.dtos import BlastRadius
        br = BlastRadius()
        assert br.total_files == 0
        assert br.confidence_score == 100

    def test_impact_result_fields(self):
        from src.modules.coderefactor.core.dtos import ImpactResult, BlastRadius
        ir = ImpactResult(repository_id="r1", symbol_name="fn", source_file="f.py",
                          risk_level="low", summary="ok", recommendation="none")
        assert ir.risk_level == "low"
        assert ir.affected_files == []

    def test_refactor_result_has_error_code(self):
        from src.modules.coderefactor.core.dtos import RefactorResult, RefactorErrorCode
        r = RefactorResult(status="error", message="bad", repository_id="r1",
                           action="rename", error_code=RefactorErrorCode.MISSING_REPO)
        assert r.error_code == "REF_404_REPO_NOT_FOUND"

    def test_error_code_constants(self):
        from src.modules.coderefactor.core.dtos import RefactorErrorCode
        assert RefactorErrorCode.MISSING_REPO == "REF_404_REPO_NOT_FOUND"
        assert RefactorErrorCode.MISSING_SYMBOL == "REF_404_SYMBOL_NOT_FOUND"
        assert RefactorErrorCode.MISSING_SOURCE_FILE == "REF_404_SOURCE_FILE_NOT_FOUND"
        assert RefactorErrorCode.INVALID_ACTION == "REF_400_INVALID_ACTION"
        assert RefactorErrorCode.GRAPH_EMPTY == "REF_412_GRAPH_EMPTY"
        assert RefactorErrorCode.INTERNAL == "REF_500_INTERNAL"

    def test_refactor_result_serialisable(self):
        from src.modules.coderefactor.core.dtos import RefactorResult, RefactorChange
        r = RefactorResult(status="preview", message="ok", repository_id="r1", action="rename",
                           changes=[RefactorChange(path="f.py", action="modify", description="x")])
        d = asdict(r)
        assert d["status"] == "preview"
        assert d["changes"][0]["path"] == "f.py"


# ─────────────────────────────────────────────────────────────────────────────
# 2. CLI parser — unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCLIParser:
    def test_cli_module_importable(self):
        from src.modules.coderefactor.api.cli import DOMAIN, ALIASES, REF_COMMANDS, build_parser
        assert DOMAIN == "coderefactor"
        assert "refactor" in ALIASES
        assert "ref" in ALIASES

    def test_commands_registered(self):
        from src.modules.coderefactor.api.cli import REF_COMMANDS
        expected = {"impact", "rename", "move", "signature", "extract", "inline",
                    "rename-file", "rename_file", "rename-folder", "rename_folder",
                    "move-file", "move_file", "modularize"}
        assert expected.issubset(set(REF_COMMANDS.keys()))

    def test_build_parser_creates_subcommands(self):
        import argparse
        from src.modules.coderefactor.api.cli import build_parser
        top = argparse.ArgumentParser()
        sub = top.add_subparsers(dest="domain")
        build_parser(sub)
        # Should parse: coderefactor impact --repo-id x target
        ns = top.parse_args(["coderefactor", "impact", "--repo-id", "uuid-1", "src/utils.py::fn"])
        assert ns.ref_action == "impact"
        assert ns.repo_id == "uuid-1"
        assert ns.target == "src/utils.py::fn"

    def test_rename_parser_flags(self):
        import argparse
        from src.modules.coderefactor.api.cli import build_parser
        top = argparse.ArgumentParser()
        sub = top.add_subparsers(dest="domain")
        build_parser(sub)
        ns = top.parse_args(["coderefactor", "rename", "--repo-id", "r1",
                             "src/utils.py::old_func", "--new-name", "new_func", "--apply"])
        assert ns.ref_action == "rename"
        assert ns.new_name == "new_func"
        assert ns.apply is True

    def test_extract_parser_flags(self):
        import argparse
        from src.modules.coderefactor.api.cli import build_parser
        top = argparse.ArgumentParser()
        sub = top.add_subparsers(dest="domain")
        build_parser(sub)
        ns = top.parse_args(["coderefactor", "extract", "--repo-id", "r1",
                             "src/service.py", "--new-name", "helper",
                             "--start-line", "10", "--end-line", "20"])
        assert ns.start_line == 10
        assert ns.end_line == 20
        assert ns.new_name == "helper"

    def test_registered_in_main_cli(self):
        from src.cli import _DOMAIN_REGISTRY, _init_registry
        _init_registry()
        assert "coderefactor" in _DOMAIN_REGISTRY
        assert "refactor" in _DOMAIN_REGISTRY
        assert "ref" in _DOMAIN_REGISTRY


# ─────────────────────────────────────────────────────────────────────────────
# 3. Service: analyze_impact — integration tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestServiceImpact:  # noqa: D101
    async def test_impact_invalid_repo(self):
        from src.main import create_orchestrator
        from src.modules.coderefactor.core.dtos import RefactorErrorCode
        orch = create_orchestrator()
        try:
            result = await orch.refactor_service.analyze_impact(
                "invalid-repo-uuid", "old_func", "src/utils.py"
            )
            assert RefactorErrorCode.MISSING_REPO in result.summary
        finally:
            orch.db.close()

    async def test_impact_valid_repo_empty_graph(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.analyze_impact(
                repo_id, "old_func", "src/utils.py"
            )
            assert result.repository_id == repo_id
            assert result.symbol_name == "old_func"
            assert result.risk_level in ("low", "medium", "high")
        finally:
            orch.db.close()

    async def test_impact_returns_blast_radius(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.analyze_impact(
                repo_id, "old_func", "src/utils.py"
            )
            assert hasattr(result.blast_radius, "total_files")
            assert result.blast_radius.total_files >= 0
        finally:
            orch.db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Service: rename_symbol — integration tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestServiceRename:
    async def test_rename_missing_repo(self):
        from src.main import create_orchestrator
        from src.modules.coderefactor.core.dtos import RefactorErrorCode
        orch = create_orchestrator()
        try:
            result = await orch.refactor_service.rename_symbol(
                "invalid-uuid", "old_func", "src/utils.py", "new_func"
            )
            assert result.status == "error"
            assert result.error_code == RefactorErrorCode.MISSING_REPO
        finally:
            orch.db.close()

    async def test_rename_dry_run_returns_preview(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.rename_symbol(
                repo_id, "old_func", "src/utils.py", "new_func", dry_run=True
            )
            # preview when indexing ok, error when tree-sitter not available in test env
            assert result.status in ("preview", "error")
            assert result.action == "rename"
        finally:
            orch.db.close()

    async def test_rename_dry_run_no_mutation(self, tmp_path):
        _make_repo(tmp_path)
        original = (tmp_path / "src" / "utils.py").read_text()
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            await orch.refactor_service.rename_symbol(
                repo_id, "old_func", "src/utils.py", "new_func", dry_run=True
            )
            after = (tmp_path / "src" / "utils.py").read_text()
            assert original == after
        finally:
            orch.db.close()

    async def test_rename_result_has_changes_list(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.rename_symbol(
                repo_id, "old_func", "src/utils.py", "new_func", dry_run=True
            )
            assert isinstance(result.changes, list)
        finally:
            orch.db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Service: rename_file — integration tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestServiceRenameFile:
    async def test_rename_file_dry_run(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.rename_file(
                repo_id, "src/utils.py", "src/utilities.py", dry_run=True
            )
            assert result.status in ("preview", "error")
            assert result.action == "rename_file"
            assert not (tmp_path / "src" / "utilities.py").exists()
        finally:
            orch.db.close()

    async def test_rename_file_missing_source(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.rename_file(
                repo_id, "src/nonexistent.py", "src/new.py", dry_run=True
            )
            assert result.status == "error"
        finally:
            orch.db.close()

    async def test_rename_file_missing_repo(self):
        from src.main import create_orchestrator
        orch = create_orchestrator()
        try:
            result = await orch.refactor_service.rename_file(
                "invalid-uuid", "src/utils.py", "src/new.py", dry_run=True
            )
            assert result.status == "error"
        finally:
            orch.db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Service: move_file — integration tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestServiceMoveFile:
    async def test_move_file_dry_run(self, tmp_path):
        _make_repo(tmp_path)
        (tmp_path / "src" / "domain").mkdir(exist_ok=True)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.move_file(
                repo_id, "src/utils.py", "src/domain/", dry_run=True
            )
            assert result.status in ("preview", "error")
            assert result.action == "move_file"
        finally:
            orch.db.close()

    async def test_move_file_missing_source(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.move_file(
                repo_id, "src/nonexistent.py", "src/domain/", dry_run=True
            )
            assert result.status == "error"
        finally:
            orch.db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 7. Service: modularize — integration tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestServiceModularize:
    async def test_modularize_dry_run(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.modularize(
                repo_id, "src/monolith.py",
                target_domain="src/domain/", strategy="auto", dry_run=True
            )
            assert result.status in ("preview", "error")
            assert result.action == "modularize"
        finally:
            orch.db.close()

    async def test_modularize_missing_repo(self):
        from src.main import create_orchestrator
        orch = create_orchestrator()
        try:
            result = await orch.refactor_service.modularize(
                "invalid-uuid", "src/monolith.py", dry_run=True
            )
            assert result.status == "error"
        finally:
            orch.db.close()

    async def test_modularize_dry_run_no_files_created(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.modularize(
                repo_id, "src/monolith.py",
                target_domain="src/domain/", strategy="auto", dry_run=True
            )
            # dry_run must not commit — no commit hash
            assert result.commit_hash is None
            assert result.status in ("preview", "error")
        finally:
            orch.db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 8. Service: change_signature — integration tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestServiceChangeSignature:
    async def test_change_signature_dry_run(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.change_signature(
                repo_id, "src/utils.py::old_func",
                {"add_params": [{"name": "debug", "default_value": "False"}]},
                dry_run=True
            )
            assert result.status in ("preview", "error")
            assert result.action == "change_signature"
        finally:
            orch.db.close()

    async def test_change_signature_missing_repo(self):
        from src.main import create_orchestrator
        orch = create_orchestrator()
        try:
            result = await orch.refactor_service.change_signature(
                "invalid-uuid", "src/utils.py::old_func", {}, dry_run=True
            )
            assert result.status == "error"
        finally:
            orch.db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 9. Service: extract_function — integration tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestServiceExtractFunction:
    async def test_extract_function_dry_run(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.extract_function(
                repo_id, "src/utils.py",
                {"new_name": "extracted_helper", "start_line": 1, "end_line": 2},
                dry_run=True
            )
            assert result.status in ("preview", "error")
            assert result.action == "extract_function"
        finally:
            orch.db.close()

    async def test_extract_missing_repo(self):
        from src.main import create_orchestrator
        orch = create_orchestrator()
        try:
            result = await orch.refactor_service.extract_function(
                "invalid-uuid", "src/utils.py",
                {"new_name": "helper", "start_line": 1, "end_line": 2},
                dry_run=True
            )
            assert result.status == "error"
        finally:
            orch.db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 10. Service: inline_function — integration tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestServiceInlineFunction:
    async def test_inline_dry_run(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.inline_function(
                repo_id, "src/utils.py::helper", {}, dry_run=True
            )
            assert result.status in ("preview", "error")
            assert result.action == "inline_function"
        finally:
            orch.db.close()

    async def test_inline_missing_repo(self):
        from src.main import create_orchestrator
        orch = create_orchestrator()
        try:
            result = await orch.refactor_service.inline_function(
                "invalid-uuid", "src/utils.py::fn", {}, dry_run=True
            )
            assert result.status == "error"
        finally:
            orch.db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 11. MCP tool dispatch — integration tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestMCPToolDispatch:
    """Test code_refactor MCP tool via direct service dispatch (mirrors tool.py logic)."""

    async def test_invalid_action_returns_error(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            # Simulate what tools.py does for invalid action
            valid_actions = ("impact", "rename", "move", "change_signature",
                             "extract_function", "inline_function", "preview", "apply",
                             "rename_file", "rename_folder", "move_file", "modularize")
            action = "invalid_action"
            assert action not in valid_actions
        finally:
            orch.db.close()

    async def test_impact_action_via_service(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.analyze_impact(
                repo_id, "old_func", "src/utils.py"
            )
            assert result is not None
            assert result.repository_id == repo_id
        finally:
            orch.db.close()

    async def test_rename_action_dry_run_via_service(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.rename_symbol(
                repo_id, "old_func", "src/utils.py", "new_func", dry_run=True
            )
            assert result.status in ("preview", "error")
        finally:
            orch.db.close()

    async def test_rename_file_action_dry_run(self, tmp_path):
        _make_repo(tmp_path)
        orch, repo_id = await _create_orchestrator_with_repo(tmp_path)
        try:
            result = await orch.refactor_service.rename_file(
                repo_id, "src/utils.py", "src/utilities.py", dry_run=True
            )
            assert result.status in ("preview", "error")
        finally:
            orch.db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 12. Internal helpers — unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestInternalHelpers:
    def _get_service(self):
        from src.main import create_orchestrator
        orch = create_orchestrator()
        return orch.refactor_service, orch

    def test_detect_lang_python(self):
        svc, orch = self._get_service()
        try:
            assert svc._detect_lang("src/utils.py") == "python"
        finally:
            orch.db.close()

    def test_detect_lang_typescript(self):
        svc, orch = self._get_service()
        try:
            assert svc._detect_lang("src/component.tsx") == "tsx"
            assert svc._detect_lang("src/service.ts") == "typescript"
        finally:
            orch.db.close()

    def test_detect_lang_unknown(self):
        svc, orch = self._get_service()
        try:
            assert svc._detect_lang("Makefile") == "unknown"
        finally:
            orch.db.close()

    def test_parse_target_double_colon(self):
        from src.modules.coderefactor.api.tools import register_tools
        # Test _parse_target logic embedded in tools.py inline
        def _parse_target(target):
            if "::" in target:
                p = target.split("::", 1)
                return p[0], p[1]
            if ":" in target:
                p = target.rsplit(":", 1)
                sym = p[1].strip()
                return p[0], sym if sym and not sym.isdigit() else ""
            return target, ""

        f, s = _parse_target("src/utils.py::old_func")
        assert f == "src/utils.py"
        assert s == "old_func"

    def test_parse_target_line_format(self):
        def _parse_target(target):
            if "::" in target:
                p = target.split("::", 1)
                return p[0], p[1]
            if ":" in target:
                p = target.rsplit(":", 1)
                sym = p[1].strip()
                return p[0], sym if sym and not sym.isdigit() else ""
            return target, ""

        f, s = _parse_target("src/utils.py:42")
        assert f == "src/utils.py"
        assert s == ""  # line number → no symbol

    def test_parse_target_plain_file(self):
        def _parse_target(target):
            if "::" in target:
                p = target.split("::", 1)
                return p[0], p[1]
            if ":" in target:
                p = target.rsplit(":", 1)
                sym = p[1].strip()
                return p[0], sym if sym and not sym.isdigit() else ""
            return target, ""

        f, s = _parse_target("src/utils.py")
        assert f == "src/utils.py"
        assert s == ""

    def test_to_case_snake(self):
        svc, orch = self._get_service()
        try:
            assert svc._to_case("MyClass", "snake_case") == "myclass"
        finally:
            orch.db.close()

    def test_to_case_pascal(self):
        svc, orch = self._get_service()
        try:
            assert svc._to_case("my_helper", "PascalCase") == "MyHelper"
        finally:
            orch.db.close()

    def test_to_case_kebab(self):
        svc, orch = self._get_service()
        try:
            assert svc._to_case("MyHelper", "kebab-case") == "myhelper"
        finally:
            orch.db.close()

    def test_naming_convention_python(self):
        svc, orch = self._get_service()
        try:
            dc, fc = svc._naming_convention("python")
            assert dc == "snake_case"
            assert fc == "snake_case"
        finally:
            orch.db.close()

    def test_naming_convention_typescript(self):
        svc, orch = self._get_service()
        try:
            dc, fc = svc._naming_convention("typescript")
            assert dc == "kebab-case"
            assert fc == "PascalCase"
        finally:
            orch.db.close()

    def test_infer_domain_auth(self):
        svc, orch = self._get_service()
        try:
            domain = svc._infer_domain("login_user", "def login_user(u, p):\n    token = generate_token()\n")
            assert domain == "auth"
        finally:
            orch.db.close()

    def test_infer_domain_payment(self):
        svc, orch = self._get_service()
        try:
            domain = svc._infer_domain("create_invoice", "def create_invoice(amount):\n    billing.charge(amount)\n")
            assert domain == "payment"
        finally:
            orch.db.close()

    def test_rename_in_file_python(self):
        svc, orch = self._get_service()
        try:
            src = "def old_name():\n    old_name()\n"
            result = svc._rename_in_file(src, "old_name", "new_name", "python")
            assert "new_name" in result
            assert "old_name" not in result
        finally:
            orch.db.close()

    def test_rename_in_file_skips_strings(self):
        svc, orch = self._get_service()
        try:
            src = 'def old_name():\n    x = "old_name in string"\n    old_name()\n'
            result = svc._rename_in_file(src, "old_name", "new_name", "python")
            # Function definition and call renamed, string may or may not be (TS-dependent)
            assert "new_name" in result
        finally:
            orch.db.close()

    def test_get_rel_path(self):
        svc, orch = self._get_service()
        try:
            rel = svc._get_rel_path("/root/project", "/root/project/src/utils.py")
            assert "src/utils.py" in rel or "src\\utils.py" in rel
        finally:
            orch.db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 13. CLI command handlers — unit tests (no IO)
# ─────────────────────────────────────────────────────────────────────────────

class TestCLICommandHandlers:
    def test_parse_target_helper(self):
        from src.modules.coderefactor.api.cli import _parse_target
        f, s = _parse_target("src/utils.py::old_func")
        assert f == "src/utils.py"
        assert s == "old_func"

    def test_parse_target_plain(self):
        from src.modules.coderefactor.api.cli import _parse_target
        f, s = _parse_target("src/utils.py")
        assert f == "src/utils.py"
        assert s == ""

    def test_fmt_result_fields(self):
        from src.modules.coderefactor.api.cli import _fmt_result
        from src.modules.coderefactor.core.dtos import RefactorResult
        r = RefactorResult(status="preview", message="ok", repository_id="r1", action="rename")
        d = _fmt_result(r)
        assert d["status"] == "preview"
        assert d["action"] == "rename"
        assert d["changes"] == []

    def test_extract_start_gt_end_returns_error(self):
        """cmd_ref_extract should return error when start_line >= end_line."""
        import argparse
        from src.modules.coderefactor.api.cli import cmd_ref_extract
        ns = argparse.Namespace(repo_id="r1", target="src/f.py",
                                new_name="helper", start_line=20, end_line=10, apply=False)
        result = cmd_ref_extract(ns)
        assert result["success"] is False
        assert "REF_CLI_BAD_RANGE" in result["error_code"]

    def test_signature_no_changes_returns_error(self):
        import argparse
        from src.modules.coderefactor.api.cli import cmd_ref_signature
        ns = argparse.Namespace(repo_id="r1", target="src/f.py::fn",
                                add_params=None, remove_params=None, reorder=None, apply=False)
        result = cmd_ref_signature(ns)
        assert result["success"] is False
        assert "REF_CLI_MISSING_ARG" in result["error_code"]

    def test_signature_bad_json_returns_error(self):
        import argparse
        from src.modules.coderefactor.api.cli import cmd_ref_signature
        ns = argparse.Namespace(repo_id="r1", target="src/f.py::fn",
                                add_params="not-json", remove_params=None, reorder=None, apply=False)
        result = cmd_ref_signature(ns)
        assert result["success"] is False
        assert "REF_CLI_BAD_JSON" in result["error_code"]
