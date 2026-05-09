import os
import tempfile
import pytest
from src.domain.codetester.infrastructure.adapters.jest_adapter import JestAdapter

def test_jest_adapter_init():
    """Test that the JestAdapter can be instantiated."""
    adapter = JestAdapter()
    assert adapter.get_name() == "jest"

def test_jest_adapter_run_with_invalid_path():
    """Test that the JestAdapter handles invalid paths gracefully."""
    adapter = JestAdapter()
    result = adapter.run("/nonexistent/path")
    assert result["tool"] == "jest"
    assert result["status"] == "error"
    assert "does not exist" in result["error"]

def test_jest_adapter_run_without_package_json():
    """Test that the JestAdapter handles missing package.json gracefully."""
    adapter = JestAdapter()
    # Create a temporary directory without package.json
    with tempfile.TemporaryDirectory() as tmpdir:
        result = adapter.run(tmpdir)
        assert result["tool"] == "jest"
        assert result["status"] == "error"
        assert "package.json not found" in result["error"]

def test_jest_adapter_run_with_path_traversal():
    """Test that the JestAdapter prevents path traversal."""
    adapter = JestAdapter()
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a package.json to pass the first check
        package_json_path = os.path.join(tmpdir, "package.json")
        with open(package_json_path, "w") as f:
            f.write('{}')
        
        # Try to access a parent directory
        result = adapter.run(tmpdir, target_path="../../etc")
        assert result["tool"] == "jest"
        assert result["status"] == "error"
        assert "outside the repository" in result["error"]