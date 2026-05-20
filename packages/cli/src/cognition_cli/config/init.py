"""Config initialization command for the Cognition System CLI."""

from __future__ import annotations

import argparse
import json
import sys

from cognition_cli.constants import EXIT_OK, EXIT_RUNTIME_FAILURE


def config_init_command(args: argparse.Namespace) -> int:
    try:
        from config_assembly.runtime import init_default_config_root

        result = init_default_config_root(
            args.config_root,
            overwrite=args.overwrite,
        )
    except Exception as exc:  # pragma: no cover - defensive packaging boundary.
        print(f"cognition config init error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_FAILURE

    payload = {
        "command": "cognition config init",
        "config_root": result.config_root,
        "source": result.source,
        "files": [file.to_json_dict() for file in result.files],
        "status": "succeeded",
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return EXIT_OK

    lines = [
        "Cognition System config initialized",
        f"config_root: {result.config_root}",
        f"source: {result.source}",
    ]
    lines.extend(f"{file.status}: {file.relative_path}" for file in result.files)
    lines.append("next: cognition chat --config-root " + result.config_root)
    print("\n".join(lines))
    return EXIT_OK
