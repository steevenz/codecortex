"""
Tests for framework detection.
"""
import sys
import tempfile
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.modules.codeindex.services.framework_detection import (
    detect_frameworks,
    detect_from_source,
)


def test_detect_fastapi_from_source():
    content = """
from fastapi import FastAPI
from fastapi.routing import APIRouter
app = FastAPI()
"""
    detected = detect_from_source(content, "main.py")
    assert "fastapi" in detected


def test_detect_django_from_source():
    content = "from django.urls import path\nfrom django.contrib import admin"
    detected = detect_from_source(content, "urls.py")
    assert "django" in detected


def test_detect_express_from_source():
    content = "const express = require('express')"
    detected = detect_from_source(content, "app.js")
    assert "express" in detected


def test_detect_frameworks_from_manifest():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        pkg = root / "package.json"
        pkg.write_text('{"dependencies": {"next": "14.0.0", "express": "4.18.0"}}')
        frameworks = detect_frameworks(root)
        assert "nextjs" in frameworks
        assert "express" in frameworks


def test_detect_nestjs():
    content = "import { Module } from '@nestjs/core';"
    detected = detect_from_source(content, "app.module.ts")
    assert "nestjs" in detected


if __name__ == "__main__":
    test_detect_fastapi_from_source()
    test_detect_django_from_source()
    test_detect_express_from_source()
    test_detect_frameworks_from_manifest()
    test_detect_nestjs()
    print("All framework detection tests passed.")
