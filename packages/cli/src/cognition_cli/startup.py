"""Startup banner and status helpers for the Cognition System CLI."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cognition_cli.constants import (
    ADAPTER,
    AGENT_FRAMEWORK,
    BACKEND,
    CLI_COMMAND,
    EXIT_OK,
    MODE,
    PRODUCT_DEFINITION,
    PRODUCT_NAME,
)


def print_startup(args: argparse.Namespace) -> int:
    status = startup_status()
    if args.json:
        print(json.dumps(status, ensure_ascii=False, sort_keys=True))
        return EXIT_OK
    if args.no_banner:
        return EXIT_OK
    print(startup_text(status))
    return EXIT_OK


def startup_status() -> dict[str, Any]:
    return {
        "product": PRODUCT_NAME,
        "definition": PRODUCT_DEFINITION,
        "cli": CLI_COMMAND,
        "backend": BACKEND,
        "agent_framework": AGENT_FRAMEWORK,
        "adapter": ADAPTER,
        "mode": MODE,
        "governance": "enabled",
        "evidence": "enabled",
        "workspace": str(Path.cwd()),
        "session": "not-created",
        "available_commands": [
            "cognition",
            "cognition run",
            "cognition chat",
            "cognition external-readonly fetch",
            "cognition config init",
        ],
    }


def startup_text(status: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            str(status["product"]),
            PRODUCT_DEFINITION,
            "",
            f"CLI: {status['cli']}",
            f"Backend: {status['backend']}",
            f"Agent Framework: {status['agent_framework']}",
            f"Adapter: {status['adapter']}",
            f"Mode: {status['mode']}",
            f"Governance: {status['governance']}",
            f"Evidence: {status['evidence']}",
            f"Workspace: {status['workspace']}",
            f"Session: {status['session']}",
            "",
            "Available commands:",
            "  cognition",
            "  cognition run",
            "  cognition chat",
            "  cognition external-readonly fetch",
            "  cognition config init",
        ]
    )
