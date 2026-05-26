from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from adk_adapter import AdkRunConfigOptions, AdkRunnerServiceBundleOptions
from composition.adk_workflow_runner_assembly import (
    AdkWorkflowRunnerAssemblyOptions,
    AdkWorkflowRunnerRuntimeAssembly,
    build_adk_workflow_runner_runtime,
)
from composition.runtime import RuntimeCompositionOptions
from google.adk.models.lite_llm import LiteLLMClient
from contract_core.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from contract_core.model_routing import ModelRouteFacts
from contract_core.runtime import (
    InvocationRef,
    RuntimeInput,
    RuntimeProductizationGateConfigView,
    RuntimeStatus,
    WorkflowRef,
)
from runtime_container.controlled_adk_run_entry import (
    ControlledAdkRunRequest,
    OperatorApprovalFacts,
    evaluate_controlled_adk_run_final_preflight,
    evaluate_controlled_live_adk_run_final_preflight,
    evaluate_controlled_live_llm_preflight,
    run_productized_controlled_adk_run,
)


class NoLiveGovernedLlmInvocationService:
    def __init__(self) -> None:
        self.requests: list[LlmInvocationRequest] = []

    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        self.requests.append(request)
        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=request.route_facts,
            governance_precondition=request.governance_precondition,
            call_attempted=False,
            call_allowed=True,
            runtime_call_performed=False,
            success=False,
            response_non_empty=False,
            failure_type=LlmInvocationFailureType.LIVE_DISABLED,
            error_message_sanitized="live invocation remains disabled",
            metadata={"source": "test_controlled_adk_run_entry"},
        )


class FakeLiveGovernedLlmInvocationService:
    def __init__(self) -> None:
        self.requests: list[LlmInvocationRequest] = []

    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        self.requests.append(request)
        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=request.route_facts,
            governance_precondition=request.governance_precondition,
            call_attempted=True,
            call_allowed=True,
            runtime_call_performed=True,
            success=True,
            response_non_empty=True,
            sanitized_response_length=len("controlled live response"),
            sanitized_response_preview="controlled live response",
            failure_type=None,
            metadata={
                "source": "test_controlled_live_entry",
                "llm_live_profile": {
                    "controlled_live": True,
                    "live_options_source": (
                        "config_contexts.runtime.RuntimeLiveLlmConfigView"
                    ),
                    "live_service_profile": "adk_litellm_ollama",
                    "configured_model_name": "ollama/gemma4-pro:latest",
                    "timeout_seconds": 45,
                    "temperature": 0,
                    "max_tokens": 64,
                    "local_no_proxy_applied": True,
                },
            },
        )


REPO_ROOT = Path(__file__).resolve().parents[3]
ENTRY_SOURCE = (
    REPO_ROOT
    / "packages"
    / "runtime_container"
    / "src"
    / "runtime_container"
    / "controlled_adk_run_entry.py"
)


class FakeAgentShellLiveClient(LiteLLMClient):
    def __init__(self, content: str = "controlled live Agent shell response") -> None:
        self._content = content
        self.calls: list[dict[str, object]] = []

    async def acompletion(self, *, model: str, messages, tools, **kwargs):
        from litellm import ModelResponse

        self.calls.append(
            {
                "model": model,
                "message_count": len(messages),
                "tools": tools,
                **kwargs,
            }
        )
        return ModelResponse(
            model=model,
            choices=[
                {
                    "finish_reason": "stop",
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": self._content,
                    },
                }
            ],
        )


class FailingAgentShellLiveClient(LiteLLMClient):
    async def acompletion(self, *, model: str, messages, tools, **kwargs):
        raise RuntimeError("provider unavailable: raw_response carried secret token")


def test_final_preflight_blocks_missing_operator_approval() -> None:
    preflight = evaluate_controlled_adk_run_final_preflight(
        productization_gate=_approved_gate(),
        operator_approval=OperatorApprovalFacts(approved=False),
    )

    assert preflight["allowed"] is False
    assert "operator_approval_not_true" in preflight["blocking_reasons"]
    assert "operator_approval_ref_missing" in preflight["blocking_reasons"]
    assert preflight["productization_gating"]["adk_run_allowed"] is True
    assert preflight["productization_gating"]["adk_run_performed"] is False
    assert preflight["productization_gating"]["execution_performed"] is False


def test_controlled_live_llm_preflight_requires_explicit_live_approval() -> None:
    preflight = evaluate_controlled_live_llm_preflight(
        productization_gate=_approved_gate(),
        operator_approval=OperatorApprovalFacts(
            approved=True,
            approval_ref="approval://ce-179-no-live",
            audit_ref="audit://ce-166-productized-controlled-run",
            request_adk_run=True,
            allow_adk_run=True,
        ),
    )

    assert preflight["allowed"] is False
    assert preflight["runtime_call_performed"] is False
    assert preflight["live_llm_call_performed"] is False
    assert preflight["ollama_call_performed"] is False
    assert preflight["degrade_to_no_live"] is True
    assert "live_llm_allowed_not_true" in preflight["blocking_reasons"]
    assert "ollama_allowed_not_true" in preflight["blocking_reasons"]
    assert "operator_approval_allow_live_llm_not_true" in preflight[
        "blocking_reasons"
    ]
    assert "operator_approval_live_llm_ref_missing" in preflight[
        "blocking_reasons"
    ]
    assert preflight["route_facts"]["provider"] == "litellm"
    assert preflight["route_facts"]["backend_provider"] == "ollama"


