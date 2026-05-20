from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from product_gateway.agent_shell import (
    AgentShellGatewayInput,
    build_agent_shell_gateway_projection,
    build_agent_shell_gateway_request,
    run_agent_shell_gateway_request,
)
from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayResponse,
    ProductGatewayStatus,
)
from product_gateway.response_summary_projection import (
    project_product_gateway_response_summary,
)
from schemas.product_gateway_response_summary import (
    validate_product_gateway_response_summary,
)


PRODUCT_GATEWAY_ROOT = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "product_gateway"
    / "src"
    / "product_gateway"
)


def test_agent_shell_gateway_request_uses_agent_shell_entry() -> None:
    request = build_agent_shell_gateway_request(
        AgentShellGatewayInput(
            request_id="request-agent-shell",
            agent_shell_evidence_ref="agent-shell-evidence://evidence-1",
            agent_task_advice_ref="agent-task-advice://advice-1",
            governance_summary_ref="governance-summary://payload-1",
            agent_shell_status="success",
            agent_shell_ready_for_review=True,
        )
    )

    assert request.entry_kind is ProductGatewayEntryKind.AGENT_SHELL
    assert request.execution_mode is ProductGatewayExecutionMode.NO_LIVE
    assert request.input_refs.governance_summary_ref == (
        "governance-summary://payload-1"
    )
    assert [ref.kind for ref in request.input_refs.additional_refs] == [
        "agent_shell_evidence",
        "agent_task_advice",
    ]
    assert request.metadata["source"] == "product_gateway.agent_shell"
    assert request.metadata["agent_shell_status"] == "success"


def test_agent_shell_projection_has_only_sanitized_refs_and_facts() -> None:
    projection = build_agent_shell_gateway_projection(
        {
            "request_id": "request-agent-shell-projection",
            "agent_shell_evidence_ref": "agent-shell-evidence://projection",
            "agent_shell_run_ref": "agent-shell-run://projection",
            "agent_shell_audit_ref": "agent-shell-audit://projection",
            "agent_task_advice_ref": "agent-task-advice://projection",
            "agent_task_advice_candidate_ref": (
                "agent-task-advice-candidate://projection"
            ),
            "governance_summary_ref": "governance-summary://projection",
            "agent_shell_status": "success",
            "agent_shell_controlled_live": True,
            "agent_shell_runtime_call_performed": True,
            "agent_shell_call_attempted": True,
            "agent_shell_ready_for_review": True,
            "agent_task_recommendation": "continue_with_controlled_agent_review",
            "agent_task_advice_status": "ready_for_controlled_review",
            "warnings": ["review_only"],
            "metadata": {"operator_visible": True},
        }
    )
    payload = projection.model_dump()

    assert payload == {
        "request_id": "request-agent-shell-projection",
        "entry_kind": "agent_shell",
        "execution_mode": "no_live",
        "agent_shell_evidence_ref": "agent-shell-evidence://projection",
        "agent_shell_run_ref": "agent-shell-run://projection",
        "agent_shell_audit_ref": "agent-shell-audit://projection",
        "agent_task_advice_ref": "agent-task-advice://projection",
        "agent_task_advice_candidate_ref": (
            "agent-task-advice-candidate://projection"
        ),
        "governance_summary_ref": "governance-summary://projection",
        "agent_shell_status": "success",
        "agent_shell_failure_type": None,
        "agent_shell_controlled_live": True,
        "agent_shell_runtime_call_performed": True,
        "agent_shell_call_attempted": True,
        "agent_shell_ready_for_review": True,
        "agent_task_recommendation": "continue_with_controlled_agent_review",
        "agent_task_advice_status": "ready_for_controlled_review",
        "blocking_reasons": [],
        "warnings": ["review_only"],
        "metadata": {
            "operator_visible": True,
            "agent_shell_status": "success",
            "agent_shell_controlled_live": True,
            "agent_shell_runtime_call_performed": True,
            "agent_shell_call_attempted": True,
            "agent_shell_ready_for_review": True,
            "agent_task_recommendation": "continue_with_controlled_agent_review",
            "agent_task_advice_status": "ready_for_controlled_review",
            "source": "product_gateway.agent_shell",
        },
    }
    payload_text = repr(payload)
    assert "governance_summary_payload" not in payload_text
    assert "raw_adk_object" not in payload_text
    assert "AgentTaskAdviceCandidate" not in payload_text


