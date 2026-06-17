"""
Unit tests for Codelogs module — LogService, LogGraphService, and integration.

:project: CodeCortex
:package: Tests.Unit.Codelogs
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
"""
from __future__ import annotations

import os
import json
import tempfile
import shutil
import time
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

from src.modules.codelogs.services.log_service import (
    LogService, LogSearchFilter, LogEntry,
    LOG_LEVEL_PATTERN, TIMESTAMP_PATTERNS,
)
from src.modules.codelogs.services.loggraph_service import LogGraphService


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture
def temp_project():
    """Create a temp project with logs/ and outputs/logs/ directories."""
    with tempfile.TemporaryDirectory() as tmp:
        logs_dir = os.path.join(tmp, "logs")
        outputs_logs_dir = os.path.join(tmp, "outputs", "logs")
        os.makedirs(logs_dir)
        os.makedirs(outputs_logs_dir)
        yield tmp


@pytest.fixture
def svc(temp_project):
    s = LogService(project_root=temp_project)
    return s


# ── LogService: Path Validation ──────────────────────────

class TestLogServicePathValidation:
    def test_valid_log_directory(self, svc, temp_project):
        roots = svc._get_log_roots()
        expected_logs = os.path.join(temp_project, "logs")
        expected_outputs = os.path.join(temp_project, "outputs", "logs")
        assert expected_logs in roots
        assert expected_outputs in roots

    def test_path_outside_allowed_raises(self, svc):
        with pytest.raises(PermissionError, match="outside allowed"):
            svc._validate_path("C:\\Windows\\System32")

    def test_valid_log_path(self, svc, temp_project):
        allowed = os.path.join(temp_project, "logs", "app.log")
        Path(allowed).touch()
        result = svc._validate_path(allowed)
        assert result == os.path.normpath(allowed)

    def test_no_project_root_returns_empty(self):
        s = LogService()
        assert s._get_log_roots() == []

    def test_invalid_project_root_raises(self):
        s = LogService()
        with pytest.raises(ValueError, match="Not a valid directory"):
            s.set_project_root("/nonexistent_path_xyz_123")


# ── LogService: Log File Detection ───────────────────────

class TestLogFileDetection:
    def test_log_extensions(self, svc):
        assert svc._is_log_file("app.log")
        assert svc._is_log_file("server.out")
        assert svc._is_log_file("error.err")
        assert svc._is_log_file("history.txt")
        assert svc._is_log_file("app.log.gz")
        assert svc._is_log_file("app.log.1")
        assert svc._is_log_file("app.log.9")
        assert not svc._is_log_file("main.py")
        assert not svc._is_log_file("data.csv")
        assert not svc._is_log_file("image.png")


# ── LogService: Log Level & Timestamp Parsing ────────────

class TestLogParsing:
    def test_parse_log_level(self, svc):
        assert svc._parse_log_level("ERROR: something broke") == "ERROR"
        assert svc._parse_log_level("WARNING: disk full") == "WARN"
        assert svc._parse_log_level("WARN: disk full") == "WARN"
        assert svc._parse_log_level("INFO: server started") == "INFO"
        assert svc._parse_log_level("DEBUG: var=42") == "DEBUG"
        assert svc._parse_log_level("TRACE: entry") == "TRACE"
        assert svc._parse_log_level("CRITICAL: out of memory") == "CRITICAL"
        assert svc._parse_log_level("FATAL: kernel panic") == "CRITICAL"
        assert svc._parse_log_level("just a normal line") == "INFO"

    def test_parse_timestamp(self, svc):
        assert svc._parse_timestamp("2026-06-17T14:30:00 ERROR: test") is not None
        assert svc._parse_timestamp("2026-06-17 14:30:00.123 INFO: test") is not None
        assert svc._parse_timestamp("no timestamp here") is None


# ── LogService: Scan ─────────────────────────────────────

class TestScan:
    def test_scan_empty_dirs(self, svc):
        files = svc.scan_logs()
        assert files == []

    def test_scan_finds_logs(self, svc, temp_project):
        log_a = os.path.join(temp_project, "logs", "app.log")
        log_b = os.path.join(temp_project, "outputs", "logs", "server.log")
        Path(log_a).write_text("INFO: test\n", encoding="utf-8")
        Path(log_b).write_text("ERROR: fail\n", encoding="utf-8")

        files = svc.scan_logs()
        assert len(files) == 2
        paths = {f["path"] for f in files}
        assert any("app.log" in p for p in paths)
        assert any("server.log" in p for p in paths)

    def test_scan_ignores_non_logs(self, svc, temp_project):
        Path(os.path.join(temp_project, "logs", "main.py")).write_text("x=1\n")
        Path(os.path.join(temp_project, "logs", "data.json")).write_text("{}\n")

        files = svc.scan_logs()
        assert files == []