def test_controlled_live_llm_preflight_can_be_allowed_without_calling_model() -> None:
    preflight = evaluate_controlled_live_llm_preflight(
        productization_gate=_controlled_live_gate(),
        operator_approval=OperatorApprovalFacts(
            approved=True,
            approval_ref="approval://ce-179-controlled-live",
            approved_by="operator://ce-179-test",
            audit_ref="audit://ce-179-controlled-live",
            request_adk_run=True,
            allow_adk_run=True,
            allow_live_llm=True,
            allow_ollama=True,
            live_llm_approval_ref="approval://ce-179-live-llm",
            does_not_trigger_live_llm=False,
        ),
    )

    assert preflight["allowed"] is True
    assert preflight["blocking_reasons"] == []
    assert preflight["runtime_call_performed"] is False
    assert preflight["live_llm_call_performed"] is False
    assert preflight["ollama_call_performed"] is False
    assert preflight["degrade_to_no_live"] is False
    assert preflight["productization_gating"]["live_llm_allowed"] is True
    assert preflight["operator_approval"]["allow_live_llm"] is True
    assert preflight["operator_approval"]["does_not_trigger_live_llm"] is False


def test_controlled_live_final_preflight_can_be_allowed_without_calling_model() -> None:
    preflight = evaluate_controlled_live_adk_run_final_preflight(
        productization_gate=_controlled_live_gate(),
        operator_approval=_controlled_live_approval(),
        runtime_assembly_metadata={
            "assembly": "composition.adk_workflow_runner_assembly",
            "service_bundle": {"source": "in_memory"},
        },
    )

    assert preflight["allowed"] is True
    assert preflight["execution_scope"] == "productized_controlled_live_adk_run"
    assert preflight["controlled_live_llm_preflight"]["allowed"] is True
    assert preflight["runtime_call_performed"] is False
    assert preflight["live_llm_call_performed"] is False
    assert preflight["ollama_call_performed"] is False
    assert preflight["degrade_to_no_live"] is False
    assert "service_bundle_source_in_memory" in preflight["warnings"]


def test_productized_entry_blocks_without_calling_runtime() -> None:
    class BlockingRuntimeRunner:
        def run(self, runtime_input: RuntimeInput) -> None:
            raise AssertionError("runtime must not run when final preflight blocks")

    class BlockingAssembly:
        runtime_runner = BlockingRuntimeRunner()
        metadata = {
            "assembly": "composition.adk_workflow_runner_assembly",
            "service_bundle": {"source": "in_memory"},
        }

    result = run_productized_controlled_adk_run(
        ControlledAdkRunRequest(
            runtime_assembly=BlockingAssembly(),  # type: ignore[arg-type]
            runtime_input=_runtime_input(),
            productization_gate=_approved_gate(),
            operator_approval=OperatorApprovalFacts(approved=False),
        )
    )

    assert result["execution_mode"] == "productized_controlled_adk_run"
    assert result["productized_controlled_run"] is True
    assert result["dev_only"] is False
    assert result["adk_run_allowed"] is False
    assert result["adk_run_performed"] is False
    assert result["execution_performed"] is False
    assert result["live_llm_call_performed"] is False
    assert result["governance_summary_payload"] is None
    assert result["llm_invocation_readonly_facts"] is None
    assert result["raw_adk_object_included"] is False
    assert result["raw_state_values_included"] is False


