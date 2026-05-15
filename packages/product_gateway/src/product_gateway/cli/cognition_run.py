"""cognition-run CLI adapter for product gateway."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from product_gateway.cognition_run import run_cognition_run_gateway_request
from product_gateway.cli.presenter import (
    product_gateway_response_to_json_text,
    product_gateway_response_to_text,
)
from product_gateway.contracts import ProductGatewayResponse

EXIT_USAGE_ERROR = 2
DEFAULT_OUTPUT_FORMAT = "text"


def run_cognition_run_cli(argv: Sequence[str] | None = None) -> int:
    """Run the product-gateway cognition-run CLI adapter."""

    parser = build_cognition_run_cli_parser()
    try:
        args = parser.parse_args(argv)
        gateway_input = _gateway_input_from_args(args)
        response = run_cognition_run_gateway_request(gateway_input)
        output_text = _format_response(response, output_format=args.format)
        _write_output(output_text, output_path=args.output)
    except (TypeError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        print(f"product_gateway cognition-run error: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR
    except OSError as exc:
        print(f"product_gateway cognition-run output error: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR
    except SystemExit as exc:
        return _exit_code(exc.code)
    return response.exit_code if response.exit_code is not None else 1


def build_cognition_run_cli_parser() -> argparse.ArgumentParser:
    """Build the parser for the product-gateway cognition-run adapter."""

    parser = argparse.ArgumentParser(
        prog="product-gateway cognition-run",
        description="Normalize cognition-run requests through product_gateway.",
    )
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--runtime-id", required=True)
    parser.add_argument("--workflow-id")
    parser.add_argument("--workflow-name")
    parser.add_argument("--environment", default="local")
    parser.add_argument("--profile")
    parser.add_argument("--input-json")
    parser.add_argument("--operator-approved", action="store_true")
    parser.add_argument("--approval-ref")
    parser.add_argument("--audit-ref")
    parser.add_argument("--sanitized-evidence-ref")
    parser.add_argument("--governance-summary-output-ref")
    parser.add_argument("--request-live-llm", action="store_true")
    parser.add_argument("--request-ollama", action="store_true")
    parser.add_argument("--allow-live-llm", action="store_true")
    parser.add_argument("--allow-ollama", action="store_true")
    parser.add_argument("--live-llm-approval-ref")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default=DEFAULT_OUTPUT_FORMAT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser


def _exit_code(value: object) -> int:
    if isinstance(value, int):
        return value
    return EXIT_USAGE_ERROR


def _gateway_input_from_args(args: argparse.Namespace) -> dict[str, Any]:
    output_format = "json" if args.json else args.format
    args.format = output_format
    payload = _input_payload_from_text(args.input_json)
    gateway_input = {
        "request_id": args.request_id,
        "runtime_id": args.runtime_id,
        "environment": args.environment,
        "profile": args.profile,
        "input_payload": payload,
        "operator_approved": args.operator_approved,
        "approval_ref": args.approval_ref,
        "audit_ref": args.audit_ref,
        "sanitized_evidence_ref": args.sanitized_evidence_ref,
        "governance_summary_output_ref": args.governance_summary_output_ref,
        "request_live_llm": args.request_live_llm,
        "request_ollama": args.request_ollama,
        "allow_live_llm": args.allow_live_llm,
        "allow_ollama": args.allow_ollama,
        "live_llm_approval_ref": args.live_llm_approval_ref,
        "preflight_only": args.preflight_only,
        "metadata": {
            "source": "product_gateway.cli.cognition_run",
            "output_format": output_format,
        },
    }
    if args.workflow_id:
        gateway_input["workflow_id"] = args.workflow_id
    if args.workflow_name:
        gateway_input["workflow_name"] = args.workflow_name
    return gateway_input


def _input_payload_from_text(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise TypeError("--input-json must be a JSON object.")
    return payload


def _format_response(
    response: ProductGatewayResponse,
    *,
    output_format: str,
) -> str:
    if output_format == "json":
        return product_gateway_response_to_json_text(response)
    return product_gateway_response_to_text(response)


def _write_output(output_text: str, *, output_path: Path | None) -> None:
    if output_path:
        output_path.write_text(output_text + "\n", encoding="utf-8")
        return
    print(output_text)


__all__ = [
    "build_cognition_run_cli_parser",
    "run_cognition_run_cli",
]
