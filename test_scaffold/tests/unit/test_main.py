"""
@project   Myawesomeproject
@package   tests.unit
@author    Steeven Andrian
@copyright (c) Steeven Andrian
@fileoverview Unit tests for the main entry point.
"""

import pytest

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the health check endpoint returns 200."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Myawesomeproject" in data["message"]