def test_agent_shell_gateway_maps_success_refs_and_metadata() -> None:
    response = run_agent_shell_gateway_request(
        {
            "request_id": "request-agent-shell-success",
            "agent_shell_evidence_ref": "agent-shell-evidence://success",
            "agent_shell_run_ref": "agent-shell-run://success",
            "agent_shell_audit_ref": "agent-shell-audit://success",
            "agent_task_advice_ref": "agent-task-advice://success",
            "agent_task_advice_candidate_ref": (
                "agent-task-advice-candidate://success"
            ),
            "governance_summary_ref": "governance-summary://success",
            "agent_shell_status": "success",
            "agent_shell_controlled_live": True,
            "agent_shell_runtime_call_performed": True,
            "agent_shell_call_attempted": True,
            "agent_shell_ready_for_review": True,
            "agent_task_recommendation": "continue_with_controlled_agent_review",
            "agent_task_advice_status": "ready_for_controlled_review",
            "warnings": ["readonly"],
        }
    )

    assert isinstance(response, ProductGatewayResponse)
    assert response.entry_kind is ProductGatewayEntryKind.AGENT_SHELL
    assert response.status is ProductGatewayStatus.SUCCESS
    assert response.exit_code == 0
    assert response.governance_summary_ref == "governance-summary://success"
    assert response.output_refs.governance_summary_ref == (
        "governance-summary://success"
    )
    assert [(ref.ref, ref.kind, ref.purpose) for ref in response.evidence_refs] == [
        (
            "agent-shell-evidence://success",
            "agent_shell_evidence",
            "agent_shell",
        )
    ]
    assert [(ref.ref, ref.kind) for ref in response.audit_refs] == [
        ("agent-shell-run://success", "agent_shell_run"),
        ("agent-shell-audit://success", "agent_shell_audit"),
    ]
    assert [(ref.ref, ref.kind) for ref in response.agent_advice_refs] == [
        ("agent-task-advice://success", "agent_task_advice"),
        (
            "agent-task-advice-candidate://success",
            "agent_task_advice_candidate",
        ),
    ]
    assert response.agent_advice_refs[0].metadata == {
        "source_key": "agent_task_advice_ref"
    }
    assert response.metadata["source"] == "product_gateway.agent_shell"
    assert response.metadata["agent_shell_controlled_live"] is True
    assert response.metadata["agent_task_advice_status"] == (
        "ready_for_controlled_review"
    )
    assert response.warnings == ["readonly"]

    summary = _assert_projected_response_summary(response)
    assert summary["entry_kind"] == "agent_shell"
    assert summary["governance_summary_ref"] == "governance-summary://success"
    assert [ref["ref"] for ref in summary["evidence_refs"]] == [
        "agent-shell-evidence://success"
    ]
    assert [ref["ref"] for ref in summary["audit_refs"]] == [
        "agent-shell-run://success",
        "agent-shell-audit://success",
    ]
    assert [ref["ref"] for ref in summary["agent_advice_refs"]] == [
        "agent-task-advice://success",
        "agent-task-advice-candidate://success",
    ]


def test_agent_shell_gateway_maps_failed_status() -> None:
    response = run_agent_shell_gateway_request(
        {
            "request_id": "request-agent-shell-failed",
            "agent_shell_status": "failure",
            "agent_shell_failure_type": "provider_unavailable",
            "agent_shell_runtime_call_performed": True,
            "agent_shell_call_attempted": True,
        }
    )

    assert response.status is ProductGatewayStatus.FAILED
    assert response.exit_code == 1
    assert response.metadata["agent_shell_failure_type"] == "provider_unavailable"


