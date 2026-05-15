from __future__ import annotations

import pytest
from pydantic import ValidationError

from product_gateway import (
    CognitionRunGatewayInput,
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayResponse,
    ProductGatewayStatus,
    build_cognition_run_compatibility_projection,
    build_cognition_run_gateway_request,
    run_cognition_run_gateway_request,
)


def test_cognition_run_gateway_request_defaults_to_no_live() -> None:
    request = build_cognition_run_gateway_request(
        CognitionRunGatewayInput(
            request_id="request-1",
            runtime_id="runtime-1",
            input_payload={"input_summary": "用户请求摘要"},
        )
    )

    assert request.entry_kind is ProductGatewayEntryKind.COGNITION_RUN
    assert request.execution_mode is ProductGatewayExecutionMode.NO_LIVE
    assert request.input_payload == {"input_summary": "用户请求摘要"}
    assert request.metadata["source"] == "product_gateway.cognition_run"
    assert request.metadata["runtime_id"] == "runtime-1"


def test_cognition_run_gateway_request_maps_operator_approval_and_refs() -> None:
    request = build_cognition_run_gateway_request(
        {
            "request_id": "request-approved",
            "runtime_id": "runtime-approved",
            "input_payload": {"input_summary": "已脱敏输入"},
            "operator_approved": True,
            "approval_ref": "operator-approval://request-approved",
            "audit_ref": "audit://request-approved",
            "sanitized_evidence_ref": "evidence://request-approved",
            "governance_summary_output_ref": "governance-summary://request-approved",
        }
    )

    assert request.operator_approval.approved is True
    assert request.operator_approval.approval_ref == (
        "operator-approval://request-approved"
    )
    assert request.input_refs.operator_approval_ref == (
        "operator-approval://request-approved"
    )
    assert request.input_refs.audit_ref == "audit://request-approved"
    assert request.input_refs.sanitized_evidence_ref == (
        "evidence://request-approved"
    )
    assert request.input_refs.governance_summary_ref == (
        "governance-summary://request-approved"
    )


def test_cognition_run_gateway_request_maps_controlled_live_options() -> None:
    request = build_cognition_run_gateway_request(
        {
            "request_id": "request-live",
            "runtime_id": "runtime-live",
            "request_live_llm": True,
            "request_ollama": True,
            "allow_live_llm": True,
            "allow_ollama": True,
            "live_llm_approval_ref": "operator-approval://live",
        }
    )

    assert request.execution_mode is ProductGatewayExecutionMode.CONTROLLED_LIVE
    assert request.live_options.request_live_llm is True
    assert request.live_options.request_ollama is True
    assert request.live_options.allow_live_llm is True
    assert request.live_options.allow_ollama is True
    assert request.live_options.live_llm_approval_ref == "operator-approval://live"
    assert request.live_options.override_source == "explicit_product_entry"


def test_cognition_run_gateway_request_maps_preflight_only() -> None:
    request = build_cognition_run_gateway_request(
        {
            "request_id": "request-preflight",
            "runtime_id": "runtime-preflight",
            "request_live_llm": True,
            "request_ollama": True,
            "live_llm_approval_ref": "operator-approval://preflight",
            "preflight_only": True,
        }
    )

    assert request.execution_mode is ProductGatewayExecutionMode.PREFLIGHT_ONLY
    assert request.live_options.override_source == "explicit_product_entry"


