from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayResponse,
    ProductGatewayStatus,
)
from product_gateway.tool_smoke import (
    ToolSmokeGatewayInput,
    build_tool_smoke_gateway_projection,
    build_tool_smoke_gateway_request,
    run_tool_smoke_gateway_request,
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


def test_tool_smoke_gateway_request_uses_tool_smoke_entry() -> None:
    request = build_tool_smoke_gateway_request(
        ToolSmokeGatewayInput(
            request_id="request-tool-smoke",
            tool_evidence_ref="tool-evidence://evidence-1",
            tool_run_ref="tool-run://run-1",
            governance_summary_ref="governance-summary://payload-1",
            tool_status="success",
            tool_runtime_call_performed=True,
            tool_smoke_ready=True,
        )
    )

    assert request.entry_kind is ProductGatewayEntryKind.TOOL_SMOKE
    assert request.execution_mode is ProductGatewayExecutionMode.SMOKE
    assert request.input_refs.governance_summary_ref == (
        "governance-summary://payload-1"
    )
    assert [ref.kind for ref in request.input_refs.additional_refs] == [
        "tool_evidence",
        "tool_run",
    ]
    assert request.metadata["source"] == "product_gateway.tool_smoke"
    assert request.metadata["tool_status"] == "success"
    assert request.metadata["tool_runtime_call_performed"] is True


def test_tool_smoke_projection_has_only_sanitized_refs_and_facts() -> None:
    projection = build_tool_smoke_gateway_projection(
        {
            "request_id": "request-tool-smoke-projection",
            "tool_evidence_ref": "tool-evidence://projection",
            "tool_run_ref": "tool-run://projection",
            "tool_audit_ref": "tool-audit://projection",
            "governance_summary_ref": "governance-summary://projection",
            "tool_status": "success",
            "tool_runtime_call_performed": True,
            "tool_confirmation_required": True,
            "tool_confirmation_granted": True,
            "adk_tool_confirmation_requested": True,
            "tool_confirmation_decision_source": "operator_approval_ref",
            "controlled_live_external_tool_smoke_enabled": True,
            "controlled_live_external_tool_smoke_source": "controlled_live",
            "tool_smoke_ready": True,
            "low_risk_tool_allowlist_count": 2,
            "warnings": ["sanitized_only"],
            "metadata": {"operator_visible": True},
        }
    )
    payload = projection.model_dump()

    assert payload == {
        "request_id": "request-tool-smoke-projection",
        "entry_kind": "tool_smoke",
        "execution_mode": "smoke",
        "tool_evidence_ref": "tool-evidence://projection",
        "tool_run_ref": "tool-run://projection",
        "tool_audit_ref": "tool-audit://projection",
        "governance_summary_ref": "governance-summary://projection",
        "tool_status": "success",
        "tool_failure_type": None,
        "tool_runtime_call_performed": True,
        "tool_confirmation_required": True,
        "tool_confirmation_granted": True,
        "adk_tool_confirmation_requested": True,
        "tool_confirmation_decision_source": "operator_approval_ref",
        "controlled_live_external_tool_smoke_enabled": True,
        "controlled_live_external_tool_smoke_source": "controlled_live",
        "tool_smoke_ready": True,
        "low_risk_tool_allowlist_count": 2,
        "blocking_reasons": [],
        "warnings": ["sanitized_only"],
        "metadata": {
            "operator_visible": True,
            "tool_status": "success",
            "tool_runtime_call_performed": True,
            "tool_confirmation_required": True,
            "tool_confirmation_granted": True,
            "adk_tool_confirmation_requested": True,
            "tool_confirmation_decision_source": "operator_approval_ref",
            "controlled_live_external_tool_smoke_enabled": True,
            "controlled_live_external_tool_smoke_source": "controlled_live",
            "tool_smoke_ready": True,
            "low_risk_tool_allowlist_count": 2,
            "source": "product_gateway.tool_smoke",
        },
    }
    payload_text = repr(payload)
    assert "ToolConfirmation" not in payload_text
    assert "ToolContext" not in payload_text
    assert "raw_tool_input" not in payload_text
    assert "raw_tool_output" not in payload_text


def test_tool_smoke_gateway_maps_success_refs_and_metadata() -> None:
    response = run_tool_smoke_gateway_request(
        {
            "request_id": "request-tool-smoke-success",
            "tool_evidence_ref": "tool-evidence://success",
            "tool_run_ref": "tool-run://success",
            "tool_audit_ref": "tool-audit://success",
            "governance_summary_ref": "governance-summary://success",
            "tool_status": "success",
            "tool_runtime_call_performed": True,
            "tool_confirmation_required": True,
            "tool_confirmation_granted": True,
            "adk_tool_confirmation_requested": True,
            "tool_confirmation_decision_source": "operator_approval_ref",
            "controlled_live_external_tool_smoke_enabled": True,
            "controlled_live_external_tool_smoke_source": "controlled_live",
            "tool_smoke_ready": True,
            "low_risk_tool_allowlist_count": 3,
            "warnings": ["readonly"],
        }
    )

    assert isinstance(response, ProductGatewayResponse)
    assert response.entry_kind is ProductGatewayEntryKind.TOOL_SMOKE
    assert response.status is ProductGatewayStatus.SUCCESS
    assert response.exit_code == 0
    assert response.governance_summary_ref == "governance-summary://success"
    assert response.output_refs.governance_summary_ref == (
        "governance-summary://success"
    )
    assert [(ref.ref, ref.kind, ref.purpose) for ref in response.tool_audit_refs] == [
        ("tool-evidence://success", "tool_evidence", "tool_smoke"),
        ("tool-run://success", "tool_run", "tool_smoke"),
        ("tool-audit://success", "tool_audit", "tool_smoke"),
    ]
    assert response.output_refs.tool_audit_refs == response.tool_audit_refs
    assert response.tool_audit_refs[0].metadata == {
        "source_key": "tool_evidence_ref"
    }
    assert response.metadata["source"] == "product_gateway.tool_smoke"
    assert response.metadata["tool_status"] == "success"
    assert response.metadata["tool_runtime_call_performed"] is True
    assert response.metadata["tool_confirmation_required"] is True
    assert response.metadata["tool_confirmation_granted"] is True
    assert response.metadata["adk_tool_confirmation_requested"] is True
    assert response.metadata["low_risk_tool_allowlist_count"] == 3

    summary = _assert_projected_response_summary(response)
    assert summary["entry_kind"] == "tool_smoke"
    assert summary["governance_summary_ref"] == "governance-summary://success"
    assert summary["evidence_refs"] == []
    assert summary["audit_refs"] == []
    assert [ref["ref"] for ref in summary["tool_audit_refs"]] == [
        "tool-evidence://success",
        "tool-run://success",
        "tool-audit://success",
    ]
    assert [ref["purpose"] for ref in summary["tool_audit_refs"]] == [
        "tool_smoke",
        "tool_smoke",
        "tool_smoke",
    ]
    assert response.warnings == ["readonly"]


@pytest.mark.parametrize(
    ("failure_type", "reason"),
    [
        ("tool_confirmation_required", "tool_confirmation_required"),
        ("tool_smoke_disabled", "tool_smoke_disabled"),
        ("tool_not_in_low_risk_allowlist", "tool_not_in_low_risk_allowlist"),
        (
            "tool_smoke_override_source_missing",
            "tool_smoke_override_source_missing",
        ),
        ("tool_call_not_allowed", "tool_call_not_allowed"),
    ],
)
def test_tool_smoke_gateway_maps_blocking_failure_types(
    failure_type: str,
    reason: str,
) -> None:
    response = run_tool_smoke_gateway_request(
        {
            "request_id": f"request-tool-smoke-{failure_type}",
            "tool_status": "failed",
            "tool_failure_type": failure_type,
            "blocking_reasons": [reason],
        }
    )

    assert response.status is ProductGatewayStatus.BLOCKED
    assert response.exit_code == 2
    assert response.blocking_reasons == [reason]
    assert response.metadata["tool_failure_type"] == failure_type


def test_tool_smoke_gateway_maps_confirmation_required_without_grant_to_blocked() -> None:
    response = run_tool_smoke_gateway_request(
        {
            "request_id": "request-tool-smoke-confirmation-required",
            "tool_confirmation_required": True,
            "tool_confirmation_granted": False,
            "tool_runtime_call_performed": False,
            "blocking_reasons": ["tool_confirmation_required"],
        }
    )

    assert response.status is ProductGatewayStatus.BLOCKED
    assert response.exit_code == 2
    assert response.blocking_reasons == ["tool_confirmation_required"]


@pytest.mark.parametrize("tool_status", ["skipped", "not_run"])
def test_tool_smoke_gateway_maps_skipped_status(tool_status: str) -> None:
    response = run_tool_smoke_gateway_request(
        {
            "request_id": f"request-tool-smoke-{tool_status}",
            "tool_status": tool_status,
        }
    )

    assert response.status is ProductGatewayStatus.SKIPPED
    assert response.exit_code == 0


def test_tool_smoke_gateway_maps_failed_status() -> None:
    response = run_tool_smoke_gateway_request(
        {
            "request_id": "request-tool-smoke-failed",
            "tool_status": "failed",
            "tool_failure_type": "tool_runtime_failure",
            "tool_runtime_call_performed": True,
        }
    )

    assert response.status is ProductGatewayStatus.FAILED
    assert response.exit_code == 1
    assert response.metadata["tool_failure_type"] == "tool_runtime_failure"


def test_tool_smoke_gateway_maps_ready_without_status_to_success() -> None:
    response = run_tool_smoke_gateway_request(
        {
            "request_id": "request-tool-smoke-ready",
            "tool_smoke_ready": True,
        }
    )

    assert response.status is ProductGatewayStatus.SUCCESS
    assert response.exit_code == 0


def test_tool_smoke_gateway_maps_missing_status_without_failure_to_skipped() -> None:
    response = run_tool_smoke_gateway_request(
        {
            "request_id": "request-tool-smoke-no-status",
        }
    )

    assert response.status is ProductGatewayStatus.SKIPPED
    assert response.exit_code == 0
    assert response.metadata["status_warning"] == (
        "tool_status_missing_without_failure_type"
    )


def test_tool_smoke_gateway_rejects_blocked_without_reasons() -> None:
    with pytest.raises(ValidationError):
        run_tool_smoke_gateway_request(
            {
                "request_id": "request-tool-smoke-blocked-invalid",
                "tool_failure_type": "tool_smoke_disabled",
            }
        )


@pytest.mark.parametrize(
    "raw_payload",
    [
        {"metadata": {"raw_tool_input": {"arg": "raw"}}},
        {"metadata": {"raw_tool_output": {"result": "raw"}}},
        {"metadata": {"ToolConfirmation": {"state": "requested"}}},
        {"metadata": {"ToolContext": {"kind": "raw"}}},
        {"metadata": {"function_args": {"query": "raw"}}},
        {"metadata": {"function_response": {"result": "raw"}}},
        {"metadata": {"provider_payload": {"raw": True}}},
        {"metadata": {"low_risk_tool_allowlist": ["raw-tool-name"]}},
        {"metadata": {"tool": "ToolConfirmation"}},
        {"metadata": {"tool_context": {"object_module": "google.adk.tools"}}},
        {"tool_confirmation_ref": "tool-confirmation://not-yet-contractual"},
        {"tool_policy_ref": "tool-policy://not-yet-contractual"},
    ],
)
def test_tool_smoke_gateway_rejects_raw_payloads(
    raw_payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        build_tool_smoke_gateway_request(
            {
                "request_id": "request-tool-smoke-raw",
                **raw_payload,
            }
        )


def test_tool_smoke_gateway_rejects_negative_allowlist_count() -> None:
    with pytest.raises(ValidationError):
        ToolSmokeGatewayInput(
            request_id="request-tool-smoke-negative-count",
            low_risk_tool_allowlist_count=-1,
        )


def test_tool_smoke_adapter_has_no_runtime_agent_or_tool_dependencies() -> None:
    source = (
        PRODUCT_GATEWAY_ROOT / "tool_smoke.py"
    ).read_text(encoding="utf-8")

    forbidden = (
        "from runtime_container",
        "import runtime_container",
        "from cognition_agent",
        "import cognition_agent",
        "from composition",
        "import composition",
        "from adk_adapter",
        "import adk_adapter",
        "google.adk",
        "litellm",
        "schemas.adk_tool",
        "behavior_contracts",
        "contract_core",
    )
    for pattern in forbidden:
        assert pattern not in source


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
    assert "raw_tool_input" not in summary_text
    assert "raw_tool_output" not in summary_text
    assert "ToolConfirmation" not in summary_text
    assert "ToolContext" not in summary_text
    assert "config_context" not in summary_text
    return summary
