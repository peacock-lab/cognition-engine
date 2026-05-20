"""External-readonly refs CLI channel."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from cognition_cli.constants import (
    EXIT_BLOCKING,
    EXIT_OUTPUT_BOUNDARY_FAILURE,
    EXIT_RUNTIME_FAILURE,
    EXIT_OK,
    PRODUCT_NAME,
)
from contract_core.external_readonly_archive import (
    external_readonly_fetch_output_boundary_violated,
)
from contract_core.external_readonly_evidence import (
    build_external_readonly_evidence_read_context,
    validate_external_readonly_evidence_path,
)


EXTERNAL_READONLY_REFS_COMMAND = "cognition external-readonly refs"
EXTERNAL_READONLY_REFS_SOURCE = "cognition_cli.external_readonly.refs"
EXTERNAL_READONLY_REFS_REQUEST_ID = "external-readonly-refs-request://cli/refs"
EXTERNAL_READONLY_REFS_FAILURE = "external_readonly_refs_cli_failure"

ExternalReadonlyRefsApplicationExecutor = Callable[..., Any]


def external_readonly_refs_command(
    args: argparse.Namespace,
    *,
    executor: ExternalReadonlyRefsApplicationExecutor | None = None,
) -> int:
    """Run refs-only product application assembly for archived evidence."""

    try:
        exit_code, output = build_external_readonly_refs_cli_output(
            tuple(getattr(args, "evidence_paths", ()) or ()),
            request_id=args.request_id,
            executor=executor,
        )
    except Exception as exc:  # pragma: no cover - defensive product boundary.
        print(f"{EXTERNAL_READONLY_REFS_COMMAND} error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_FAILURE
    return _emit_external_readonly_refs_output(args, output, exit_code=exit_code)


def build_external_readonly_refs_cli_output(
    evidence_paths: Sequence[str],
    *,
    request_id: str = EXTERNAL_READONLY_REFS_REQUEST_ID,
    executor: ExternalReadonlyRefsApplicationExecutor | None = None,
    repo_root: Path | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Build refs-only CLI output without printing it."""

    evidence_path_items = tuple(evidence_paths or ())
    root = Path.cwd() if repo_root is None else repo_root
    preflight_output = _preflight_output(
        request_id=request_id,
        evidence_paths=evidence_path_items,
        repo_root=root,
    )
    if preflight_output is not None:
        return EXIT_BLOCKING, preflight_output

    read_context = build_external_readonly_evidence_read_context(
        evidence_path_items,
        repo_root=root,
    )
    result = (executor or _execute_external_readonly_refs_application)(
        read_context,
        request_id=request_id,
        metadata={
            "source": EXTERNAL_READONLY_REFS_SOURCE,
            "cli_command": EXTERNAL_READONLY_REFS_COMMAND,
            "evidence_path_count": len(evidence_path_items),
            **dict(metadata or {}),
        },
    )
    output = _output_from_application_result(
        request_id,
        result,
        evidence_paths=evidence_path_items,
    )
    exit_code = _exit_code_from_output(output)
    output["exit_code"] = exit_code
    return exit_code, output


def _execute_external_readonly_refs_application(
    read_context: Any,
    *,
    request_id: str,
    metadata: Mapping[str, Any] | None = None,
) -> Any:
    from product_application_assembly import (
        assemble_external_readonly_refs_product_application,
    )

    return assemble_external_readonly_refs_product_application(
        read_context,
        request_id=request_id,
        metadata=metadata,
    )


def _preflight_output(
    *,
    request_id: str,
    evidence_paths: tuple[str, ...],
    repo_root: Path,
) -> dict[str, Any] | None:
    if not evidence_paths:
        return _blocked_output(
            request_id,
            evidence_paths=evidence_paths,
            blocking_reasons=("evidence_output_path_required",),
        )

    blocking_reasons: list[str] = []
    for evidence_path in evidence_paths:
        issue = validate_external_readonly_evidence_path(
            evidence_path=evidence_path,
            repo_root=repo_root,
        )
        if issue:
            blocking_reasons.append(f"{evidence_path}:{issue}")
    if blocking_reasons:
        return _blocked_output(
            request_id,
            evidence_paths=evidence_paths,
            blocking_reasons=tuple(blocking_reasons),
        )
    return None


