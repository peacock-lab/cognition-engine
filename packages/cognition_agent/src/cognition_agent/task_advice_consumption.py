"""Narrow product-consumption payloads for agent task advice."""

from __future__ import annotations

from typing import Any

from cognition_agent.task_context import AgentTaskAdviceCandidate


TASK_ADVICE_CONSUMPTION_PAYLOAD_VERSION = (
    "agent_task_advice_consumption_payload_v1"
)
TASK_ADVICE_CONSUMPTION_PAYLOAD_SOURCE = "cognition_agent.task_advice_consumption"

_PRODUCT = "cognition_agent"
_PAYLOAD_TYPE = "agent_task_advice_consumption_payload"


def build_agent_task_advice_consumption_payload(
    advice: AgentTaskAdviceCandidate,
) -> dict[str, Any]:
    """Project an advice candidate into a stable read-only product payload."""

    status = _status(advice.recommendation)
    return {
        "product": _PRODUCT,
        "payload_type": _PAYLOAD_TYPE,
        "payload_version": TASK_ADVICE_CONSUMPTION_PAYLOAD_VERSION,
        "source": TASK_ADVICE_CONSUMPTION_PAYLOAD_SOURCE,
        "candidate_type": advice.candidate_type,
        "candidate_id": advice.candidate_id,
        "advice_version": advice.advice_version,
        "task_context_candidate_id": advice.task_context_candidate_id,
        "task_candidate_id": advice.task_candidate_id,
        "agent_shell_audit_candidate_id": advice.agent_shell_audit_candidate_id,
        "agent_shell_evidence_ref": advice.agent_shell_evidence_ref,
        "agent_shell_run_ref": advice.agent_shell_run_ref,
        "agent_shell_status": advice.agent_shell_status,
        "agent_shell_failure_type": advice.agent_shell_failure_type,
        "agent_shell_controlled_live": advice.agent_shell_controlled_live,
        "product_gateway_response_view_candidate_id": (
            advice.product_gateway_response_view_candidate_id
        ),
        "product_gateway_request_id": advice.product_gateway_request_id,
        "product_gateway_entry_kind": advice.product_gateway_entry_kind,
        "product_gateway_status": advice.product_gateway_status,
        "product_gateway_exit_code": advice.product_gateway_exit_code,
        "product_gateway_response_ref": advice.product_gateway_response_ref,
        "product_gateway_governance_summary_ref": (
            advice.product_gateway_governance_summary_ref
        ),
        "product_gateway_evidence_refs": list(advice.product_gateway_evidence_refs),
        "product_gateway_audit_refs": list(advice.product_gateway_audit_refs),
        "product_gateway_agent_advice_refs": list(
            advice.product_gateway_agent_advice_refs
        ),
        "product_gateway_tool_audit_refs": list(
            advice.product_gateway_tool_audit_refs
        ),
        "product_gateway_blocking_reasons": list(
            advice.product_gateway_blocking_reasons
        ),
        "product_gateway_warnings": list(advice.product_gateway_warnings),
        "product_gateway_ready_for_review": advice.product_gateway_ready_for_review,
        "recommendation": advice.recommendation,
        "status": status,
        "display_summary": _display_summary(status=status, advice=advice),
        "plan_steps": list(advice.plan_steps),
        "risk_notes": list(advice.risk_notes),
        "next_step": advice.next_step,
        "blocking_reasons": list(advice.blocking_reasons),
        "warnings": list(advice.warnings),
        "governance_refs": list(advice.governance_refs),
        "config_refs": list(advice.config_refs),
        "readonly": True,
        "candidate_only": True,
        "execution_enabled": False,
    }


def _status(recommendation: str) -> str:
    if recommendation == "defer_until_context_ready":
        return "blocked"
    if recommendation == "collect_governed_run_evidence":
        return "needs_evidence"
    if recommendation == "continue_with_controlled_agent_review":
        return "ready_for_controlled_review"
    if recommendation == "continue_with_no_live_review":
        return "ready_for_no_live_review"
    if recommendation == "review_agent_shell_failure":
        return "needs_agent_shell_review"
    if recommendation == "continue_with_product_gateway_review":
        return "ready_for_product_gateway_review"
    if recommendation == "continue_with_product_gateway_skipped_review":
        return "ready_for_product_gateway_skipped_review"
    if recommendation in {
        "review_product_gateway_blocking_reasons",
        "review_product_gateway_failure",
    }:
        return "needs_product_gateway_review"
    return "blocked"


def _display_summary(*, status: str, advice: AgentTaskAdviceCandidate) -> str:
    return (
        "Agent task advice consumption payload: "
        f"status={status}, recommendation={advice.recommendation}, "
        f"blocking_reasons={len(advice.blocking_reasons)}, "
        f"warnings={len(advice.warnings)}. "
        "This payload is read-only and does not grant execution permission."
    )
