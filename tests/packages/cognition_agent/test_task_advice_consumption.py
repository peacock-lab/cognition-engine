from __future__ import annotations

import re
from pathlib import Path

import pytest

from cognition_agent import (
    TASK_ADVICE_CONSUMPTION_PAYLOAD_SOURCE,
    TASK_ADVICE_CONSUMPTION_PAYLOAD_VERSION,
    TASK_ADVICE_SOURCE,
    AgentTaskAdviceCandidate,
    build_agent_task_advice_consumption_payload,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
COGNITION_AGENT_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "cognition_agent" / "src" / "cognition_agent"
)

EXPECTED_PAYLOAD_FIELDS = {
    "product",
    "payload_type",
    "payload_version",
    "source",
    "candidate_type",
    "candidate_id",
    "advice_version",
    "task_context_candidate_id",
    "task_candidate_id",
    "agent_shell_audit_candidate_id",
    "agent_shell_evidence_ref",
    "agent_shell_run_ref",
    "agent_shell_status",
    "agent_shell_failure_type",
    "agent_shell_controlled_live",
    "product_gateway_response_view_candidate_id",
    "product_gateway_request_id",
    "product_gateway_entry_kind",
    "product_gateway_status",
    "product_gateway_exit_code",
    "product_gateway_response_ref",
    "product_gateway_governance_summary_ref",
    "product_gateway_evidence_refs",
    "product_gateway_audit_refs",
    "product_gateway_agent_advice_refs",
    "product_gateway_tool_audit_refs",
    "product_gateway_blocking_reasons",
    "product_gateway_warnings",
    "product_gateway_ready_for_review",
    "recommendation",
    "status",
    "display_summary",
    "plan_steps",
    "risk_notes",
    "next_step",
    "blocking_reasons",
    "warnings",
    "governance_refs",
    "config_refs",
    "readonly",
    "candidate_only",
    "execution_enabled",
}

FORBIDDEN_PAYLOAD_FIELDS = {
    "metadata",
    "domain_metadata",
    "prompt",
    "messages",
    "response_text",
    "raw_response",
    "raw_provider_response",
}


@pytest.mark.parametrize(
    ("recommendation", "expected_status"),
    [
        ("defer_until_context_ready", "blocked"),
        ("collect_governed_run_evidence", "needs_evidence"),
        (
            "continue_with_controlled_agent_review",
            "ready_for_controlled_review",
        ),
        ("continue_with_no_live_review", "ready_for_no_live_review"),
        ("review_agent_shell_failure", "needs_agent_shell_review"),
        (
            "continue_with_product_gateway_review",
            "ready_for_product_gateway_review",
        ),
        (
            "continue_with_product_gateway_skipped_review",
            "ready_for_product_gateway_skipped_review",
        ),
        (
            "review_product_gateway_blocking_reasons",
            "needs_product_gateway_review",
        ),
        ("review_product_gateway_failure", "needs_product_gateway_review"),
        ("unknown_recommendation", "blocked"),
    ],
)
def test_builds_task_advice_consumption_payload_statuses(
    recommendation: str,
    expected_status: str,
) -> None:
    advice = _advice(recommendation=recommendation)

    payload = build_agent_task_advice_consumption_payload(advice)

    assert set(payload) == EXPECTED_PAYLOAD_FIELDS
    assert payload["product"] == "cognition_agent"
    assert payload["payload_type"] == "agent_task_advice_consumption_payload"
    assert payload["payload_version"] == TASK_ADVICE_CONSUMPTION_PAYLOAD_VERSION
    assert payload["source"] == TASK_ADVICE_CONSUMPTION_PAYLOAD_SOURCE
    assert payload["candidate_type"] == "agent_task_advice_candidate"
    assert payload["candidate_id"] == "agent-task-advice-1"
    assert payload["task_context_candidate_id"] == "agent-task-context-1"
    assert payload["task_candidate_id"] == "agent-task-1"
    assert payload["agent_shell_audit_candidate_id"] is None
    assert payload["agent_shell_evidence_ref"] is None
    assert payload["agent_shell_run_ref"] is None
    assert payload["agent_shell_status"] is None
    assert payload["agent_shell_failure_type"] is None
    assert payload["agent_shell_controlled_live"] is False
    assert payload["product_gateway_response_view_candidate_id"] is None
    assert payload["product_gateway_request_id"] is None
    assert payload["product_gateway_entry_kind"] is None
    assert payload["product_gateway_status"] is None
    assert payload["product_gateway_exit_code"] is None
    assert payload["product_gateway_response_ref"] is None
    assert payload["product_gateway_governance_summary_ref"] is None
    assert payload["product_gateway_evidence_refs"] == []
    assert payload["product_gateway_audit_refs"] == []
    assert payload["product_gateway_agent_advice_refs"] == []
    assert payload["product_gateway_tool_audit_refs"] == []
    assert payload["product_gateway_blocking_reasons"] == []
    assert payload["product_gateway_warnings"] == []
    assert payload["product_gateway_ready_for_review"] is None
    assert payload["recommendation"] == recommendation
    assert payload["status"] == expected_status
    assert payload["readonly"] is True
    assert payload["candidate_only"] is True
    assert payload["execution_enabled"] is False


