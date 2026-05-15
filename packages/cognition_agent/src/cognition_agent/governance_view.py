"""Read-only governance view candidates for the cognition agent shell."""

from __future__ import annotations

from typing import Any, Sequence

from contract_core.governance_candidate import (
    ActionCandidateConfigViewCandidate,
    ActionCandidateSchema,
    CandidateGuardResult,
    GovernanceCaseSchemaCandidate,
    GovernanceDecisionCandidateSchema,
    GovernanceEvidenceSchemaCandidate,
    ReleaseGovernanceConfigViewCandidate,
    validate_governance_candidate_guards,
)
from pydantic import Field, model_validator

from cognition_agent.models import AgentBaseCandidate

GOVERNANCE_PRECONDITION_SUMMARY_VERSION = "governance_precondition_summary_v1"
GOVERNANCE_PRECONDITION_SUMMARY_SOURCE = "composition.governance_precondition"


class AgentGovernanceViewCandidate(AgentBaseCandidate):
    """Read-only governance view for candidate agent consumers."""

    candidate_type: str = "agent_governance_view_candidate"
    evidence_candidate_refs: list[str] = Field(default_factory=list)
    case_candidate_refs: list[str] = Field(default_factory=list)
    decision_candidate_refs: list[str] = Field(default_factory=list)
    action_candidate_refs: list[str] = Field(default_factory=list)
    readonly: bool = True
    candidate_only: bool = True
    execution_enabled: bool = False
    formal_decision_enabled: bool = False
    formal_outcome_enabled: bool = False
    action_execution_enabled: bool = False
    release_action_enabled: bool = False
    runtime_action_enabled: bool = False
    guard_violations: list[str] = Field(default_factory=list)
    config_view_refs: list[str] = Field(default_factory=list)
    summary_version: str | None = None
    governance_summary_source: str | None = None
    precondition_allowed: bool | None = None
    precondition_reason: str | None = None
    precondition_decision: str | None = None
    policy_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_governance_view_candidate(self) -> "AgentGovernanceViewCandidate":
        if not self.readonly:
            raise ValueError("readonly must remain true.")
        if not self.candidate_only:
            raise ValueError("candidate_only must remain true.")
        if self.execution_enabled:
            raise ValueError("execution_enabled must remain false.")
        if self.formal_decision_enabled:
            raise ValueError("formal_decision_enabled must remain false.")
        if self.formal_outcome_enabled:
            raise ValueError("formal_outcome_enabled must remain false.")
        if self.action_execution_enabled:
            raise ValueError("action_execution_enabled must remain false.")
        if self.release_action_enabled:
            raise ValueError("release_action_enabled must remain false.")
        if self.runtime_action_enabled:
            raise ValueError("runtime_action_enabled must remain false.")
        return self


