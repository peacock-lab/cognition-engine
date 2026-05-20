from __future__ import annotations

import pytest
from pydantic import ValidationError

from product_gateway.cognition_run import (
    CognitionRunGatewayInput,
    RUNTIME_SERVICE_NOT_INJECTED_BLOCKING_REASON,
    RUNTIME_SERVICE_NOT_INJECTED_REF,
    build_cognition_run_config_selection,
    build_cognition_run_controlled_execution_request,
    build_cognition_run_live_llm_options,
    build_cognition_run_gateway_request,
    execute_cognition_run_gateway_request,
    run_cognition_run_gateway_request,
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
from schemas.controlled_execution import (
    ControlledExecutionRequestSchema,
    ControlledExecutionRuntimeSummarySchema,
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


def test_cognition_run_builds_controlled_execution_request_contract() -> None:
    request = build_cognition_run_controlled_execution_request(
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
    payload = request.to_runtime_mapping()

    assert payload == {
        "runtime_id": "runtime-projection",
        "invocation_id": "request-projection",
        "workflow_id": "workflow-1",
        "workflow_name": "workflow name",
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
        "metadata": {
            "source": "product_gateway.cognition_run",
            "product_request_id": "request-projection",
            "entry_kind": "cognition_run",
            "execution_mode": "no_live",
        },
    }
    config_selection = build_cognition_run_config_selection(
        {
            "request_id": "request-projection",
            "runtime_id": "runtime-projection",
            "config_root": "config/test",
            "environment": "local",
            "profile": "dev",
        }
    )
    assert config_selection.config_root == "config/test"
    assert config_selection.environment == "local"
    assert config_selection.profile == "dev"


def test_cognition_run_builds_live_llm_options_context() -> None:
    options = build_cognition_run_live_llm_options(
        {
            "request_id": "request-live-options",
            "runtime_id": "runtime-live-options",
            "request_live_llm": True,
            "request_ollama": True,
            "allow_live_llm": True,
            "allow_ollama": True,
            "live_llm_approval_ref": "approval://live-options",
            "ollama_api_base": "http://127.0.0.1:11434",
            "live_llm_timeout_seconds": 11,
            "live_llm_max_tokens": 64,
            "response_preview_limit": 200,
            "metadata": {
                "source": "cognition_cli.run.gateway",
                "cli_command": "cognition run",
            },
        }
    )

    assert options.ollama_api_base == "http://127.0.0.1:11434"
    assert options.timeout_seconds == 11
    assert options.max_tokens == 64
    assert options.response_preview_limit == 200
    assert options.selection_source == "cognition_cli.run.gateway"
    assert options.metadata == {
        "cli_command": "cognition run",
        "cli_controlled_live": True,
    }


def test_cognition_run_request_excludes_runtime_and_provider_boundaries() -> None:
    request = build_cognition_run_controlled_execution_request(
        {
            "request_id": "request-boundary",
            "runtime_id": "runtime-boundary",
            "input_payload": {"input_summary": "已脱敏输入"},
        }
    )
    payload_text = repr(request.to_runtime_mapping())

    assert "config_root" not in payload_text
    assert "environment" not in payload_text
    assert "profile" not in payload_text
    assert "runtime_assembly" not in payload_text
    assert "llm_invocation_service" not in payload_text
    assert "agent_shell_live_client" not in payload_text
    assert "ControlledAdkRunRequestBuildInput" not in payload_text
    assert "runtime_container" not in payload_text
    assert "google.adk" not in payload_text
    assert "litellm" not in payload_text
    assert "provider_response" not in payload_text


def test_cognition_run_gateway_blocks_when_runtime_service_not_injected() -> None:
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
    assert RUNTIME_SERVICE_NOT_INJECTED_BLOCKING_REASON in response.blocking_reasons
    assert response.metadata["runtime_service"] == RUNTIME_SERVICE_NOT_INJECTED_REF
    assert response.metadata["adk_run_performed"] is False
    assert response.metadata["execution_performed"] is False


def test_cognition_run_gateway_consumes_injected_runtime_service_blocked_path() -> None:
    response = run_cognition_run_gateway_request(
        {
            "request_id": "request-runtime-blocked-226",
            "runtime_id": "runtime-runtime-blocked-226",
            "input_payload": {"input_summary": "缺少审批的受控运行请求"},
        },
        runtime_service=_blocked_runtime_service,
        runtime_service_ref="tests.product_gateway.blocked_runtime_service",
    )

    assert isinstance(response, ProductGatewayResponse)
    assert response.status is ProductGatewayStatus.BLOCKED
    assert response.exit_code == 2
    assert "operator_approval_not_true" in response.blocking_reasons
    assert response.metadata["runtime_service"] == (
        "tests.product_gateway.blocked_runtime_service"
    )
    assert response.metadata["adk_run_performed"] is False
    assert response.metadata["execution_performed"] is False


def test_cognition_run_gateway_execution_retains_runtime_summary() -> None:
    execution = execute_cognition_run_gateway_request(
        {
            "request_id": "request-execute-448",
            "runtime_id": "runtime-execute-448",
            "input_payload": {"input_summary": "已脱敏的受控运行请求"},
            "operator_approved": True,
            "approval_ref": "operator-approval://request-execute-448",
            "audit_ref": "audit://request-execute-448",
            "sanitized_evidence_ref": "evidence://request-execute-448",
            "governance_summary_output_ref": (
                "governance-summary://request-execute-448"
            ),
        },
        runtime_service=_allowed_runtime_service,
        runtime_service_ref="tests.product_gateway.allowed_runtime_service",
    )

    assert execution.product_request.request_id == "request-execute-448"
    assert execution.product_response.status is ProductGatewayStatus.SUCCESS
    assert execution.product_response_summary == (
        project_product_gateway_response_summary(execution.product_response)
    )
    assert validate_product_gateway_response_summary(
        execution.product_response_summary
    ).model_dump(mode="python") == execution.product_response_summary
    assert execution.product_response_summary["entry_kind"] == "cognition_run"
    assert execution.product_response_summary["product_gateway_response_ref"] is None
    assert execution.runtime_summary.status == "success"
    assert execution.runtime_summary.execution_performed is True
    assert execution.runtime_summary.final_preflight is not None
    assert execution.runtime_summary.controlled_live_llm_preflight is not None
    assert execution.product_response.metadata["runtime_service"] == (
        "tests.product_gateway.allowed_runtime_service"
    )


def test_cognition_run_gateway_consumes_runtime_service_allowed_no_live_path() -> None:
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
        },
        runtime_service=_allowed_runtime_service,
        runtime_service_ref="tests.product_gateway.allowed_runtime_service",
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

    summary = _assert_projected_response_summary(response)
    assert summary["entry_kind"] == "cognition_run"
    assert summary["governance_summary_ref"] == (
        "governance-summary://request-allowed-226"
    )
    assert [ref["ref"] for ref in summary["evidence_refs"]] == [
        "evidence://request-allowed-226"
    ]
    assert [ref["ref"] for ref in summary["audit_refs"]] == [
        "audit://request-allowed-226"
    ]
    assert [ref["purpose"] for ref in summary["tool_audit_refs"]] == [
        "cognition_run",
        "cognition_run",
    ]


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
        },
        runtime_service=_allowed_runtime_service,
        runtime_service_ref="tests.product_gateway.allowed_runtime_service",
    )
    request = build_cognition_run_controlled_execution_request(
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
    config_selection = build_cognition_run_config_selection(
        {
            "request_id": "request-no-config-root-226",
            "runtime_id": "runtime-no-config-root-226",
            "config_root": "config/test",
        }
    )

    assert response.status is ProductGatewayStatus.SUCCESS
    assert "config_root" not in repr(request.to_runtime_mapping())
    assert config_selection.config_root == "config/test"


def _allowed_runtime_service(
    request: ControlledExecutionRequestSchema,
    **_: object,
) -> ControlledExecutionRuntimeSummarySchema:
    return ControlledExecutionRuntimeSummarySchema(
        runtime_id=request.runtime_id,
        invocation_id=request.invocation_id,
        workflow_id=request.workflow_id,
        execution_mode="tests_controlled_execution_service",
        status="success",
        controlled_run=True,
        productized_controlled_run=True,
        sanitized=True,
        adk_run_allowed=True,
        adk_run_performed=True,
        execution_performed=True,
        live_llm_allowed=request.allow_live_llm,
        live_llm_call_performed=False,
        ollama_allowed=request.allow_ollama,
        ollama_call_performed=False,
        sanitized_evidence_ref=request.sanitized_evidence_ref,
        audit_ref=request.audit_ref,
        governance_summary_output_ref=request.governance_summary_output_ref,
        tool_evidence_ref="evidence://tool-audit",
        tool_run_ref="run://tool-audit",
        final_preflight={"allowed": True},
        controlled_live_llm_preflight={"allowed": False},
    )


def _blocked_runtime_service(
    request: ControlledExecutionRequestSchema,
    **_: object,
) -> ControlledExecutionRuntimeSummarySchema:
    return ControlledExecutionRuntimeSummarySchema(
        runtime_id=request.runtime_id,
        invocation_id=request.invocation_id,
        workflow_id=request.workflow_id,
        execution_mode="tests_controlled_execution_service",
        status="blocked",
        sanitized=True,
        adk_run_allowed=False,
        adk_run_performed=False,
        execution_performed=False,
        live_llm_allowed=False,
        live_llm_call_performed=False,
        ollama_allowed=False,
        ollama_call_performed=False,
        blocking_reasons=("operator_approval_not_true",),
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
