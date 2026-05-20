from __future__ import annotations

import pytest
from pydantic import ValidationError

from config_contexts.runtime import RuntimeConfigSelectionContext
from contract_core.controlled_execution import (
    ControlledExecutionRequestSchema,
    ControlledExecutionRuntimeSummarySchema,
)
from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayResponse,
    ProductGatewayStatus,
)
from product_gateway.controlled_live import (
    ControlledLiveGatewayInput,
    RUNTIME_SERVICE_NOT_INJECTED_BLOCKING_REASON,
    RUNTIME_SERVICE_NOT_INJECTED_REF,
    build_controlled_live_config_selection,
    build_controlled_live_controlled_execution_request,
    build_controlled_live_gateway_request,
    run_controlled_live_gateway_request,
)
from product_gateway.response_summary_projection import (
    project_product_gateway_response_summary,
)
from schemas.product_gateway_response_summary import (
    validate_product_gateway_response_summary,
)


def test_controlled_live_gateway_request_uses_controlled_live_entry() -> None:
    request = build_controlled_live_gateway_request(
        ControlledLiveGatewayInput(
            request_id="request-controlled-live",
            runtime_id="runtime-controlled-live",
            input_payload={"input_summary": "已脱敏 controlled-live 输入"},
            request_live_llm=True,
            allow_live_llm=True,
            live_llm_approval_ref="approval://controlled-live",
        )
    )

    assert request.entry_kind is ProductGatewayEntryKind.CONTROLLED_LIVE
    assert request.execution_mode is ProductGatewayExecutionMode.CONTROLLED_LIVE
    assert request.live_options.request_live_llm is True
    assert request.live_options.allow_live_llm is True
    assert request.live_options.live_llm_approval_ref == "approval://controlled-live"
    assert request.live_options.override_source == (
        "explicit_controlled_live_product_entry"
    )
    assert request.metadata["source"] == "product_gateway.controlled_live"


def test_controlled_live_gateway_request_maps_preflight_only() -> None:
    request = build_controlled_live_gateway_request(
        {
            "request_id": "request-controlled-live-preflight",
            "runtime_id": "runtime-controlled-live-preflight",
            "preflight_only": True,
        }
    )

    assert request.entry_kind is ProductGatewayEntryKind.CONTROLLED_LIVE
    assert request.execution_mode is ProductGatewayExecutionMode.PREFLIGHT_ONLY


def test_controlled_live_builds_controlled_execution_request_contract() -> None:
    request = build_controlled_live_controlled_execution_request(
        {
            "request_id": "request-controlled-live-projection",
            "runtime_id": "runtime-controlled-live-projection",
            "workflow_id": "workflow-controlled-live",
            "workflow_name": "controlled-live-workflow",
            "environment": "local",
            "profile": "dev",
            "input_payload": {"input_summary": "已脱敏输入"},
            "operator_approved": True,
            "approval_ref": "approval://projection",
            "audit_ref": "audit://projection",
            "sanitized_evidence_ref": "evidence://projection",
            "governance_summary_output_ref": "governance://projection",
            "request_live_llm": True,
            "allow_live_llm": True,
            "live_llm_approval_ref": "approval://live-projection",
        }
    )
    payload = request.to_runtime_mapping()

    assert payload == {
        "runtime_id": "runtime-controlled-live-projection",
        "invocation_id": "request-controlled-live-projection",
        "workflow_id": "workflow-controlled-live",
        "workflow_name": "controlled-live-workflow",
        "input_payload": {"input_summary": "已脱敏输入"},
        "operator_approved": True,
        "approval_ref": "approval://projection",
        "audit_ref": "audit://projection",
        "sanitized_evidence_ref": "evidence://projection",
        "governance_summary_output_ref": "governance://projection",
        "request_live_llm": True,
        "request_ollama": False,
        "allow_live_llm": True,
        "allow_ollama": False,
        "live_llm_approval_ref": "approval://live-projection",
        "metadata": {
            "source": "product_gateway.controlled_live",
            "product_request_id": "request-controlled-live-projection",
            "entry_kind": "controlled_live",
            "execution_mode": "controlled_live",
        },
    }
    config_selection = build_controlled_live_config_selection(
        {
            "request_id": "request-controlled-live-projection",
            "runtime_id": "runtime-controlled-live-projection",
            "environment": "local",
            "profile": "dev",
        }
    )
    assert config_selection.environment == "local"
    assert config_selection.profile == "dev"
    assert "config_root" not in repr(payload)
    assert "runtime_container" not in repr(payload)