def build_agent_governance_view_candidate(
    *,
    candidate_id: str,
    source: str,
    summary: str,
    evidence_candidates: Sequence[GovernanceEvidenceSchemaCandidate] = (),
    case_candidates: Sequence[GovernanceCaseSchemaCandidate] = (),
    decision_candidates: Sequence[GovernanceDecisionCandidateSchema] = (),
    action_candidates: Sequence[ActionCandidateSchema] = (),
    action_config_view: ActionCandidateConfigViewCandidate | None = None,
    release_config_view: ReleaseGovernanceConfigViewCandidate | None = None,
    metadata: dict[str, Any] | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> AgentGovernanceViewCandidate:
    """Build a read-only governance view from public candidate contracts."""

    guard_result = _validate_action_candidates(action_candidates)
    return AgentGovernanceViewCandidate(
        candidate_id=candidate_id,
        source=source,
        summary=summary,
        governance_refs=[
            *_evidence_refs(evidence_candidates),
            *_case_refs(case_candidates),
            *_decision_refs(decision_candidates),
            *_action_refs(action_candidates),
        ],
        config_refs=_config_refs(
            action_config_view=action_config_view,
            release_config_view=release_config_view,
        ),
        evidence_candidate_refs=_evidence_refs(evidence_candidates),
        case_candidate_refs=_case_refs(case_candidates),
        decision_candidate_refs=_decision_refs(decision_candidates),
        action_candidate_refs=_action_refs(action_candidates),
        guard_violations=list(guard_result.violations),
        config_view_refs=_config_refs(
            action_config_view=action_config_view,
            release_config_view=release_config_view,
        ),
        metadata={
            "view_semantics": "candidate_only",
            "readonly": True,
            "does_not_call_governance_builders": True,
            "does_not_call_runtime": True,
            "does_not_call_release": True,
            "does_not_call_llm": True,
            "guard_passed": guard_result.passed,
            **(metadata or {}),
        },
        domain_metadata=domain_metadata or {},
    )


def build_agent_governance_view_from_precondition_summary(
    *,
    candidate_id: str,
    precondition_summary: dict[str, Any],
    source: str = GOVERNANCE_PRECONDITION_SUMMARY_SOURCE,
    metadata: dict[str, Any] | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> AgentGovernanceViewCandidate:
    """Build a read-only agent governance view from composition metadata."""

    precondition_metadata = _mapping(precondition_summary.get("metadata"))
    allowed = _optional_bool(precondition_summary.get("allowed"))
    reason = _optional_string(precondition_summary.get("reason"))
    decision = _optional_string(precondition_summary.get("decision"))
    policy_refs = _as_string_list(precondition_metadata.get("policy_refs", ()))
    candidate_scope = _optional_string(precondition_metadata.get("candidate_scope"))
    summary = _precondition_view_summary(
        allowed=allowed,
        reason=reason,
        decision=decision,
    )

    return AgentGovernanceViewCandidate(
        candidate_id=candidate_id,
        source=source,
        summary=summary,
        governance_refs=_governance_summary_refs(
            decision=decision,
            policy_refs=policy_refs,
            candidate_scope=candidate_scope,
        ),
        metadata={
            "view_semantics": "candidate_only",
            "readonly": True,
            "summary_version": GOVERNANCE_PRECONDITION_SUMMARY_VERSION,
            "summary_source": source,
            "does_not_call_governance_builders": True,
            "does_not_import_cognition_governance": True,
            "does_not_call_runtime": True,
            "does_not_call_release": True,
            "does_not_call_llm": True,
            "does_not_consume_action_candidate": True,
            "does_not_consume_runtime_action_candidate": True,
            "precondition_metadata": dict(precondition_metadata),
            **(metadata or {}),
        },
        domain_metadata=domain_metadata or {},
        summary_version=GOVERNANCE_PRECONDITION_SUMMARY_VERSION,
        governance_summary_source=source,
        precondition_allowed=allowed,
        precondition_reason=reason,
        precondition_decision=decision,
        policy_refs=policy_refs,
    )


def _validate_action_candidates(
    action_candidates: Sequence[ActionCandidateSchema],
) -> CandidateGuardResult:
    violations: list[str] = []
    for action_candidate in action_candidates:
        result = validate_governance_candidate_guards(
            action_candidate.model_dump(mode="python")
        )
        violations.extend(result.violations)
    return CandidateGuardResult(
        passed=not violations,
        violations=tuple(violations),
    )


def _evidence_refs(
    evidence_candidates: Sequence[GovernanceEvidenceSchemaCandidate],
) -> list[str]:
    return [candidate.evidence_id for candidate in evidence_candidates]


def _case_refs(case_candidates: Sequence[GovernanceCaseSchemaCandidate]) -> list[str]:
    return [candidate.case_id for candidate in case_candidates]


def _decision_refs(
    decision_candidates: Sequence[GovernanceDecisionCandidateSchema],
) -> list[str]:
    return [candidate.decision_id for candidate in decision_candidates]


def _action_refs(action_candidates: Sequence[ActionCandidateSchema]) -> list[str]:
    return [candidate.action_candidate_id for candidate in action_candidates]


def _config_refs(
    *,
    action_config_view: ActionCandidateConfigViewCandidate | None,
    release_config_view: ReleaseGovernanceConfigViewCandidate | None,
) -> list[str]:
    refs: list[str] = []
    if action_config_view is not None:
        refs.append("action_candidate_config_view")
    if release_config_view is not None:
        refs.append("release_governance_config_view")
    return refs


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item) for item in value]
    return [str(value)]


def _precondition_view_summary(
    *,
    allowed: bool | None,
    reason: str | None,
    decision: str | None,
) -> str:
    status = "unknown" if allowed is None else ("allowed" if allowed else "blocked")
    reason_text = reason or "governance_precondition_summary"
    decision_text = decision or "unspecified"
    return (
        "Read-only governance precondition summary: "
        f"status={status}, reason={reason_text}, decision={decision_text}."
    )


def _governance_summary_refs(
    *,
    decision: str | None,
    policy_refs: list[str],
    candidate_scope: str | None,
) -> list[str]:
    refs = list(policy_refs)
    if decision:
        refs.append(f"governance_decision:{decision}")
    if candidate_scope:
        refs.append(f"governance_candidate_scope:{candidate_scope}")
    return refs
