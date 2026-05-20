"""Human review and outcome candidates for internal governance decisions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from cognition_governance.models import GovernanceDecision
from cognition_governance.unified_decision_candidate import (
    POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER,
    POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE,
    POLICY_DOMAIN_RELEASE_GOVERNANCE,
    UnifiedGovernanceDecisionCandidateResult,
    UnifiedGovernancePolicyDomain,
)


HumanReviewResultCandidate = Literal[
    "accept_candidate",
    "reject_candidate",
    "request_evidence",
    "request_fix",
    "defer",
]

HumanReviewStatusCandidate = Literal[
    "recorded",
    "superseded",
]

GovernanceOutcomeStatusCandidate = Literal[
    "open",
    "validated",
    "failed",
    "superseded",
    "deferred",
]

ALLOWED_HUMAN_REVIEW_RESULTS = [
    "accept_candidate",
    "reject_candidate",
    "request_evidence",
    "request_fix",
    "defer",
]

ALLOWED_OUTCOME_STATUS_CANDIDATES = [
    "open",
    "validated",
    "failed",
    "superseded",
    "deferred",
]

_ADK2_OUTCOME_METADATA_KEYS = [
    "workflow_name",
    "runtime_kind",
    "run_config_followup",
    "service_bundle_followup",
    "artifact_session_event_followup",
    "governance_modeling_followup",
    "runtime_boundary_fix",
]

_RELEASE_OUTCOME_METADATA_KEYS = [
    "target_version",
    "phase",
    "release_target",
    "provider_results",
    "public_surface_followup",
    "pypi_followup",
    "trusted_publishing_followup",
    "credential_followup",
    "release_action_refs",
    "post_release_verification_refs",
]

_PRODUCT_AGENT_OUTPUT_OUTCOME_METADATA_KEYS = [
    "product_gateway_request_id",
    "product_gateway_entry_kind",
    "product_gateway_status",
    "product_gateway_exit_code",
    "agent_advice_candidate_id",
    "agent_advice_status",
    "agent_advice_recommendation",
    "ready_for_review",
    "evidence_statuses",
    "missing_evidence",
    "warning_candidates",
    "block_candidates",
    "human_review_reasons",
    "summary_only",
    "refs_only",
    "candidate_only",
]

_SUPPORTED_POLICY_DOMAINS = {
    POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER,
    POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE,
    POLICY_DOMAIN_RELEASE_GOVERNANCE,
}

_FORBIDDEN_OBJECT_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "runtime_container",
    "composition",
)


class HumanReviewRecordCandidate(BaseModel):
    """Internal human review record candidate; it is not a decision action."""

    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(..., min_length=1)
    decision_candidate_id: str = Field(..., min_length=1)
    case_id: str = Field(..., min_length=1)
    reviewer: str = Field(..., min_length=1)
    review_status: HumanReviewStatusCandidate = "recorded"
    review_result: HumanReviewResultCandidate
    review_reasons: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    reviewed_at: str = Field(..., min_length=1)
    policy_domain: UnifiedGovernancePolicyDomain
    candidate_scope: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceOutcomeCandidate(BaseModel):
    """Internal outcome candidate; it is not a formal GovernanceOutcome."""

    model_config = ConfigDict(extra="forbid")

    outcome_candidate_id: str = Field(..., min_length=1)
    decision_candidate_id: str = Field(..., min_length=1)
    human_review_id: str = Field(..., min_length=1)
    case_id: str = Field(..., min_length=1)
    policy_domain: UnifiedGovernancePolicyDomain
    outcome_semantics: str = "candidate_only"
    formal_decision_required: bool = True
    formal_outcome_enabled: bool = False
    release_action_enabled: bool = False
    status_candidate: GovernanceOutcomeStatusCandidate = "open"
    summary: str = Field(..., min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    blocked_formal_outcome_reasons: list[str] = Field(default_factory=list)
    domain_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceOutcomeCandidateResult(BaseModel):
    """Internal candidate package; no formal outcome is produced."""

    model_config = ConfigDict(extra="forbid")

    human_review_record: HumanReviewRecordCandidate
    outcome_candidate: GovernanceOutcomeCandidate
    notes: list[str] = Field(default_factory=list)


def create_human_review_record_candidate(
    decision_candidate: UnifiedGovernanceDecisionCandidateResult
    | GovernanceDecision
    | dict[str, Any],
    *,
    reviewer: str,
    review_result: HumanReviewResultCandidate,
    review_reasons: list[str] | None = None,
    required_followups: list[str] | None = None,
    reviewed_at: str | None = None,
    review_status: HumanReviewStatusCandidate = "recorded",
    metadata: dict[str, Any] | None = None,
) -> HumanReviewRecordCandidate:
    """Record human review of a decision candidate without mutating it."""

    decision = _as_decision_candidate(decision_candidate)
    decision_metadata = _mapping(decision.metadata)
    return HumanReviewRecordCandidate(
        review_id=f"human-review-candidate-{uuid4()}",
        decision_candidate_id=decision.decision_id,
        case_id=decision.case_id,
        reviewer=reviewer,
        review_status=review_status,
        review_result=review_result,
        review_reasons=list(review_reasons or []),
        required_followups=list(required_followups or []),
        reviewed_at=reviewed_at or _now_utc_iso(),
        policy_domain=_policy_domain(decision),
        candidate_scope=_candidate_scope(decision),
        metadata={
            "review_semantics": "candidate_only",
            "decision_semantics": decision_metadata.get("decision_semantics"),
            "formal_decision_enabled": False,
            "policy_execution_enabled": False,
            "formal_outcome_enabled": False,
            "release_action_enabled": False,
            "allowed_review_results": list(ALLOWED_HUMAN_REVIEW_RESULTS),
            "review_result_boundary": _review_result_boundary(review_result),
            "does_not_mutate_decision_candidate": True,
            **_sanitize_mapping(metadata or {}),
        },
    )


def create_governance_outcome_candidate(
    decision_candidate: UnifiedGovernanceDecisionCandidateResult
    | GovernanceDecision
    | dict[str, Any],
    human_review_record: HumanReviewRecordCandidate | dict[str, Any],
    *,
    status_candidate: GovernanceOutcomeStatusCandidate | None = None,
    summary: str | None = None,
    evidence_refs: list[str] | None = None,
    domain_metadata: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> GovernanceOutcomeCandidateResult:
    """Create an outcome candidate from a decision candidate and review record."""

    decision = _as_decision_candidate(decision_candidate)
    review = _as_human_review_record(human_review_record)
    if review.decision_candidate_id != decision.decision_id:
        raise ValueError("HumanReviewRecord must reference the decision candidate.")

    resolved_status = status_candidate or _status_from_review_result(
        review.review_result
    )
    outcome = GovernanceOutcomeCandidate(
        outcome_candidate_id=f"governance-outcome-candidate-{uuid4()}",
        decision_candidate_id=decision.decision_id,
        human_review_id=review.review_id,
        case_id=decision.case_id,
        policy_domain=_policy_domain(decision),
        status_candidate=resolved_status,
        summary=summary or _outcome_summary(decision, review, resolved_status),
        evidence_refs=list(evidence_refs or decision.evidence_ids),
        blocked_formal_outcome_reasons=_blocked_formal_outcome_reasons(
            decision,
            review,
        ),
        domain_metadata=_outcome_domain_metadata(decision, domain_metadata),
        metadata={
            "outcome_semantics": "candidate_only",
            "formal_decision_required": True,
            "formal_outcome_enabled": False,
            "release_action_enabled": False,
            "decision_semantics": _mapping(decision.metadata).get(
                "decision_semantics"
            ),
            "human_review_result": review.review_result,
            "allowed_status_candidates": list(ALLOWED_OUTCOME_STATUS_CANDIDATES),
            "does_not_record_real_action_result": True,
            **_sanitize_mapping(metadata or {}),
        },
    )
    return GovernanceOutcomeCandidateResult(
        human_review_record=review,
        outcome_candidate=outcome,
        notes=[
            "Internal GovernanceOutcome candidate only.",
            "HumanReviewRecord candidate is required before the outcome candidate.",
            "No formal GovernanceDecision is produced.",
            "No formal GovernanceOutcome is produced.",
            "No release, block, pass, publish, upload, tag, or push action is executed.",
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
    value: HumanReviewRecordCandidate | dict[str, Any],
) -> HumanReviewRecordCandidate:
    if isinstance(value, HumanReviewRecordCandidate):
        return value
    if isinstance(value, dict):
        return HumanReviewRecordCandidate.model_validate(value)
    raise TypeError("HumanReviewRecordCandidate or compatible mapping is required.")


def _policy_domain(decision: GovernanceDecision) -> UnifiedGovernancePolicyDomain:
    value = _mapping(decision.metadata).get("policy_domain")
    if value in _SUPPORTED_POLICY_DOMAINS:
        return value
    if isinstance(value, str) and value:
        raise ValueError(f"Unsupported policy_domain for outcome candidate: {value}.")
    return POLICY_DOMAIN_RELEASE_GOVERNANCE


def _candidate_scope(decision: GovernanceDecision) -> str:
    value = _mapping(decision.metadata).get("candidate_scope")
    return value if isinstance(value, str) and value else "unknown_candidate_scope"


def _status_from_review_result(
    review_result: HumanReviewResultCandidate,
) -> GovernanceOutcomeStatusCandidate:
    if review_result in {"request_evidence", "request_fix", "defer"}:
        return "deferred"
    if review_result == "reject_candidate":
        return "failed"
    return "open"


def _review_result_boundary(review_result: str) -> str:
    boundaries = {
        "accept_candidate": "accept_candidate does not create a formal decision.",
        "reject_candidate": "reject_candidate does not execute block.",
        "request_evidence": "request_evidence does not execute any action.",
        "request_fix": "request_fix does not execute block.",
        "defer": "defer does not mean pass.",
    }
    return boundaries.get(review_result, "review result is candidate-only.")


def _outcome_summary(
    decision: GovernanceDecision,
    review: HumanReviewRecordCandidate,
    status_candidate: str,
) -> str:
    return (
        f"Governance outcome candidate for {decision.case_id}: "
        f"review_result={review.review_result}, "
        f"status_candidate={status_candidate}."
    )


def _blocked_formal_outcome_reasons(
    decision: GovernanceDecision,
    review: HumanReviewRecordCandidate,
) -> list[str]:
    policy_domain = _policy_domain(decision)
    reasons = [
        "Outcome output is candidate-only.",
        "Formal GovernanceDecision is not available.",
        "Formal GovernanceOutcome is disabled.",
    ]
    if policy_domain == POLICY_DOMAIN_RELEASE_GOVERNANCE:
        reasons.append("Release action boundary review is pending.")
    elif policy_domain == POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE:
        reasons.extend(
            [
                "Product-agent output action boundary review is pending.",
                "Product / agent execution remains disabled.",
            ]
        )
    decision_metadata = _mapping(decision.metadata)
    if decision_metadata.get("decision_semantics") != "candidate_only":
        reasons.append("Decision candidate semantics is not explicitly candidate_only.")
    if decision_metadata.get("formal_decision_enabled") is not False:
        reasons.append("Decision candidate does not disable formal decisions.")
    if review.metadata.get("review_semantics") != "candidate_only":
        reasons.append("Human review record is not explicitly candidate_only.")
    if review.review_result in {"request_evidence", "request_fix", "defer"}:
        reasons.append("Human review requires follow-up before any formal outcome.")
    return _dedupe(reasons)


def _outcome_domain_metadata(
    decision: GovernanceDecision,
    extra: dict[str, Any] | None,
) -> dict[str, Any]:
    policy_domain = _policy_domain(decision)
    decision_domain_metadata = _mapping(
        _mapping(decision.metadata).get("domain_metadata")
    )
    if policy_domain == POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER:
        keys = _ADK2_OUTCOME_METADATA_KEYS
    elif policy_domain == POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE:
        keys = _PRODUCT_AGENT_OUTPUT_OUTCOME_METADATA_KEYS
    else:
        keys = _RELEASE_OUTCOME_METADATA_KEYS
    collected: dict[str, Any] = {}
    for key in keys:
        value = decision_domain_metadata.get(key)
        if value is not None:
            collected[key] = _sanitize(value)
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
        "object_module": _sanitize_module(type(value).__module__),
    }


def _sanitize_module(module_name: str) -> str:
    if module_name.startswith(_FORBIDDEN_OBJECT_MODULE_PREFIXES):
        return "external_runtime_object"
    return module_name


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