def test_productized_entry_runs_allowed_no_live_adk_workflow() -> None:
    assembly = _runtime_assembly()
    llm_service = NoLiveGovernedLlmInvocationService()

    result = run_productized_controlled_adk_run(
        ControlledAdkRunRequest(
            runtime_assembly=assembly,
            runtime_input=_runtime_input(),
            productization_gate=_approved_gate(),
            operator_approval=OperatorApprovalFacts(
                approved=True,
                approval_ref="approval://ce-166-productized-controlled-run",
                approved_by="operator://ce-166-test",
                audit_ref="audit://ce-166-productized-controlled-run",
                request_adk_run=True,
                allow_adk_run=True,
            ),
            evidence_id="runtime-container-controlled-adk-run-166",
            llm_invocation_service=llm_service,
        )
    )

    assert result["adk_run_allowed"] is True
    assert result["adk_run_performed"] is True
    assert result["execution_performed"] is True
    assert result["live_llm_allowed"] is False
    assert result["live_llm_call_performed"] is False
    assert result["ollama_allowed"] is False
    assert result["ollama_call_performed"] is False
    assert result["llm_invocation_result_ref"].startswith(
        "llm-invocation-result://llm-invocation-"
    )
    assert result["llm_invocation_observation_ref"].startswith(
        "llm-call-observation://llm-invocation-"
    )
    assert result["llm_invocation_summary_ref"].startswith(
        "agent-llm-invocation-summary://llm-invocation-"
    )
    assert result["llm_invocation_call_allowed"] is True
    assert result["llm_invocation_call_attempted"] is False
    assert result["llm_invocation_runtime_call_performed"] is False
    assert result["llm_invocation_failure_type"] == "live_disabled"
    assert result["controlled_live_llm_preflight"]["allowed"] is False
    assert result["controlled_live_llm_preflight"]["runtime_call_performed"] is False
    assert (
        result["controlled_live_llm_preflight"]["live_llm_call_performed"] is False
    )
    assert "live_llm_allowed_not_true" in result[
        "controlled_live_llm_preflight"
    ]["blocking_reasons"]
    assert result["llm_invocation_readonly_facts"]["request_id"].startswith(
        "llm-invocation-"
    )
    assert result["llm_invocation_readonly_facts"]["call_allowed"] is True
    assert result["llm_invocation_readonly_facts"]["call_attempted"] is False
    assert (
        result["llm_invocation_readonly_facts"]["runtime_call_performed"] is False
    )
    assert result["llm_invocation_readonly_facts"]["failure_type"] == "live_disabled"
    assert result["llm_invocation_readonly_facts"]["live_profile"] is None
    assert result["llm_invocation_readonly_facts"]["readonly"] is True
    assert result["llm_invocation_readonly_facts"]["candidate_only"] is True
    assert result["llm_invocation_readonly_facts"]["does_not_call_model"] is True
    assert (
        result["llm_invocation_readonly_facts"][
            "does_not_store_raw_provider_response"
        ]
        is True
    )
    assert len(llm_service.requests) == 1
    llm_request = llm_service.requests[0]
    assert isinstance(llm_request.route_facts, ModelRouteFacts)
    assert llm_request.route_facts.provider == "litellm"
    assert llm_request.route_facts.runtime_call_performed is False
    assert llm_request.route_facts.metadata["backend_provider"] == "ollama"
    assert isinstance(llm_request.governance_precondition, LlmGovernancePrecondition)
    assert llm_request.governance_precondition.allowed is True
    assert result["final_preflight"]["allowed"] is True
    assert "service_bundle_source_in_memory" in result["warnings"]
    assert result["runtime_result_summary"]["status"] == RuntimeStatus.SUCCESS.value
    assert result["runtime_result_summary"]["event_count"] >= 1
    assert result["workflow_result_summary"]["artifact_delta_count"] == 1
    assert result["governance_summary_payload"]["evidence_id"] == (
        "runtime-container-controlled-adk-run-166"
    )
    assert result["governance_summary_payload"]["sanitized"] is True
    assert result["governance_summary_payload"]["summary_generation"][
        "does_not_call_adk_runner"
    ] is True
    assert result["governance_summary_payload"]["productization_gating"][
        "adk_run_performed"
    ] is False
    llm_audit = result["governance_summary_payload"]["llm_invocation_audit"]
    assert llm_audit == {
        "llm_invocation_result_ref": result["llm_invocation_result_ref"],
        "llm_invocation_observation_ref": result["llm_invocation_observation_ref"],
        "llm_invocation_summary_ref": result["llm_invocation_summary_ref"],
        "call_allowed": True,
        "call_attempted": False,
        "runtime_call_performed": False,
        "failure_type": "live_disabled",
        "controlled_live": False,
        "live_llm_call_performed": False,
        "ollama_call_performed": False,
        "live_profile": None,
        "readonly_facts_embedded": False,
        "does_not_store_prompt": True,
        "does_not_store_raw_provider_response": True,
    }
    assert "llm_invocation_readonly_facts" not in llm_audit
    tool_audit = result["governance_summary_payload"]["tool_audit"]
    assert result["tool_evidence_ref"] == tool_audit["tool_evidence_ref"]
    assert result["tool_run_ref"] == tool_audit["tool_run_ref"]
    assert result["tool_status"] == "success"
    assert result["tool_failure_type"] is None
    assert result["tool_runtime_call_performed"] is True
    assert tool_audit["tool_evidence_ref"].startswith(
        "adk-tool-call-evidence://adk-tool-call-evidence-"
    )
    assert tool_audit["tool_run_ref"] == (
        "adk-function-tool-run://function-tool-inv-ce-166-productized-controlled-run"
    )
    assert tool_audit["tool_name"] == "review_task_context"
    assert tool_audit["tool_kind"] == "deterministic_no_live_task_review"
    assert tool_audit["tool_call_allowed"] is True
    assert tool_audit["tool_call_attempted"] is True
    assert tool_audit["tool_runtime_call_performed"] is True
    assert tool_audit["tool_confirmation_required"] is True
    assert tool_audit["tool_confirmation_granted"] is True
    assert tool_audit["adk_tool_confirmation_requested"] is False
    assert tool_audit["tool_approval_ref"] == (
        "approval://ce-166-productized-controlled-run"
    )
    assert tool_audit["tool_confirmation_decision_source"] == (
        "runtime_container.operator_approval"
    )
    assert tool_audit["tool_failure_type"] is None
    assert tool_audit["readonly_facts_embedded"] is False
    assert tool_audit["does_not_store_raw_tool_input"] is True
    assert tool_audit["does_not_store_raw_tool_output"] is True
    assert tool_audit["raw_adk_object_included"] is False
    assert "raw_tool_input" not in tool_audit
    assert "raw_tool_output" not in tool_audit
    assert "tool_input" not in tool_audit
    assert "tool_output" not in tool_audit
    assert tool_audit["tool_input_summary"]["argument_keys"] == [
        "evidence_ref",
        "task_kind",
        "task_ref",
    ]
    assert tool_audit["tool_output_summary"]["result_kind"] == (
        "deterministic_no_live_task_review"
    )
    agent_shell_audit = result["governance_summary_payload"]["agent_shell_audit"]
    assert agent_shell_audit["agent_shell_evidence_ref"].startswith(
        "adk-agent-shell-evidence://adk-agent-shell-evidence-"
    )
    assert agent_shell_audit["agent_shell_run_ref"] == (
        "adk-agent-shell-run://agent-shell-inv-ce-166-productized-controlled-run"
    )
    assert agent_shell_audit["agent_name"] == "cognition_agent_shell"
    assert agent_shell_audit["agent_type"] == "LlmAgent"
    assert agent_shell_audit["app_name"] == "cognition_agent_shell_product_entry"
    assert agent_shell_audit["requested_invocation_id"] == (
        "agent-shell-inv-ce-166-productized-controlled-run"
    )
    assert agent_shell_audit["adk_invocation_id"]
    assert agent_shell_audit["adk_invocation_id"] != (
        agent_shell_audit["requested_invocation_id"]
    )
    assert agent_shell_audit["status"] == "success"
    assert agent_shell_audit["event_count"] >= 2
    assert agent_shell_audit["no_live_execution_observed"] is True
    assert agent_shell_audit["runtime_call_performed"] is True
    assert agent_shell_audit["failure_type"] is None
    assert agent_shell_audit["readonly_facts_embedded"] is False
    assert agent_shell_audit["does_not_store_prompt"] is True
    assert agent_shell_audit["does_not_store_raw_response"] is True
    assert agent_shell_audit["raw_adk_object_included"] is False
    assert agent_shell_audit["raw_adk_event_included"] is False
    assert agent_shell_audit["raw_adk_session_included"] is False
    assert "prompt" not in agent_shell_audit
    assert "messages" not in agent_shell_audit
    assert "response_text" not in agent_shell_audit
    assert "recorded_run" not in result
    assert result["lifecycle_facts"]["context_state"][
        "raw_state_values_included"
    ] is False
    assert result["run_config_service_bundle_facts"]["service_bundle"][
        "external_persistence_enabled"
    ] is False
    assert result["run_config_service_bundle_facts"]["run_config"][
        "live_call_enabled"
    ] is False
    assert result["raw_adk_object_included"] is False
    assert result["artifact_content_included"] is False


