"""Read-only governed run evidence context for the cognition agent shell."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from cognition_agent.agent_shell_audit_view import (
    AgentShellAuditReadonlyViewCandidate,
)
from cognition_agent.agent_tool_audit_view import (
    AgentToolAuditReadonlyViewCandidate,
)
from cognition_agent.governance_summary_view import (
    AgentGovernanceEvidenceSummaryViewCandidate,
)
from cognition_agent.llm_invocation_view import AgentLlmInvocationSummaryCandidate
from cognition_agent.models import AgentBaseCandidate


GOVERNED_RUN_EVIDENCE_CONTEXT_VERSION = (
    "agent_governed_run_evidence_context_v1"
)
GOVERNED_RUN_EVIDENCE_CONTEXT_SOURCE = (
    "cognition_agent.governed_run_evidence_context"
)

FORBIDDEN_GOVERNED_RUN_EVIDENCE_KEYS = frozenset(
    {
        "api_key",
        "completion",
        "full_response",
        "message",
        "messages",
        "prompt",
        "raw_provider_response",
        "raw_response",
        "raw_tool_input",
        "raw_tool_output",
        "response",
        "response_text",
        "secret",
        "system_prompt",
        "text",
        "token",
    }
)


class AgentGovernedRunEvidenceContextCandidate(AgentBaseCandidate):
    """Agent-facing read-only context over governed run evidence facts."""

    candidate_type: str = "agent_governed_run_evidence_context_candidate"
    context_version: str = GOVERNED_RUN_EVIDENCE_CONTEXT_VERSION
    governance_summary_candidate_id: str
    llm_invocation_summary_candidate_id: str | None = None
    llm_invocation_result_ref: str | None = None
    llm_invocation_observation_ref: str | None = None
    llm_invocation_summary_ref: str | None = None
    llm_invocation_call_allowed: bool = False
    llm_invocation_call_attempted: bool = False
    llm_invocation_runtime_call_performed: bool = False
    llm_invocation_failure_type: str | None = None
    controlled_live: bool = False
    live_llm_call_performed: bool = False
    ollama_call_performed: bool = False
    live_profile: dict[str, Any] | None = None
    agent_shell_audit_candidate_id: str | None = None
    agent_shell_evidence_ref: str | None = None
    agent_shell_run_ref: str | None = None
    agent_shell_status: str | None = None
    agent_shell_failure_type: str | None = None
    agent_shell_controlled_live: bool = False
    agent_shell_runtime_call_performed: bool = False
    agent_shell_call_attempted: bool = False
    agent_shell_live_profile: dict[str, Any] | None = None
    agent_tool_audit_candidate_id: str | None = None
    tool_evidence_ref: str | None = None
    tool_run_ref: str | None = None
    tool_name: str | None = None
    tool_kind: str | None = None
    tool_status: str | None = None
    tool_failure_type: str | None = None
    tool_call_allowed: bool = False
    tool_call_attempted: bool = False
    tool_runtime_call_performed: bool = False
    tool_confirmation_required: bool = False
    tool_confirmation_granted: bool = False
    adk_tool_confirmation_requested: bool = False
    tool_approval_ref: str | None = None
    tool_confirmation_decision_source: str | None = None
    ready_for_review: bool = False
    warnings: list[str] = Field(default_factory=list)
    readonly: bool = True
    candidate_only: bool = True
    execution_enabled: bool = False
    runtime_permission_granted: bool = False
    agent_runtime_enabled: bool = False
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
    def validate_governed_run_evidence_context(
        self,
    ) -> "AgentGovernedRunEvidenceContextCandidate":
        if not self.readonly:
            raise ValueError("readonly must remain true.")
        if not self.candidate_only:
            raise ValueError("candidate_only must remain true.")
        if self.execution_enabled:
            raise ValueError("execution_enabled must remain false.")
        if self.runtime_permission_granted:
            raise ValueError("runtime_permission_granted must remain false.")
        if self.agent_runtime_enabled:
            raise ValueError("agent_runtime_enabled must remain false.")
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
        violations = _forbidden_context_key_violations(self.model_dump(mode="python"))
        if violations:
            raise ValueError("; ".join(violations))
        return self


def build_agent_governed_run_evidence_context_candidate(
    *,
    candidate_id: str,
    governance_summary_view: AgentGovernanceEvidenceSummaryViewCandidate,
    llm_invocation_summary: AgentLlmInvocationSummaryCandidate | None = None,
    llm_invocation_audit: dict[str, Any] | None = None,
    agent_shell_audit_view: AgentShellAuditReadonlyViewCandidate | None = None,
    agent_tool_audit_view: AgentToolAuditReadonlyViewCandidate | None = None,
    metadata: dict[str, Any] | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> AgentGovernedRunEvidenceContextCandidate:
    """Build a non-executing review context from read-only evidence views."""

    audit = _safe_audit(llm_invocation_audit or {})
    live_profile = _compact_live_profile(audit.get("live_profile"))
    llm_values = _llm_values(
        llm_invocation_summary=llm_invocation_summary,
        audit=audit,
        live_profile=live_profile,
    )
    agent_shell_values = _agent_shell_values(agent_shell_audit_view)
    agent_tool_values = _agent_tool_values(agent_tool_audit_view)
    warnings = _warnings(
        llm_invocation_summary=llm_invocation_summary,
        audit=audit,
        llm_values=llm_values,
        agent_shell_values=agent_shell_values,
        agent_tool_values=agent_tool_values,
    )
    ready_for_review = not _review_blocking_warnings(warnings)
    governance_refs = _refs(
        list(governance_summary_view.governance_refs),
        agent_shell_values["agent_shell_evidence_ref"],
        agent_shell_values["agent_shell_run_ref"],
        agent_tool_values["tool_evidence_ref"],
        agent_tool_values["tool_run_ref"],
        agent_tool_values["tool_approval_ref"],
    )
    return AgentGovernedRunEvidenceContextCandidate(
        candidate_id=candidate_id,
        source=GOVERNED_RUN_EVIDENCE_CONTEXT_SOURCE,
        summary=_summary_text(
            governance_summary_view=governance_summary_view,
            llm_values=llm_values,
            ready_for_review=ready_for_review,
        ),
        governance_summary_candidate_id=governance_summary_view.candidate_id,
        llm_invocation_summary_candidate_id=(
            llm_invocation_summary.candidate_id
            if llm_invocation_summary is not None
            else None
        ),
        ready_for_review=ready_for_review,
        warnings=warnings,
        governance_refs=governance_refs,
        config_refs=list(governance_summary_view.config_refs),
        metadata={
            "view_semantics": "agent_readonly_governed_run_evidence_context",
            "readonly": True,
            "candidate_only": True,
            "context_version": GOVERNED_RUN_EVIDENCE_CONTEXT_VERSION,
            "review_context_is_execution_permission": False,
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
            "governance_summary_candidate_id": governance_summary_view.candidate_id,
            "llm_invocation_summary_candidate_id": (
                llm_invocation_summary.candidate_id
                if llm_invocation_summary is not None
                else None
            ),
            "agent_shell_audit_candidate_id": (
                agent_shell_audit_view.candidate_id
                if agent_shell_audit_view is not None
                else None
            ),
            "agent_tool_audit_candidate_id": (
                agent_tool_audit_view.candidate_id
                if agent_tool_audit_view is not None
                else None
            ),
            **_safe_mapping(metadata or {}),
        },
        domain_metadata=_safe_mapping(domain_metadata or {}),
        **llm_values,
        **agent_shell_values,
        **agent_tool_values,
    )


def _llm_values(
    *,
    llm_invocation_summary: AgentLlmInvocationSummaryCandidate | None,
    audit: dict[str, Any],
    live_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "llm_invocation_result_ref": _optional_string(
            audit.get("llm_invocation_result_ref")
        ),
        "llm_invocation_observation_ref": _optional_string(
            audit.get("llm_invocation_observation_ref")
        ),
        "llm_invocation_summary_ref": _optional_string(
            audit.get("llm_invocation_summary_ref")
        ),
        "llm_invocation_call_allowed": _bool(
            audit.get("call_allowed"),
            fallback=(
                llm_invocation_summary.call_allowed
                if llm_invocation_summary is not None
                else False
            ),
        ),
        "llm_invocation_call_attempted": _bool(
            audit.get("call_attempted"),
            fallback=(
                llm_invocation_summary.call_attempted
                if llm_invocation_summary is not None
                else False
            ),
        ),
        "llm_invocation_runtime_call_performed": _bool(
            audit.get("runtime_call_performed"),
            fallback=(
                llm_invocation_summary.runtime_call_performed
                if llm_invocation_summary is not None
                else False
            ),
        ),
        "llm_invocation_failure_type": _optional_string(
            audit.get("failure_type")
        )
        or (
            llm_invocation_summary.failure_type
            if llm_invocation_summary is not None
            else None
        ),
        "controlled_live": _bool(audit.get("controlled_live")),
        "live_llm_call_performed": _bool(audit.get("live_llm_call_performed")),
        "ollama_call_performed": _bool(audit.get("ollama_call_performed")),
        "live_profile": live_profile,
    }


def _warnings(
    *,
    llm_invocation_summary: AgentLlmInvocationSummaryCandidate | None,
    audit: dict[str, Any],
    llm_values: dict[str, Any],
    agent_shell_values: dict[str, Any],
    agent_tool_values: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if not audit:
        warnings.append("llm_invocation_audit_missing")
    if llm_invocation_summary is None:
        warnings.append("llm_invocation_summary_missing")
    if llm_values["llm_invocation_failure_type"] == "live_disabled":
        warnings.append("llm_invocation_live_disabled")
    if llm_values["controlled_live"] and llm_values["live_profile"] is None:
        warnings.append("controlled_live_profile_missing")
    if not llm_values["llm_invocation_runtime_call_performed"]:
        warnings.append("llm_runtime_call_not_performed")
    if agent_shell_values["agent_shell_audit_candidate_id"] is not None:
        if agent_shell_values["agent_shell_failure_type"]:
            warnings.append(
                "agent_shell_failure:"
                f"{agent_shell_values['agent_shell_failure_type']}"
            )
        if not agent_shell_values["agent_shell_runtime_call_performed"]:
            warnings.append("agent_shell_runtime_call_not_performed")
    if agent_tool_values["agent_tool_audit_candidate_id"] is not None:
        if agent_tool_values["tool_failure_type"]:
            warnings.append(f"tool_failure:{agent_tool_values['tool_failure_type']}")
        if not agent_tool_values["tool_runtime_call_performed"]:
            warnings.append("tool_runtime_call_not_performed")
        if (
            agent_tool_values["tool_confirmation_required"]
            and not agent_tool_values["tool_confirmation_granted"]
        ):
            warnings.append("tool_confirmation_not_granted")
    return warnings


def _review_blocking_warnings(warnings: list[str]) -> list[str]:
    return [
        warning
        for warning in warnings
        if warning in {"llm_invocation_audit_missing"}
    ]


def _summary_text(
    *,
    governance_summary_view: AgentGovernanceEvidenceSummaryViewCandidate,
    llm_values: dict[str, Any],
    ready_for_review: bool,
) -> str:
    readiness = "ready" if ready_for_review else "incomplete"
    call_state = (
        "performed"
        if llm_values["llm_invocation_runtime_call_performed"]
        else "not_performed"
    )
    controlled_live = (
        "controlled_live" if llm_values["controlled_live"] else "no_live"
    )
    workflow = (
        governance_summary_view.workflow_name
        or governance_summary_view.workflow_id
        or "unknown_workflow"
    )
    return (
        "Read-only governed run evidence context: "
        f"review={readiness}, workflow={workflow}, "
        f"llm_call={call_state}, mode={controlled_live}. "
        "Review context is not execution permission."
    )


def _agent_shell_values(
    agent_shell_audit_view: AgentShellAuditReadonlyViewCandidate | None,
) -> dict[str, Any]:
    if agent_shell_audit_view is None:
        return {
            "agent_shell_audit_candidate_id": None,
            "agent_shell_evidence_ref": None,
            "agent_shell_run_ref": None,
            "agent_shell_status": None,
            "agent_shell_failure_type": None,
            "agent_shell_controlled_live": False,
            "agent_shell_runtime_call_performed": False,
            "agent_shell_call_attempted": False,
            "agent_shell_live_profile": None,
        }
    return {
        "agent_shell_audit_candidate_id": agent_shell_audit_view.candidate_id,
        "agent_shell_evidence_ref": agent_shell_audit_view.agent_shell_evidence_ref,
        "agent_shell_run_ref": agent_shell_audit_view.agent_shell_run_ref,
        "agent_shell_status": agent_shell_audit_view.status,
        "agent_shell_failure_type": agent_shell_audit_view.failure_type,
        "agent_shell_controlled_live": agent_shell_audit_view.controlled_live,
        "agent_shell_runtime_call_performed": (
            agent_shell_audit_view.runtime_call_performed
        ),
        "agent_shell_call_attempted": agent_shell_audit_view.call_attempted,
        "agent_shell_live_profile": agent_shell_audit_view.live_profile,
    }


def _agent_tool_values(
    agent_tool_audit_view: AgentToolAuditReadonlyViewCandidate | None,
) -> dict[str, Any]:
    if agent_tool_audit_view is None:
        return {
            "agent_tool_audit_candidate_id": None,
            "tool_evidence_ref": None,
            "tool_run_ref": None,
            "tool_name": None,
            "tool_kind": None,
            "tool_status": None,
            "tool_failure_type": None,
            "tool_call_allowed": False,
            "tool_call_attempted": False,
            "tool_runtime_call_performed": False,
            "tool_confirmation_required": False,
            "tool_confirmation_granted": False,
            "adk_tool_confirmation_requested": False,
            "tool_approval_ref": None,
            "tool_confirmation_decision_source": None,
        }
    return {
        "agent_tool_audit_candidate_id": agent_tool_audit_view.candidate_id,
        "tool_evidence_ref": agent_tool_audit_view.tool_evidence_ref,
        "tool_run_ref": agent_tool_audit_view.tool_run_ref,
        "tool_name": agent_tool_audit_view.tool_name,
        "tool_kind": agent_tool_audit_view.tool_kind,
        "tool_status": agent_tool_audit_view.status,
        "tool_failure_type": agent_tool_audit_view.tool_failure_type,
        "tool_call_allowed": agent_tool_audit_view.tool_call_allowed,
        "tool_call_attempted": agent_tool_audit_view.tool_call_attempted,
        "tool_runtime_call_performed": (
            agent_tool_audit_view.tool_runtime_call_performed
        ),
        "tool_confirmation_required": (
            agent_tool_audit_view.tool_confirmation_required
        ),
        "tool_confirmation_granted": (
            agent_tool_audit_view.tool_confirmation_granted
        ),
        "adk_tool_confirmation_requested": (
            agent_tool_audit_view.adk_tool_confirmation_requested
        ),
        "tool_approval_ref": agent_tool_audit_view.tool_approval_ref,
        "tool_confirmation_decision_source": (
            agent_tool_audit_view.tool_confirmation_decision_source
        ),
    }


def _refs(existing_refs: list[str], *candidate_refs: Any) -> list[str]:
    refs = list(existing_refs)
    for candidate_ref in candidate_refs:
        if isinstance(candidate_ref, str) and candidate_ref and candidate_ref not in refs:
            refs.append(candidate_ref)
    return refs


def _safe_audit(value: dict[str, Any]) -> dict[str, Any]:
    violations = _forbidden_context_key_violations(value, path="$.llm_invocation_audit")
    if violations:
        raise ValueError("; ".join(violations))
    return dict(value)


def _safe_mapping(value: dict[str, Any]) -> dict[str, Any]:
    violations = _forbidden_context_key_violations(value, path="$.metadata")
    if violations:
        raise ValueError("; ".join(violations))
    return dict(value)


def _compact_live_profile(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    allowed_keys = (
        "controlled_live",
        "live_options_source",
        "live_service_profile",
        "configured_model_name",
        "timeout_seconds",
        "temperature",
        "max_tokens",
        "local_no_proxy_applied",
    )
    profile = {
        key: item
        for key in allowed_keys
        if (item := value.get(key)) is not None
        and isinstance(item, bool | int | float | str)
    }
    violations = _forbidden_context_key_violations(profile, path="$.live_profile")
    if violations:
        raise ValueError("; ".join(violations))
    return profile or None


def _forbidden_context_key_violations(value: Any, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            key_path = f"{path}.{key_text}"
            if key_text.lower() in FORBIDDEN_GOVERNED_RUN_EVIDENCE_KEYS:
                violations.append(
                    f"governed run evidence context key is forbidden at {key_path}"
                )
            violations.extend(_forbidden_context_key_violations(item, key_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(_forbidden_context_key_violations(item, f"{path}[{index}]"))
    return violations


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _bool(value: Any, *, fallback: bool = False) -> bool:
    return value if isinstance(value, bool) else fallback