def test_task_advice_consumption_payload_keeps_refs_and_lists_json_friendly() -> None:
    advice = _advice(
        recommendation="continue_with_controlled_agent_review",
        plan_steps=["review_sanitized_task_context"],
        risk_notes=["evidence_warnings_present"],
        blocking_reasons=[],
        warnings=["governed_run_warning"],
    )

    payload = build_agent_task_advice_consumption_payload(advice)

    assert payload["plan_steps"] == ["review_sanitized_task_context"]
    assert payload["risk_notes"] == ["evidence_warnings_present"]
    assert payload["blocking_reasons"] == []
    assert payload["warnings"] == ["governed_run_warning"]
    assert payload["governance_refs"] == ["governance:summary"]
    assert payload["config_refs"] == ["config:runtime"]
    assert "read-only" in str(payload["display_summary"])
    assert "does not grant execution permission" in str(payload["display_summary"])


def test_task_advice_consumption_payload_carries_agent_shell_audit_refs() -> None:
    advice = _advice(
        recommendation="review_agent_shell_failure",
        agent_shell_audit_candidate_id="agent-shell-audit-view-1",
        agent_shell_evidence_ref="agent-shell-evidence://agent-shell-run-1",
        agent_shell_run_ref="agent-shell-run://agent-shell-run-1",
        agent_shell_status="failure",
        agent_shell_failure_type="provider_error",
        agent_shell_controlled_live=True,
    )

    payload = build_agent_task_advice_consumption_payload(advice)

    assert payload["status"] == "needs_agent_shell_review"
    assert payload["agent_shell_audit_candidate_id"] == "agent-shell-audit-view-1"
    assert payload["agent_shell_evidence_ref"] == (
        "agent-shell-evidence://agent-shell-run-1"
    )
    assert payload["agent_shell_run_ref"] == "agent-shell-run://agent-shell-run-1"
    assert payload["agent_shell_status"] == "failure"
    assert payload["agent_shell_failure_type"] == "provider_error"
    assert payload["agent_shell_controlled_live"] is True


def test_task_advice_consumption_payload_carries_product_gateway_refs() -> None:
    advice = _advice(
        recommendation="review_product_gateway_blocking_reasons",
        product_gateway_response_view_candidate_id=(
            "agent-product-gateway-response-view-1"
        ),
        product_gateway_request_id="product-gateway-request-1",
        product_gateway_entry_kind="agent_shell",
        product_gateway_status="blocked",
        product_gateway_exit_code=1,
        product_gateway_response_ref=(
            "product-gateway-response://product-gateway-request-1"
        ),
        product_gateway_governance_summary_ref=(
            "governance-summary://product-gateway-request-1"
        ),
        product_gateway_evidence_refs=[
            {"ref": "evidence://product-gateway-evidence-1", "kind": "evidence"}
        ],
        product_gateway_blocking_reasons=["product_gateway_blocked"],
        product_gateway_warnings=["product_gateway_warning"],
        product_gateway_ready_for_review=False,
    )

    payload = build_agent_task_advice_consumption_payload(advice)

    assert payload["status"] == "needs_product_gateway_review"
    assert payload["product_gateway_response_view_candidate_id"] == (
        "agent-product-gateway-response-view-1"
    )
    assert payload["product_gateway_status"] == "blocked"
    assert payload["product_gateway_evidence_refs"] == [
        {"ref": "evidence://product-gateway-evidence-1", "kind": "evidence"}
    ]
    assert payload["product_gateway_blocking_reasons"] == [
        "product_gateway_blocked"
    ]
    assert payload["product_gateway_ready_for_review"] is False


