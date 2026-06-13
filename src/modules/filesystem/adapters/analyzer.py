"""
Class SourceCodeAnalyzer – AST-agnostic pattern analysis for source code files.
Detects bugs, dead code, stubs, TODOs, placeholders, dead variables,
security issues, code smells, anti-patterns, and AI slop.
Renamed from source_analyzer.py for naming consistency.

:project: CodeCortex
:package: Modules.Filesystem.Adapters.Analyzer
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Filesystem-v1.0
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

_TODO_PATTERNS = [
    (re.compile(r"(?i)\bTODO\b"), "todo", "info"),
    (re.compile(r"(?i)\bFIXME\b"), "fixme", "warning"),
    (re.compile(r"(?i)\bHACK\b"), "hack", "warning"),
    (re.compile(r"(?i)\bXXX\b"), "xxx", "info"),
    (re.compile(r"(?i)\bBUG\b"), "bug", "error"),
    (re.compile(r"(?i)\bOPTIMIZE\b"), "optimize", "info"),
    (re.compile(r"(?i)\bREVIEW\b"), "review", "warning"),
    (re.compile(r"(?i)\bWORKAROUND\b"), "workaround", "info"),
    (re.compile(r"(?i)\bHARDCODED\b"), "hardcoded", "warning"),
    (re.compile(r"(?i)\bTEMPORARY\b"), "temporary", "info"),
    (re.compile(r"(?i)\bDEPRECATED\b"), "deprecated", "warning"),
]

_STUB_PATTERNS = {
    "python": [
        re.compile(r"raise\s+NotImplementedError"),
        re.compile(r"raise\s+NotImplementedException"),
        re.compile(r"\.\.\.\s*$", re.MULTILINE),
    ],
    "javascript": [
        re.compile(r"throw\s+new\s+Error\(['\"]Not implemented['\"]\)"),
        re.compile(r"throw\s+new\s+NotImplementedError"),
        re.compile(r"\.\.\.\s*$", re.MULTILINE),
    ],
}

_PLACEHOLDER_PATTERNS = [
    (re.compile(r"(?i)#\s*TODO\b"), "todo_comment"),
    (re.compile(r"(?i)//\s*TODO\b"), "todo_comment"),
    (re.compile(r"(?i)#\s*FIXME\b"), "fixme_comment"),
    (re.compile(r"(?i)//\s*FIXME\b"), "fixme_comment"),
    (re.compile(r"(?i)#\s*Your\s+code\s+here"), "placeholder"),
    (re.compile(r"(?i)//\s*Your\s+code\s+here"), "placeholder"),
    (re.compile(r"(?i)#\s*Insert\s+(your\s+)?code\s+here"), "placeholder"),
    (re.compile(r"(?i)//\s*Insert\s+(your\s+)?code\s+here"), "placeholder"),
    (re.compile(r"(?i)#\s*\.\.\.\s*rest"), "placeholder"),
    (re.compile(r"(?i)//\s*\.\.\.\s*rest"), "placeholder"),
    (re.compile(r"(?i)#\s*implement\s+(this|the)\s+(function|method|logic)"), "placeholder"),
    (re.compile(r"(?i)//\s*implement\s+(this|the)\s+(function|method|logic)"), "placeholder"),
    (re.compile(r"(?i)pass\s+#\s*TODO"), "stub_placeholder"),
    (re.compile(r"(?i)return\s+None\s+#\s*TODO"), "stub_placeholder"),
    (re.compile(r"(?i)return\s+None\s+//\s*TODO"), "stub_placeholder"),
]

_SECURITY_PATTERNS = [
    (re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^'\"]+['\"]"), "hardcoded_password", "high"),
    (re.compile(r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"][A-Za-z0-9_\-]{8,}['\"]"), "api_key_leak", "high"),
    (re.compile(r"(?i)(secret|secret[_-]?key)\s*[=:]\s*['\"][^'\"]{8,}['\"]"), "secret_leak", "high"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws_access_key", "critical"),
    (re.compile(r"-----BEGIN\s+(RSA|OPENSSH|EC|DSA|PRIVATE)\s+KEY-----"), "private_key", "critical"),
    (re.compile(r"(?i)(sk-[A-Za-z0-9]{20,}|sk-[A-Za-z0-9\-]{20,})"), "openai_api_key", "critical"),
    (re.compile(r"(?i)(ghp_|gho_|github_pat_)[A-Za-z0-9_\-]{36,}"), "github_token", "critical"),
    (re.compile(r"(?i)(postgresql|mysql|mongodb)\://[^@\s]+@"), "connection_string_with_creds", "high"),
    (re.compile(r"\beval\s*\("), "unsafe_eval", "critical"),
    (re.compile(r"\bexec\s*\("), "unsafe_exec", "critical"),
    (re.compile(r"\b__import__\s*\("), "unsafe_dynamic_import", "high"),
    (re.compile(r"(?i)sql\s*\+=\s*['\"]"), "sql_injection_concat", "critical"),
    (re.compile(r"(?i)cursor\.execute\(\s*['\"].*\{.*\}"), "sql_injection_format", "high"),
    (re.compile(r"(?i)cursor\.execute\(\s*f['\"]"), "sql_injection_fstring", "high"),
    (re.compile(r"(?i)(cursor|execute|query)\.\s*(execute|executemany)\(\s*['\"].*\s*\+"), "sql_injection_concat", "critical"),
    (re.compile(r"(?i)(db|conn|pg|sql)\.\s*(query|run|exec)\(\s*['\"].*\s*\+"), "sql_injection_concat", "critical"),
    (re.compile(r"(?i)\.execute\(.*%[sdi%]"), "sql_injection_percent", "high"),
    (re.compile(r"(?i)pickle\.loads?\s*\("), "unsafe_deserialization", "high"),
    (re.compile(r"(?i)subprocess\.(call|popen|run)\(.*shell=True"), "shell_injection", "critical"),
    (re.compile(r"(?i)os\.system\s*\("), "shell_injection_os", "critical"),
]

_SMELL_PATTERNS = [
    (re.compile(r"except\s*:\s*\n\s*pass\b"), "empty_except_handler", "warning"),
    (re.compile(r"except\s+Exception\s*:\s*\n\s*pass\b"), "empty_except_handler_broad", "warning"),
    (re.compile(r"\bpass\b"), "bare_pass_marker"),
    (re.compile(r"except\s*:"), "bare_except", "warning"),
    (re.compile(r"\bassert\s+"), "assert_in_production", "info"),
    (re.compile(r"(?i)print\s*\("), "print_statement", "info"),
    (re.compile(r"\bdebugger\b", re.I), "debugger_statement", "info"),
]

_COMMENT_PATTERNS = [
    (re.compile(r"#.*$", re.MULTILINE), "hash"),
    (re.compile(r"//.*$", re.MULTILINE), "double_slash"),
    (re.compile(r"/\*.*?\*/", re.DOTALL), "block"),
    (re.compile(r"'''[\s\S]*?'''", re.DOTALL), "docstring_triple_single"),
    (re.compile(r'"""[\s\S]*?"""', re.DOTALL), "docstring_triple_double"),
]

def _token_count(text: str) -> int:
    return len(text.split())

class SourceCodeAnalyzer:
    """
    Pattern-based source code analysis engine.
    Scans for bugs, dead code, stubs, TODOs, placeholders, dead variables,
    security issues, code smells, and AI slop indicators.
    """

    def analyze(self, content: str, language: str, filename: str, lines: List[str]) -> Dict[str, Any]:
        findings = {
            "todos": self._find_comment_tags(content, lines),
            "stubs": self._find_stubs(content, lines, language),
            "placeholders": self._find_placeholders(content, lines),
            "security_issues": self._find_security_issues(content, lines),
            "code_smells": self._find_code_smells(content, lines),
            "dead_variables": self._find_dead_variables(lines, language),
            "potential_bugs": self._find_potential_bugs(content, lines, language),
        }

        slop = self._calc_slop_score(findings)
        recommendations = self._generate_recommendations(findings, slop)

        return {
            "ai_slop_detection": slop,
            "linting_status": self._build_linting_status(findings),
            "code_smells": findings["code_smells"],
            "security_issues": findings["security_issues"],
            "potential_bugs": findings["potential_bugs"],
            "dead_code": findings["stubs"],
            "unused_variables": findings["dead_variables"],
            "todos": findings["todos"],
            "placeholders": findings["placeholders"],
            "ai_recommendations": recommendations,
        }

    def _find_comment_tags(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        results = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            for pattern, kind, severity in _TODO_PATTERNS:
                for m in pattern.finditer(stripped):
                    col = stripped.find(m.group()) + 1
                    results.append({
                        "type": kind,
                        "message": stripped.strip("# /;").strip(),
                        "line": i,
                        "column": col,
                        "severity": severity,
                    })
                    break
        return results

    def _find_stubs(self, content: str, lines: List[str], language: str) -> List[Dict[str, Any]]:
        results = []

        if language in _STUB_PATTERNS:
            for pattern in _STUB_PATTERNS[language]:
                for m in pattern.finditer(content):
                    line_no = content[:m.start()].count("\n") + 1
                    results.append({
                        "type": "stub_function",
                        "message": f"Stub detected: '{m.group().strip()}'",
                        "line": line_no,
                        "severity": "warning",
                        "suggestion": "Implement the function body",
                    })

        func_body_patterns = {
            "python": re.compile(r"def\s+\w+\s*\([^)]*\)\s*:\s*\n(\s+)pass\s*$", re.MULTILINE),
            "javascript": re.compile(r"(function|=>)\s*[^{]*\{\s*\n\s*\}", re.MULTILINE),
        }
        if language in func_body_patterns:
            for m in func_body_patterns[language].finditer(content):
                line_no = content[:m.start()].count("\n") + 1
                results.append({
                    "type": "empty_function_body",
                    "message": "Function has empty body",
                    "line": line_no,
                    "severity": "warning",
                    "suggestion": "Implement or remove the function",
                })

        stub_class_pattern = re.compile(r"class\s+\w+.*:\s*\n(\s+)pass\s*$", re.MULTILINE)
        for m in stub_class_pattern.finditer(content):
            line_no = content[:m.start()].count("\n") + 1
            results.append({
                "type": "stub_class",
                "message": "Class has no members (only pass)",
                "line": line_no,
                "severity": "warning",
                "suggestion": "Implement class members or remove",
            })

        return results

    def _find_placeholders(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        results = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            for pattern, ptype in _PLACEHOLDER_PATTERNS:
                if pattern.search(stripped):
                    results.append({
                        "type": ptype,
                        "message": stripped.strip("# //;").strip() or ptype,
                        "line": i,
                        "severity": "warning" if ptype != "todo_comment" else "info",
                        "confidence": 0.85,
                    })
                    break
        return results

    def _find_security_issues(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        results = []
        for i, line in enumerate(lines, 1):
            for pattern, stype, severity in _SECURITY_PATTERNS:
                for m in pattern.finditer(line):
                    results.append({
                        "type": stype,
                        "message": f"Potential {stype.replace('_', ' ')} detected",
                        "line": i,
                        "column": m.start() + 1,
                        "severity": severity,
                        "snippet": m.group()[:60],
                    })
                    break
        return results

    def _find_code_smells(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        results = []

        for pattern, stype, *rest in _SMELL_PATTERNS:
            severity = rest[0] if rest else "info"
            for m in pattern.finditer(content):
                line_no = content[:m.start()].count("\n") + 1
                results.append({
                    "type": stype,
                    "message": f"{stype.replace('_', ' ').title()} detected",
                    "line": line_no,
                    "severity": severity,
                })

        long_funcs = self._detect_long_functions(lines)
        results.extend(long_funcs)

        many_params = self._detect_many_parameters(lines)
        results.extend(many_params)

        deep_nesting = self._detect_deep_nesting(lines)
        results.extend(deep_nesting)

        return results

    def _detect_long_functions(self, lines: List[str]) -> List[Dict[str, Any]]:
        results = []
        func_start = None
        func_name = ""
        brace_depth = 0
        indent = 0

        for i, line in enumerate(lines):
            stripped = line.rstrip()
            if re.match(r"^(def|function|func|async\s+def|async\s+function)\s+\w+", stripped):
                if func_start is not None and (i - func_start) > 50:
                    results.append({
                        "type": "long_function",
                        "message": f"Function '{func_name}' is {i - func_start} lines long (>50)",
                        "line": func_start + 1,
                        "severity": "warning",
                        "suggestion": "Consider breaking into smaller functions",
                    })
                func_start = i
                m = re.match(r"(?:async\s+)?(?:def|function|func)\s+(\w+)", stripped)
                func_name = m.group(1) if m else "anonymous"
            elif re.match(r"^\s*class\s+\w+", stripped):
                if func_start is not None and (i - func_start) > 50:
                    results.append({
                        "type": "long_function",
                        "message": f"Function '{func_name}' is {i - func_start} lines long (>50)",
                        "line": func_start + 1,
                        "severity": "warning",
                        "suggestion": "Consider breaking into smaller functions",
                    })
                func_start = None
            elif stripped.startswith("}") and brace_depth > 0:
                brace_depth -= 1
                if brace_depth == 0 and func_start is not None and (i - func_start) > 50:
                    results.append({
                        "type": "long_function",
                        "message": f"Function '{func_name}' is {i - func_start} lines long (>50)",
                        "line": func_start + 1,
                        "severity": "warning",
                        "suggestion": "Consider breaking into smaller functions",
                    })
                    func_start = None

        if func_start is not None and (len(lines) - func_start) > 50:
            results.append({
                "type": "long_function",
                "message": f"Function '{func_name}' is {len(lines) - func_start} lines long (>50)",
                "line": func_start + 1,
                "severity": "warning",
                "suggestion": "Consider breaking into smaller functions",
            })

        return results

    def _detect_many_parameters(self, lines: List[str]) -> List[Dict[str, Any]]:
        results = []
        for i, line in enumerate(lines, 1):
            m = re.match(r"^\s*(?:async\s+)?(?:def|function|func)\s+\w+\s*\(([^)]+)\)", line)
            if m:
                params = [p.strip() for p in m.group(1).split(",") if p.strip() and p.strip() != "self" and p.strip() != "cls"]
                if len(params) > 5:
                    results.append({
                        "type": "too_many_parameters",
                        "message": f"Function has {len(params)} parameters (>5)",
                        "line": i,
                        "severity": "warning",
                        "suggestion": "Consider using a config object or reducing params",
                    })
        return results

    def _detect_deep_nesting(self, lines: List[str]) -> List[Dict[str, Any]]:
        results = []
        max_nesting = 0
        current_nesting = 0

        for i, line in enumerate(lines, 1):
            stripped = line.rstrip()
            if not stripped.strip():
                continue
            indent = len(stripped) - len(stripped.lstrip())
            nest_level = indent // 4
            if nest_level > current_nesting:
                current_nesting = nest_level
                if nest_level > 4:
                    max_nesting = max(max_nesting, nest_level)

        if max_nesting > 4:
            results.append({
                "type": "deep_nesting",
                "message": f"Maximum nesting depth is {max_nesting} levels (>4 recommended)",
                "line": 1,
                "severity": "warning",
                "suggestion": "Consider extracting nested logic into helper functions",
            })
        return results

    def _find_dead_variables(self, lines: List[str], language: str) -> List[Dict[str, Any]]:
        results = []
        builtins = {"self", "cls", "True", "False", "None", "super", "print", "len", "range", "type", "str", "int",
                     "float", "list", "dict", "set", "tuple", "bool", "isinstance", "hasattr", "getattr", "setattr",
                     "open", "import", "from", "as", "return", "if", "elif", "else", "for", "while", "try", "except",
                     "finally", "with", "yield", "raise", "assert", "break", "continue", "pass", "del", "global", "nonlocal",
                     "lambda", "class", "def", "async", "await", "in", "not", "and", "or", "is", "import",
                     "key", "value", "item", "index", "i", "j", "k", "n", "x", "y", "z", "args", "kwargs"}

        assign_re = re.compile(r"^\s*(\w+)\s*=\s*[^=]")

        for i, line in enumerate(lines):
            m = assign_re.match(line)
            if not m:
                continue
            var_name = m.group(1)
            if var_name in builtins:
                continue
            if var_name.startswith("_"):
                continue
            indent = len(line) - len(line.lstrip())
            if indent == 0 and not var_name.startswith("__"):
                continue
            if self._is_var_used(var_name, lines, i):
                continue
            results.append({
                "type": "dead_variable",
                "message": f"Variable '{var_name}' is assigned but never referenced after assignment",
                "line": i + 1,
                "severity": "warning",
                "confidence": 0.7,
                "suggestion": "Remove unused variable or check for typo",
            })
        return results

    def _is_var_used(self, var_name: str, lines: List[str], assign_idx: int) -> bool:
        pattern = re.compile(r"(?<!\w)" + re.escape(var_name) + r"(?!\w)")
        for j in range(assign_idx + 1, len(lines)):
            if pattern.search(lines[j]):
                return True
        return False

    def _find_potential_bugs(self, content: str, lines: List[str], language: str) -> List[Dict[str, Any]]:
        results = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if re.search(r"==\s*None\b", stripped) and language == "python":
                results.append({
                    "type": "comparison_to_none",
                    "message": "Use 'is None' instead of '== None'",
                    "line": i,
                    "severity": "info",
                    "suggestion": "Replace '== None' with 'is None'",
                    "confidence": 0.9,
                })

            if re.search(r"except\s*:", stripped) and not re.search(r"except\s+\w+", stripped):
                results.append({
                    "type": "bare_except",
                    "message": "Bare except catches all exceptions including KeyboardInterrupt",
                    "line": i,
                    "severity": "warning",
                    "suggestion": "Catch specific exceptions",
                    "confidence": 0.95,
                })

            if re.search(r"except\s*:", stripped) and i + 1 < len(lines) and "pass" in lines[i]:
                results.append({
                    "type": "silent_except",
                    "message": "Empty except block silently swallows all exceptions",
                    "line": i,
                    "severity": "error",
                    "suggestion": "Log or handle the exception",
                    "confidence": 0.9,
                })

            if re.search(r"\bfloat\s*\(\s*['\"]\s*['\"]\s*\)", stripped):
                results.append({
                    "type": "empty_float_cast",
                    "message": "float('') will raise ValueError on non-empty string",
                    "line": i,
                    "severity": "error",
                    "confidence": 0.95,
                })

            if re.search(r"=\s*\[\s*\]\s*\n\s*for\s", stripped) or re.search(r"=\s*\[\s*\]\s*;", stripped):
                results.append({
                    "type": "inefficient_loop",
                    "message": "Consider using list comprehension instead of for+append pattern",
                    "line": i,
                    "severity": "info",
                    "confidence": 0.7,
                })

            if re.search(r"\binput\s*\(\s*\)", stripped):
                results.append({
                    "type": "unsafe_input",
                    "message": "Using input() in Python 2 is dangerous (eval). Python 3 is safe.",
                    "line": i,
                    "severity": "info" if language == "python" else "warning",
                    "confidence": 0.5,
                })

        if language == "python":
            empty_list_stack = []
            for i, line in enumerate(lines):
                if re.search(r"=\s*\[\s*\]\s*$", line) and i + 1 < len(lines) and "for" in lines[i + 1]:
                    empty_list_stack.append(i + 1)

            for i, line in enumerate(lines, 1):
                if re.search(r"for\s+\w+\s+in\s+\[\s*\]", line):
                    results.append({
                        "type": "empty_iteration",
                        "message": "Iterating over an empty list literal",
                        "line": i,
                        "severity": "info",
                        "confidence": 0.95,
                    })

        return results

    def _calc_slop_score(self, findings: Dict[str, Any]) -> Dict[str, Any]:
        weights = {
            "todos": 5,
            "stubs": 20,
            "placeholders": 15,
            "security_issues": 30,
            "code_smells": 8,
            "dead_variables": 10,
            "potential_bugs": 15,
        }

        scores = {}
        total = 0
        max_possible = 0

        for category, weight in weights.items():
            items = findings.get(category, [])
            count = len(items)
            category_score = min(count * weight, 100)
            scores[category] = {
                "count": count,
                "weight": weight,
                "score": category_score,
                "severity": self._categorize(category_score),
            }
            total += category_score
            max_possible += 100

        final_score = min(round(total / max(1, len(weights))), 100) if max_possible > 0 else 0
        overall_severity = self._categorize(final_score)

        detections = []
        for category, data in scores.items():
            for item in findings.get(category, []):
                detections.append({
                    "type": item.get("type", category),
                    "line": item.get("line", 0),
                    "message": item.get("message", ""),
                    "severity": item.get("severity", "info"),
                    "confidence": item.get("confidence", 0.8),
                })

        return {
            "slop_score": final_score,
            "severity": overall_severity,
            "detections": sorted(detections, key=lambda x: -{"critical": 4, "error": 3, "warning": 2, "info": 1}.get(x["severity"], 0))[:50],
            "category_breakdown": scores,
            "total_issues": sum(len(v) for v in findings.values()),
        }

    def _build_linting_status(self, findings: Dict[str, Any]) -> Dict[str, Any]:
        errors = sum(1 for f in findings.get("security_issues", []) if f.get("severity") in ("critical", "error"))
        errors += sum(1 for f in findings.get("potential_bugs", []) if f.get("severity") == "error")
        warnings = sum(1 for f in findings.get("code_smells", []) if f.get("severity") == "warning")
        warnings += sum(1 for f in findings.get("stubs", []) if f.get("severity") == "warning")
        info = sum(1 for f in findings.get("todos", []))
        info += sum(1 for f in findings.get("placeholders", []))

        details = []
        for f in findings.get("security_issues", [])[:10]:
            details.append({
                "rule": f.get("type", "SEC000"),
                "message": f.get("message", ""),
                "line": f.get("line", 0),
                "severity": f.get("severity", "error"),
                "fix": f.get("suggestion", ""),
            })
        for f in findings.get("potential_bugs", [])[:10]:
            details.append({
                "rule": f.get("type", "BUG000"),
                "message": f.get("message", ""),
                "line": f.get("line", 0),
                "severity": f.get("severity", "warning"),
                "fix": f.get("suggestion", ""),
            })
        for f in findings.get("code_smells", [])[:10]:
            details.append({
                "rule": f.get("type", "SMELL000"),
                "message": f.get("message", ""),
                "line": f.get("line", 0),
                "severity": f.get("severity", "info"),
                "fix": f.get("suggestion", ""),
            })

        return {
            "errors": errors,
            "warnings": warnings,
            "info": info,
            "details": details[:25],
        }

    def _generate_recommendations(self, findings: Dict[str, Any], slop: Dict[str, Any]) -> List[Dict[str, Any]]:
        recs = []

        if findings["security_issues"]:
            crit = [f for f in findings["security_issues"] if f.get("severity") in ("critical", "high")]
            if crit:
                recs.append({
                    "message": f"Fix {len(crit)} critical/high security issues immediately",
                    "priority": "critical",
                    "effort_estimate": "medium",
                })

        if findings["stubs"]:
            recs.append({
                "message": f"Implement or remove {len(findings['stubs'])} stub function(s)",
                "priority": "high",
                "effort_estimate": "low",
            })

        if findings["potential_bugs"]:
            recs.append({
                "message": f"Review {len(findings['potential_bugs'])} potential bug(s)",
                "priority": "high",
                "effort_estimate": "low",
            })

        if findings["dead_variables"]:
            recs.append({
                "message": f"Remove {len(findings['dead_variables'])} unused variable(s)",
                "priority": "medium",
                "effort_estimate": "low",
            })

        if findings["todos"]:
            recs.append({
                "message": f"Resolve {len(findings['todos'])} TODO/FIXME/HACK comment(s)",
                "priority": "medium",
                "effort_estimate": "medium",
            })

        if findings["placeholders"]:
            recs.append({
                "message": f"Replace {len(findings['placeholders'])} placeholder code segment(s)",
                "priority": "high",
                "effort_estimate": "low",
            })

        if findings["code_smells"]:
            smells = [f for f in findings["code_smells"] if f.get("severity") == "warning"]
            if smells:
                recs.append({
                    "message": f"Refactor {len(smells)} code smell(s) for better maintainability",
                    "priority": "medium",
                    "effort_estimate": "medium",
                })

        score = slop.get("slop_score", 0)
        if score > 50:
            recs.append({
                "message": f"High AI slop score ({score}/100). Review code quality thoroughly",
                "priority": "high",
                "effort_estimate": "high",
            })
        elif score > 25:
            recs.append({
                "message": f"Moderate AI slop score ({score}/100). Address flagged issues",
                "priority": "medium",
                "effort_estimate": "medium",
            })

        return recs[:10]

    def _categorize(self, score: int) -> str:
        if score >= 70:
            return "critical"
        if score >= 50:
            return "high"
        if score >= 25:
            return "medium"
        if score >= 10:
            return "low"
        return "clean"