def test_productized_entry_maps_missing_tool_confirmation_without_tool_runtime() -> None:
    assembly = _runtime_assembly()
    llm_service = NoLiveGovernedLlmInvocationService()

    result = run_productized_controlled_adk_run(
        ControlledAdkRunRequest(
            runtime_assembly=assembly,
            runtime_input=_runtime_input(),
            productization_gate=_approved_gate(),
            operator_approval=OperatorApprovalFacts(
                approved=True,
                approval_ref="approval://ce-214-product-run",
                approved_by="operator://ce-214-test",
                audit_ref="audit://ce-166-productized-controlled-run",
                request_adk_run=True,
                allow_adk_run=True,
                tool_confirmation_approval_ref="approval://ce-214-tool",
                tool_confirmation_decision_source="test.operator_approval",
            ),
            evidence_id="runtime-container-tool-confirmation-214",
            llm_invocation_service=llm_service,
        )
    )

    tool_audit = result["governance_summary_payload"]["tool_audit"]

    assert result["adk_run_performed"] is True
    assert result["execution_performed"] is True
    assert result["tool_status"] == "failed"
    assert result["tool_failure_type"] == "tool_confirmation_required"
    assert result["tool_runtime_call_performed"] is False
    assert tool_audit["tool_confirmation_required"] is True
    assert tool_audit["tool_confirmation_granted"] is False
    assert tool_audit["adk_tool_confirmation_requested"] is True
    assert tool_audit["tool_runtime_call_performed"] is False
    assert tool_audit["tool_approval_ref"] == "approval://ce-214-tool"
    assert tool_audit["tool_confirmation_decision_source"] == (
        "test.operator_approval"
    )
    assert "raw_tool_input" not in tool_audit
    assert "raw_tool_output" not in tool_audit


