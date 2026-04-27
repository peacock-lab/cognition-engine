"""Shared path helpers for the formal CLI shell."""

from __future__ import annotations

import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python3"


def resolve_python_executable() -> Path:
    """Prefer the project virtualenv interpreter when available."""
    if VENV_PYTHON.exists():
        return VENV_PYTHON
    return Path(sys.executable).resolve()

