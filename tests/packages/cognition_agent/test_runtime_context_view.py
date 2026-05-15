from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognition_agent import (
    READONLY_RUNTIME_CONTEXT_SOURCE,
    READONLY_RUNTIME_CONTEXT_VERSION,
    AgentReadonlyRuntimeContextCandidate,
    build_agent_governance_view_from_precondition_summary,
    build_agent_llm_invocation_summary_from_invocation_result,
    build_agent_readonly_runtime_context_candidate,
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


def test_agent_readonly_runtime_context_aggregates_views_without_execution() -> None:
    context = build_agent_readonly_runtime_context_candidate(
        candidate_id="agent-readonly-runtime-context-1",
        governance_view=_governance_view(allowed=True),
        llm_invocation_summary=_llm_summary(
            failure_type=LlmInvocationFailureType.LIVE_DISABLED,
            call_allowed=True,
            runtime_call_performed=False,
        ),
    )

    assert isinstance(context, AgentReadonlyRuntimeContextCandidate)
    assert context.candidate_type == "agent_readonly_runtime_context_candidate"
    assert context.context_version == READONLY_RUNTIME_CONTEXT_VERSION
    assert context.source == READONLY_RUNTIME_CONTEXT_SOURCE
    assert context.ready_for_runtime is True
    assert context.blocking_reasons == []
    assert "llm_invocation_live_disabled" in context.warnings
    assert "llm_runtime_call_not_performed" in context.warnings
    assert context.readonly is True
    assert context.candidate_only is True
    assert context.execution_enabled is False
    assert context.agent_runtime_enabled is False
    assert context.runtime_permission_granted is False
    assert context.runtime_container_call_enabled is False
    assert context.service_invoke_enabled is False
    assert context.llm_call_enabled is False
    assert context.chat_enabled is False
    assert context.gateway_enabled is False
    assert context.tool_execution_enabled is False
    assert context.metadata["readiness_is_execution_permission"] is False
    assert context.metadata["does_not_call_runtime_container"] is True
    assert context.metadata["does_not_call_service_invoke"] is True


def test_agent_readonly_runtime_context_blocks_on_governance_denial() -> None:
    context = build_agent_readonly_runtime_context_candidate(
        candidate_id="agent-readonly-runtime-context-2",
        governance_view=_governance_view(
            allowed=False,
            reason="governance_decision_precondition_denied",
        ),
        llm_invocation_summary=_llm_summary(
            failure_type=LlmInvocationFailureType.GOVERNANCE_BLOCKED,
            call_allowed=False,
            runtime_call_performed=False,
        ),
    )

    assert context.ready_for_runtime is False
    assert (
        "governance_precondition_blocked:"
        "governance_decision_precondition_denied"
    ) in context.blocking_reasons
    assert "llm_invocation_not_allowed" in context.blocking_reasons
    assert "llm_invocation_failure:governance_blocked" in context.blocking_reasons
    assert "Readiness is not execution permission." in context.summary


def test_agent_readonly_runtime_context_rejects_execution_flags() -> None:
    with pytest.raises(ValidationError):
        AgentReadonlyRuntimeContextCandidate(
            candidate_id="agent-readonly-runtime-context-invalid-1",
            source=READONLY_RUNTIME_CONTEXT_SOURCE,
            summary="Invalid runtime context.",
            governance_view=_governance_view(allowed=True),
            llm_invocation_summary=_llm_summary(
                failure_type=LlmInvocationFailureType.LIVE_DISABLED,
                call_allowed=True,
                runtime_call_performed=False,
            ),
            runtime_permission_granted=True,
        )


def test_cognition_agent_runtime_context_source_has_no_execution_dependencies() -> None:
    source = (COGNITION_AGENT_SOURCE_ROOT / "runtime_context_view.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:adk_adapter|litellm|google\.adk|runtime_container|runtime)\b",
        re.MULTILINE,
    )
    forbidden_calls = re.compile(
        r"\b(?:completion|acompletion|service\.invoke|run_governed_llm_invocation)\s*\("
    )

    assert forbidden_imports.search(source) is None
    assert forbidden_calls.search(source) is None
    assert "live_enabled=True" not in source
    assert "ActionCandidate" not in source
    assert "RuntimeActionCandidate" not in source
    assert "ToolExecutor" not in source
    assert "Chat" not in source
    assert "Gateway" not in source


def _governance_view(
    *,
    allowed: bool,
    reason: str = "governance_precondition_allowed",
):
    return build_agent_governance_view_from_precondition_summary(
        candidate_id=f"agent-governance-view-{allowed}",
        precondition_summary={
            "allowed": allowed,
            "reason": reason,
            "decision": "continue" if allowed else "block",
            "metadata": {
                "policy_refs": ["policy:runtime"],
                "candidate_scope": "runtime_context",
            },
        },
    )


def _llm_summary(
    *,
    failure_type: LlmInvocationFailureType,
    call_allowed: bool,
    runtime_call_performed: bool,
):
    return build_agent_llm_invocation_summary_from_invocation_result(
        candidate_id=f"agent-llm-summary-{failure_type.value}",
        invocation_result=LlmInvocationResult(
            request_id="llm-request-1",
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
                allowed=call_allowed,
                reason="governance_allowed" if call_allowed else "governance_blocked",
                decision="continue" if call_allowed else "block",
                governance_decision_ref="governance-decision-1",
            ),
            call_attempted=runtime_call_performed,
            call_allowed=call_allowed,
            runtime_call_performed=runtime_call_performed,
            success=False,
            response_non_empty=False,
            failure_type=failure_type,
            error_message_sanitized=failure_type.value,
        ),
    )