# ── LogService: Search ───────────────────────────────────

class TestSearch:
    def test_search_basic(self, svc, temp_project):
        log_path = os.path.join(temp_project, "logs", "app.log")
        Path(log_path).write_text(
            "INFO: Server started\n"
            "ERROR: Connection refused\n"
            "WARN: Retry attempt 1\n"
            "ERROR: Timeout after 30s\n",
            encoding="utf-8",
        )
        filt = LogSearchFilter(query="ERROR", max_results=10)
        entries = svc.search(filt)
        assert len(entries) == 2
        assert all(e.level == "ERROR" for e in entries)

    def test_search_by_level(self, svc, temp_project):
        log_path = os.path.join(temp_project, "logs", "app.log")
        Path(log_path).write_text(
            "INFO: Server started\n"
            "ERROR: Connection refused\n"
            "WARN: Retry attempt\n",
            encoding="utf-8",
        )
        filt = LogSearchFilter(log_levels=["WARN"], max_results=10)
        entries = svc.search(filt)
        assert len(entries) == 1
        assert entries[0].level == "WARN"

    def test_search_by_text(self, svc, temp_project):
        log_path = os.path.join(temp_project, "logs", "app.log")
        Path(log_path).write_text(
            "INFO: Server started\n"
            "ERROR: Database connection timeout\n"
            "WARN: Memory usage high\n",
            encoding="utf-8",
        )
        filt = LogSearchFilter(query="database", max_results=10)
        entries = svc.search(filt)
        assert len(entries) == 1
        assert "database" in entries[0].message.lower()

    def test_search_pagination(self, svc, temp_project):
        log_path = os.path.join(temp_project, "logs", "app.log")
        lines = "\n".join(f"INFO: Line {i}" for i in range(20))
        Path(log_path).write_text(lines, encoding="utf-8")
        filt = LogSearchFilter(max_results=5, offset=0)
        entries = svc.search(filt)
        assert len(entries) == 5


# ── LogService: Validation ───────────────────────────────

class TestValidate:
    def test_validate_valid_log(self, svc, temp_project):
        log_path = os.path.join(temp_project, "logs", "valid.log")
        Path(log_path).write_text(
            "2026-06-17T14:30:00 INFO: Server started\n"
            "2026-06-17T14:31:00 ERROR: Connection refused\n",
            encoding="utf-8",
        )
        result = svc.validate(log_path)
        assert result["valid"] is True
        assert result["total_lines"] == 2

    def test_validate_nonexistent(self, svc):
        result = svc.validate("/nonexistent.log")
        assert result["valid"] is False

    def test_validate_tracks_levels(self, svc, temp_project):
        log_path = os.path.join(temp_project, "logs", "multi.log")
        Path(log_path).write_text(
            "INFO: start\n" "ERROR: fail\n" "WARN: retry\n",
            encoding="utf-8",
        )
        result = svc.validate(log_path)
        assert result["levels_found"].get("INFO") == 1
        assert result["levels_found"].get("ERROR") == 1
        assert result["levels_found"].get("WARN") == 1


# ── LogService: Cleanup ──────────────────────────────────

class TestCleanup:
    def test_cleanup_dry_run(self, svc, temp_project):
        log_path = os.path.join(temp_project, "logs", "old.log")
        Path(log_path).write_text("old data\n", encoding="utf-8")
        result = svc.cleanup(days=0, dry_run=True)
        assert result["dry_run"] is True
        assert result["removed"] >= 1
        assert os.path.exists(log_path)

    def test_cleanup_recent_files_kept(self, svc, temp_project):
        log_path = os.path.join(temp_project, "logs", "recent.log")
        Path(log_path).write_text("recent data\n", encoding="utf-8")
        result = svc.cleanup(days=30, dry_run=True)
        # File just created so it's not old enough
        assert result["removed"] == 0


# ── LogService: Rotation ─────────────────────────────────

