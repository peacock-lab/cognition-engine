"""Product console channel package for Cognition System."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

PRODUCT_CONSOLE_PACKAGE = "product_console"
PRODUCT_CONSOLE_STATUS = "candidate"


def build_product_console_home_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from product_console.console import build_product_console_home_payload as _build

    return _build(*args, **kwargs)


def render_product_console_home(*args: Any, **kwargs: Any) -> str:
    from product_console.console import render_product_console_home as _render

    return _render(*args, **kwargs)


def run_product_console(
    argv: Sequence[str] | None = None,
    *,
    output_writer: Callable[[str], None] | None = None,
    **kwargs: Any,
) -> int:
    from product_console.console import run_product_console as _run

    return _run(argv, output_writer=output_writer, **kwargs)


__all__ = (
    "PRODUCT_CONSOLE_PACKAGE",
    "PRODUCT_CONSOLE_STATUS",
    "build_product_console_home_payload",
    "render_product_console_home",
    "run_product_console",
)
