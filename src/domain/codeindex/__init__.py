"""
/**
 * @project   CodeCortex
 * @package   Domain/CodeIndex
 * @author    Steeven Andrian
 * @copyright (c) 2026 Aegis Codework
 * @standard  Aegis-CrossStack-v1.0
 * @stack     Python
 * * Domain CodeIndex – Entrypoint for modularised symbol indexing.
 */
"""

from .application.service import CodeIndexService

__all__ = ["CodeIndexService"]
