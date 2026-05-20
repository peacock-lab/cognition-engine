from __future__ import annotations

import inspect
import re

import pytest

from cognition_governance import (
    AGENT_TASK_ADVICE_PAYLOAD_EVIDENCE_TYPE,
    PRODUCT_AGENT_OUTPUT_GOVERNANCE_CASE_TYPE,
    PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_REF,
    PRODUCT_AGENT_OUTPUT_GOVERNANCE_SOURCE,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_EVIDENCE_TYPE,
    GovernanceCase,
    GovernanceEvidence,
    ProductAgentOutputGovernanceMappingResult,
    map_agent_task_advice_payload_to_governance_evidence,
    map_product_agent_output_evidence_to_governance_case,
    map_product_agent_output_governance_package,
    map_product_gateway_response_summary_to_governance_evidence,
)
import cognition_governance.product_agent_output_governance_mapping as mapping


def test_product_gateway_summary_maps_to_governance_evidence() -> None:
    evidence = map_product_gateway_response_summary_to_governance_evidence(
        _product_gateway_summary()
    )

    assert isinstance(evidence, GovernanceEvidence)
    assert evidence.evidence_type == PRODUCT_GATEWAY_RESPONSE_SUMMARY_EVIDENCE_TYPE
    assert evidence.source == PRODUCT_AGENT_OUTPUT_GOVERNANCE_SOURCE
    assert evidence.content_ref == "product-gateway-response://request-1"
    assert evidence.metadata["request_id"] == "request-1"
    assert evidence.metadata["entry_kind"] == "agent_shell"
    assert evidence.metadata["status"] == "success"
    assert evidence.metadata["summary_only"] is True
    assert evidence.metadata["refs_only"] is True
    assert evidence.metadata["candidate_only"] is True
    assert evidence.metadata["block_candidates"] == []
    assert evidence.metadata["human_review_reasons"] == []


@pytest.mark.parametrize(
    "entry_kind",
    [
        "cognition_run",
        "controlled_live",
        "agent_shell",
        "tool_smoke",
        "task_workflow_route",
        "task_workflow_execution",
        "external_readonly_fetch",
    ],
)
def test_product_gateway_summary_entry_kinds_map_to_governance_evidence(
    entry_kind: str,
) -> None:
    evidence = map_product_gateway_response_summary_to_governance_evidence(
        _product_gateway_summary(entry_kind=entry_kind)
    )

    assert evidence.metadata["entry_kind"] == entry_kind
    assert evidence.metadata["summary_only"] is True
    assert evidence.metadata["refs_only"] is True


@pytest.mark.parametrize(
    ("status", "expected_key"),
    [
        ("blocked", "product_gateway_response_blocked"),
        ("failed", "product_gateway_response_failed"),
        ("skipped", "product_gateway_response_skipped"),
    ],
)
def test_product_gateway_summary_statuses_map_to_review_candidates(
    status: str,
    expected_key: str,
) -> None:
    evidence = map_product_gateway_response_summary_to_governance_evidence(
        _product_gateway_summary(status=status)
    )

    metadata = evidence.metadata
    assert expected_key in (
        metadata["block_candidates"] + metadata["warning_candidates"]
    )
    assert metadata["human_review_reasons"]


def test_product_gateway_summary_rejects_blocked_without_reasons() -> None:
    summary = _product_gateway_summary(status="blocked")
    summary["blocking_reasons"] = []

    with pytest.raises(ValueError):
        map_product_gateway_response_summary_to_governance_evidence(summary)


def test_product_gateway_summary_rejects_raw_payload_keys() -> None:
    summary = _product_gateway_summary()
    summary["metadata"] = {"raw_response": "must not enter governance evidence"}

    with pytest.raises(ValueError):
        map_product_gateway_response_summary_to_governance_evidence(summary)


