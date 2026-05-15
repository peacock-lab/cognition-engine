from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognition_agent import (
    GOVERNED_RUN_EVIDENCE_CONTEXT_SOURCE,
    GOVERNED_RUN_EVIDENCE_CONTEXT_VERSION,
    AgentGovernedRunEvidenceContextCandidate,
    build_agent_governance_evidence_summary_view,
    build_agent_governed_run_evidence_context_candidate,
    build_agent_llm_invocation_summary_from_invocation_result,
    build_agent_tool_audit_readonly_view,
)
from schemas.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationResult,
)
from schemas.model_routing import ModelRouteFacts


REPO_ROOT = Path(__file__).resolve().parents[3]
COGNITION_AGENT_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "cognition_agent" / "src" / "cognition_agent"
)


def test_governed_run_evidence_context_combines_controlled_live_readonly_views() -> None:
    context = build_agent_governed_run_evidence_context_candidate(
        candidate_id="agent-governed-run-evidence-context-1",
        governance_summary_view=_governance_summary_view(),
        llm_invocation_summary=_llm_invocation_summary(
            success=True,
            failure_type=None,
            runtime_call_performed=True,
        ),
        llm_invocation_audit=_llm_invocation_audit(controlled_live=True),
        agent_tool_audit_view=build_agent_tool_audit_readonly_view(
            candidate_id="agent-tool-audit-view-1",
            tool_audit=_tool_audit(status="success", failure_type=None),
        ),
    )

    assert isinstance(context, AgentGovernedRunEvidenceContextCandidate)
    assert context.candidate_type == "agent_governed_run_evidence_context_candidate"
    assert context.context_version == GOVERNED_RUN_EVIDENCE_CONTEXT_VERSION
    assert context.source == GOVERNED_RUN_EVIDENCE_CONTEXT_SOURCE
    assert context.governance_summary_candidate_id == "agent-governance-summary-view-1"
    assert context.llm_invocation_summary_candidate_id == "agent-llm-summary-1"
    assert context.llm_invocation_result_ref == (
        "llm-invocation-result://llm-request-agent-1"
    )
    assert context.llm_invocation_call_allowed is True
    assert context.llm_invocation_call_attempted is True
    assert context.llm_invocation_runtime_call_performed is True
    assert context.llm_invocation_failure_type is None
    assert context.controlled_live is True
    assert context.live_llm_call_performed is True
    assert context.ollama_call_performed is True
    assert context.agent_tool_audit_candidate_id == "agent-tool-audit-view-1"
    assert context.tool_evidence_ref == (
        "adk-tool-call-evidence://adk-tool-call-evidence-1"
    )
    assert context.tool_run_ref == "adk-function-tool-run://tool-run-1"
    assert context.tool_name == "review_task_context"
    assert context.tool_kind == "deterministic_no_live_task_review"
    assert context.tool_status == "success"
    assert context.tool_failure_type is None
    assert context.tool_call_allowed is True
    assert context.tool_call_attempted is True
    assert context.tool_runtime_call_performed is True
    assert context.tool_confirmation_required is False
    assert context.tool_confirmation_granted is True
    assert context.adk_tool_confirmation_requested is False
    assert context.tool_approval_ref == "approval://tool-1"
    assert context.tool_confirmation_decision_source == "test.operator_approval"
    assert context.live_profile == {
        "controlled_live": True,
        "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
        "live_service_profile": "adk_litellm_ollama",
        "configured_model_name": "ollama/gemma4-pro:latest",
        "timeout_seconds": 45,
        "temperature": 0,
        "max_tokens": 64,
        "local_no_proxy_applied": True,
    }
    assert context.ready_for_review is True
    assert context.warnings == []
    assert context.readonly is True
    assert context.candidate_only is True
    assert context.execution_enabled is False
    assert context.runtime_permission_granted is False
    assert context.runtime_container_call_enabled is False
    assert context.service_invoke_enabled is False
    assert context.llm_call_enabled is False
    assert context.metadata["review_context_is_execution_permission"] is False
    assert context.metadata["does_not_call_runtime_container"] is True
    assert context.metadata["does_not_call_llm"] is True
    assert context.metadata["agent_tool_audit_candidate_id"] == (
        "agent-tool-audit-view-1"
    )
    assert "adk-tool-call-evidence://adk-tool-call-evidence-1" in (
        context.governance_refs
    )
    assert "adk-function-tool-run://tool-run-1" in context.governance_refs
    assert "approval://tool-1" in context.governance_refs