def test_productized_entry_runs_controlled_live_with_injected_service() -> None:
    assembly = _runtime_assembly()
    llm_service = FakeLiveGovernedLlmInvocationService()
    agent_shell_client = FakeAgentShellLiveClient()

    result = run_productized_controlled_adk_run(
        ControlledAdkRunRequest(
            runtime_assembly=assembly,
            runtime_input=_runtime_input(),
            productization_gate=_controlled_live_gate(),
            operator_approval=_controlled_live_approval(),
            evidence_id="runtime-container-controlled-live-182",
            llm_invocation_service=llm_service,
            agent_shell_live_client=agent_shell_client,
        )
    )

    assert result["adk_run_allowed"] is True
    assert result["adk_run_performed"] is True
    assert result["execution_performed"] is True
    assert result["live_llm_allowed"] is True
    assert result["live_llm_call_performed"] is True
    assert result["ollama_allowed"] is True
    assert result["ollama_call_performed"] is True
    assert result["summary"]["does_not_call_live_llm"] is False
    assert result["summary"]["does_not_call_ollama"] is False
    assert result["controlled_live_llm_preflight"]["allowed"] is True
    assert result["final_preflight"]["allowed"] is True
    assert result["final_preflight"]["execution_scope"] == (
        "productized_controlled_live_adk_run"
    )
    assert result["llm_invocation_call_allowed"] is True
    assert result["llm_invocation_call_attempted"] is True
    assert result["llm_invocation_runtime_call_performed"] is True
    assert result["llm_invocation_failure_type"] is None
    assert result["tool_evidence_ref"].startswith(
        "adk-tool-call-evidence://adk-tool-call-evidence-"
    )
    assert result["tool_run_ref"] == (
        "adk-function-tool-run://function-tool-inv-ce-166-productized-controlled-run"
    )
    assert result["tool_status"] == "success"
    assert result["tool_runtime_call_performed"] is True
    assert result["llm_invocation_readonly_facts"]["call_attempted"] is True
    assert result["llm_invocation_readonly_facts"]["runtime_call_performed"] is True
    assert result["llm_invocation_readonly_facts"]["failure_type"] is None
    assert result["llm_invocation_readonly_facts"]["sanitized_response_length"] == (
        len("controlled live response")
    )
    assert result["llm_invocation_readonly_facts"]["sanitized_response_preview"] == (
        "controlled live response"
    )
    assert result["llm_invocation_readonly_facts"]["live_profile"] == {
        "controlled_live": True,
        "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
        "live_service_profile": "adk_litellm_ollama",
        "configured_model_name": "ollama/gemma4-pro:latest",
        "timeout_seconds": 45,
        "temperature": 0,
        "max_tokens": 64,
        "local_no_proxy_applied": True,
    }
    llm_audit = result["governance_summary_payload"]["llm_invocation_audit"]
    assert llm_audit["llm_invocation_result_ref"] == (
        result["llm_invocation_result_ref"]
    )
    assert llm_audit["llm_invocation_observation_ref"] == (
        result["llm_invocation_observation_ref"]
    )
    assert llm_audit["llm_invocation_summary_ref"] == (
        result["llm_invocation_summary_ref"]
    )
    assert llm_audit["call_allowed"] is True
    assert llm_audit["call_attempted"] is True
    assert llm_audit["runtime_call_performed"] is True
    assert llm_audit["failure_type"] is None
    assert llm_audit["controlled_live"] is True
    assert llm_audit["live_llm_call_performed"] is True
    assert llm_audit["ollama_call_performed"] is True
    assert llm_audit["live_profile"] == (
        result["llm_invocation_readonly_facts"]["live_profile"]
    )
    assert llm_audit["readonly_facts_embedded"] is False
    assert "llm_invocation_readonly_facts" not in llm_audit
    agent_shell_audit = result["governance_summary_payload"]["agent_shell_audit"]
    assert agent_shell_audit["agent_shell_evidence_ref"].startswith(
        "adk-agent-shell-evidence://adk-agent-shell-evidence-"
    )
    assert agent_shell_audit["agent_shell_run_ref"] == (
        "adk-agent-shell-run://agent-shell-live-"
        "inv-ce-166-productized-controlled-run"
    )
    assert agent_shell_audit["status"] == "success"
    assert agent_shell_audit["event_count"] >= 2
    assert agent_shell_audit["no_live_execution_observed"] is False
    assert agent_shell_audit["runtime_call_performed"] is True
    assert agent_shell_audit["call_attempted"] is True
    assert agent_shell_audit["controlled_live"] is True
    assert agent_shell_audit["controlled_live_smoke"] is True
    assert agent_shell_audit["controlled_live_smoke_enabled"] is True
    assert agent_shell_audit["failure_type"] is None
    assert agent_shell_audit["live_profile"] == {
        "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
        "live_service_profile": "adk_litellm_ollama",
        "configured_model_name": "ollama/gemma4-pro:latest",
        "ollama_api_base": "http://127.0.0.1:11434",
        "timeout_seconds": 45,
        "temperature": 0,
        "max_tokens": 64,
        "enabled_by_default": False,
    }
    assert agent_shell_audit["does_not_store_prompt"] is True
    assert agent_shell_audit["does_not_store_raw_response"] is True
    assert agent_shell_audit["raw_adk_object_included"] is False
    assert agent_shell_audit["raw_adk_event_included"] is False
    assert agent_shell_audit["raw_adk_session_included"] is False
    assert "prompt" not in agent_shell_audit
    assert "messages" not in agent_shell_audit
    assert "response_text" not in agent_shell_audit
    assert agent_shell_client.calls
    assert agent_shell_client.calls[0]["model"] == "ollama/gemma4-pro:latest"
    assert agent_shell_client.calls[0]["api_base"] == "http://127.0.0.1:11434"
    assert len(llm_service.requests) == 1
    llm_request = llm_service.requests[0]
    assert llm_request.governance_precondition.decision == "continue_controlled_live"
    assert llm_request.governance_precondition.metadata["controlled_live_gate"] is True
    assert llm_request.metadata["controlled_live"] is True
    assert llm_request.metadata["live_llm_allowed"] is True
    assert llm_request.metadata["ollama_allowed"] is True
    assert "recorded_run" not in result
    assert result["raw_adk_object_included"] is False
    assert result["artifact_content_included"] is False


