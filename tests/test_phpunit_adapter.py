import os
import tempfile
import pytest
from src.domain.codetester.infrastructure.adapters.phpunit_adapter import PHPUnitAdapter

def test_phpunit_adapter_init():
    """Test that the PHPUnitAdapter can be instantiated."""
    adapter = PHPUnitAdapter()
    assert adapter.get_name() == "phpunit"

def test_phpunit_adapter_run_with_invalid_path():
    """Test that the PHPUnitAdapter handles invalid paths gracefully."""
    adapter = PHPUnitAdapter()
    result = adapter.run("/nonexistent/path")
    assert result["tool"] == "phpunit"
    assert result["status"] == "error"
    assert "does not exist" in result["error"]

def test_phpunit_adapter_run_without_phpunit_xml():
    """Test that the PHPUnitAdapter handles missing phpunit.xml gracefully."""
    adapter = PHPUnitAdapter()
    # Create a temporary directory without phpunit.xml
    with tempfile.TemporaryDirectory() as tmpdir:
        result = adapter.run(tmpdir)
        assert result["tool"] == "phpunit"
        assert result["status"] == "error"
        assert "phpunit.xml or phpunit.xml.dist not found" in result["error"]

def test_phpunit_adapter_run_with_path_traversal():
    """Test that the PHPUnitAdapter prevents path traversal."""
    adapter = PHPUnitAdapter()
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a phpunit.xml to pass the first check
        phpunit_xml_path = os.path.join(tmpdir, "phpunit.xml")
        with open(phpunit_xml_path, "w") as f:
            f.write('<phpunit></phpunit>')
        
        # Try to access a parent directory
        result = adapter.run(tmpdir, target_path="../../etc")
        assert result["tool"] == "phpunit"
        assert result["status"] == "error"
        assert "outside the repository" in result["error"]