def _blocked_output(
    request_id: str,
    *,
    evidence_paths: tuple[str, ...],
    blocking_reasons: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "product": PRODUCT_NAME,
        "command": EXTERNAL_READONLY_REFS_COMMAND,
        "status": "blocked",
        "success": False,
        "failure_type": EXTERNAL_READONLY_REFS_FAILURE,
        "request_id": request_id,
        "evidence_path_count": len(evidence_paths),
        "evidence_ref_count": 0,
        "additional_ref_count": 0,
        "readonly_refs_status": "blocked",
        "blocking_reasons": list(blocking_reasons),
        "warnings": [],
        "product_response_summary": None,
        "raw_response_included": False,
        "raw_html_included": False,
        "response_headers_included": False,
        "uploads_content": False,
        "writes_files": False,
        "external_network_call_performed": False,
        "exit_code": EXIT_BLOCKING,
    }


def _output_from_application_result(
    request_id: str,
    result: Any,
    *,
    evidence_paths: tuple[str, ...],
) -> dict[str, Any]:
    product_response_summary = dict(result.product_response_summary)
    readonly_public_refs_status = dict(result.readonly_public_refs_status)
    facts = _readonly_facts(readonly_public_refs_status)
    evidence_refs = _list_value(product_response_summary.get("evidence_refs"))
    additional_refs = _list_value(product_response_summary.get("additional_refs"))
    status = str(product_response_summary.get("status") or "failed")
    return {
        "product": PRODUCT_NAME,
        "command": EXTERNAL_READONLY_REFS_COMMAND,
        "status": status,
        "success": status == "success",
        "failure_type": None if status == "success" else EXTERNAL_READONLY_REFS_FAILURE,
        "request_id": request_id,
        "evidence_path_count": len(evidence_paths),
        "evidence_ref_count": len(evidence_refs),
        "additional_ref_count": len(additional_refs),
        "readonly_refs_status": str(facts.get("status") or status),
        "blocking_reasons": list(product_response_summary.get("blocking_reasons") or ()),
        "warnings": list(product_response_summary.get("warnings") or ()),
        "product_response_summary": product_response_summary,
        "raw_response_included": False,
        "raw_html_included": False,
        "response_headers_included": False,
        "uploads_content": False,
        "writes_files": False,
        "external_network_call_performed": False,
    }


def _emit_external_readonly_refs_output(
    args: argparse.Namespace,
    output: Mapping[str, Any],
    *,
    exit_code: int,
) -> int:
    if external_readonly_fetch_output_boundary_violated(output):
        print(
            f"{EXTERNAL_READONLY_REFS_COMMAND} output boundary violation",
            file=sys.stderr,
        )
        return EXIT_OUTPUT_BOUNDARY_FAILURE

    if args.format == "json" or args.json:
        print(json.dumps(dict(output), ensure_ascii=False, sort_keys=True))
    else:
        print(_text_output(output))
    return exit_code


def _text_output(output: Mapping[str, Any]) -> str:
    lines = [
        str(output["product"]),
        f"command: {output['command']}",
        f"status: {output['status']}",
        f"request_id: {output['request_id']}",
        f"evidence_path_count: {output['evidence_path_count']}",
        f"evidence_ref_count: {output['evidence_ref_count']}",
        f"additional_ref_count: {output['additional_ref_count']}",
        f"readonly_refs_status: {output['readonly_refs_status']}",
    ]
    blocking = output.get("blocking_reasons") or []
    warnings = output.get("warnings") or []
    if blocking:
        lines.append("blocking_reasons: " + ", ".join(map(str, blocking)))
    if warnings:
        lines.append("warnings: " + ", ".join(map(str, warnings)))
    return "\n".join(lines)


def _exit_code_from_output(output: Mapping[str, Any]) -> int:
    status = output.get("status")
    if status == "success" or status == "skipped":
        return EXIT_OK
    if status == "blocked":
        return EXIT_BLOCKING
    return EXIT_RUNTIME_FAILURE


def _readonly_facts(status: Mapping[str, Any]) -> Mapping[str, Any]:
    facts = status.get("external_readonly_evidence_readonly_facts")
    return facts if isinstance(facts, Mapping) else {}


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


__all__ = [
    "EXTERNAL_READONLY_REFS_COMMAND",
    "EXTERNAL_READONLY_REFS_REQUEST_ID",
    "ExternalReadonlyRefsApplicationExecutor",
    "build_external_readonly_refs_cli_output",
    "external_readonly_refs_command",
]
