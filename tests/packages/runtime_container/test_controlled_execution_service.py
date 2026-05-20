from __future__ import annotations

from pathlib import Path
from typing import Any

import runtime_container.controlled_execution_service as service_module
import runtime_container.controlled_live_llm_service as live_llm_service_module
from config_contexts.runtime import (
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmInvocationOptionsContext,
)
from contract_core.controlled_execution import (
    ControlledExecutionRuntimeService,
    ControlledExecutionRequestSchema,
    ControlledExecutionRuntimeSummarySchema,
)
from runtime_container.controlled_execution_service import (
    run_controlled_execution_service,
)
from runtime_container._controlled_run_facade import (
    ControlledRunFacadeInput,
    ControlledRunFacadeResult,
)


def test_controlled_execution_service_returns_runtime_summary(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run_controlled_run_facade(
        facade_input: ControlledRunFacadeInput,
        **kwargs: Any,
    ) -> ControlledRunFacadeResult:
        captured["facade_input"] = facade_input
        captured["kwargs"] = kwargs
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
            sanitized_evidence_ref="evidence://controlled-execution",
            audit_ref="audit://controlled-execution",
            final_preflight={"status": "allowed"},
        )

    monkeypatch.setattr(
        service_module,
        "run_controlled_run_facade",
        fake_run_controlled_run_facade,
    )

    summary = run_controlled_execution_service(
        ControlledExecutionRequestSchema(
            runtime_id="runtime-controlled-execution",
            invocation_id="request-controlled-execution",
            workflow_id="workflow-controlled-execution",
            workflow_name="controlled execution",
            input_payload={"input_summary": "已脱敏输入"},
            operator_approved=True,
            approval_ref="approval://controlled-execution",
            audit_ref="audit://controlled-execution-input",
            metadata={"source": "test"},
        ),
        config_selection=RuntimeConfigSelectionContext(
            config_root="config/test",
            environment="local",
            profile="dev",
            selection_source="test",
        ),
        workflow_registry=object(),
        llm_invocation_service=object(),
        agent_shell_live_client=object(),
        entry_runner=lambda request: {"runtime_id": request.runtime_id},
    )

    facade_input = captured["facade_input"]
    assert isinstance(summary, ControlledExecutionRuntimeSummarySchema)
    assert isinstance(facade_input, ControlledRunFacadeInput)
    assert facade_input.config_root == Path("config/test")
    assert facade_input.runtime_id == "runtime-controlled-execution"
    assert facade_input.input_payload == {"input_summary": "已脱敏输入"}
    assert summary.status == "success"
    assert summary.execution_performed is True
    assert summary.final_preflight == {"status": "allowed"}
    assert "entry_runner" in captured["kwargs"]


def test_runtime_summary_preserves_cli_runtime_mapping() -> None:
    facade_result = ControlledRunFacadeResult(
        runtime_id="runtime-summary",
        invocation_id="request-summary",
        workflow_id="workflow-summary",
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
        llm_invocation_call_allowed=True,
        llm_invocation_call_attempted=True,
        llm_invocation_runtime_call_performed=True,
        llm_invocation_result_ref="llm-result://summary",
        llm_invocation_observation_ref="llm-observation://summary",
        llm_invocation_summary_ref="llm-summary://summary",
        sanitized_response_display="脱敏展示文本",
        sanitized_response_preview="脱敏预览文本",
        sanitized_evidence_ref="evidence://summary",
        audit_ref="audit://summary",
        governance_summary_payload_ref="governance://payload-summary",
        governance_summary_output_ref="governance://output-summary",
        tool_evidence_ref="tool-evidence://summary",
        tool_run_ref="tool-run://summary",
        tool_runtime_call_performed=True,
        tool_status="success",
        observability_source="runtime_container",
        final_preflight={"allowed": True},
        controlled_live_llm_preflight={"allowed": True},
        lifecycle_facts={"phase": "completed"},
        run_config_service_bundle_facts={"profile": "local"},
        warnings=("warn",),
    )

    summary = ControlledExecutionRuntimeSummarySchema.model_validate(
        facade_result.to_mapping()
    )

    assert summary.to_runtime_mapping() == facade_result.to_mapping()


