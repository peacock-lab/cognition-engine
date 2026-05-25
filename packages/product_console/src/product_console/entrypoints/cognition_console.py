"""Installed product console entrypoint."""

from __future__ import annotations

from collections.abc import Sequence
import warnings


def main(argv: Sequence[str] | None = None) -> int:
    showwarning = warnings.showwarning
    warnings.showwarning = _suppress_import_warning
    try:
        from product_console.console import run_product_console
    finally:
        warnings.showwarning = showwarning

    return run_product_console(argv)


def _suppress_import_warning(*args: object, **kwargs: object) -> None:
    return None


__all__ = ("main",)