@pytest.mark.parametrize(
    "raw_payload",
    [
        {"prompt": "raw prompt"},
        {"messages": [{"role": "user", "content": "raw"}]},
        {"user_message": "raw"},
        {"raw_user_message": "raw"},
    ],
)
def test_cognition_run_gateway_request_rejects_raw_input_payloads(
    raw_payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        build_cognition_run_gateway_request(
            {
                "request_id": "request-raw",
                "runtime_id": "runtime-raw",
                "input_payload": raw_payload,
            }
        )


def test_cognition_run_compatibility_projection_has_stable_fields() -> None:
    projection = build_cognition_run_compatibility_projection(
        {
            "request_id": "request-projection",
            "runtime_id": "runtime-projection",
            "workflow_id": "workflow-1",
            "workflow_name": "workflow name",
            "environment": "local",
            "profile": "dev",
            "input_payload": {"input_summary": "已脱敏输入"},
            "operator_approved": True,
            "approval_ref": "operator-approval://projection",
            "audit_ref": "audit://projection",
            "sanitized_evidence_ref": "evidence://projection",
            "governance_summary_output_ref": "governance-summary://projection",
        }
    )
    payload = projection.model_dump()

    assert payload == {
        "request_id": "request-projection",
        "entry_kind": "cognition_run",
        "execution_mode": "no_live",
        "runtime_id": "runtime-projection",
        "workflow_id": "workflow-1",
        "workflow_name": "workflow name",
        "environment": "local",
        "profile": "dev",
        "input_payload": {"input_summary": "已脱敏输入"},
        "operator_approved": True,
        "approval_ref": "operator-approval://projection",
        "audit_ref": "audit://projection",
        "sanitized_evidence_ref": "evidence://projection",
        "governance_summary_output_ref": "governance-summary://projection",
        "request_live_llm": False,
        "request_ollama": False,
        "allow_live_llm": False,
        "allow_ollama": False,
        "live_llm_approval_ref": None,
        "metadata": {
            "source": "product_gateway.cognition_run",
            "runtime_id": "runtime-projection",
            "workflow_id": "workflow-1",
            "workflow_name": "workflow name",
            "environment": "local",
            "profile": "dev",
        },
    }


def test_cognition_run_projection_excludes_runtime_and_provider_boundaries() -> None:
    projection = build_cognition_run_compatibility_projection(
        {
            "request_id": "request-boundary",
            "runtime_id": "runtime-boundary",
            "input_payload": {"input_summary": "已脱敏输入"},
        }
    )
    payload_text = repr(projection.model_dump())

    assert "config_root" not in payload_text
    assert "runtime_assembly" not in payload_text
    assert "llm_invocation_service" not in payload_text
    assert "agent_shell_live_client" not in payload_text
    assert "ControlledAdkRunRequestBuildInput" not in payload_text
    assert "runtime_container" not in payload_text
    assert "google.adk" not in payload_text
    assert "litellm" not in payload_text
    assert "provider_response" not in payload_text


def test_cognition_run_gateway_consumes_runtime_facade_blocked_path() -> None:
    response = run_cognition_run_gateway_request(
        {
            "request_id": "request-blocked-226",
            "runtime_id": "runtime-blocked-226",
            "input_payload": {"input_summary": "缺少审批的受控运行请求"},
        }
    )

    assert isinstance(response, ProductGatewayResponse)
    assert response.status is ProductGatewayStatus.BLOCKED
    assert response.exit_code == 2
    assert "operator_approval_not_true" in response.blocking_reasons
    assert response.metadata["runtime_facade"] == (
        "runtime_container.controlled_run_facade"
    )
    assert response.metadata["adk_run_performed"] is False
    assert response.metadata["execution_performed"] is False


def test_cognition_run_gateway_consumes_runtime_facade_allowed_no_live_path() -> None:
    response = run_cognition_run_gateway_request(
        {
            "request_id": "request-allowed-226",
            "runtime_id": "runtime-allowed-226",
            "input_payload": {"input_summary": "已脱敏的受控运行请求"},
            "operator_approved": True,
            "approval_ref": "operator-approval://request-allowed-226",
            "audit_ref": "audit://request-allowed-226",
            "sanitized_evidence_ref": "evidence://request-allowed-226",
            "governance_summary_output_ref": (
                "governance-summary://request-allowed-226"
            ),
        }
    )

    assert response.status is ProductGatewayStatus.SUCCESS
    assert response.exit_code == 0
    assert response.governance_summary_ref == (
        "governance-summary://request-allowed-226"
    )
    assert response.evidence_refs[0].ref == "evidence://request-allowed-226"
    assert response.audit_refs[0].ref == "audit://request-allowed-226"
    assert response.tool_audit_refs
    assert response.metadata["adk_run_performed"] is True
    assert response.metadata["execution_performed"] is True
    assert response.metadata["live_llm_call_performed"] is False
    assert response.metadata["ollama_call_performed"] is False
    assert "raw_prompt" not in repr(response.model_dump())
    assert "raw_provider_response" not in repr(response.model_dump())
    assert "raw_tool_input" not in repr(response.model_dump())


def test_cognition_run_gateway_response_does_not_put_config_root_in_projection() -> None:
    response = run_cognition_run_gateway_request(
        {
            "request_id": "request-no-config-root-226",
            "runtime_id": "runtime-no-config-root-226",
            "operator_approved": True,
            "approval_ref": "operator-approval://no-config-root-226",
            "audit_ref": "audit://no-config-root-226",
            "sanitized_evidence_ref": "evidence://no-config-root-226",
            "governance_summary_output_ref": (
                "governance-summary://no-config-root-226"
            ),
        }
    )
    projection = build_cognition_run_compatibility_projection(
        {
            "request_id": "request-no-config-root-226",
            "runtime_id": "runtime-no-config-root-226",
            "operator_approved": True,
            "approval_ref": "operator-approval://no-config-root-226",
            "audit_ref": "audit://no-config-root-226",
            "sanitized_evidence_ref": "evidence://no-config-root-226",
            "governance_summary_output_ref": (
                "governance-summary://no-config-root-226"
            ),
        }
    )

    assert response.status is ProductGatewayStatus.SUCCESS
    assert "config_root" not in repr(projection.model_dump())
