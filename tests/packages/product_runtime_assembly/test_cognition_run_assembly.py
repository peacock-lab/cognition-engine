from __future__ import annotations

from typing import Any

from product_runtime_assembly import cognition_run
from product_runtime_assembly.cognition_run import (
    DEFAULT_COGNITION_RUN_RUNTIME_SERVICE_REF,
    execute_cognition_run_with_default_runtime,
)
from product_runtime_assembly.external_readonly_answer_provider_factory import (
    ProductRuntimeAssemblyExternalReadonlyAnswerLlmInvocationServiceFactory,
)
from product_runtime_assembly.twf_provider_factory import (
    ProductRuntimeAssemblyTwfLlmInvocationServiceFactory,
)
from schemas.controlled_execution import (
    ControlledExecutionRequestSchema,
    ControlledExecutionRuntimeSummarySchema,
)


def test_cognition_run_default_assembly_injects_runtime_service(monkeypatch) -> None:
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
            execution_mode="tests_product_runtime_assembly",
            status="success",
            controlled_run=True,
            productized_controlled_run=True,
            sanitized=True,
            adk_run_allowed=True,
            adk_run_performed=True,
            execution_performed=True,
            sanitized_evidence_ref=request.sanitized_evidence_ref,
            audit_ref=request.audit_ref,
            governance_summary_output_ref=request.governance_summary_output_ref,
            final_preflight={"allowed": True},
            controlled_live_llm_preflight={"allowed": False},
        )

    monkeypatch.setattr(
        cognition_run,
        "_run_default_controlled_execution_service",
        fake_runtime_service,
    )

    execution = execute_cognition_run_with_default_runtime(
        {
            "request_id": "request-product-runtime-assembly",
            "runtime_id": "runtime-product-runtime-assembly",
            "config_root": "config/test",
            "environment": "local",
            "profile": "dev",
            "input_payload": {"input_summary": "已脱敏输入"},
            "operator_approved": True,
            "approval_ref": "approval://product-runtime-assembly",
            "audit_ref": "audit://product-runtime-assembly",
            "sanitized_evidence_ref": "evidence://product-runtime-assembly",
            "governance_summary_output_ref": (
                "governance-summary://product-runtime-assembly"
            ),
        }
    )

    assert captured["request"].runtime_id == "runtime-product-runtime-assembly"
    assert captured["config_selection"].config_root == "config/test"
    assert captured["config_selection"].profile == "dev"
    assert captured["live_llm_options"].selection_source == (
        "product_gateway.cognition_run"
    )
    assert execution.product_response.status.value == "success"
    assert execution.product_response.metadata["runtime_service"] == (
        DEFAULT_COGNITION_RUN_RUNTIME_SERVICE_REF
    )
    assert execution.product_response_summary["entry_kind"] == "cognition_run"


def test_product_runtime_entrypoint_injects_default_executor(monkeypatch) -> None:
    from product_runtime_assembly.entrypoints import cognition

    captured: dict[str, Any] = {}

    def fake_run_cli(argv: list[str], **kwargs: Any) -> int:
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return 7

    monkeypatch.setattr(
        "cognition_cli.entrypoints.cognition.run_cli",
        fake_run_cli,
    )

    assert cognition.run_cli(["run", "--json"]) == 7
    assert captured["argv"] == ["run", "--json"]
    assert captured["kwargs"]["run_gateway_executor"] is (
        execute_cognition_run_with_default_runtime
    )
    assert isinstance(
        captured["kwargs"]["twf_llm_invocation_service_factory"],
        ProductRuntimeAssemblyTwfLlmInvocationServiceFactory,
    )
    assert isinstance(
        captured["kwargs"]["external_readonly_ask_llm_invocation_service_factory"],
        ProductRuntimeAssemblyExternalReadonlyAnswerLlmInvocationServiceFactory,
    )