class TestRotate:
    def test_rotate_dry_run(self, svc, temp_project):
        log_path = os.path.join(temp_project, "logs", "big.log")
        content = "x" * 1024 * 1024  # 1 MB
        Path(log_path).write_text(content, encoding="utf-8")
        result = svc.rotate(max_size_mb=1, keep=3, dry_run=True)
        assert result["dry_run"] is True
        assert result["rotated"] >= 1

    def test_rotate_small_file_skipped(self, svc, temp_project):
        log_path = os.path.join(temp_project, "logs", "small.log")
        Path(log_path).write_text("small\n", encoding="utf-8")
        result = svc.rotate(max_size_mb=50, dry_run=True)
        assert result["rotated"] == 0


# ── LogGraphService ──────────────────────────────────────

class TestLogGraphService:
    def test_generate_empty(self, temp_project):
        svc = LogGraphService(LogService(project_root=temp_project))
        data = svc.generate(days=7)
        assert "error" not in data
        assert data["summary"]["total_files"] == 0

    def test_generate_with_logs(self, temp_project):
        log_path = os.path.join(temp_project, "logs", "app.log")
        Path(log_path).write_text(
            "2026-06-17T14:30:00 INFO: Server started\n"
            "2026-06-17T14:31:00 ERROR: Connection refused\n"
            "2026-06-17T14:32:00 WARN: Retry attempt\n"
            "2026-06-17T14:33:00 ERROR: Timeout\n",
            encoding="utf-8",
        )
        svc = LogGraphService(LogService(project_root=temp_project))
        data = svc.generate(days=7)
        assert data["summary"]["total_files"] == 1
        assert data["summary"]["total_lines"] == 4
        assert data["error_frequency"]["total_errors"] == 2
        assert data["error_frequency"]["total_warnings"] == 1
        assert data["error_frequency"]["total_info"] == 1

    def test_error_frequency(self, temp_project):
        log_path = os.path.join(temp_project, "logs", "app.log")
        Path(log_path).write_text(
            "2026-06-17T14:30:00 ERROR: fail1\n"
            "2026-06-17T14:31:00 ERROR: fail2\n"
            "2026-06-17T14:32:00 INFO: ok\n",
            encoding="utf-8",
        )
        svc = LogGraphService(LogService(project_root=temp_project))
        data = svc.error_frequency(days=7)
        assert data["error_frequency"]["total_errors"] == 2

    def test_time_trend(self, temp_project):
        log_path = os.path.join(temp_project, "logs", "app.log")
        Path(log_path).write_text(
            "2026-06-17T14:30:00 INFO: start\n"
            "2026-06-17T14:31:00 ERROR: fail\n"
            "2026-06-17T15:00:00 INFO: next hour\n",
            encoding="utf-8",
        )
        svc = LogGraphService(LogService(project_root=temp_project))
        data = svc.time_trend(days=7, granularity="hourly")
        assert data["granularity"] == "hourly"
        assert len(data["trend"]) >= 2

    def test_summary(self, temp_project):
        log_path = os.path.join(temp_project, "logs", "app.log")
        Path(log_path).write_text(
            "2026-06-17T14:30:00 ERROR: crash\n"
            "2026-06-17T14:31:00 INFO: restart\n",
            encoding="utf-8",
        )
        svc = LogGraphService(LogService(project_root=temp_project))
        data = svc.summary(days=7)
        assert "summary" in data
        assert "error_frequency" in data
        assert "top_error_messages" in data


# ── Security: Path Restriction ───────────────────────────

class TestSecurity:
    def test_logs_outside_allowed_blocked(self, temp_project):
        svc = LogService(project_root=temp_project)
        outside = os.path.join(temp_project, "config", "secrets.log")
        os.makedirs(os.path.join(temp_project, "config"))
        Path(outside).touch()
        with pytest.raises(PermissionError):
            svc._validate_path(outside)

    def test_outputs_logs_allowed(self, temp_project):
        svc = LogService(project_root=temp_project)
        allowed = os.path.join(temp_project, "outputs", "logs", "server.log")
        Path(allowed).touch()
        result = svc._validate_path(allowed)
        assert result == os.path.normpath(allowed)

    def test_multiple_allowed_roots(self, temp_project):
        svc = LogService(project_root=temp_project)
        roots = svc._get_log_roots()
        assert len(roots) == 2
        assert all(os.path.isdir(r) for r in roots)
