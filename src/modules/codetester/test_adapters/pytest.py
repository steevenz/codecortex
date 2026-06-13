"""
Pytest - pytest test framework support with discover, coverage, and result parsing.

:project: CodeCortex
:package: Modules.Codetester.Test_adapters.Pytest
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-CodeTester-v1.0
"""

import subprocess
import json
import tempfile
import os
import re
from typing import Dict, Any, Optional
from src.modules.codetester.test_adapters.base import BaseQA

class Pytest(BaseQA):
    def run(self, repo_path: str, target_path: Optional[str] = None, extra_args: Optional[str] = None) -> Dict[str, Any]:
        if not os.path.isdir(repo_path):
            return {"tool": "pytest", "status": "error", "error": f"Repository path does not exist: {repo_path}"}

        if target_path:
            repo_path_abs = os.path.abspath(repo_path)
            target_path_abs = os.path.abspath(os.path.join(repo_path, target_path))
            if not target_path_abs.startswith(repo_path_abs):
                return {"tool": "pytest", "status": "error", "error": "Target path is outside the repository"}

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            report_path = tmp.name

        cmd = ["pytest", "--json-report", f"--json-report-file={report_path}"]
        if target_path:
            cmd.append(target_path)
        if extra_args:
            cmd.extend(extra_args.split())

        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=120
            )

            summary = {"tool": "pytest", "status": "success" if result.returncode in (0, 1) else "failed"}

            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                    summary["report"] = {
                        "total_tests": report_data.get("summary", {}).get("total", 0),
                        "passed": report_data.get("summary", {}).get("passed", 0),
                        "failed": report_data.get("summary", {}).get("failed", 0),
                        "skipped": report_data.get("summary", {}).get("skipped", 0),
                        "duration": report_data.get("duration", 0),
                    }
                    tests_raw = report_data.get("tests", [])
                    parsed = []
                    for t in tests_raw:
                        entry = {
                            "name": t.get("name", ""),
                            "file": t.get("file", ""),
                            "line": t.get("line", 0),
                            "status": t.get("outcome", "unknown"),
                            "duration_ms": t.get("duration", 0) * 1000,
                        }
                        if t.get("call") and t["call"].get("longrepr"):
                            entry["failure"] = {
                                "type": "AssertionError",
                                "message": t["call"]["longrepr"],
                                "traceback": t["call"].get("longrepr", ""),
                            }
                        parsed.append(entry)
                    summary["parsed_tests"] = parsed
                os.remove(report_path)

            summary.update({
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:],
            })

            return summary
        except subprocess.TimeoutExpired:
            if os.path.exists(report_path):
                os.remove(report_path)
            return {"tool": "pytest", "status": "error", "error": "Pytest execution timed out"}
        except Exception as e:
            if os.path.exists(report_path):
                os.remove(report_path)
            return {"tool": "pytest", "status": "error", "error": "An error occurred while running pytest"}

    def get_name(self) -> str:
        return "pytest"

    def discover(self, repo_path: str, target_path: Optional[str] = None) -> Dict[str, Any]:
        if not os.path.isdir(repo_path):
            return {"tests": [], "test_files": [], "markers": [], "categories": {}}

        use_path = os.path.join(repo_path, target_path) if target_path else repo_path

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            report_path = tmp.name

        cmd = ["pytest", "--collect-only", "--json-report", f"--json-report-file={report_path}"]
        cmd.append(use_path)

        try:
            subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=60)

            test_files_set = set()
            tests = []
            markers_set = set()
            categories = {}

            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                for collector in report_data.get("collectors", []):
                    for node in collector.get("result", []):
                        fname = node.get("file", "")
                        test_files_set.add(fname)
                        tests.append({
                            "name": node.get("name", ""),
                            "file": fname,
                            "line": node.get("line", 0),
                            "markers": [],
                            "category": "unit",
                        })
                os.remove(report_path)

            return {
                "tests": tests,
                "test_files": sorted(test_files_set),
                "markers": sorted(markers_set),
                "categories": categories,
            }
        except Exception:
            if os.path.exists(report_path):
                os.remove(report_path)
            return {"tests": [], "test_files": [], "markers": [], "categories": {}}

    def run_with_coverage(self, repo_path: str, target_path: Optional[str] = None) -> Dict[str, Any]:
        run_result = self.run(repo_path, target_path, extra_args="--cov")

        coverage_data = {"overall_coverage": 0.0, "files": [], "recommendations": []}
        stdout = run_result.get("stdout", "")

        cov_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", stdout)
        if cov_match:
            coverage_data["overall_coverage"] = float(cov_match.group(1))

        file_cov_pattern = re.finditer(
            r"^(\S+\.py)\s+(\d+)\s+(\d+)\s+(\d+)%\s*$",
            stdout,
            re.MULTILINE,
        )
        for m in file_cov_pattern:
            cov_pct = float(m.group(4))
            coverage_data["files"].append({
                "file": m.group(1),
                "coverage": cov_pct,
                "total_lines": int(m.group(2)),
                "covered_lines": int(m.group(3)),
                "uncovered_lines": [],
                "uncovered_functions": [],
            })
            if cov_pct < 50:
                coverage_data["recommendations"].append({
                    "severity": "high",
                    "message": f"File {m.group(1)} has low coverage ({cov_pct}%)",
                    "file": m.group(1),
                    "suggested_tests": [],
                })

        return dict(run_result, **{"coverage": coverage_data})

    def parse_results(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        parsed_tests = raw_output.pop("parsed_tests", [])
        report = raw_output.get("report", {})

        summary = {
            "total": report.get("total_tests", len(parsed_tests)),
            "passed": report.get("passed", 0),
            "failed": report.get("failed", 0),
            "skipped": report.get("skipped", 0),
            "errors": 0,
        }

        for t in parsed_tests:
            if t["status"] == "error":
                summary["errors"] += 1

        return {
            "framework": "pytest",
            "duration_seconds": report.get("duration", 0),
            "summary": summary,
            "results": parsed_tests,
            "status": raw_output.get("status", "completed"),
        }
