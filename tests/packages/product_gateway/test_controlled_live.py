from __future__ import annotations

import pytest
from pydantic import ValidationError

import product_gateway.controlled_live as controlled_live_module
from product_gateway import (
    ControlledLiveGatewayInput,
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayResponse,
    ProductGatewayStatus,
    build_controlled_live_compatibility_projection,
    build_controlled_live_gateway_request,
    run_controlled_live_gateway_request,
)
from runtime_container.controlled_run_facade import (
    ControlledRunFacadeInput,
    ControlledRunFacadeResult,
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


def test_controlled_live_projection_has_stable_facade_fields() -> None:
    projection = build_controlled_live_compatibility_projection(
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
    payload = projection.model_dump()

    assert payload == {
        "request_id": "request-controlled-live-projection",
        "entry_kind": "controlled_live",
        "execution_mode": "controlled_live",
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
        "request_ollama": False,
        "allow_live_llm": True,
        "allow_ollama": False,
        "live_llm_approval_ref": "approval://live-projection",
        "metadata": {
            "source": "product_gateway.controlled_live",
            "runtime_id": "runtime-controlled-live-projection",
            "workflow_id": "workflow-controlled-live",
            "workflow_name": "controlled-live-workflow",
            "environment": "local",
            "profile": "dev",
        },
    }
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


def test_controlled_live_gateway_maps_blocked_facade_result(monkeypatch) -> None:
    def fake_run(facade_input: ControlledRunFacadeInput) -> ControlledRunFacadeResult:
        assert facade_input.runtime_id == "runtime-blocked"
        return ControlledRunFacadeResult(
            runtime_id=facade_input.runtime_id,
            invocation_id=facade_input.invocation_id,
            workflow_id=facade_input.workflow_id,
            execution_mode="controlled_live",
            status="blocked",
            blocking_reasons=("operator_approval_not_true",),
            warnings=("approval required",),
        )

    monkeypatch.setattr(
        controlled_live_module,
        "run_controlled_run_facade",
        fake_run,
    )

    response = run_controlled_live_gateway_request(
        {
            "request_id": "request-blocked",
            "runtime_id": "runtime-blocked",
            "request_live_llm": True,
            "live_llm_approval_ref": "approval://requested-only",
        }
    )

    assert isinstance(response, ProductGatewayResponse)
    assert response.entry_kind is ProductGatewayEntryKind.CONTROLLED_LIVE
    assert response.status is ProductGatewayStatus.BLOCKED
    assert response.exit_code == 2
    assert response.blocking_reasons == ["operator_approval_not_true"]
    assert response.warnings == ["approval required"]


def test_controlled_live_gateway_maps_success_facade_result(monkeypatch) -> None:
    def fake_run(facade_input: ControlledRunFacadeInput) -> ControlledRunFacadeResult:
        assert facade_input.request_live_llm is True
        assert facade_input.allow_live_llm is True
        return ControlledRunFacadeResult(
            runtime_id=facade_input.runtime_id,
            invocation_id=facade_input.invocation_id,
            workflow_id=facade_input.workflow_id,
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

    monkeypatch.setattr(
        controlled_live_module,
        "run_controlled_run_facade",
        fake_run,
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
        }
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
    assert response.metadata["live_llm_allowed"] is True
    assert response.metadata["live_llm_call_performed"] is True
    assert response.metadata["ollama_allowed"] is True
    assert response.metadata["ollama_call_performed"] is True
    assert response.metadata["tool_status"] == "success"
    assert "raw_prompt" not in repr(response.model_dump())
    assert "raw_provider_response" not in repr(response.model_dump())
    assert "raw_tool_input" not in repr(response.model_dump())


def test_controlled_live_gateway_maps_failed_facade_result(monkeypatch) -> None:
    def fake_run(facade_input: ControlledRunFacadeInput) -> ControlledRunFacadeResult:
        return ControlledRunFacadeResult(
            runtime_id=facade_input.runtime_id,
            invocation_id=facade_input.invocation_id,
            workflow_id=facade_input.workflow_id,
            execution_mode="controlled_live",
            status="provider_failed",
            warnings=("provider unavailable",),
            tool_failure_type="provider_unavailable",
        )

    monkeypatch.setattr(
        controlled_live_module,
        "run_controlled_run_facade",
        fake_run,
    )

    response = run_controlled_live_gateway_request(
        {
            "request_id": "request-failed",
            "runtime_id": "runtime-failed",
            "request_live_llm": True,
            "live_llm_approval_ref": "approval://failed",
        }
    )

    assert response.status is ProductGatewayStatus.FAILED
    assert response.exit_code == 1
    assert response.blocking_reasons == []
    assert response.warnings == ["provider unavailable"]
    assert response.metadata["tool_failure_type"] == "provider_unavailable"