def test_agent_task_advice_payload_maps_to_governance_evidence() -> None:
    evidence = map_agent_task_advice_payload_to_governance_evidence(
        _agent_task_advice_payload()
    )

    assert isinstance(evidence, GovernanceEvidence)
    assert evidence.evidence_type == AGENT_TASK_ADVICE_PAYLOAD_EVIDENCE_TYPE
    assert evidence.source == PRODUCT_AGENT_OUTPUT_GOVERNANCE_SOURCE
    assert evidence.content_ref is None
    assert evidence.metadata["candidate_id"] == "agent-task-advice-1"
    assert evidence.metadata["recommendation"] == "continue_with_product_gateway_review"
    assert evidence.metadata["status"] == "ready_for_product_gateway_review"
    assert evidence.metadata["readonly"] is True
    assert evidence.metadata["candidate_only"] is True
    assert evidence.metadata["execution_enabled"] is False
    assert evidence.metadata["summary_only"] is True
    assert evidence.metadata["refs_only"] is True


def test_agent_task_advice_payload_review_status_maps_to_human_review() -> None:
    payload = _agent_task_advice_payload(
        recommendation="review_product_gateway_failure",
        status="needs_product_gateway_review",
        product_gateway_status="failed",
    )

    evidence = map_agent_task_advice_payload_to_governance_evidence(payload)

    assert "review_product_gateway_failure" in evidence.metadata["block_candidates"]
    assert evidence.metadata["human_review_reasons"]


def test_agent_task_advice_payload_requires_candidate_only_boundary() -> None:
    payload = _agent_task_advice_payload()
    payload["execution_enabled"] = True

    with pytest.raises(ValueError):
        map_agent_task_advice_payload_to_governance_evidence(payload)


def test_product_agent_output_evidence_maps_to_governance_case() -> None:
    product_evidence = map_product_gateway_response_summary_to_governance_evidence(
        _product_gateway_summary()
    )
    agent_evidence = map_agent_task_advice_payload_to_governance_evidence(
        _agent_task_advice_payload()
    )

    case = map_product_agent_output_evidence_to_governance_case(
        [product_evidence, agent_evidence]
    )

    assert isinstance(case, GovernanceCase)
    assert case.case_type == PRODUCT_AGENT_OUTPUT_GOVERNANCE_CASE_TYPE
    assert case.subject == "request-1"
    assert case.evidence_refs == [product_evidence.evidence_id, agent_evidence.evidence_id]
    assert case.policy_refs == [PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_REF]
    assert case.context["product_gateway_request_id"] == "request-1"
    assert case.context["agent_advice_status"] == "ready_for_product_gateway_review"
    assert case.metadata["missing_evidence"] == []
    assert case.metadata["summary_only"] is True
    assert case.metadata["refs_only"] is True
    assert case.metadata["candidate_only"] is True


def test_product_agent_output_case_marks_missing_evidence() -> None:
    product_evidence = map_product_gateway_response_summary_to_governance_evidence(
        _product_gateway_summary()
    )

    case = map_product_agent_output_evidence_to_governance_case([product_evidence])

    assert case.metadata["missing_evidence"] == [
        AGENT_TASK_ADVICE_PAYLOAD_EVIDENCE_TYPE
    ]
    assert case.metadata["human_review_required"] is True
    assert case.metadata["decision_candidate_blocked"] is True


def test_product_agent_output_package_returns_evidence_and_case_only() -> None:
    result = map_product_agent_output_governance_package(
        product_gateway_summary=_product_gateway_summary(),
        agent_task_advice_payload=_agent_task_advice_payload(),
    )

    assert isinstance(result, ProductAgentOutputGovernanceMappingResult)
    assert len(result.governance_evidence) == 2
    assert result.governance_case.case_type == PRODUCT_AGENT_OUTPUT_GOVERNANCE_CASE_TYPE
    assert not hasattr(result, "governance_decision")
    assert not hasattr(result, "governance_outcome")


