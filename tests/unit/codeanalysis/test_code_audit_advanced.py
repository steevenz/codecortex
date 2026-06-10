"""
Advanced tests for CodeAuditor with N+1, empty code, and structure detection.

Tests cover:
- N+1 query detection
- Empty function/class detection
- Unclosed bracket detection
- Unclosed HTML/XML tag detection
- JSON output validation
"""

import pytest
import tempfile
import os
import json
from pathlib import Path

from src.modules.codeanalysis.analyzers.audit import CodeAuditor


class TestNPlusOneDetection:
    """Test N+1 query pattern detection."""

    def test_nplus1_in_python_loop(self):
        """Test detection of N+1 pattern in Python loop."""
        content = '''
users = User.objects.all()
for user in users:
    orders = user.orders.count()
'''
        findings = CodeAuditor._find_nplus1_queries(content, "test.py")
        assert len(findings) >= 1
        assert findings[0]["type"] == "nplus1_query"
        assert findings[0]["severity"] == "high"

    def test_no_nplus1_without_loop(self):
        """Test that non-loop queries are not flagged."""
        content = '''
users = User.objects.all()
orders = Order.objects.count()
'''
        findings = CodeAuditor._find_nplus1_queries(content, "test.py")
        assert len(findings) == 0

    def test_nplus1_in_javascript(self):
        """Test detection in JavaScript context."""
        content = '''
const users = await User.findMany();
for (const user of users) {
    const count = await user.orders.count();
}
'''
        findings = CodeAuditor._find_nplus1_queries(content, "test.js")
        assert len(findings) >= 1


class TestEmptyFunctionDetection:
    """Test empty function detection."""

    def test_empty_function_with_pass(self):
        """Test detection of empty function with pass."""
        content = '''
def my_function():
    pass
'''
        findings = CodeAuditor._find_empty_functions(content, "test.py")
        assert len(findings) >= 1
        assert findings[0]["type"] == "empty_function"

    def test_empty_function_with_not_implemented(self):
        """Test detection of function with NotImplementedError."""
        content = '''
def my_function():
    raise NotImplementedError("Not implemented")
'''
        findings = CodeAuditor._find_empty_functions(content, "test.py")
        assert len(findings) >= 1

    def test_empty_function_with_braces(self):
        """Test detection of empty function with {}."""
        content = '''
def my_function(): {}
'''
        findings = CodeAuditor._find_empty_functions(content, "test.py")
        assert len(findings) >= 1

    def test_non_empty_function_not_flagged(self):
        """Test that non-empty functions are not flagged."""
        content = '''
def my_function():
    return 42
'''
        findings = CodeAuditor._find_empty_functions(content, "test.py")
        assert len(findings) == 0


class TestEmptyClassDetection:
    """Test empty class detection."""

    def test_empty_class_with_pass(self):
        """Test detection of empty class with pass."""
        content = '''
class MyClass:
    pass
'''
        findings = CodeAuditor._find_empty_classes(content, "test.py")
        assert len(findings) >= 1
        assert findings[0]["type"] == "empty_class"

    def test_empty_class_with_braces(self):
        """Test detection of empty class with {}."""
        content = '''
class MyClass: {}
'''
        findings = CodeAuditor._find_empty_classes(content, "test.py")
        assert len(findings) >= 1

    def test_non_empty_class_not_flagged(self):
        """Test that non-empty classes are not flagged."""
        content = '''
class MyClass:
    def __init__(self):
        self.value = 42
'''
        findings = CodeAuditor._find_empty_classes(content, "test.py")
        assert len(findings) == 0


