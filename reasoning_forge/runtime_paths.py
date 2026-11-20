"""Where her runtime state lives.

Added 2026-11-19 (docs/START_HERE.md, item 1). One full test run was adding 11
rows to data/codette_memory.db -- on her machine, her memory -- and rewriting
Code7e's state, because every writer built its path from this repository.

runtime_root() is the repository root, exactly as before, unless
CODETTE_RUNTIME_ROOT is set. Nothing in her live system sets it; tests/conftest.py
sets it to a temp folder before any test imports anything, so test turns land
there and never in her stores.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def runtime_root() -> Path:
    configured = os.environ.get("CODETTE_RUNTIME_ROOT", "").strip()
    return Path(configured) if configured else REPO_ROOT