def test_productized_live_entry_uses_sanitized_message_prompt_preview() -> None:
    assembly = _runtime_assembly()
    llm_service = FakeLiveGovernedLlmInvocationService()
    agent_shell_client = FakeAgentShellLiveClient()

    run_productized_controlled_adk_run(
        ControlledAdkRunRequest(
            runtime_assembly=assembly,
            runtime_input=_runtime_input(
                input_payload={
                    "case_id": "ce-186",
                    "message": "  请只回复：你好\n\n不要输出其它内容  ",
                }
            ),
            productization_gate=_controlled_live_gate(),
            operator_approval=_controlled_live_approval(),
            evidence_id="runtime-container-controlled-live-186",
            llm_invocation_service=llm_service,
            agent_shell_live_client=agent_shell_client,
        )
    )

    llm_request = llm_service.requests[0]

    assert llm_request.prompt_ref == (
        "input-payload-ref://runtime-ce-166-productized-controlled-run"
    )
    assert llm_request.prompt_preview_sanitized == "请只回复：你好 不要输出其它内容"
    assert "message" not in llm_request.metadata
    assert "prompt" not in llm_request.metadata
    assert agent_shell_client.calls


def test_productized_live_entry_uses_input_summary_prompt_preview() -> None:
    assembly = _runtime_assembly()
    llm_service = FakeLiveGovernedLlmInvocationService()
    agent_shell_client = FakeAgentShellLiveClient()

    run_productized_controlled_adk_run(
        ControlledAdkRunRequest(
            runtime_assembly=assembly,
            runtime_input=_runtime_input(
                input_payload={
                    "input_summary": "  心情不好\n\n能聊聊吗  ",
                    "chat_session_id": "cli-chat-test",
                    "turn_index": 2,
                }
            ),
            productization_gate=_controlled_live_gate(),
            operator_approval=_controlled_live_approval(),
            evidence_id="runtime-container-controlled-live-input-summary",
            llm_invocation_service=llm_service,
            agent_shell_live_client=agent_shell_client,
        )
    )

    llm_request = llm_service.requests[0]

    assert llm_request.prompt_preview_sanitized == "心情不好 能聊聊吗"
    assert llm_request.metadata["interaction_mode"] == "cli_chat"
    assert llm_request.metadata["cli_chat_context"] == {
        "current_user_input": "心情不好 能聊聊吗",
        "history": [],
    }
    assert "input_summary" not in llm_request.metadata
    assert agent_shell_client.calls


def test_productized_live_entry_includes_cli_chat_history_in_prompt_preview() -> None:
    assembly = _runtime_assembly()
    llm_service = FakeLiveGovernedLlmInvocationService()
    agent_shell_client = FakeAgentShellLiveClient()

    run_productized_controlled_adk_run(
        ControlledAdkRunRequest(
            runtime_assembly=assembly,
            runtime_input=_runtime_input(
                input_payload={
                    "input_summary": "能详细解释下这个电影吗",
                    "chat_session_id": "cli-chat-test",
                    "turn_index": 3,
                    "turn_history_summary": [
                        {
                            "user": "电影，有什么电影推荐",
                            "assistant": "推荐了《爱在黎明破晓前》。",
                        }
                    ],
                }
            ),
            productization_gate=_controlled_live_gate(),
            operator_approval=_controlled_live_approval(),
            evidence_id="runtime-container-controlled-live-chat-history",
            llm_invocation_service=llm_service,
            agent_shell_live_client=agent_shell_client,
        )
    )

    llm_request = llm_service.requests[0]

    assert llm_request.prompt_preview_sanitized == "能详细解释下这个电影吗"
    assert llm_request.metadata["interaction_mode"] == "cli_chat"
    assert llm_request.metadata["cli_chat_context"] == {
        "current_user_input": "能详细解释下这个电影吗",
        "history": [
            {
                "user": "电影，有什么电影推荐",
                "assistant": "推荐了《爱在黎明破晓前》。",
            }
        ],
    }
    assert "turn_history_summary" not in llm_request.metadata
    assert agent_shell_client.calls


