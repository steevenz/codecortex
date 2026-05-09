import os
import tempfile
import pytest
from src.domain.codetester.infrastructure.adapters.go_test_adapter import GoTestAdapter

def test_go_test_adapter_init():
    """Test that the GoTestAdapter can be instantiated."""
    adapter = GoTestAdapter()
    assert adapter.get_name() == "go_test"

def test_go_test_adapter_run_with_invalid_path():
    """Test that the GoTestAdapter handles invalid paths gracefully."""
    adapter = GoTestAdapter()
    result = adapter.run("/nonexistent/path")
    assert result["tool"] == "go_test"
    assert result["status"] == "error"
    assert "does not exist" in result["error"]

def test_go_test_adapter_run_without_go_mod():
    """Test that the GoTestAdapter handles missing go.mod gracefully."""
    adapter = GoTestAdapter()
    # Create a temporary directory without go.mod
    with tempfile.TemporaryDirectory() as tmpdir:
        result = adapter.run(tmpdir)
        assert result["tool"] == "go_test"
        assert result["status"] == "error"
        assert "go.mod not found" in result["error"]

def test_go_test_adapter_run_with_path_traversal():
    """Test that the GoTestAdapter prevents path traversal."""
    adapter = GoTestAdapter()
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a go.mod to pass the first check
        go_mod_path = os.path.join(tmpdir, "go.mod")
        with open(go_mod_path, "w") as f:
            f.write('module test\n')
        
        # Try to access a parent directory
        result = adapter.run(tmpdir, target_path="../../etc")
        assert result["tool"] == "go_test"
        assert result["status"] == "error"
        assert "outside the repository" in result["error"]