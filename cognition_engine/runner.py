"""Command execution helpers for the formal CLI shell."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Iterable, Optional, Sequence

from cognition_engine.paths import PROJECT_ROOT, resolve_python_executable


def format_command(command: Sequence[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run_subprocess(
    command: Sequence[str],
    description: str,
    *,
    cwd: Optional[Path] = None,
) -> int:
    print(f"▶ {description}...")
    result = subprocess.run(
        list(command),
        cwd=str(cwd or PROJECT_ROOT),
        text=True,
    )
    if result.returncode == 0:
        print("  ✓ 完成")
    else:
        print(f"  ✗ 失败 (退出码: {result.returncode})")
    return result.returncode


def run_python_module(
    module: str,
    args: Iterable[str],
    description: str,
) -> int:
    python_executable = resolve_python_executable()
    command = [str(python_executable), "-m", module, *list(args)]
    return run_subprocess(command, description)


def run_python_code(code: str, description: str) -> int:
    python_executable = resolve_python_executable()
    command = [str(python_executable), "-c", code]
    return run_subprocess(command, description)


def command_output(
    command: Sequence[str],
    *,
    cwd: Optional[Path] = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(cwd or PROJECT_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )


def exit_with_status(status: int) -> None:
    raise SystemExit(status)


def current_python_command() -> str:
    return shlex.quote(str(resolve_python_executable()))
