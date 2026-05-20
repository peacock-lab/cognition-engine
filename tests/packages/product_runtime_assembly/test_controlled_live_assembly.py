from __future__ import annotations

from typing import Any

from product_runtime_assembly import controlled_live
from product_runtime_assembly.controlled_live import (
    DEFAULT_CONTROLLED_LIVE_RUNTIME_SERVICE_REF,
    run_controlled_live_with_default_runtime,
)
from schemas.controlled_execution import (
    ControlledExecutionRequestSchema,
    ControlledExecutionRuntimeSummarySchema,
)


def test_controlled_live_default_assembly_injects_runtime_service(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_runtime_service(
        request: ControlledExecutionRequestSchema,
        **kwargs: Any,
    ) -> ControlledExecutionRuntimeSummarySchema:
        captured["request"] = request
        captured.update(kwargs)
        return ControlledExecutionRuntimeSummarySchema(
            runtime_id=request.runtime_id,
            invocation_id=request.invocation_id,
            workflow_id=request.workflow_id,
            execution_mode="tests_product_runtime_assembly_controlled_live",
            status="success",
            controlled_run=True,
            productized_controlled_run=True,
            sanitized=True,
            adk_run_allowed=True,
            adk_run_performed=True,
            execution_performed=True,
            live_llm_allowed=True,
            live_llm_call_performed=True,
            sanitized_evidence_ref=request.sanitized_evidence_ref,
            audit_ref=request.audit_ref,
            governance_summary_output_ref=request.governance_summary_output_ref,
            final_preflight={"allowed": True},
            controlled_live_llm_preflight={"allowed": True},
        )

    monkeypatch.setattr(
        controlled_live,
        "_run_default_controlled_execution_service",
        fake_runtime_service,
    )

    response = run_controlled_live_with_default_runtime(
        {
            "request_id": "request-controlled-live-assembly",
            "runtime_id": "runtime-controlled-live-assembly",
            "environment": "local",
            "profile": "dev",
            "input_payload": {"input_summary": "已脱敏 controlled-live 输入"},
            "operator_approved": True,
            "approval_ref": "approval://controlled-live-assembly",
            "audit_ref": "audit://controlled-live-assembly",
            "sanitized_evidence_ref": "evidence://controlled-live-assembly",
            "governance_summary_output_ref": (
                "governance-summary://controlled-live-assembly"
            ),
            "request_live_llm": True,
            "allow_live_llm": True,
            "live_llm_approval_ref": "approval://controlled-live-llm",
        }
    )

    assert captured["request"].runtime_id == "runtime-controlled-live-assembly"
    assert captured["config_selection"].environment == "local"
    assert captured["config_selection"].profile == "dev"
    assert captured["live_llm_options"] is None
    assert response.status.value == "success"
    assert response.metadata["runtime_service"] == (
        DEFAULT_CONTROLLED_LIVE_RUNTIME_SERVICE_REF
    )
    assert response.entry_kind.value == "controlled_live"
