"""
Comprehensive tests for enhanced CodeAuditor with multi-language support.

Tests cover:
- Comment tag detection across Python, JavaScript, Java, TypeScript
- Priority classification
- Confidence scoring
- Context extraction
- Error handling
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.modules.codeanalysis.analyzers.audit import (
    CodeAuditor,
    CommentTag,
    TAG_PATTERNS,
    Priority,
)


class TestCommentTagDetection:
    """Test comment tag detection across multiple languages."""

    def test_python_todo_detection(self):
        """Test TODO detection in Python code."""
        content = '''
# TODO: Implement this function
def my_function():
    pass
'''
        tags = CodeAuditor._find_comment_tags(content, "test.py", None, None)
        assert len(tags) == 1
        assert tags[0].tag == "TODO"
        assert tags[0].priority == "high"
        assert tags[0].line == 2

    def test_python_fixme_detection(self):
        """Test FIXME detection in Python code."""
        content = '''
# FIXME: This is a bug
x = broken_function()
'''
        tags = CodeAuditor._find_comment_tags(content, "test.py", None, None)
        assert len(tags) == 1
        assert tags[0].tag == "FIXME"
        assert tags[0].priority == "critical"

    def test_python_docstring_detection(self):
        """Test tag detection in Python docstrings."""
        content = '''
def my_function():
    """
    TODO: Add proper documentation
    FIXME: This needs fixing
    """
    pass
'''
        tags = CodeAuditor._find_comment_tags(content, "test.py", None, None)
        assert len(tags) >= 2
        tag_types = [t.tag for t in tags]
        assert "TODO" in tag_types
        assert "FIXME" in tag_types

    def test_javascript_line_comment(self):
        """Test detection in JavaScript line comments."""
        content = '''
// TODO: Fix this later
// FIXME: Critical bug here
// HACK: Temporary workaround
'''
        tags = CodeAuditor._find_comment_tags(content, "test.js", None, None)
        assert len(tags) >= 3
        tag_types = [t.tag for t in tags]
        assert "TODO" in tag_types
        assert "FIXME" in tag_types
        assert "HACK" in tag_types

    def test_javascript_block_comment(self):
        """Test detection in JavaScript block comments."""
        content = '''
/*
 * TODO: Implement feature
 * NOTE: This is important
 */
'''
        tags = CodeAuditor._find_comment_tags(content, "test.js", None, None)
        assert len(tags) >= 2

    def test_java_comment_detection(self):
        """Test detection in Java code."""
        content = '''
// TODO: Add implementation
/* FIXME: Bug in this method */
'''
        tags = CodeAuditor._find_comment_tags(content, "test.java", None, None)
        assert len(tags) >= 2

    def test_typescript_comment_detection(self):
        """Test detection in TypeScript code."""
        content = '''
// TODO: Type this properly
// WARN: Potential issue
'''
        tags = CodeAuditor._find_comment_tags(content, "test.ts", None, None)
        assert len(tags) >= 2


class TestPriorityClassification:
    """Test priority classification for comment tags."""

    def test_critical_priority(self):
        """Test critical priority tags."""
        critical_tags = ["FIXME", "BUG"]
        for tag in critical_tags:
            pattern = next(p for p in TAG_PATTERNS if p["tag"] == tag)
            assert pattern["priority"] == "critical"

    def test_high_priority(self):
        """Test high priority tags."""
        high_tags = ["TODO", "XXX", "STUB"]
        for tag in high_tags:
            pattern = next(p for p in TAG_PATTERNS if p["tag"] == tag)
            assert pattern["priority"] == "high"

    def test_medium_priority(self):
        """Test medium priority tags."""
        medium_tags = ["HACK", "WARN", "REVIEW", "DEPRECATED", "UNDONE", "CONSIDER", "QUESTION"]
        for tag in medium_tags:
            pattern = next(p for p in TAG_PATTERNS if p["tag"] == tag)
            assert pattern["priority"] == "medium"

    def test_low_priority(self):
        """Test low priority tags."""
        low_tags = ["NOTE", "OPTIMIZE"]
        for tag in low_tags:
            pattern = next(p for p in TAG_PATTERNS if p["tag"] == tag)
            assert pattern["priority"] == "low"


class TestConfidenceScoring:
    """Test confidence scoring for tag detection."""

    def test_high_confidence_in_comment(self):
        """Test high confidence when tag is in actual comment."""
        content = "# TODO: This is a real task"
        tags = CodeAuditor._find_comment_tags(content, "test.py", None, None)
        assert len(tags) == 1
        assert tags[0].confidence >= 0.8

    def test_no_detection_in_string_literal(self):
        """Test that tags inside string literals are not detected."""
        content = 'x = "TODO"'
        tags = CodeAuditor._find_comment_tags(content, "test.py", None, None)
        assert len(tags) == 0


class TestContextExtraction:
    """Test context extraction functionality."""

    def test_line_number_extraction(self):
        """Test line number is correctly extracted."""
        content = '''line1
line2
# TODO: Task on line 3
line4'''
        tags = CodeAuditor._find_comment_tags(content, "test.py", None, None)
        assert tags[0].line == 3

    def test_column_extraction(self):
        """Test column position is extracted."""
        content = '''# TODO: Task at column 2'''
        tags = CodeAuditor._find_comment_tags(content, "test.py", None, None)
        assert tags[0].column >= 0

    def test_message_extraction(self):
        """Test message is extracted from comment."""
        content = "# TODO: Implement this feature"
        tags = CodeAuditor._find_comment_tags(content, "test.py", None, None)
        assert "Implement this feature" in tags[0].message

    def test_context_extraction(self):
        """Test broader context is extracted."""
        content = '''
# TODO: Task description
x = 1
y = 2
'''
        tags = CodeAuditor._find_comment_tags(content, "test.py", None, None)
        assert len(tags[0].context) > 0


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_nonexistent_path(self):
        """Test handling of nonexistent target path."""
        result = CodeAuditor.audit({"target_path": "/nonexistent/path"})
        assert result["success"] is False
        assert result["status_code"] == 400

    def test_unsupported_file_extension(self):
        """Test handling of unsupported file types."""
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"some content")
            fname = f.name
        try:
            result = CodeAuditor.audit({
                "target_path": fname,
                "scan_categories": ["comments"]
            })
            assert result["success"] is True
        finally:
            os.unlink(fname)

    def test_invalid_regex_handling(self):
        """Test that invalid regex patterns don't crash the auditor."""
        original_patterns = TAG_PATTERNS.copy()
        try:
            TAG_PATTERNS.append({
                "tag": "TEST",
                "pattern": r"[invalid(regex",
                "priority": "medium",
            })
            content = "# TODO: Task"
            tags = CodeAuditor._find_comment_tags(content, "test.py", None, None)
            assert len(tags) >= 1
        finally:
            TAG_PATTERNS[:] = original_patterns


