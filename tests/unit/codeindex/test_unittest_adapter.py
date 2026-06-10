import os
import tempfile
import pytest
from src.modules.codetester.test_adapters.unittest import Unittest as UnittestAdapter

def test_unittest_adapter_init():
    """Test that the UnittestAdapter can be instantiated."""
    adapter = UnittestAdapter()
    assert adapter.get_name() == "unittest"

def test_unittest_adapter_run_with_invalid_path():
    """Test that the UnittestAdapter handles invalid paths gracefully."""
    adapter = UnittestAdapter()
    result = adapter.run("/nonexistent/path")
    assert result["tool"] == "unittest"
    assert result["status"] == "error"
    assert "does not exist" in result["error"]

def test_unittest_adapter_run_with_path_traversal():
    """Test that the UnittestAdapter prevents path traversal."""
    adapter = UnittestAdapter()
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Try to access a parent directory
        result = adapter.run(tmpdir, target_path="../../etc")
        assert result["tool"] == "unittest"
        assert result["status"] == "error"
        assert "outside the repository" in result["error"]