@pytest.mark.parametrize(
    "raw_payload",
    [
        {"raw_prompt": "不要进入产品入口"},
        {"raw_provider_response": {"content": "raw"}},
        {"raw_tool_input": {"argument": "raw"}},
    ],
)
def test_controlled_live_gateway_request_rejects_raw_payloads(
    raw_payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        build_controlled_live_gateway_request(
            {
                "request_id": "request-controlled-live-raw",
                "runtime_id": "runtime-controlled-live-raw",
                "input_payload": raw_payload,
            }
        )


def test_controlled_live_requires_live_approval_for_allowed_live() -> None:
    with pytest.raises(ValidationError):
        build_controlled_live_gateway_request(
            {
                "request_id": "request-controlled-live-approval",
                "runtime_id": "runtime-controlled-live-approval",
                "allow_live_llm": True,
            }
        )


def test_controlled_live_gateway_blocks_without_runtime_service() -> None:
    response = run_controlled_live_gateway_request(
        {
            "request_id": "request-runtime-service-missing",
            "runtime_id": "runtime-service-missing",
            "request_live_llm": True,
            "live_llm_approval_ref": "approval://requested-only",
            "sanitized_evidence_ref": "evidence://missing-service",
            "audit_ref": "audit://missing-service",
        }
    )

    assert isinstance(response, ProductGatewayResponse)
    assert response.entry_kind is ProductGatewayEntryKind.CONTROLLED_LIVE
    assert response.status is ProductGatewayStatus.BLOCKED
    assert response.exit_code == 2
    assert response.blocking_reasons == [
        RUNTIME_SERVICE_NOT_INJECTED_BLOCKING_REASON
    ]
    assert response.warnings == ["runtime_service_required_for_controlled_live"]
    assert response.metadata["runtime_service"] == RUNTIME_SERVICE_NOT_INJECTED_REF
    assert response.evidence_refs[0].ref == "evidence://missing-service"
    assert response.audit_refs[0].ref == "audit://missing-service"


def test_controlled_live_gateway_maps_blocked_runtime_summary() -> None:
    def fake_run(
        request: ControlledExecutionRequestSchema,
        *,
        config_selection: RuntimeConfigSelectionContext,
    ) -> ControlledExecutionRuntimeSummarySchema:
        assert request.runtime_id == "runtime-blocked"
        assert config_selection.environment == "local"
        return ControlledExecutionRuntimeSummarySchema(
            runtime_id=request.runtime_id,
            invocation_id=request.invocation_id,
            workflow_id=request.workflow_id,
            execution_mode="controlled_live",
            status="blocked",
            blocking_reasons=("operator_approval_not_true",),
            warnings=("approval required",),
        )

    response = run_controlled_live_gateway_request(
        {
            "request_id": "request-blocked",
            "runtime_id": "runtime-blocked",
            "request_live_llm": True,
            "live_llm_approval_ref": "approval://requested-only",
        },
        runtime_service=fake_run,
        runtime_service_ref="test.controlled_live.fake_blocked_runtime_service",
    )

    assert isinstance(response, ProductGatewayResponse)
    assert response.entry_kind is ProductGatewayEntryKind.CONTROLLED_LIVE
    assert response.status is ProductGatewayStatus.BLOCKED
    assert response.exit_code == 2
    assert response.blocking_reasons == ["operator_approval_not_true"]
    assert response.warnings == ["approval required"]
    assert response.metadata["runtime_service"] == (
        "test.controlled_live.fake_blocked_runtime_service"
    )


def test_controlled_live_gateway_maps_success_runtime_summary() -> None:
    def fake_run(
        request: ControlledExecutionRequestSchema,
        *,
        config_selection: RuntimeConfigSelectionContext,
    ) -> ControlledExecutionRuntimeSummarySchema:
        assert request.request_live_llm is True
        assert request.allow_live_llm is True
        assert config_selection.environment == "local"
        return ControlledExecutionRuntimeSummarySchema(
            runtime_id=request.runtime_id,
            invocation_id=request.invocation_id,
            workflow_id=request.workflow_id,
            execution_mode="controlled_live",
            status="success",
            controlled_run=True,
            productized_controlled_run=True,
            adk_run_allowed=True,
            adk_run_performed=True,
            execution_performed=True,
            live_llm_allowed=True,
            live_llm_call_performed=True,
            ollama_allowed=True,
            ollama_call_performed=True,
            sanitized_evidence_ref="evidence://controlled-live",
            audit_ref="audit://controlled-live",
            governance_summary_payload_ref="governance://controlled-live-payload",
            governance_summary_output_ref="governance://controlled-live-output",
            tool_evidence_ref="tool-evidence://controlled-live",
            tool_run_ref="tool-run://controlled-live",
            tool_status="success",
        )

    response = run_controlled_live_gateway_request(
        {
            "request_id": "request-success",
            "runtime_id": "runtime-success",
            "operator_approved": True,
            "approval_ref": "approval://controlled-live",
            "audit_ref": "audit://controlled-live-input",
            "sanitized_evidence_ref": "evidence://controlled-live-input",
            "governance_summary_output_ref": "governance://controlled-live-output",
            "request_live_llm": True,
            "request_ollama": True,
            "allow_live_llm": True,
            "allow_ollama": True,
            "live_llm_approval_ref": "approval://live",
        },
        runtime_service=fake_run,
        runtime_service_ref="test.controlled_live.fake_success_runtime_service",
    )

    assert response.status is ProductGatewayStatus.SUCCESS
    assert response.exit_code == 0
    assert response.governance_summary_ref == "governance://controlled-live-payload"
    assert response.evidence_refs[0].ref == "evidence://controlled-live"
    assert response.audit_refs[0].ref == "audit://controlled-live"
    assert [ref.ref for ref in response.tool_audit_refs] == [
        "tool-evidence://controlled-live",
        "tool-run://controlled-live",
    ]
    assert response.tool_audit_refs[0].purpose == "controlled_live"
    assert response.metadata["source"] == "product_gateway.controlled_live"
    assert response.metadata["runtime_service"] == (
        "test.controlled_live.fake_success_runtime_service"
    )
    assert response.metadata["live_llm_allowed"] is True
    assert response.metadata["live_llm_call_performed"] is True
    assert response.metadata["ollama_allowed"] is True
    assert response.metadata["ollama_call_performed"] is True
    assert response.metadata["tool_status"] == "success"
    assert "raw_prompt" not in repr(response.model_dump())
    assert "raw_provider_response" not in repr(response.model_dump())
    assert "raw_tool_input" not in repr(response.model_dump())

    summary = _assert_projected_response_summary(response)
    assert summary["entry_kind"] == "controlled_live"
    assert summary["governance_summary_ref"] == "governance://controlled-live-payload"
    assert [ref["ref"] for ref in summary["evidence_refs"]] == [
        "evidence://controlled-live"
    ]
    assert [ref["ref"] for ref in summary["audit_refs"]] == [
        "audit://controlled-live"
    ]
    assert [ref["purpose"] for ref in summary["tool_audit_refs"]] == [
        "controlled_live",
        "controlled_live",
    ]


def test_controlled_live_gateway_maps_failed_runtime_summary() -> None:
    def fake_run(
        request: ControlledExecutionRequestSchema,
        *,
        config_selection: RuntimeConfigSelectionContext,
    ) -> ControlledExecutionRuntimeSummarySchema:
        assert config_selection.environment == "local"
        return ControlledExecutionRuntimeSummarySchema(
            runtime_id=request.runtime_id,
            invocation_id=request.invocation_id,
            workflow_id=request.workflow_id,
            execution_mode="controlled_live",
            status="provider_failed",
            warnings=("provider unavailable",),
            tool_failure_type="provider_unavailable",
        )

    response = run_controlled_live_gateway_request(
        {
            "request_id": "request-failed",
            "runtime_id": "runtime-failed",
            "request_live_llm": True,
            "live_llm_approval_ref": "approval://failed",
        },
        runtime_service=fake_run,
        runtime_service_ref="test.controlled_live.fake_failed_runtime_service",
    )

    assert response.status is ProductGatewayStatus.FAILED
    assert response.exit_code == 1
    assert response.blocking_reasons == []
    assert response.warnings == ["provider unavailable"]
    assert response.metadata["tool_failure_type"] == "provider_unavailable"
    assert response.metadata["runtime_service"] == (
        "test.controlled_live.fake_failed_runtime_service"
    )


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
    assert "raw_prompt" not in summary_text
    assert "raw_provider_response" not in summary_text
    assert "raw_tool_input" not in summary_text
    assert "config_context" not in summary_text
    return summary
