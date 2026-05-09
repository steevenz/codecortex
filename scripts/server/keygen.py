#!/usr/bin/env python3
"""
CodeCortex Bootstrap API Key Generator

Generates a secure bootstrap API key and optionally installs it into .env.

Author: Steeven Andrian Salim — Senior Principal Architect

Usage:
    python scripts/server/keygen.py                  # Generate and display
    python scripts/server/keygen.py --install        # Generate and install to .env
    python scripts/server/keygen.py --install --force # Overwrite existing key
"""
from __future__ import annotations

import argparse
import os
import secrets
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
KEY_NAME = "CODECORTEX_BOOTSTRAP_API_KEY"


def generate_key() -> str:
    return f"codecortex_bootstrap_{secrets.token_urlsafe(32)}"


def install_to_env(value: str, *, force: bool = False) -> tuple[bool, str]:
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    found_index = -1
    for i, raw in enumerate(lines):
        if raw.strip().startswith(f"{KEY_NAME}="):
            found_index = i
            break

    if found_index >= 0 and not force:
        return False, "existing_key_detected"

    assignment = f"{KEY_NAME}={value}"
    if found_index >= 0:
        lines[found_index] = assignment
    else:
        lines.append(assignment)

    ENV_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return True, "installed"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate bootstrap API key for CodeCortex shared server auth.")
    parser.add_argument("--install", action="store_true", help="Install generated key into .env")
    parser.add_argument("--force", action="store_true", help="Overwrite existing key in .env when used with --install")
    args = parser.parse_args()

    key = generate_key()
    print("\n=== CODECORTEX API KEY GENERATOR ===")
    print(f"Generated {KEY_NAME}:\n{key}\n")

    if args.install:
        ok, status = install_to_env(key, force=args.force)
        if ok:
            print(f"Installed to: {ENV_PATH}")
        elif status == "existing_key_detected":
            print(f"Skipped install: existing {KEY_NAME} found in {ENV_PATH}. Use --force to overwrite.")
        else:
            print("Install failed.")

    print("Next step:")
    print(f"- Set the same value in MCP server environment variable: {KEY_NAME}")
    print("- Keep this key secret; rotate periodically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