def test_product_agent_output_mapping_source_keeps_execution_layers_out() -> None:
    source = inspect.getsource(mapping)
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|cognition_agent|google\.adk|adk_adapter|"
        r"runtime_container|composition|litellm|subprocess)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None
    assert "ProductGatewayResponse" not in source
    assert "GovernanceOutcome(" not in source


def _product_gateway_summary(
    *,
    entry_kind: str = "agent_shell",
    status: str = "success",
) -> dict[str, object]:
    return {
        "product": "product_gateway",
        "payload_type": "product_gateway_response_summary",
        "payload_version": "product_gateway_response_summary_v1",
        "request_id": "request-1",
        "entry_kind": entry_kind,
        "status": status,
        "exit_code": 0 if status in {"success", "skipped"} else 1,
        "product_gateway_response_ref": "product-gateway-response://request-1",
        "governance_summary_ref": "governance-summary://request-1",
        "evidence_refs": [
            {
                "ref": "evidence://request-1",
                "kind": "evidence",
                "purpose": "review",
                "metadata": {"source": "product_gateway.agent_shell"},
            }
        ],
        "audit_refs": [{"ref": "audit://request-1", "kind": "audit"}],
        "agent_advice_refs": [
            {"ref": "agent-advice://agent-task-advice-1", "kind": "agent_advice"}
        ],
        "tool_audit_refs": [
            {"ref": "tool-audit://tool-smoke-1", "kind": "tool_audit"}
        ],
        "blocking_reasons": ["product_gateway_blocked"]
        if status == "blocked"
        else [],
        "warnings": ["product_gateway_warning"] if status == "skipped" else [],
        "metadata": {"source": "product_gateway.agent_shell"},
    }


def _agent_task_advice_payload(
    *,
    recommendation: str = "continue_with_product_gateway_review",
    status: str = "ready_for_product_gateway_review",
    product_gateway_status: str = "success",
) -> dict[str, object]:
    return {
        "product": "cognition_agent",
        "payload_type": "agent_task_advice_consumption_payload",
        "payload_version": "agent_task_advice_consumption_payload_v1",
        "source": "cognition_agent.task_advice_consumption",
        "candidate_type": "agent_task_advice_candidate",
        "candidate_id": "agent-task-advice-1",
        "advice_version": "agent_task_advice_v1",
        "task_context_candidate_id": "agent-task-context-1",
        "task_candidate_id": "agent-task-1",
        "product_gateway_response_view_candidate_id": "agent-pg-view-1",
        "product_gateway_request_id": "request-1",
        "product_gateway_entry_kind": "agent_shell",
        "product_gateway_status": product_gateway_status,
        "product_gateway_exit_code": 0 if product_gateway_status == "success" else 1,
        "product_gateway_response_ref": "product-gateway-response://request-1",
        "product_gateway_governance_summary_ref": "governance-summary://request-1",
        "product_gateway_evidence_refs": [
            {"ref": "evidence://request-1", "kind": "evidence"}
        ],
        "product_gateway_audit_refs": [{"ref": "audit://request-1", "kind": "audit"}],
        "product_gateway_agent_advice_refs": [
            {"ref": "agent-advice://agent-task-advice-1", "kind": "agent_advice"}
        ],
        "product_gateway_tool_audit_refs": [
            {"ref": "tool-audit://tool-smoke-1", "kind": "tool_audit"}
        ],
        "product_gateway_blocking_reasons": ["product_gateway_failed"]
        if product_gateway_status in {"blocked", "failed"}
        else [],
        "product_gateway_warnings": [],
        "product_gateway_ready_for_review": product_gateway_status == "success",
        "recommendation": recommendation,
        "status": status,
        "display_summary": "read-only product gateway review advice",
        "plan_steps": ["review_product_gateway_refs"],
        "risk_notes": [],
        "next_step": "review",
        "blocking_reasons": [],
        "warnings": [],
        "governance_refs": ["governance-summary://request-1"],
        "config_refs": [],
        "readonly": True,
        "candidate_only": True,
        "execution_enabled": False,
    }
