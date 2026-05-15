"""Read-only runtime context aggregation for the cognition agent shell."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from cognition_agent.governance_view import AgentGovernanceViewCandidate
from cognition_agent.llm_invocation_view import AgentLlmInvocationSummaryCandidate
from cognition_agent.models import AgentBaseCandidate


READONLY_RUNTIME_CONTEXT_VERSION = "agent_readonly_runtime_context_v1"
READONLY_RUNTIME_CONTEXT_SOURCE = "cognition_agent.readonly_runtime_context"


class AgentReadonlyRuntimeContextCandidate(AgentBaseCandidate):
    """Agent-facing aggregate over read-only governance and LLM summaries."""

    candidate_type: str = "agent_readonly_runtime_context_candidate"
    context_version: str = READONLY_RUNTIME_CONTEXT_VERSION
    governance_view: AgentGovernanceViewCandidate
    llm_invocation_summary: AgentLlmInvocationSummaryCandidate
    ready_for_runtime: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    readonly: bool = True
    candidate_only: bool = True
    execution_enabled: bool = False
    agent_runtime_enabled: bool = False
    runtime_permission_granted: bool = False
    runtime_container_call_enabled: bool = False
    runtime_helper_call_enabled: bool = False
    service_invoke_enabled: bool = False
    llm_call_enabled: bool = False
    action_execution_enabled: bool = False
    cli_enabled: bool = False
    chat_enabled: bool = False
    gateway_enabled: bool = False
    tool_execution_enabled: bool = False

    @model_validator(mode="after")
    def validate_readonly_runtime_context(
        self,
    ) -> "AgentReadonlyRuntimeContextCandidate":
        if not self.readonly:
            raise ValueError("readonly must remain true.")
        if not self.candidate_only:
            raise ValueError("candidate_only must remain true.")
        if self.execution_enabled:
            raise ValueError("execution_enabled must remain false.")
        if self.agent_runtime_enabled:
            raise ValueError("agent_runtime_enabled must remain false.")
        if self.runtime_permission_granted:
            raise ValueError("runtime_permission_granted must remain false.")
        if self.runtime_container_call_enabled:
            raise ValueError("runtime_container_call_enabled must remain false.")
        if self.runtime_helper_call_enabled:
            raise ValueError("runtime_helper_call_enabled must remain false.")
        if self.service_invoke_enabled:
            raise ValueError("service_invoke_enabled must remain false.")
        if self.llm_call_enabled:
            raise ValueError("llm_call_enabled must remain false.")
        if self.action_execution_enabled:
            raise ValueError("action_execution_enabled must remain false.")
        if self.cli_enabled:
            raise ValueError("cli_enabled must remain false.")
        if self.chat_enabled:
            raise ValueError("chat_enabled must remain false.")
        if self.gateway_enabled:
            raise ValueError("gateway_enabled must remain false.")
        if self.tool_execution_enabled:
            raise ValueError("tool_execution_enabled must remain false.")
        if self.ready_for_runtime and self.blocking_reasons:
            raise ValueError("ready_for_runtime cannot include blocking_reasons.")
        return self


def build_agent_readonly_runtime_context_candidate(
    *,
    candidate_id: str,
    governance_view: AgentGovernanceViewCandidate,
    llm_invocation_summary: AgentLlmInvocationSummaryCandidate,
    metadata: dict[str, Any] | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> AgentReadonlyRuntimeContextCandidate:
    """Build a non-executing aggregate context from read-only agent views."""

    blocking_reasons = _blocking_reasons(
        governance_view=governance_view,
        llm_invocation_summary=llm_invocation_summary,
    )
    warnings = _warnings(
        governance_view=governance_view,
        llm_invocation_summary=llm_invocation_summary,
    )
    ready_for_runtime = not blocking_reasons
    return AgentReadonlyRuntimeContextCandidate(
        candidate_id=candidate_id,
        source=READONLY_RUNTIME_CONTEXT_SOURCE,
        summary=_context_summary(
            ready_for_runtime=ready_for_runtime,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
        ),
        governance_view=governance_view,
        llm_invocation_summary=llm_invocation_summary,
        ready_for_runtime=ready_for_runtime,
        blocking_reasons=blocking_reasons,
        warnings=warnings,
        governance_refs=list(governance_view.governance_refs),
        config_refs=list(governance_view.config_refs),
        metadata={
            "view_semantics": "agent_readonly_runtime_context",
            "readonly": True,
            "candidate_only": True,
            "context_version": READONLY_RUNTIME_CONTEXT_VERSION,
            "readiness_is_execution_permission": False,
            "runtime_permission_granted": False,
            "does_not_call_runtime": True,
            "does_not_call_runtime_container": True,
            "does_not_call_runtime_helper": True,
            "does_not_call_service_invoke": True,
            "does_not_call_llm": True,
            "does_not_execute_action": True,
            "does_not_enable_cli": True,
            "does_not_enable_chat": True,
            "does_not_enable_gateway": True,
            "governance_view_candidate_id": governance_view.candidate_id,
            "llm_invocation_summary_candidate_id": llm_invocation_summary.candidate_id,
            **(metadata or {}),
        },
        domain_metadata=domain_metadata or {},
    )


def _blocking_reasons(
    *,
    governance_view: AgentGovernanceViewCandidate,
    llm_invocation_summary: AgentLlmInvocationSummaryCandidate,
) -> list[str]:
    reasons: list[str] = []
    if governance_view.precondition_allowed is False:
        reasons.append(
            f"governance_precondition_blocked:{governance_view.precondition_reason}"
        )
    if governance_view.guard_violations:
        reasons.append("governance_guard_violations_present")
    if llm_invocation_summary.call_allowed is False:
        reasons.append("llm_invocation_not_allowed")
    if llm_invocation_summary.failure_type in {
        "governance_blocked",
        "governance_needs_evidence",
        "route_facts_invalid",
    }:
        reasons.append(f"llm_invocation_failure:{llm_invocation_summary.failure_type}")
    return reasons


def _warnings(
    *,
    governance_view: AgentGovernanceViewCandidate,
    llm_invocation_summary: AgentLlmInvocationSummaryCandidate,
) -> list[str]:
    warnings: list[str] = []
    if governance_view.precondition_allowed is None:
        warnings.append("governance_precondition_unknown")
    if llm_invocation_summary.failure_type == "live_disabled":
        warnings.append("llm_invocation_live_disabled")
    if not llm_invocation_summary.runtime_call_performed:
        warnings.append("llm_runtime_call_not_performed")
    return warnings


def _context_summary(
    *,
    ready_for_runtime: bool,
    blocking_reasons: list[str],
    warnings: list[str],
) -> str:
    readiness = "ready" if ready_for_runtime else "blocked"
    return (
        "Read-only runtime context summary: "
        f"readiness={readiness}, "
        f"blocking_reasons={len(blocking_reasons)}, warnings={len(warnings)}. "
        "Readiness is not execution permission."
    )