class TestExportFormats:
    """Test export functionality."""

    def test_json_export(self):
        """Test JSON export format."""
        data = {
            "target": "/test",
            "scanned_files": 1,
            "summary": {"high": 1},
            "findings": {"comment_tags": []}
        }
        result = CodeAuditor.export_results(data, format="json")
        assert '"target": "/test"' in result

    def test_csv_export(self):
        """Test CSV export format."""
        data = {
            "findings": {
                "comment_tags": [{
                    "file": "test.py",
                    "tag": "TODO",
                    "priority": "high",
                    "line": 1,
                    "message": "Test",
                    "author": "",
                    "last_modified": "",
                    "comment_type": "line",
                    "confidence": 1.0
                }]
            }
        }
        result = CodeAuditor.export_results(data, format="csv")
        assert "file,tag,priority" in result
        assert "test.py" in result

    def test_report_export(self):
        """Test report export format."""
        data = {
            "target": "/test",
            "scanned_files": 1,
            "summary": {"high": 1},
            "findings": {"comment_tags": []}
        }
        result = CodeAuditor.export_results(data, format="report")
        assert "CODE AUDIT REPORT" in result
        assert "/test" in result


class TestIntegration:
    """Integration tests with real files."""

    def test_scan_directory(self):
        """Test scanning a directory with multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            py_file = Path(tmpdir) / "test.py"
            py_file.write_text('''
# TODO: Implement this
def foo():
    # FIXME: Bug here
    pass
''')

            js_file = Path(tmpdir) / "test.js"
            js_file.write_text('''
// TODO: JS task
// NOTE: Important
''')

            result = CodeAuditor.audit({
                "target_path": tmpdir,
                "scan_categories": ["comments"]
            })

            assert result["success"] is True
            assert result["data"]["scanned_files"] == 2

    def test_scan_single_file(self):
        """Test scanning a single file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('''
# TODO: Task 1
# FIXME: Bug 1
# NOTE: Note 1
''')
            fname = f.name

        try:
            result = CodeAuditor.audit({
                "target_path": fname,
                "scan_categories": ["comments"]
            })

            assert result["success"] is True
            assert len(result["data"]["findings"]["comment_tags"]) >= 3
        finally:
            os.unlink(fname)


class TestTagConfiguration:
    """Test tag configuration extensibility."""

    def test_all_tags_have_required_fields(self):
        """Test that all tags have required configuration fields."""
        required_fields = ["tag", "pattern", "priority", "description"]
        for pattern in TAG_PATTERNS:
            for field in required_fields:
                assert field in pattern, f"Missing field {field} in {pattern.get('tag', 'unknown')}"

    def test_all_priorities_valid(self):
        """Test that all priorities are valid."""
        valid_priorities = {"critical", "high", "medium", "low"}
        for pattern in TAG_PATTERNS:
            assert pattern["priority"] in valid_priorities


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