def test_governed_run_evidence_context_keeps_no_live_as_reviewable_warning() -> None:
    context = build_agent_governed_run_evidence_context_candidate(
        candidate_id="agent-governed-run-evidence-context-no-live-1",
        governance_summary_view=_governance_summary_view(),
        llm_invocation_summary=_llm_invocation_summary(
            success=False,
            failure_type=LlmInvocationFailureType.LIVE_DISABLED,
            runtime_call_performed=False,
        ),
        llm_invocation_audit=_llm_invocation_audit(controlled_live=False),
    )

    assert context.ready_for_review is True
    assert context.controlled_live is False
    assert context.live_profile is None
    assert context.llm_invocation_failure_type == "live_disabled"
    assert "llm_invocation_live_disabled" in context.warnings
    assert "llm_runtime_call_not_performed" in context.warnings
    assert "Review context is not execution permission." in context.summary


def test_governed_run_evidence_context_missing_audit_is_incomplete() -> None:
    context = build_agent_governed_run_evidence_context_candidate(
        candidate_id="agent-governed-run-evidence-context-missing-audit-1",
        governance_summary_view=_governance_summary_view(),
        llm_invocation_summary=_llm_invocation_summary(
            success=False,
            failure_type=LlmInvocationFailureType.LIVE_DISABLED,
            runtime_call_performed=False,
        ),
    )

    assert context.ready_for_review is False
    assert "llm_invocation_audit_missing" in context.warnings
    assert context.llm_invocation_result_ref is None


def test_governed_run_evidence_context_rejects_raw_audit_payloads() -> None:
    with pytest.raises(ValueError):
        build_agent_governed_run_evidence_context_candidate(
            candidate_id="agent-governed-run-evidence-context-raw-1",
            governance_summary_view=_governance_summary_view(),
            llm_invocation_summary=_llm_invocation_summary(
                success=True,
                failure_type=None,
                runtime_call_performed=True,
            ),
            llm_invocation_audit={
                **_llm_invocation_audit(controlled_live=True),
                "response_text": "raw provider output",
            },
        )


def test_governed_run_evidence_context_rejects_execution_flags() -> None:
    with pytest.raises(ValidationError):
        AgentGovernedRunEvidenceContextCandidate(
            candidate_id="agent-governed-run-evidence-context-invalid-1",
            source=GOVERNED_RUN_EVIDENCE_CONTEXT_SOURCE,
            summary="Invalid governed run evidence context.",
            governance_summary_candidate_id="agent-governance-summary-view-1",
            execution_enabled=True,
        )


def test_governed_run_evidence_context_source_has_no_execution_dependencies() -> None:
    source = (
        COGNITION_AGENT_SOURCE_ROOT / "governed_run_evidence_context_view.py"
    ).read_text(encoding="utf-8")
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:adk_adapter|litellm|google\.adk|runtime_container|runtime|"
        r"observability_hub|composition)\b",
        re.MULTILINE,
    )
    forbidden_calls = re.compile(
        r"\b(?:completion|acompletion|service\.invoke|runner\.run|run_async)\s*\("
    )

    assert forbidden_imports.search(source) is None
    assert forbidden_calls.search(source) is None
    assert "live_enabled=True" not in source
    assert "ready_for_runtime" not in source
    assert "runtime_permission_granted=True" not in source
    assert "ToolExecutor" not in source
    assert "Chat" not in source
    assert "Gateway" not in source


def _governance_summary_view():
    return build_agent_governance_evidence_summary_view(
        candidate_id="agent-governance-summary-view-1",
        governance_evidence_metadata={
            "lifecycle_summary": {
                "summary_id": "adk-lifecycle-summary-agent-1",
                "runtime_id": "runtime-agent-1",
                "workflow_id": "workflow-agent-1",
                "workflow_name": "agent-workflow",
                "status": "success",
                "session": {"session_id": "session-agent-1", "event_count": 2},
                "events": {"event_count": 2, "event_types": ["node_completed"]},
                "context_state": {
                    "state_delta_count": 0,
                    "state_delta_entity_mode": "event_payload_summary_only",
                },
                "metadata": {"sanitized": True},
            },
            "run_config_service_bundle_summary": {
                "summary_id": "adk-run-config-service-bundle-summary-agent-1",
                "runtime_id": "runtime-agent-1",
                "workflow_id": "workflow-agent-1",
                "workflow_name": "agent-workflow",
                "status": "success",
                "run_config": {
                    "mapped_fields": ["max_llm_calls"],
                    "unmapped_fields": [],
                    "deferred_fields": [],
                    "no_live_mode": True,
                    "call_attempted": False,
                },
                "service_bundle": {
                    "service_bundle_source": "in_memory",
                    "artifact_service_present": True,
                    "session_service_present": True,
                },
                "metadata": {"sanitized": True},
            },
        },
    )