def test_task_advice_consumption_payload_omits_raw_and_candidate_internal_fields() -> None:
    payload = build_agent_task_advice_consumption_payload(
        _advice(recommendation="continue_with_no_live_review")
    )

    assert FORBIDDEN_PAYLOAD_FIELDS.isdisjoint(payload)
    assert "summary" not in payload
    assert "status" in payload


def test_task_advice_consumption_source_has_no_execution_dependencies() -> None:
    source = (
        COGNITION_AGENT_SOURCE_ROOT / "task_advice_consumption.py"
    ).read_text(encoding="utf-8")
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|adk_adapter|litellm|google\.adk|runtime_container|runtime|"
        r"observability_hub|composition|cognition_governance|subprocess)\b",
        re.MULTILINE,
    )
    forbidden_calls = re.compile(
        r"\b(?:completion|acompletion|service\.invoke|runner\.run|run_async)\s*\("
    )

    assert forbidden_imports.search(source) is None
    assert forbidden_calls.search(source) is None
    assert "live_enabled=True" not in source


def _advice(
    *,
    recommendation: str,
    plan_steps: list[str] | None = None,
    risk_notes: list[str] | None = None,
    blocking_reasons: list[str] | None = None,
    warnings: list[str] | None = None,
    agent_shell_audit_candidate_id: str | None = None,
    agent_shell_evidence_ref: str | None = None,
    agent_shell_run_ref: str | None = None,
    agent_shell_status: str | None = None,
    agent_shell_failure_type: str | None = None,
    agent_shell_controlled_live: bool = False,
    product_gateway_response_view_candidate_id: str | None = None,
    product_gateway_request_id: str | None = None,
    product_gateway_entry_kind: str | None = None,
    product_gateway_status: str | None = None,
    product_gateway_exit_code: int | None = None,
    product_gateway_response_ref: str | None = None,
    product_gateway_governance_summary_ref: str | None = None,
    product_gateway_evidence_refs: list[dict[str, object]] | None = None,
    product_gateway_audit_refs: list[dict[str, object]] | None = None,
    product_gateway_agent_advice_refs: list[dict[str, object]] | None = None,
    product_gateway_tool_audit_refs: list[dict[str, object]] | None = None,
    product_gateway_blocking_reasons: list[str] | None = None,
    product_gateway_warnings: list[str] | None = None,
    product_gateway_ready_for_review: bool | None = None,
) -> AgentTaskAdviceCandidate:
    return AgentTaskAdviceCandidate(
        candidate_id="agent-task-advice-1",
        source=TASK_ADVICE_SOURCE,
        summary="Agent task advice candidate for product consumption tests.",
        task_context_candidate_id="agent-task-context-1",
        task_candidate_id="agent-task-1",
        agent_shell_audit_candidate_id=agent_shell_audit_candidate_id,
        agent_shell_evidence_ref=agent_shell_evidence_ref,
        agent_shell_run_ref=agent_shell_run_ref,
        agent_shell_status=agent_shell_status,
        agent_shell_failure_type=agent_shell_failure_type,
        agent_shell_controlled_live=agent_shell_controlled_live,
        product_gateway_response_view_candidate_id=(
            product_gateway_response_view_candidate_id
        ),
        product_gateway_request_id=product_gateway_request_id,
        product_gateway_entry_kind=product_gateway_entry_kind,
        product_gateway_status=product_gateway_status,
        product_gateway_exit_code=product_gateway_exit_code,
        product_gateway_response_ref=product_gateway_response_ref,
        product_gateway_governance_summary_ref=(
            product_gateway_governance_summary_ref
        ),
        product_gateway_evidence_refs=product_gateway_evidence_refs or [],
        product_gateway_audit_refs=product_gateway_audit_refs or [],
        product_gateway_agent_advice_refs=product_gateway_agent_advice_refs or [],
        product_gateway_tool_audit_refs=product_gateway_tool_audit_refs or [],
        product_gateway_blocking_reasons=product_gateway_blocking_reasons or [],
        product_gateway_warnings=product_gateway_warnings or [],
        product_gateway_ready_for_review=product_gateway_ready_for_review,
        recommendation=recommendation,
        plan_steps=plan_steps or ["review_sanitized_task_context"],
        risk_notes=risk_notes or [],
        next_step="Continue with read-only agent review candidate.",
        blocking_reasons=blocking_reasons or [],
        warnings=warnings or [],
        governance_refs=["governance:summary"],
        config_refs=["config:runtime"],
    )
