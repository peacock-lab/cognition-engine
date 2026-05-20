"""Default chat profile helpers for the Cognition System CLI."""

from __future__ import annotations

import argparse


DEFAULT_LOCAL_LIVE_APPROVAL_REF = "approval://cognition/local-live"
DEFAULT_LOCAL_LIVE_AUDIT_REF = "audit://cognition/local-live"
DEFAULT_LOCAL_LIVE_EVIDENCE_REF = "evidence://cognition/local-live"
DEFAULT_LOCAL_LIVE_ARTIFACT_REF = "artifact://cognition/local-live"
DEFAULT_LOCAL_LIVE_LLM_APPROVAL_REF = "approval://cognition/local-live-llm"
DEFAULT_LOCAL_LIVE_OLLAMA_API_BASE = "http://127.0.0.1:11434"
DEFAULT_LOCAL_LIVE_TIMEOUT_SECONDS = 180


def apply_default_local_live_chat_profile(args: argparse.Namespace) -> None:
    """Apply the one-word `cognition` default chat controls."""

    args.operator_approved = True
    args.approval_ref = args.approval_ref or DEFAULT_LOCAL_LIVE_APPROVAL_REF
    args.audit_ref = args.audit_ref or DEFAULT_LOCAL_LIVE_AUDIT_REF
    args.sanitized_evidence_ref = (
        args.sanitized_evidence_ref or DEFAULT_LOCAL_LIVE_EVIDENCE_REF
    )
    args.governance_summary_output_ref = (
        args.governance_summary_output_ref or DEFAULT_LOCAL_LIVE_ARTIFACT_REF
    )
    args.request_live_llm = True
    args.request_ollama = True
    args.allow_live_llm = True
    args.allow_ollama = True
    args.live_llm_approval_ref = (
        args.live_llm_approval_ref or DEFAULT_LOCAL_LIVE_LLM_APPROVAL_REF
    )
    args.ollama_api_base = args.ollama_api_base or DEFAULT_LOCAL_LIVE_OLLAMA_API_BASE
    args.live_llm_timeout_seconds = (
        args.live_llm_timeout_seconds or DEFAULT_LOCAL_LIVE_TIMEOUT_SECONDS
    )
    args._cognition_default_profile = "local-live"