def _llm_invocation_summary(
    *,
    success: bool,
    failure_type: LlmInvocationFailureType | None,
    runtime_call_performed: bool,
):
    return build_agent_llm_invocation_summary_from_invocation_result(
        candidate_id="agent-llm-summary-1",
        invocation_result=LlmInvocationResult(
            request_id="llm-request-agent-1",
            route_facts=ModelRouteFacts(
                model_name="ollama/gemma4-pro:latest",
                provider="litellm",
                source="adk_adapter.models",
                metadata={
                    "backend_provider": "ollama",
                    "route_target": "ollama/gemma4-pro:latest",
                    "route_kind": "adk_litellm",
                },
            ),
            governance_precondition=LlmGovernancePrecondition(
                allowed=True,
                reason="governance_allowed",
                decision="continue_controlled_live" if success else "continue_no_live",
                governance_decision_ref="artifact://governance-summary-agent-1",
            ),
            call_attempted=runtime_call_performed,
            call_allowed=True,
            runtime_call_performed=runtime_call_performed,
            success=success,
            response_non_empty=success,
            sanitized_response_length=2 if success else None,
            sanitized_response_preview="ok" if success else None,
            failure_type=failure_type,
            error_message_sanitized=(
                None if success else (failure_type.value if failure_type else None)
            ),
        ),
    )


def _llm_invocation_audit(*, controlled_live: bool) -> dict[str, object]:
    return {
        "llm_invocation_result_ref": "llm-invocation-result://llm-request-agent-1",
        "llm_invocation_observation_ref": (
            "llm-call-observation://llm-request-agent-1"
        ),
        "llm_invocation_summary_ref": (
            "agent-llm-invocation-summary://llm-request-agent-1"
        ),
        "call_allowed": True,
        "call_attempted": controlled_live,
        "runtime_call_performed": controlled_live,
        "failure_type": None if controlled_live else "live_disabled",
        "controlled_live": controlled_live,
        "live_llm_call_performed": controlled_live,
        "ollama_call_performed": controlled_live,
        "live_profile": (
            {
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
            }
            if controlled_live
            else None
        ),
        "readonly_facts_embedded": False,
        "does_not_store_prompt": True,
        "does_not_store_raw_provider_response": True,
    }


def _tool_audit(
    *,
    status: str,
    failure_type: str | None,
    tool_call_allowed: bool = True,
    tool_call_attempted: bool = True,
    tool_runtime_call_performed: bool = True,
) -> dict[str, object]:
    return {
        "tool_evidence_ref": "adk-tool-call-evidence://adk-tool-call-evidence-1",
        "tool_run_ref": "adk-function-tool-run://tool-run-1",
        "tool_name": "review_task_context",
        "tool_kind": "deterministic_no_live_task_review",
        "status": status,
        "tool_call_allowed": tool_call_allowed,
        "tool_call_attempted": tool_call_attempted,
        "tool_runtime_call_performed": tool_runtime_call_performed,
        "tool_confirmation_required": False,
        "tool_confirmation_granted": True,
        "adk_tool_confirmation_requested": False,
        "tool_approval_ref": "approval://tool-1",
        "tool_confirmation_decision_source": "test.operator_approval",
        "tool_failure_type": failure_type,
        "tool_input_summary": {
            "argument_keys": ["task_ref"],
            "argument_count": 1,
            "input_digest": "abc",
        },
        "tool_output_summary": {
            "result_kind": "deterministic_no_live_task_review",
            "recommendation": "review_ready",
            "output_digest": "def",
        },
        "does_not_store_raw_tool_input": True,
        "does_not_store_raw_tool_output": True,
        "raw_adk_object_included": False,
    }