class TestUnclosedBracketDetection:
    """Test unclosed bracket detection."""

    def test_unclosed_square_bracket(self):
        """Test detection of unclosed square bracket."""
        content = '''
arr = [1, 2, 3
'''
        findings = CodeAuditor._find_unclosed_brackets(content, "test.py")
        assert len(findings) >= 1
        assert findings[0]["type"] == "unclosed_bracket"

    def test_unclosed_parenthesis(self):
        """Test detection of unclosed parenthesis."""
        content = '''
result = func(1, 2, 3
'''
        findings = CodeAuditor._find_unclosed_brackets(content, "test.py")
        assert len(findings) >= 1

    def test_unclosed_brace(self):
        """Test detection of unclosed brace."""
        content = '''
data = {"key": "value"
'''
        findings = CodeAuditor._find_unclosed_brackets(content, "test.py")
        assert len(findings) >= 1

    def test_mismatched_brackets(self):
        """Test detection of mismatched brackets."""
        content = '''
arr = [1, 2, 3)
'''
        findings = CodeAuditor._find_unclosed_brackets(content, "test.py")
        assert len(findings) >= 1
        assert findings[0]["type"] == "mismatched_bracket"

    def test_valid_brackets_not_flagged(self):
        """Test that valid brackets are not flagged."""
        content = '''
arr = [1, 2, 3]
obj = {"key": "value"}
result = func(1, 2, 3)
'''
        findings = CodeAuditor._find_unclosed_brackets(content, "test.py")
        assert len(findings) == 0


class TestUnclosedHTMLTagDetection:
    """Test unclosed HTML/XML tag detection."""

    def test_unclosed_html_tag(self):
        """Test detection of unclosed HTML tag."""
        content = '''
<div>Hello World
<p>This is a paragraph
'''
        findings = CodeAuditor._find_unclosed_html_tags(content, "test.html")
        assert len(findings) >= 2
        assert findings[0]["type"] == "unclosed_html_tag"

    def test_void_elements_not_flagged(self):
        """Test that void elements are not flagged."""
        content = '''
<br>
<hr>
<img src="test.jpg">
'''
        findings = CodeAuditor._find_unclosed_html_tags(content, "test.html")
        assert len(findings) == 0

    def test_valid_html_not_flagged(self):
        """Test that valid HTML is not flagged."""
        content = '''
<div>Hello</div>
<p>World</p>
'''
        findings = CodeAuditor._find_unclosed_html_tags(content, "test.html")
        assert len(findings) == 0


class TestJSONOutput:
    """Test JSON output structure."""

    def test_output_structure(self):
        """Test that JSON output has correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('''
def my_function():
    pass

# TODO: Implement this
for item in items:
    item.count()
''')

            result = CodeAuditor.audit({
                "target_path": tmpdir,
                "scan_categories": ["comments", "empty_code", "nplus1"]
            })

            assert result["success"] is True
            assert "data" in result
            data = result["data"]
            assert "target" in data
            assert "scanned_files" in data
            assert "summary" in data
            assert "findings" in data
            assert "recommendations" in data

    def test_findings_structure(self):
        """Test that findings have correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('''
def my_function():
    pass
''')

            result = CodeAuditor.audit({
                "target_path": tmpdir,
                "scan_categories": ["empty_code"]
            })

            findings = result["data"]["findings"]
            assert "empty_functions" in findings
            assert len(findings["empty_functions"]) >= 1

            func_finding = findings["empty_functions"][0]
            assert "type" in func_finding
            assert "severity" in func_finding
            assert "line" in func_finding
            assert "message" in func_finding
            assert "file" in func_finding


class TestIntegration:
    """Integration tests for full audit workflow."""

    def test_full_audit_workflow(self):
        """Test complete audit workflow with all categories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text('''
import os

# TODO: Implement this function
def my_function():
    pass

# FIXME: This is broken
class MyClass:
    pass

# N+1 pattern
for user in users:
    User.objects.get(user=user)
''')

            result = CodeAuditor.audit({
                "target_path": tmpdir,
                "scan_categories": ["comments", "empty_code", "nplus1", "secrets", "pii"]
            })

            assert result["success"] is True
            data = result["data"]
            assert data["scanned_files"] == 1
            assert data["summary"]["medium"] >= 2
            assert data["summary"]["high"] >= 1
            assert data["summary"]["critical"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
