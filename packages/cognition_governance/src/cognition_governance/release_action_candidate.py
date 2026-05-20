"""Release action candidates for internal governance review."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from cognition_governance.action_candidate import (
    ActionCandidate,
    create_action_candidate,
)
from cognition_governance.human_review_outcome_candidate import (
    GovernanceOutcomeCandidate,
    GovernanceOutcomeCandidateResult,
    HumanReviewRecordCandidate,
)
from cognition_governance.models import GovernanceDecision
from cognition_governance.unified_decision_candidate import (
    POLICY_DOMAIN_RELEASE_GOVERNANCE,
    UnifiedGovernanceDecisionCandidateResult,
)


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

ReleaseActionDomainCandidate = Literal["release_governance"]

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

FORBIDDEN_RELEASE_ACTION_KINDS = [
    "release",
    "block",
    "pass",
    "publish",
    "upload",
    "twine_upload",
    "git_tag",
    "git_push",
    "github_release",
    "trusted_publishing",
]


class ReleaseActionCandidate(BaseModel):
    """Internal release action candidate; it is never executable by itself."""

    model_config = ConfigDict(extra="forbid")

    action_candidate_id: str = Field(..., min_length=1)
    decision_candidate_id: str = Field(..., min_length=1)
    human_review_id: str | None = None
    outcome_candidate_id: str | None = None
    case_id: str = Field(..., min_length=1)
    action_kind: ReleaseActionKindCandidate
    action_domain: ReleaseActionDomainCandidate = POLICY_DOMAIN_RELEASE_GOVERNANCE
    action_semantics: str = "candidate_only"
    execution_enabled: bool = False
    requires_operator_confirmation: bool = True
    reviewer: str | None = None
    executor: str | None = None
    operator_notes: list[str] = Field(default_factory=list)
    blocked_execution_reasons: list[str] = Field(default_factory=list)
    required_confirmations: list[str] = Field(default_factory=list)
    source_decision_kind: str = Field(..., min_length=1)
    source_review_result: str | None = None
    source_outcome_status: str | None = None
    domain_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(..., min_length=1)


class ReleaseActionCandidateResult(BaseModel):
    """Internal release action candidate result; no action is executed."""

    model_config = ConfigDict(extra="forbid")

    action_candidate: ReleaseActionCandidate
    unified_action_candidate: ActionCandidate | None = None
    notes: list[str] = Field(default_factory=list)


def create_release_action_candidate(
    decision_candidate: UnifiedGovernanceDecisionCandidateResult
    | GovernanceDecision
    | dict[str, Any],
    human_review_record: HumanReviewRecordCandidate | dict[str, Any] | None = None,
    outcome_candidate: GovernanceOutcomeCandidateResult
    | GovernanceOutcomeCandidate
    | dict[str, Any]
    | None = None,
    *,
    action_kind: ReleaseActionKindCandidate,
    executor: str | None = None,
    operator_notes: list[str] | None = None,
    required_confirmations: list[str] | None = None,
    domain_metadata: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> ReleaseActionCandidateResult:
    """Create a release action candidate without executing any release action."""

    unified_result = create_action_candidate(
        decision_candidate,
        human_review_record,
        outcome_candidate,
        action_domain=POLICY_DOMAIN_RELEASE_GOVERNANCE,
        action_kind=action_kind,
        executor=executor,
        operator_notes=operator_notes,
        required_confirmations=required_confirmations,
        domain_metadata=domain_metadata,
        metadata={
            "release_action_candidate": True,
            **(metadata or {}),
        },
        created_at=created_at,
    )
    unified = unified_result.action_candidate

    action = ReleaseActionCandidate(
        action_candidate_id=unified.action_candidate_id,
        decision_candidate_id=unified.decision_candidate_id or "missing-decision-candidate",
        human_review_id=unified.human_review_id,
        outcome_candidate_id=unified.outcome_candidate_id,
        case_id=unified.case_id or "missing-case",
        action_kind=action_kind,
        action_domain=POLICY_DOMAIN_RELEASE_GOVERNANCE,
        action_semantics="candidate_only",
        execution_enabled=False,
        requires_operator_confirmation=True,
        reviewer=unified.reviewer,
        executor=executor,
        operator_notes=list(unified.operator_notes),
        blocked_execution_reasons=list(unified.blocked_execution_reasons),
        required_confirmations=list(unified.required_confirmations),
        source_decision_kind=unified.source_decision_kind or "missing-decision",
        source_review_result=unified.source_review_result,
        source_outcome_status=unified.source_outcome_status,
        domain_metadata=dict(unified.domain_metadata),
        metadata={
            "action_semantics": "candidate_only",
            "execution_enabled": False,
            "requires_operator_confirmation": True,
            "allowed_action_kinds": list(ALLOWED_RELEASE_ACTION_KINDS),
            "forbidden_action_kinds": list(FORBIDDEN_RELEASE_ACTION_KINDS),
            "blocked_formal_action_reasons": list(unified.blocked_execution_reasons),
            "reviewer_executor_boundary": (
                "reviewer records governance review; executor/operator performs "
                "a separate confirmation outside cognition_governance."
            ),
            "does_not_execute_release_action": True,
            "does_not_call_scripts": True,
            "does_not_generate_formal_decision": True,
            "does_not_generate_formal_outcome": True,
            "unified_action_candidate_id": unified.action_candidate_id,
            **_sanitize_mapping(metadata or {}),
        },
        created_at=unified.created_at,
    )
    return ReleaseActionCandidateResult(
        action_candidate=action,
        unified_action_candidate=unified,
        notes=[
            "Internal ReleaseActionCandidate only.",
            "No release, block, pass, publish, upload, tag, push, or GitHub Release action is executed.",
            "Operator confirmation remains outside cognition_governance.",
        ],
    )


def _as_decision_candidate(
    value: UnifiedGovernanceDecisionCandidateResult
    | GovernanceDecision
    | dict[str, Any],
) -> GovernanceDecision:
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
    decision: GovernanceDecision,
    review: HumanReviewRecordCandidate | None,
    outcome: GovernanceOutcomeCandidate | None,
) -> list[str]:
    reasons = [
        "ReleaseActionCandidate is candidate-only.",
        "Execution is disabled inside cognition_governance.",
        "Operator confirmation is required outside cognition_governance.",
        "Formal GovernanceDecision is not produced.",
        "Formal GovernanceOutcome is not produced.",
    ]
    decision_metadata = _mapping(decision.metadata)
    if decision_metadata.get("policy_domain") != POLICY_DOMAIN_RELEASE_GOVERNANCE:
        reasons.append("Decision candidate policy_domain is not release_governance.")
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
        if review.decision_candidate_id != decision.decision_id:
            reasons.append("HumanReviewRecord candidate does not match the decision.")
        if review.metadata.get("review_semantics") != "candidate_only":
            reasons.append("HumanReviewRecord semantics is not candidate_only.")
        if review.metadata.get("formal_outcome_enabled") is not False:
            reasons.append("HumanReviewRecord does not disable formal outcome.")
        if review.metadata.get("release_action_enabled") is not False:
            reasons.append("HumanReviewRecord does not disable release action.")

    if outcome is None:
        reasons.append("GovernanceOutcome candidate is missing.")
    else:
        if outcome.decision_candidate_id != decision.decision_id:
            reasons.append("GovernanceOutcome candidate does not match the decision.")
        if review and outcome.human_review_id != review.review_id:
            reasons.append("GovernanceOutcome candidate does not match the review.")
        if outcome.outcome_semantics != "candidate_only":
            reasons.append("GovernanceOutcome candidate semantics is not candidate_only.")
        if outcome.formal_decision_required is not True:
            reasons.append("GovernanceOutcome candidate does not require formal decision.")
        if outcome.formal_outcome_enabled is not False:
            reasons.append("GovernanceOutcome candidate does not disable formal outcome.")
        if outcome.release_action_enabled is not False:
            reasons.append("GovernanceOutcome candidate does not disable release action.")
    return _dedupe(reasons)


def _required_confirmations(values: list[str] | None) -> list[str]:
    defaults = [
        "human_review_record_candidate",
        "governance_outcome_candidate",
        "operator_confirmation",
        "release_workflow_or_cli_confirmation",
    ]
    return _dedupe([*defaults, *(values or [])])


def _release_domain_metadata(
    *,
    decision: GovernanceDecision,
    review: HumanReviewRecordCandidate | None,
    outcome: GovernanceOutcomeCandidate | None,
    extra: dict[str, Any] | None,
) -> dict[str, Any]:
    decision_domain = _mapping(_mapping(decision.metadata).get("domain_metadata"))
    collected: dict[str, Any] = {}
    for key in (
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
    ):
        value = decision_domain.get(key, _mapping(decision.metadata).get(key))
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
