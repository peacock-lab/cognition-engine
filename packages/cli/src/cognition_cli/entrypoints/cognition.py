"""Public cognition CLI entrypoint.

The public ``cognition`` console script is owned by this package. Runtime
execution remains delegated to runtime_container.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

EXIT_RUNTIME_ENTRYPOINT_UNAVAILABLE = 4


def main(argv: Sequence[str] | None = None) -> int:
    """Delegate runtime execution to runtime_container."""

    try:
        from runtime_container.entrypoints.cognition import main as runtime_main
    except ModuleNotFoundError as exc:
        if exc.name == "runtime_container":
            print(
                "cognition_cli requires runtime_container.",
                file=sys.stderr,
            )
            return EXIT_RUNTIME_ENTRYPOINT_UNAVAILABLE
        raise

    return int(runtime_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
