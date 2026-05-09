"""
/**
 * @project   CodeCortex
 * @package   Domain/CodeTester
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Class QAService - Manage testing and linting jobs with background execution and webhooks.
 */
"""

import json
import uuid
import threading
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path
from src.core.database import DatabaseManager
from src.core.logging_config import get_logger
from src.domain.codetester.infrastructure.adapters.pytest_adapter import PytestAdapter
from src.domain.codetester.infrastructure.adapters.flake8_adapter import Flake8Adapter
from src.domain.codetester.infrastructure.adapters.unittest_adapter import UnittestAdapter
from src.domain.codetester.infrastructure.adapters.jest_adapter import JestAdapter
from src.domain.codetester.infrastructure.adapters.phpunit_adapter import PHPUnitAdapter
from src.domain.codetester.infrastructure.adapters.npm_adapter import NpmAdapter
from src.domain.codetester.infrastructure.adapters.pnpm_adapter import PnpmAdapter
from src.domain.codetester.infrastructure.adapters.vitest_adapter import VitestAdapter
from src.domain.codetester.infrastructure.adapters.yarn_adapter import YarnAdapter
from src.domain.codetester.infrastructure.adapters.go_test_adapter import GoTestAdapter
from src.domain.codetester.infrastructure.adapters.cargo_test_adapter import CargoTestAdapter
from src.domain.codetester.infrastructure.adapters.swift_test_adapter import SwiftTestAdapter
from src.domain.codetester.infrastructure.adapters.kotlin_test_adapter import KotlinTestAdapter
from src.domain.codetester.infrastructure.adapters.sbt_test_adapter import SbtTestAdapter
from src.domain.codetester.infrastructure.adapters.maven_test_adapter import MavenTestAdapter
from src.domain.codetester.infrastructure.adapters.ruby_test_adapter import RubyTestAdapter
from src.domain.codetester.infrastructure.adapters.flutter_test_adapter import FlutterTestAdapter
from src.domain.codetester.infrastructure.adapters.dart_test_adapter import DartTestAdapter
from src.domain.codetester.infrastructure.adapters.haskell_test_adapter import HaskellTestAdapter
from src.domain.codetester.infrastructure.adapters.elixir_test_adapter import ElixirTestAdapter
from src.domain.codetester.infrastructure.adapters.dotnet_test_adapter import DotNetTestAdapter
from src.domain.codetester.infrastructure.adapters.perl_test_adapter import PerlTestAdapter
from src.domain.codetester.infrastructure.adapters.stylelint_adapter import StylelintAdapter
from src.domain.codetester.infrastructure.adapters.ctest_adapter import CtestAdapter

logger = get_logger("CodeCortex.Domain.CodeTester.QA")

class QAService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.adapters = {
            "pytest": PytestAdapter(),
            "flake8": Flake8Adapter(),
            "unittest": UnittestAdapter(),
            "jest": JestAdapter(),
            "phpunit": PHPUnitAdapter(),
            "npm": NpmAdapter(),
            "pnpm": PnpmAdapter(),
            "vitest": VitestAdapter(),
            "yarn": YarnAdapter(),
            "go_test": GoTestAdapter(),
            "cargo_test": CargoTestAdapter(),
            "swift_test": SwiftTestAdapter(),
            "kotlin_test": KotlinTestAdapter(),
            "sbt_test": SbtTestAdapter(),
            "maven_test": MavenTestAdapter(),
            "ruby_test": RubyTestAdapter(),
            "flutter_test": FlutterTestAdapter(),
            "dart_test": DartTestAdapter(),
            "haskell_test": HaskellTestAdapter(),
            "elixir_test": ElixirTestAdapter(),
            "dotnet_test": DotNetTestAdapter(),
            "perl_test": PerlTestAdapter(),
            "stylelint": StylelintAdapter(),
            "ctest": CtestAdapter()
        }

    def _log_event(self, level: str, event_code: str, context: Dict):
        msg = f"[{event_code}] {json.dumps(context)}"
        if level == "ERROR":
            logger.error(msg)
        else:
            logger.info(msg)

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
                args=(task_id, tool, repo_root, target_path, extra_args, webhook_url)
            )
            thread.start()
            return {"status": "accepted", "task_id": task_id, "message": "Task started in background."}
        else:
            return self._execute_and_update(task_id, tool, repo_root, target_path, extra_args, webhook_url)

    def _execute_and_update(self, task_id: str, tool_name: str, repo_path: str, 
                           target: Optional[str], args: Optional[str], 
                           webhook_url: Optional[str]) -> Dict[str, Any]:
        """Core execution loop for background tasks."""
        try:
            # Update status to running
            with self.db.transaction() as txn:
                txn.execute("UPDATE execution_tasks SET status = 'running', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (task_id,))

            adapter = self.adapters[tool_name]
            result = adapter.run(repo_path, target, args)

            # Check for success in various formats
            is_success = result.get("status") == "success" or result.get("exit_code") == 0
            status = "completed" if is_success else "failed"
            
            # Update DB with result
            with self.db.transaction() as txn:
                txn.execute(
                    "UPDATE execution_tasks SET status = ?, result = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, json.dumps(result), task_id)
                )

            # Webhook Notification
            if webhook_url:
                try:
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
