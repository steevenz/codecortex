import os
import tempfile
import pytest
from src.modules.codetester.test_adapters.stylelint import Stylelint as StylelintAdapter

def test_stylelint_adapter_init():
    """Test that the StylelintAdapter can be instantiated."""
    adapter = StylelintAdapter()
    assert adapter.get_name() == "stylelint"

def test_stylelint_adapter_run_with_invalid_path():
    """Test that the StylelintAdapter handles invalid paths gracefully."""
    adapter = StylelintAdapter()
    result = adapter.run("/nonexistent/path")
    assert result["tool"] == "stylelint"
    assert result["status"] == "error"
    assert "does not exist" in result["error"]

def test_stylelint_adapter_run_without_config():
    """Test that the StylelintAdapter handles missing config gracefully."""
    adapter = StylelintAdapter()
    # Create a temporary directory without stylelint config
    with tempfile.TemporaryDirectory() as tmpdir:
        result = adapter.run(tmpdir)
        assert result["tool"] == "stylelint"
        assert result["status"] == "error"
        assert "Stylelint not found" in result["error"]

def test_stylelint_adapter_run_with_path_traversal():
    """Test that the StylelintAdapter prevents path traversal."""
    adapter = StylelintAdapter()
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a stylelint config to pass the first check
        stylelint_config_path = os.path.join(tmpdir, ".stylelintrc")
        with open(stylelint_config_path, "w") as f:
            f.write('{}')
        
        # Try to access a parent directory
        result = adapter.run(tmpdir, target_path="../../etc")
        assert result["tool"] == "stylelint"
        assert result["status"] == "error"
        assert "outside the repository" in result["error"]
