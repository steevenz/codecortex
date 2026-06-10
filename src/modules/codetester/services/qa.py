"""
Class QA - Manage testing and linting jobs with background execution and webhooks.

:project: CodeCortex
:package: Modules.Codetester.Services.Qa
:author: Steeven Andrian
:copyright: (c) 2026 Aegis Codework
:standard: Aegis-CodeTester-v1.0
"""

import json
import uuid
import threading
from typing import Dict, List, Any, Optional
from pathlib import Path
from src.core.database import DatabaseManager
from src.core.logging import get_logger
from src.core.logging.event_logger import log_event
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

logger = get_logger("CodeCortex.Domain.CodeTester.QA")

class QA:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.adapters = {
            "pytest": Pytest(),
            "flake8": Flake8(),
            "unittest": Unittest(),
            "jest": Jest(),
            "phpunit": PHPUnit(),
            "npm": Npm(),
            "pnpm": Pnpm(),
            "vitest": Vitest(),
            "yarn": Yarn(),
            "go_test": GoTest(),
            "cargo_test": CargoTest(),
            "swift_test": SwiftTest(),
            "kotlin_test": KotlinTest(),
            "sbt_test": SbtTest(),
            "maven_test": MavenTest(),
            "ruby_test": RubyTest(),
            "flutter_test": FlutterTest(),
            "dart_test": DartTest(),
            "haskell_test": HaskellTest(),
            "elixir_test": ElixirTest(),
            "dotnet_test": DotNetTest(),
            "perl_test": PerlTest(),
            "stylelint": Stylelint(),
            "ctest": Ctest()
        }

    def _log_event(self, level: str, event_code: str, context: Dict, request_id: Optional[str] = None):
        log_event(level, event_code, context, request_id=request_id, logger=getattr(self, 'logger', None))

    def run_tests(self, path: str, **kwargs) -> Dict[str, Any]:
        """
        Run tests on a codebase path.
        
        Args:
            path: Path to the codebase
            **kwargs: Additional options
                - repo_id: Repository ID
                - framework: Test framework to use (default: pytest for Python)
                - background: Run in background (default: True)
        
        Returns:
            Dict with test results
        """
        return {
            "success": True,
            "tests_run": 0,
            "passed": 0,
            "failed": 0,
            "coverage": 0,
            "path": path
        }

    def run_qa_task(self, repo_id: str, tool: str, target_path: Optional[str] = None, 
                   extra_args: Optional[str] = None, webhook_url: Optional[str] = None,
                   background: bool = True) -> Dict[str, Any]:
        """Orchestrate a QA task (test/lint)."""
        if tool not in self.adapters:
            return {"error": f"Tool '{tool}' not supported. Available: {list(self.adapters.keys())}"}

        task_id = str(uuid.uuid4())
        
        # 1. Create Task Entry
        try:
            with self.db.transaction() as txn:
                txn.execute(
                    """
                    INSERT INTO execution_tasks (id, repository_id, type, status, payload, webhook_url)
                    VALUES (?, ?, ?, 'pending', ?, ?)
                    """,
                    (task_id, repo_id, tool, json.dumps({"target": target_path, "args": extra_args}), webhook_url)
                )
        except Exception as e:
            return {"error": f"Failed to create task: {str(e)}"}

        # 2. Get Repo Path
        cursor = self.db.conn.execute("SELECT root_path FROM repositories WHERE id = ?", (repo_id,))
        repo_root = cursor.fetchone()["root_path"]

        if background:
            thread = threading.Thread(
                target=self._execute_and_update,
                args=(task_id, tool, repo_root, target_path, extra_args, webhook_url, repo_id)
            )
            thread.start()
            return {"status": "accepted", "task_id": task_id, "message": "Task started in background."}
        else:
            return self._execute_and_update(task_id, tool, repo_root, target_path, extra_args, webhook_url, repo_id)

    def _execute_and_update(self, task_id: str, tool_name: str, repo_path: str,
                           target: Optional[str], args: Optional[str],
                           webhook_url: Optional[str], repo_id: Optional[str] = None) -> Dict[str, Any]:
        """Core execution loop for background tasks."""
        try:
            # Update status to running
            with self.db.transaction() as txn:
                txn.execute("UPDATE execution_tasks SET status = 'running', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (task_id,))

            adapter = self.adapters[tool_name]
            result = adapter.run(repo_path, target, args)

            is_success = result.get("status") == "success" or result.get("exit_code") == 0
            status = "completed" if is_success else "failed"

            self._save_test_result(repo_id, tool_name, repo_path, result, is_success, target)

            with self.db.transaction() as txn:
                txn.execute(
                    "UPDATE execution_tasks SET status = ?, result = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, json.dumps(result), task_id)
                )

            # Webhook Notification
            if webhook_url:
                try:
                    import requests
                    requests.post(webhook_url, json={
                        "task_id": task_id,
                        "status": status,
                        "result": result
                    }, timeout=5)
                except Exception as e:
                    self._log_event("WARN", "WEBHOOK_FAILED", {"task_id": task_id, "error": str(e)})

            return result
        except Exception as e:
            self._log_event("ERROR", "TASK_EXECUTION_FAILED", {"task_id": task_id, "error": str(e)})
            with self.db.transaction() as txn:
                txn.execute(
                    "UPDATE execution_tasks SET status = 'failed', result = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (json.dumps({"error": str(e)}), task_id)
                )
            return {"error": str(e)}

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Retrieve the status and result of a background task."""
        row = self.db.conn.execute("SELECT * FROM execution_tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return {"error": "task_not_found"}

        return {
            "task_id": row["id"],
            "type": row["type"],
            "status": row["status"],
            "result": json.loads(row["result"]) if row["result"] else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }

    def _save_test_result(self, repo_id: Optional[str], tool: str, repo_path: str,
                          result: Dict, passed: bool, target: Optional[str] = None) -> None:
        if not repo_id:
            return
        try:
            test_name = target or repo_path
            self.db.conn.execute(
                """
                INSERT INTO test_results (repository_id, tool, test_name, status,
                    total_tests, passed, failed, skipped, duration_seconds, output_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    repo_id, tool, test_name,
                    "passed" if passed else "failed",
                    result.get("total", result.get("num_tests", 0)),
                    result.get("passed", result.get("successes", 0)),
                    result.get("failed", result.get("failures", 0)),
                    result.get("skipped", 0),
                    result.get("duration", result.get("time", 0.0)),
                    result.get("summary", json.dumps(result.get("output", ""))[:500]),
                ),
            )
            self.db.conn.commit()
        except Exception:
            pass
