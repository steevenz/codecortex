#!/usr/bin/env python3
# src/services/__init__.py
#
# This file is part of the PyScaffold package.
#
# For the full copyright and license information, please view the LICENSE
# file that was distributed with this source code.
#
# @author         Steeve Andrian Salim
# @copyright      Copyright (c) Steeve Andrian Salim
#
"""
src/services/__init__.py
UI services for PyScaffold.

:project: CodeCortex
:package: Modules.Scaffolder.Services
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Scaffolder-v1.0
"""

from .cli import run_cli

__all__ = [
    "run_cli"
]
