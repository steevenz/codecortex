#!/usr/bin/env python3
"""
CodeCortex CLI — Universal Code Intelligence Engine.

Orchestrator that imports and wires together module-level CLIs.

Usage:
    codecortex repository|repo <action> [args]
    codecortex filesystem|fs   <action> [args]
    codecortex codebase|cb     <action> [args]
    codecortex scaffolder|sc   <action> [args]
    codecortex idegraph|ig     <action> [args]
    codecortex knowledge|kg    <action> [args]
    codecortex server          <action>
    codecortex cloud           <action>
    codecortex cct             <action>
    codecortex ai              <query>
    codecortex remote          <action>
    codecortex version
    codecortex help
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