def test_productized_live_entry_classifies_agent_shell_provider_failure() -> None:
    assembly = _runtime_assembly()
    llm_service = FakeLiveGovernedLlmInvocationService()

    result = run_productized_controlled_adk_run(
        ControlledAdkRunRequest(
            runtime_assembly=assembly,
            runtime_input=_runtime_input(),
            productization_gate=_controlled_live_gate(),
            operator_approval=_controlled_live_approval(),
            evidence_id="runtime-container-controlled-live-205",
            llm_invocation_service=llm_service,
            agent_shell_live_client=FailingAgentShellLiveClient(),
        )
    )

    agent_shell_audit = result["governance_summary_payload"]["agent_shell_audit"]

    assert result["adk_run_performed"] is True
    assert result["live_llm_call_performed"] is True
    assert agent_shell_audit["status"] == "failure"
    assert agent_shell_audit["runtime_call_performed"] is True
    assert agent_shell_audit["call_attempted"] is True
    assert agent_shell_audit["failure_type"] == "provider_unavailable"
    assert agent_shell_audit["controlled_live_smoke_enabled"] is True
    assert "raw_response" not in (agent_shell_audit["error_message_sanitized"] or "")
    assert "secret" not in (agent_shell_audit["error_message_sanitized"] or "")
    assert "token" not in (agent_shell_audit["error_message_sanitized"] or "")


def test_productized_live_entry_prompt_preview_fallback_and_truncation() -> None:
    assembly = _runtime_assembly()
    llm_service = FakeLiveGovernedLlmInvocationService()
    agent_shell_client = FakeAgentShellLiveClient()
    long_task = "任务-" + ("非常长" * 40)

    run_productized_controlled_adk_run(
        ControlledAdkRunRequest(
            runtime_assembly=assembly,
            runtime_input=_runtime_input(
                input_payload={
                    "message": 123,
                    "instruction": "   ",
                    "task": long_task,
                    "prompt": "should not win",
                }
            ),
            productization_gate=_controlled_live_gate(),
            operator_approval=_controlled_live_approval(),
            evidence_id="runtime-container-controlled-live-186",
            llm_invocation_service=llm_service,
            agent_shell_live_client=agent_shell_client,
        )
    )

    llm_request = llm_service.requests[0]

    assert llm_request.prompt_preview_sanitized == long_task[:80]
    assert len(llm_request.prompt_preview_sanitized) == 80
    assert agent_shell_client.calls


def test_productized_entry_prompt_preview_uses_default_for_empty_payload() -> None:
    assembly = _runtime_assembly()
    llm_service = NoLiveGovernedLlmInvocationService()

    run_productized_controlled_adk_run(
        ControlledAdkRunRequest(
            runtime_assembly=assembly,
            runtime_input=_runtime_input(input_payload={}),
            productization_gate=_approved_gate(),
            operator_approval=OperatorApprovalFacts(
                approved=True,
                approval_ref="approval://ce-166-productized-controlled-run",
                approved_by="operator://ce-166-test",
                audit_ref="audit://ce-166-productized-controlled-run",
                request_adk_run=True,
                allow_adk_run=True,
            ),
            evidence_id="runtime-container-no-live-186",
            llm_invocation_service=llm_service,
        )
    )

    llm_request = llm_service.requests[0]

    assert llm_request.prompt_preview_sanitized == "cognition run product input"


def test_productized_live_entry_blocks_without_calling_runtime_or_live_service() -> None:
    class BlockingRuntimeRunner:
        def run(self, runtime_input: RuntimeInput) -> None:
            raise AssertionError("runtime must not run when live preflight blocks")

    class BlockingAssembly:
        runtime_runner = BlockingRuntimeRunner()
        metadata = {
            "assembly": "composition.adk_workflow_runner_assembly",
            "service_bundle": {"source": "in_memory"},
        }

    llm_service = FakeLiveGovernedLlmInvocationService()
    result = run_productized_controlled_adk_run(
        ControlledAdkRunRequest(
            runtime_assembly=BlockingAssembly(),  # type: ignore[arg-type]
            runtime_input=_runtime_input(),
            productization_gate=_controlled_live_gate(),
            operator_approval=OperatorApprovalFacts(
                approved=True,
                approval_ref="approval://ce-182-controlled-live",
                audit_ref="audit://ce-179-controlled-live",
                request_adk_run=True,
                allow_adk_run=True,
                allow_live_llm=True,
                allow_ollama=True,
                live_llm_approval_ref=None,
                does_not_trigger_live_llm=False,
            ),
            llm_invocation_service=llm_service,
        )
    )

    assert result["adk_run_performed"] is False
    assert result["execution_performed"] is False
    assert result["live_llm_call_performed"] is False
    assert result["ollama_call_performed"] is False
    assert result["llm_invocation_call_attempted"] is False
    assert "controlled_live_llm_preflight_not_allowed" in result[
        "blocking_reasons"
    ]
    assert "operator_approval_live_llm_ref_missing" in result["blocking_reasons"]
    assert llm_service.requests == []


