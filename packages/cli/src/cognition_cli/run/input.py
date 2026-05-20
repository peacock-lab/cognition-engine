"""Run command input loading for the Cognition System CLI."""

from __future__ import annotations

import argparse
import json
from typing import Any


def _load_input_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_file is not None:
        payload = json.loads(args.input_file.read_text(encoding="utf-8"))
    elif args.input_json is not None:
        payload = json.loads(args.input_json)
    elif args.input_text is not None:
        input_text = args.input_text.strip()
        if not input_text:
            raise ValueError("--input-text must not be blank")
        payload = {"input_summary": input_text}
    else:
        payload = {}
    if not isinstance(payload, dict):
        raise TypeError("input payload must be a JSON object")
    return payload