def test_controlled_execution_service_conforms_to_runtime_service_contract(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_controlled_run_facade(
        facade_input: ControlledRunFacadeInput,
        **kwargs: Any,
    ) -> ControlledRunFacadeResult:
        captured["facade_input"] = facade_input
        captured["kwargs"] = kwargs
        return ControlledRunFacadeResult(
            runtime_id=facade_input.runtime_id,
            invocation_id=facade_input.invocation_id,
            workflow_id=facade_input.workflow_id,
            execution_mode="contract_conformance",
            status="success",
            controlled_run=True,
            productized_controlled_run=True,
            execution_performed=True,
            sanitized_evidence_ref="evidence://contract-conformance",
            final_preflight={"status": "allowed"},
        )

    monkeypatch.setattr(
        service_module,
        "run_controlled_run_facade",
        fake_run_controlled_run_facade,
    )

    service: ControlledExecutionRuntimeService = run_controlled_execution_service
    summary = service(
        ControlledExecutionRequestSchema(
            runtime_id="runtime-contract-conformance",
            invocation_id="request-contract-conformance",
            workflow_id="workflow-contract-conformance",
            workflow_name="contract conformance",
            input_payload={"input_summary": "sanitized input"},
            operator_approved=True,
            approval_ref="approval://contract-conformance",
            audit_ref="audit://contract-conformance",
        ),
        config_selection=RuntimeConfigSelectionContext(
            config_root="config/conformance",
            environment="local",
            profile="dev",
            selection_source="contract_conformance_test",
        ),
        live_llm_options=RuntimeLiveLlmInvocationOptionsContext(
            timeout_seconds=13,
        ),
    )

    facade_input = captured["facade_input"]
    assert isinstance(summary, ControlledExecutionRuntimeSummarySchema)
    assert summary.status == "success"
    assert facade_input.config_root == Path("config/conformance")
    assert facade_input.runtime_id == "runtime-contract-conformance"
    assert captured["kwargs"]["workflow_registry"] is None
    assert captured["kwargs"]["llm_invocation_service"] is None
    assert captured["kwargs"]["agent_shell_live_client"] is None
    assert "entry_runner" not in captured["kwargs"]


def test_controlled_execution_service_builds_default_live_llm_service(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_build_live_service(**kwargs: Any) -> str:
        captured["live_service_kwargs"] = kwargs
        return "controlled-live-service"

    def fake_run_controlled_run_facade(
        facade_input: ControlledRunFacadeInput,
        **kwargs: Any,
    ) -> ControlledRunFacadeResult:
        captured["facade_input"] = facade_input
        captured["facade_kwargs"] = kwargs
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
            final_preflight={"status": "allowed"},
        )

    monkeypatch.setattr(
        live_llm_service_module,
        "build_runtime_container_controlled_live_llm_invocation_service",
        fake_build_live_service,
    )
    monkeypatch.setattr(
        service_module,
        "run_controlled_run_facade",
        fake_run_controlled_run_facade,
    )

    summary = run_controlled_execution_service(
        ControlledExecutionRequestSchema(
            runtime_id="runtime-controlled-live-default",
            invocation_id="request-controlled-live-default",
            workflow_id="workflow-controlled-live-default",
            workflow_name="controlled live default",
            input_payload={"input_summary": "已脱敏 live 输入"},
            operator_approved=True,
            approval_ref="approval://controlled-live-default",
            audit_ref="audit://controlled-live-default",
            request_live_llm=True,
            request_ollama=True,
            allow_live_llm=True,
            allow_ollama=True,
            live_llm_approval_ref="approval://live-default",
        ),
        config_selection=RuntimeConfigSelectionContext(
            config_root="config/live",
            environment="local",
            profile="dev",
        ),
        live_llm_options=RuntimeLiveLlmInvocationOptionsContext(
            ollama_api_base="http://127.0.0.1:11434",
            timeout_seconds=11,
            max_tokens=64,
            response_preview_limit=200,
            selection_source="product_gateway.cognition_run",
            metadata={"cli_command": "cognition run"},
        ),
    )

    live_kwargs = captured["live_service_kwargs"]
    assert summary.status == "success"
    assert live_kwargs["config_root"] == "config/live"
    assert live_kwargs["environment"] == "local"
    assert live_kwargs["ollama_api_base"] == "http://127.0.0.1:11434"
    assert live_kwargs["timeout_seconds"] == 11
    assert live_kwargs["max_tokens"] == 64
    assert live_kwargs["response_preview_limit"] == 200
    assert live_kwargs["metadata"]["source"] == "product_gateway.cognition_run"
    assert live_kwargs["metadata"]["cli_command"] == "cognition run"
    assert captured["facade_kwargs"]["llm_invocation_service"] == (
        "controlled-live-service"
    )


def test_controlled_execution_service_input_is_not_public_export() -> None:
    assert "ControlledExecutionServiceInput" not in service_module.__all__