def test_controlled_adk_run_entry_keeps_product_boundary() -> None:
    source = ENTRY_SOURCE.read_text(encoding="utf-8")

    assert "scripts." not in source
    assert "dev_controlled_run_executor" not in source
    assert "dev_governance_summary_no_live_productization" not in source
    assert "google.adk" not in source
    assert "adk_adapter" not in source
    assert "completion(" not in source
    assert "acompletion(" not in source
    assert not re.search(r"^\s*(?:from|import)\s+observability_hub\b", source, re.M)
    assert not re.search(r"^\s*(?:from|import)\s+cognition_agent\b", source, re.M)
    assert "runner.run_async" not in source
    assert "live_enabled=True" not in source
    assert "external_persistence_enabled=True" not in source


def _approved_gate() -> RuntimeProductizationGateConfigView:
    return RuntimeProductizationGateConfigView(
        gate_id="gate-ce-166-productized-controlled-run",
        request_adk_run=True,
        request_live_llm=False,
        request_ollama=False,
        allow_adk_run=True,
        allow_live_llm=False,
        allow_ollama=False,
        explicit_operator_approval=True,
        sanitized_evidence_ref="evidence-bundle://ce-166-productized-controlled-run",
        governance_summary_output_ref="artifact://ce-166-governance-summary",
        audit_ref="audit://ce-166-productized-controlled-run",
        reason="first productized controlled ADK run entry",
    )


def _controlled_live_gate() -> RuntimeProductizationGateConfigView:
    return RuntimeProductizationGateConfigView(
        gate_id="gate-ce-179-controlled-live",
        request_adk_run=True,
        request_live_llm=True,
        request_ollama=True,
        allow_adk_run=True,
        allow_live_llm=True,
        allow_ollama=True,
        explicit_operator_approval=True,
        sanitized_evidence_ref="evidence-bundle://ce-179-controlled-live",
        governance_summary_output_ref="artifact://ce-179-governance-summary",
        audit_ref="audit://ce-179-controlled-live",
        reason="controlled-live preflight only",
    )


def _controlled_live_approval() -> OperatorApprovalFacts:
    return OperatorApprovalFacts(
        approved=True,
        approval_ref="approval://ce-182-controlled-live",
        approved_by="operator://ce-182-test",
        audit_ref="audit://ce-179-controlled-live",
        request_adk_run=True,
        allow_adk_run=True,
        allow_live_llm=True,
        allow_ollama=True,
        live_llm_approval_ref="approval://ce-182-live-llm",
        does_not_trigger_live_llm=False,
    )


def _runtime_input(
    *,
    input_payload: dict[str, Any] | None = None,
) -> RuntimeInput:
    return RuntimeInput(
        runtime_id="runtime-ce-166-productized-controlled-run",
        workflow_ref=WorkflowRef(
            workflow_id="workflow-ce-166-productized-controlled-run",
            name="ce-166-productized-controlled-run",
        ),
        invocation_ref=InvocationRef(
            invocation_id="inv-ce-166-productized-controlled-run",
            runtime_id="runtime-ce-166-productized-controlled-run",
            workflow_id="workflow-ce-166-productized-controlled-run",
            metadata={
                "audit_ref": "audit://ce-166-productized-controlled-run",
                "evidence_bundle_ref": (
                    "evidence-bundle://ce-166-productized-controlled-run"
                ),
            },
        ),
        input_payload=input_payload or {"case_id": "ce-166"},
        metadata={"entry_source": "runtime_container.controlled_adk_run_entry"},
    )


def _runtime_assembly() -> AdkWorkflowRunnerRuntimeAssembly:
    from google.adk.agents.context import Context
    from google.adk.events import Event
    from google.adk.events.event import NodeInfo
    from google.adk.workflow import START, BaseNode, Workflow
    from google.genai import types

    class ProductizedControlledRunNode(BaseNode):
        async def _run_impl(self, *, ctx: Context, node_input: Any):
            version = await ctx.save_artifact(
                "ce-166-productized-output.txt",
                types.Part(text="ce-166 sanitized artifact body"),
                custom_metadata={"source": "ce-166-productized-controlled-run"},
            )
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                node_info=NodeInfo(path=ctx.node_path),
                output={
                    "artifact_version": version,
                    "max_llm_calls": ctx.run_config.max_llm_calls,
                    "run_config_source": ctx.run_config.custom_metadata["source"],
                },
            )

    workflow = Workflow(
        name="ce_166_productized_controlled_run_workflow",
        edges=[(START, ProductizedControlledRunNode(name="ce_166_product_node"))],
    )
    assembly_options = AdkWorkflowRunnerAssemblyOptions(
        app_name="ce_166_productized_controlled_run",
        user_id="ce-166-product-user",
        workflow_name="ce-166-productized-controlled-run",
        service_bundle_options=AdkRunnerServiceBundleOptions(source="in_memory"),
        run_config_options=AdkRunConfigOptions(
            max_llm_calls=1,
            custom_metadata={"source": "ce-166-productized-controlled-run"},
            streaming_mode="none",
        ),
        metadata={"entry": "runtime_container.controlled_adk_run_entry"},
    )
    return build_adk_workflow_runner_runtime(
        options=RuntimeCompositionOptions(
            config_root=Path("config"),
            environment="local",
        ),
        workflow=workflow,
        assembly_options=assembly_options,
    )
