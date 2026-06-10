import os
import tempfile
import pytest
from src.modules.codetester.test_adapters.flutter_test import FlutterTest as FlutterTestAdapter

def test_flutter_test_adapter_init():
    """Test that the FlutterTestAdapter can be instantiated."""
    adapter = FlutterTestAdapter()
    assert adapter.get_name() == "flutter_test"

def test_flutter_test_adapter_run_with_invalid_path():
    """Test that the FlutterTestAdapter handles invalid paths gracefully."""
    adapter = FlutterTestAdapter()
    result = adapter.run("/nonexistent/path")
    assert result["tool"] == "flutter_test"
    assert result["status"] == "error"
    assert "does not exist" in result["error"]

def test_flutter_test_adapter_run_without_pubspec():
    """Test that the FlutterTestAdapter handles missing pubspec.yaml gracefully."""
    adapter = FlutterTestAdapter()
    # Create a temporary directory without pubspec.yaml
    with tempfile.TemporaryDirectory() as tmpdir:
        result = adapter.run(tmpdir)
        assert result["tool"] == "flutter_test"
        assert result["status"] == "error"
        assert "pubspec.yaml not found" in result["error"]

def test_flutter_test_adapter_run_with_path_traversal():
    """Test that the FlutterTestAdapter prevents path traversal."""
    adapter = FlutterTestAdapter()
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a pubspec.yaml to pass the first check
        pubspec_path = os.path.join(tmpdir, "pubspec.yaml")
        with open(pubspec_path, "w") as f:
            f.write('name: test\n')
        
        # Try to access a parent directory
        result = adapter.run(tmpdir, target_path="../../etc")
        assert result["tool"] == "flutter_test"
        assert result["status"] == "error"
        assert "outside the repository" in result["error"]
