"""Console script entrypoint for the Cognition System CLI."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
import warnings


warnings.filterwarnings(
    "ignore",
    message=r"authlib\.jose module is deprecated.*",
    category=Warning,
)
warnings.filterwarnings(
    "ignore",
    category=Warning,
    module=r"authlib\._joserfc_helpers",
)
warnings.filterwarnings(
    "ignore",
    message=r"\[EXPERIMENTAL\] feature FeatureName\..* is enabled\.",
    category=Warning,
)
warnings.filterwarnings(
    "ignore",
    category=Warning,
    module=r"google\.adk\.features\._feature_decorator",
)
try:
    from authlib.deprecate import AuthlibDeprecationWarning
except ImportError:
    pass
else:
    warnings.simplefilter("ignore", AuthlibDeprecationWarning)


def run_cli(argv: Sequence[str] | None = None, **kwargs: Any) -> int:
    """Run the CLI application after entrypoint-level warning discipline."""

    from cognition_cli.application import run_cli as _run_cli

    return _run_cli(argv, **kwargs)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Cognition System CLI."""

    from cognition_cli.application import main as _main

    return _main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
