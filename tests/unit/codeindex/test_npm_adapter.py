import os
import tempfile
import pytest
from src.modules.codetester.test_adapters.npm import Npm as NpmAdapter

def test_npm_adapter_init():
    """Test that the NpmAdapter can be instantiated."""
    adapter = NpmAdapter()
    assert adapter.get_name() == "npm"

def test_npm_adapter_run_with_invalid_path():
    """Test that the NpmAdapter handles invalid paths gracefully."""
    adapter = NpmAdapter()
    result = adapter.run("/nonexistent/path")
    assert result["tool"] == "npm"
    assert result["status"] == "error"
    assert "does not exist" in result["error"]

def test_npm_adapter_run_without_package_json():
    """Test that the NpmAdapter handles missing package.json gracefully."""
    adapter = NpmAdapter()
    # Create a temporary directory without package.json
    with tempfile.TemporaryDirectory() as tmpdir:
        result = adapter.run(tmpdir)
        assert result["tool"] == "npm"
        assert result["status"] == "error"
        assert "package.json not found" in result["error"]

def test_npm_adapter_run_with_path_traversal():
    """Test that the NpmAdapter prevents path traversal."""
    adapter = NpmAdapter()
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a package.json to pass the first check
        package_json_path = os.path.join(tmpdir, "package.json")
        with open(package_json_path, "w") as f:
            f.write('{}')
        
        # Try to access a parent directory
        result = adapter.run(tmpdir, target_path="../../etc")
        assert result["tool"] == "npm"
        assert result["status"] == "error"
        assert "outside the repository" in result["error"]