def test_agent_shell_gateway_maps_skipped_status() -> None:
    response = run_agent_shell_gateway_request(
        {
            "request_id": "request-agent-shell-skipped",
            "agent_shell_status": "skipped",
            "agent_shell_failure_type": "live_disabled",
        }
    )

    assert response.status is ProductGatewayStatus.SKIPPED
    assert response.exit_code == 0


def test_agent_shell_gateway_maps_blocked_advice_status() -> None:
    response = run_agent_shell_gateway_request(
        {
            "request_id": "request-agent-shell-blocked",
            "agent_task_advice_status": "needs_evidence",
            "blocking_reasons": ["agent_task_advice_needs_evidence"],
        }
    )

    assert response.status is ProductGatewayStatus.BLOCKED
    assert response.exit_code == 2
    assert response.blocking_reasons == ["agent_task_advice_needs_evidence"]


def test_agent_shell_gateway_rejects_blocked_without_reasons() -> None:
    with pytest.raises(ValidationError):
        run_agent_shell_gateway_request(
            {
                "request_id": "request-agent-shell-blocked-invalid",
                "agent_task_advice_status": "blocked",
            }
        )


@pytest.mark.parametrize(
    "raw_payload",
    [
        {"metadata": {"prompt": "raw"}},
        {"metadata": {"messages": [{"role": "user", "content": "raw"}]}},
        {"metadata": {"response_text": "raw"}},
        {"metadata": {"raw_adk_object": {"kind": "raw"}}},
        {"metadata": {"agent_shell_audit": {"status": "success"}}},
        {"metadata": {"advice": "AgentTaskAdviceCandidate"}},
        {"governance_summary_payload": {"agent_shell_audit": {}}},
    ],
)
def test_agent_shell_gateway_rejects_raw_payloads(
    raw_payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        build_agent_shell_gateway_request(
            {
                "request_id": "request-agent-shell-raw",
                **raw_payload,
            }
        )


def test_agent_shell_adapter_has_no_runtime_or_agent_dependencies() -> None:
    source = (
        PRODUCT_GATEWAY_ROOT / "agent_shell.py"
    ).read_text(encoding="utf-8")

    assert "from runtime_container" not in source
    assert "import runtime_container" not in source
    assert "from cognition_agent" not in source
    assert "import cognition_agent" not in source
    assert "google.adk" not in source
    assert "adk_adapter" not in source
    assert "litellm" not in source


def _assert_projected_response_summary(
    response: ProductGatewayResponse,
) -> dict[str, object]:
    summary = project_product_gateway_response_summary(response)
    validated = validate_product_gateway_response_summary(summary)

    assert validated.model_dump(mode="python") == summary
    assert summary["payload_type"] == "product_gateway_response_summary"
    assert summary["payload_version"] == "product_gateway_response_summary_v1"
    assert summary["status"] == response.status.value
    assert summary["exit_code"] == response.exit_code
    assert summary["product_gateway_response_ref"] is None
    assert summary["readonly"] is True
    assert summary["summary_only"] is True
    assert summary["refs_only"] is True
    assert summary["candidate_only"] is True
    assert summary["execution_enabled"] is False
    assert summary["runtime_permission_granted"] is False
    assert summary["llm_call_enabled"] is False
    assert summary["tool_execution_enabled"] is False
    assert summary["action_execution_enabled"] is False
    assert summary["gateway_enabled"] is False
    assert summary["metadata"] == {
        "source": "product_gateway.response_summary_projection",
        "product_gateway_response_source": response.metadata["source"],
    }
    summary_text = repr(summary)
    assert "raw_adk_object" not in summary_text
    assert "AgentTaskAdviceCandidate" not in summary_text
    assert "config_context" not in summary_text
    return summary
