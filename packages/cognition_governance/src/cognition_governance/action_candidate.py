"""Unified internal action candidates for governance domains."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from cognition_governance.human_review_outcome_candidate import (
    GovernanceOutcomeCandidate,
    GovernanceOutcomeCandidateResult,
    HumanReviewRecordCandidate,
)
from cognition_governance.models import GovernanceDecision
from cognition_governance.unified_decision_candidate import (
    POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER,
    POLICY_DOMAIN_RELEASE_GOVERNANCE,
    UnifiedGovernanceDecisionCandidateResult,
)


ActionDomainCandidate = Literal[
    "release_governance",
    "adk2_workflow_runner",
]

ReleaseActionKindCandidate = Literal[
    "prepare_release",
    "verify_release_readiness",
    "request_release_evidence",
    "request_release_fix",
    "defer_release_candidate",
    "prepare_pypi_upload",
    "prepare_tag",
    "prepare_github_release",
    "verify_pypi_release",
    "record_release_followup",
]

RuntimeActionKindCandidate = Literal[
    "request_runtime_evidence",
    "request_runtime_fix",
    "defer_runtime_candidate",
    "prepare_run_config_update",
    "prepare_service_bundle_review",
    "record_runtime_followup",
    "prepare_artifact_session_review",
    "prepare_event_trace_review",
    "continue_runtime_governance_review",
]

ActionKindCandidate = ReleaseActionKindCandidate | RuntimeActionKindCandidate

ALLOWED_ACTION_DOMAINS = [
    "release_governance",
    "adk2_workflow_runner",
]

ALLOWED_RELEASE_ACTION_KINDS = [
    "prepare_release",
    "verify_release_readiness",
    "request_release_evidence",
    "request_release_fix",
    "defer_release_candidate",
    "prepare_pypi_upload",
    "prepare_tag",
    "prepare_github_release",
    "verify_pypi_release",
    "record_release_followup",
]

ALLOWED_RUNTIME_ACTION_KINDS = [
    "request_runtime_evidence",
    "request_runtime_fix",
    "defer_runtime_candidate",
    "prepare_run_config_update",
    "prepare_service_bundle_review",
    "record_runtime_followup",
    "prepare_artifact_session_review",
    "prepare_event_trace_review",
    "continue_runtime_governance_review",
]

FORBIDDEN_ACTION_KINDS = [
    "release",
    "block",
    "pass",
    "runtime_fix",
    "run_config_update",
    "service_bundle_update",
    "publish",
    "upload",
    "tag",
    "push",
    "twine_upload",
    "git_tag",
    "git_push",
    "github_release",
    "trusted_publishing",
    "call_runtime_container",
    "call_composition",
    "call_adk_adapter",
    "execute_workflow",
]


class ActionCandidate(BaseModel):
    """Unified internal action candidate; it is never executable by itself."""

    model_config = ConfigDict(extra="forbid")

    action_candidate_id: str = Field(..., min_length=1)
    decision_candidate_id: str | None = None
    human_review_id: str | None = None
    outcome_candidate_id: str | None = None
    case_id: str | None = None
    action_domain: ActionDomainCandidate
    action_kind: ActionKindCandidate
    action_semantics: str = "candidate_only"
    execution_enabled: bool = False
    requires_operator_confirmation: bool = True
    reviewer: str | None = None
    executor: str | None = None
    operator_notes: list[str] = Field(default_factory=list)
    blocked_execution_reasons: list[str] = Field(default_factory=list)
    required_confirmations: list[str] = Field(default_factory=list)
    source_decision_kind: str | None = None
    source_review_result: str | None = None
    source_outcome_status: str | None = None
    domain_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(..., min_length=1)


class ActionCandidateResult(BaseModel):
    """Unified internal action candidate result; no action is executed."""

    model_config = ConfigDict(extra="forbid")

    action_candidate: ActionCandidate
    notes: list[str] = Field(default_factory=list)


def create_action_candidate(
    decision_candidate: UnifiedGovernanceDecisionCandidateResult
    | GovernanceDecision
    | dict[str, Any]
    | None = None,
    human_review_record: HumanReviewRecordCandidate | dict[str, Any] | None = None,
    outcome_candidate: GovernanceOutcomeCandidateResult
    | GovernanceOutcomeCandidate
    | dict[str, Any]
    | None = None,
    *,
    action_domain: ActionDomainCandidate,
    action_kind: ActionKindCandidate,
    executor: str | None = None,
    operator_notes: list[str] | None = None,
    required_confirmations: list[str] | None = None,
    domain_metadata: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> ActionCandidateResult:
    """Create a unified action candidate without executing any action."""

    decision = _as_decision_candidate(decision_candidate)
    review = _as_human_review_record(human_review_record)
    outcome = _as_outcome_candidate(outcome_candidate)
    blocked_reasons = _blocked_execution_reasons(
        action_domain=action_domain,
        action_kind=action_kind,
        decision=decision,
        review=review,
        outcome=outcome,
    )
    action = ActionCandidate(
        action_candidate_id=f"{action_domain.replace('_', '-')}-action-candidate-{uuid4()}",
        decision_candidate_id=decision.decision_id if decision else None,
        human_review_id=review.review_id if review else None,
        outcome_candidate_id=outcome.outcome_candidate_id if outcome else None,
        case_id=decision.case_id if decision else None,
        action_domain=action_domain,
        action_kind=action_kind,
        action_semantics="candidate_only",
        execution_enabled=False,
        requires_operator_confirmation=True,
        reviewer=review.reviewer if review else None,
        executor=executor,
        operator_notes=list(operator_notes or []),
        blocked_execution_reasons=blocked_reasons,
        required_confirmations=_required_confirmations(
            action_domain,
            required_confirmations,
        ),
        source_decision_kind=decision.decision if decision else None,
        source_review_result=review.review_result if review else None,
        source_outcome_status=outcome.status_candidate if outcome else None,
        domain_metadata=_domain_metadata(
            action_domain=action_domain,
            decision=decision,
            review=review,
            outcome=outcome,
            extra=domain_metadata,
        ),
        metadata={
            "action_semantics": "candidate_only",
            "execution_enabled": False,
            "requires_operator_confirmation": True,
            "allowed_action_domains": list(ALLOWED_ACTION_DOMAINS),
            "allowed_release_action_kinds": list(ALLOWED_RELEASE_ACTION_KINDS),
            "allowed_runtime_action_kinds": list(ALLOWED_RUNTIME_ACTION_KINDS),
            "forbidden_action_kinds": list(FORBIDDEN_ACTION_KINDS),
            "blocked_formal_action_reasons": list(blocked_reasons),
            "reviewer_executor_boundary": (
                "reviewer records governance review; executor/operator performs "
                "a separate confirmation outside cognition_governance."
            ),
            "does_not_execute_action": True,
            "does_not_call_execution_layers": True,
            "does_not_modify_upstream_candidates": True,
            "does_not_generate_formal_decision": True,
            "does_not_generate_formal_outcome": True,
            **_sanitize_mapping(metadata or {}),
        },
        created_at=created_at or _now_utc_iso(),
    )
    return ActionCandidateResult(
        action_candidate=action,
        notes=[
            "Internal ActionCandidate only.",
            "No real action is executed.",
            "Operator confirmation remains outside cognition_governance.",
        ],
    )


def _as_decision_candidate(
    value: UnifiedGovernanceDecisionCandidateResult
    | GovernanceDecision
    | dict[str, Any]
    | None,
) -> GovernanceDecision | None:
    if value is None:
        return None
    if isinstance(value, UnifiedGovernanceDecisionCandidateResult):
        return value.decision_candidate
    if isinstance(value, GovernanceDecision):
        return value
    if isinstance(value, dict):
        if "decision_candidate" in value:
            return GovernanceDecision.model_validate(value["decision_candidate"])
        return GovernanceDecision.model_validate(value)
    raise TypeError("GovernanceDecision candidate or compatible mapping is required.")


def _as_human_review_record(
    value: HumanReviewRecordCandidate | dict[str, Any] | None,
) -> HumanReviewRecordCandidate | None:
    if value is None:
        return None
    if isinstance(value, HumanReviewRecordCandidate):
        return value
    if isinstance(value, dict):
        return HumanReviewRecordCandidate.model_validate(value)
    raise TypeError("HumanReviewRecordCandidate or compatible mapping is required.")


def _as_outcome_candidate(
    value: GovernanceOutcomeCandidateResult
    | GovernanceOutcomeCandidate
    | dict[str, Any]
    | None,
) -> GovernanceOutcomeCandidate | None:
    if value is None:
        return None
    if isinstance(value, GovernanceOutcomeCandidateResult):
        return value.outcome_candidate
    if isinstance(value, GovernanceOutcomeCandidate):
        return value
    if isinstance(value, dict):
        if "outcome_candidate" in value:
            return GovernanceOutcomeCandidate.model_validate(value["outcome_candidate"])
        return GovernanceOutcomeCandidate.model_validate(value)
    raise TypeError("GovernanceOutcomeCandidate or compatible mapping is required.")


def _blocked_execution_reasons(
    *,
    action_domain: str,
    action_kind: str,
    decision: GovernanceDecision | None,
    review: HumanReviewRecordCandidate | None,
    outcome: GovernanceOutcomeCandidate | None,
) -> list[str]:
    reasons = [
        "ActionCandidate is candidate-only.",
        "Execution is disabled inside cognition_governance.",
        "Operator confirmation is required outside cognition_governance.",
        "Formal GovernanceDecision is not produced.",
        "Formal GovernanceOutcome is not produced.",
    ]
    reasons.extend(_domain_action_reasons(action_domain, action_kind))

    if decision is None:
        reasons.append("GovernanceDecision candidate is missing.")
    else:
        decision_metadata = _mapping(decision.metadata)
        if decision_metadata.get("policy_domain") != action_domain:
            reasons.append("Decision candidate policy_domain does not match action_domain.")
        if decision_metadata.get("decision_semantics") != "candidate_only":
            reasons.append("Decision semantics is not explicitly candidate_only.")
        if decision_metadata.get("formal_decision_enabled") is not False:
            reasons.append("Decision candidate does not disable formal decisions.")
        if decision_metadata.get("policy_execution_enabled") is not False:
            reasons.append("Decision candidate does not disable policy execution.")
        if decision_metadata.get("governance_outcome_enabled") is not False:
            reasons.append("Decision candidate does not defer GovernanceOutcome.")

    if review is None:
        reasons.append("HumanReviewRecord candidate is missing.")
    else:
        if decision and review.decision_candidate_id != decision.decision_id:
            reasons.append("HumanReviewRecord candidate does not match the decision.")
        if review.metadata.get("review_semantics") != "candidate_only":
            reasons.append("HumanReviewRecord semantics is not candidate_only.")
        if review.metadata.get("formal_outcome_enabled") is not False:
            reasons.append("HumanReviewRecord does not disable formal outcome.")
        if review.policy_domain != action_domain:
            reasons.append("HumanReviewRecord policy_domain does not match action_domain.")

    if outcome is None:
        reasons.append("GovernanceOutcome candidate is missing.")
    else:
        if decision and outcome.decision_candidate_id != decision.decision_id:
            reasons.append("GovernanceOutcome candidate does not match the decision.")
        if review and outcome.human_review_id != review.review_id:
            reasons.append("GovernanceOutcome candidate does not match the review.")
        if outcome.policy_domain != action_domain:
            reasons.append("GovernanceOutcome candidate policy_domain does not match action_domain.")
        if outcome.outcome_semantics != "candidate_only":
            reasons.append("GovernanceOutcome candidate semantics is not candidate_only.")
        if outcome.formal_decision_required is not True:
            reasons.append("GovernanceOutcome candidate does not require formal decision.")
        if outcome.formal_outcome_enabled is not False:
            reasons.append("GovernanceOutcome candidate does not disable formal outcome.")
    return _dedupe(reasons)


def _domain_action_reasons(action_domain: str, action_kind: str) -> list[str]:
    if action_domain == POLICY_DOMAIN_RELEASE_GOVERNANCE:
        if action_kind not in ALLOWED_RELEASE_ACTION_KINDS:
            return ["Action kind is not allowed for release_governance."]
        return ["Release action remains outside cognition_governance execution."]
    if action_domain == POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER:
        if action_kind not in ALLOWED_RUNTIME_ACTION_KINDS:
            return ["Action kind is not allowed for adk2_workflow_runner."]
        return [
            "Runtime action remains outside cognition_governance execution.",
            "RunConfig and ServiceBundle updates are not performed.",
            "runtime_container, composition, and adk_adapter are not called.",
        ]
    return ["Action domain is not supported."]


def _required_confirmations(
    action_domain: str,
    values: list[str] | None,
) -> list[str]:
    defaults = [
        "governance_decision_candidate",
        "human_review_record_candidate",
        "governance_outcome_candidate",
        "operator_confirmation",
    ]
    if action_domain == POLICY_DOMAIN_RELEASE_GOVERNANCE:
        defaults.append("release_workflow_or_cli_confirmation")
    elif action_domain == POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER:
        defaults.append("runtime_operator_confirmation")
    return _dedupe([*defaults, *(values or [])])


def _domain_metadata(
    *,
    action_domain: str,
    decision: GovernanceDecision | None,
    review: HumanReviewRecordCandidate | None,
    outcome: GovernanceOutcomeCandidate | None,
    extra: dict[str, Any] | None,
) -> dict[str, Any]:
    decision_domain = (
        _mapping(_mapping(decision.metadata).get("domain_metadata"))
        if decision
        else {}
    )
    keys = (
        [
            "target_version",
            "phase",
            "release_target",
            "providers",
            "provider_results",
            "failure_codes",
            "issues_summary",
            "block_candidates",
            "warning_candidates",
            "human_review_reasons",
            "missing_evidence",
        ]
        if action_domain == POLICY_DOMAIN_RELEASE_GOVERNANCE
        else [
            "runtime_kind",
            "runtime_id",
            "workflow_id",
            "workflow_name",
            "run_config",
            "service_bundle",
            "artifact_summary",
            "session_summary",
            "event_summary",
            "risk_level",
            "findings",
            "required_followups",
        ]
    )
    collected: dict[str, Any] = {}
    for key in keys:
        value = decision_domain.get(key)
        if value is None and decision:
            value = _mapping(decision.metadata).get(key)
        if value is not None:
            collected[key] = _sanitize(value)
    if review:
        collected["human_review"] = {
            "review_id": review.review_id,
            "review_result": review.review_result,
            "required_followups": list(review.required_followups),
        }
    if outcome:
        collected["outcome_candidate"] = {
            "outcome_candidate_id": outcome.outcome_candidate_id,
            "status_candidate": outcome.status_candidate,
            "blocked_formal_outcome_reasons": list(
                outcome.blocked_formal_outcome_reasons
            ),
        }
    if extra:
        collected["extra"] = _sanitize_mapping(extra)
    return collected


def _now_utc_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sanitize_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _sanitize(value) for key, value in mapping.items()}


def _sanitize(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, bool, str)):
        return value
    if isinstance(value, dict):
        return _sanitize_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return {
        "object_type": type(value).__name__,
        "object_module": type(value).__module__,
    }


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
