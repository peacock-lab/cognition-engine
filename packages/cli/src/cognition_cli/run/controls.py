"""Run command defaults and preflight controls for the Cognition System CLI."""

from __future__ import annotations

import argparse
import uuid

from cognition_cli.constants import DEFAULT_WORKFLOW_ID, DEFAULT_WORKFLOW_NAME


def _apply_run_defaults(args: argparse.Namespace) -> None:
    if not args.runtime_id:
        args.runtime_id = f"runtime-cli-{uuid.uuid4().hex[:8]}"
    if not args.workflow_name:
        args.workflow_name = DEFAULT_WORKFLOW_NAME
    if not args.workflow_id:
        args.workflow_id = DEFAULT_WORKFLOW_ID
    args.invocation_id = f"inv-{args.runtime_id}"
    if args.json:
        args.format = "json"


def _cli_blocking_reasons(args: argparse.Namespace) -> list[str]:
    reasons: list[str] = []
    if args.operator_approved is not True:
        reasons.append("operator_approval_not_true")
    if not args.approval_ref:
        reasons.append("operator_approval_ref_missing")
    if not args.audit_ref:
        reasons.append("audit_ref_missing")
    if not args.sanitized_evidence_ref:
        reasons.append("sanitized_evidence_ref_missing")
    if not args.governance_summary_output_ref:
        reasons.append("governance_summary_output_ref_missing")
    reasons.extend(_controlled_live_blocking_reasons(args))
    return reasons


def _controlled_live_blocking_reasons(args: argparse.Namespace) -> list[str]:
    if not _controlled_live_args_present(args):
        return []

    reasons: list[str] = []
    if args.request_live_llm is not True:
        reasons.append("controlled_live_request_live_llm_missing")
    if args.request_ollama is not True:
        reasons.append("controlled_live_request_ollama_missing")
    if args.allow_live_llm is not True:
        reasons.append("controlled_live_allow_live_llm_missing")
    if args.allow_ollama is not True:
        reasons.append("controlled_live_allow_ollama_missing")
    if not args.live_llm_approval_ref:
        reasons.append("controlled_live_llm_approval_ref_missing")
    if (
        args.live_llm_timeout_seconds is not None
        and args.live_llm_timeout_seconds <= 0
    ):
        reasons.append("controlled_live_timeout_seconds_not_positive")
    return reasons


def _controlled_live_args_present(args: argparse.Namespace) -> bool:
    return any(
        (
            args.request_live_llm,
            args.request_ollama,
            args.allow_live_llm,
            args.allow_ollama,
            bool(args.live_llm_approval_ref),
            bool(args.ollama_api_base),
            args.live_llm_timeout_seconds is not None,
        )
    )
