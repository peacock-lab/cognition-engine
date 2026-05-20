"""Decision candidates for ADK2 WorkflowRunner governance cases."""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from cognition_governance.adk_workflow_runner_case_mapping import (
    ADK_WORKFLOW_RUNNER_CASE_TYPE,
)
from cognition_governance.models import (
    GovernanceCase,
    GovernanceDecision,
    GovernanceEvidence,
    GovernancePolicySet,
)


ADK_WORKFLOW_RUNNER_POLICY_SET_ID = "policy-adk2-workflow-runner-governance"
ADK_WORKFLOW_RUNNER_DECISION_CANDIDATE_SCOPE = (
    "adk2_workflow_runner_decision_candidate"
)
AdkWorkflowRunnerDecisionKindCandidate = Literal[
    "need_evidence",
    "defer",
    "fix",
    "continue",
]

_FORBIDDEN_OBJECT_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "runtime_container",
    "composition",
)


class AdkWorkflowRunnerPolicySetCandidate(BaseModel):
    """Internal ADK2 WorkflowRunner policy-set candidate."""

    model_config = ConfigDict(extra="forbid")

    policy_set: GovernancePolicySet
    candidate_scope: str = ADK_WORKFLOW_RUNNER_DECISION_CANDIDATE_SCOPE
    notes: list[str] = Field(default_factory=list)


class AdkWorkflowRunnerDecisionCandidateResult(BaseModel):
    """Internal decision candidate result; no follow-up outcome is produced."""

    model_config = ConfigDict(extra="forbid")

    policy_set_candidate: AdkWorkflowRunnerPolicySetCandidate | None = None
    decision_candidate: GovernanceDecision
    notes: list[str] = Field(default_factory=list)


def build_adk_workflow_runner_policy_set_candidate() -> (
    AdkWorkflowRunnerPolicySetCandidate
):
    """Build the internal ADK2 WorkflowRunner policy-set candidate."""

    return AdkWorkflowRunnerPolicySetCandidate(
        policy_set=GovernancePolicySet(
            policy_set_id=ADK_WORKFLOW_RUNNER_POLICY_SET_ID,
            name="ADK2 WorkflowRunner governance policy candidate",
            policies=[
                "evidence_completeness",
                "run_config_mapping_completeness",
                "service_bundle_source_completeness",
                "artifact_session_event_lifecycle_completeness",
                "adk_native_object_leakage_guard",
                "governance_boundary_guard",
                "policy_set_presence_guard",
            ],
            metadata={
                "candidate_scope": ADK_WORKFLOW_RUNNER_DECISION_CANDIDATE_SCOPE,
                "policy_status": "candidate_only",
                "formal_decision_enabled": False,
                "governance_outcome_enabled": False,
                "public_contract": False,
            },
        ),
        notes=[
            "Internal policy-set candidate only.",
            "No policy execution is performed.",
            "No follow-up outcome is produced.",
        ],
    )


def make_adk_workflow_runner_decision_candidate(
    governance_case: GovernanceCase | dict[str, Any],
    governance_evidence: GovernanceEvidence
    | dict[str, Any]
    | list[GovernanceEvidence | dict[str, Any]],
    *,
    policy_set_candidate: AdkWorkflowRunnerPolicySetCandidate
    | GovernancePolicySet
    | dict[str, Any]
    | None = None,
) -> AdkWorkflowRunnerDecisionCandidateResult:
    """Create an internal GovernanceDecision candidate for ADK2 WorkflowRunner."""

    parsed_case = _as_governance_case(governance_case)
    evidence_items = _as_governance_evidence_list(governance_evidence)
    parsed_policy_set = _as_policy_set_candidate(policy_set_candidate)
    decision_kind = _decision_kind(
        governance_case=parsed_case,
        governance_evidence=evidence_items,
        policy_set_candidate=parsed_policy_set,
    )
    missing_evidence = _missing_evidence(parsed_case, evidence_items)
    human_review_reasons = _human_review_reasons(
        governance_case=parsed_case,
        governance_evidence=evidence_items,
        policy_set_candidate=parsed_policy_set,
        missing_evidence=missing_evidence,
    )
    formal_decision_reasons = _formal_decision_reasons(
        governance_case=parsed_case,
        governance_evidence=evidence_items,
        policy_set_candidate=parsed_policy_set,
        missing_evidence=missing_evidence,
    )
    policy_set = parsed_policy_set.policy_set if parsed_policy_set else None

    decision = GovernanceDecision(
        decision_id=f"adk-workflow-runner-decision-candidate-{uuid4()}",
        case_id=parsed_case.case_id,
        decision=decision_kind,
        rationale=_rationale(
            governance_case=parsed_case,
            governance_evidence=evidence_items,
            decision_kind=decision_kind,
            policy_set=policy_set,
            missing_evidence=missing_evidence,
        ),
        evidence_ids=_evidence_ids(parsed_case, evidence_items),
        policy_set_id=policy_set.policy_set_id if policy_set else None,
        metadata={
            "candidate_scope": ADK_WORKFLOW_RUNNER_DECISION_CANDIDATE_SCOPE,
            "decision_semantics": "candidate_only",
            "formal_decision_enabled": False,
            "policy_execution_enabled": False,
            "governance_outcome_enabled": False,
            "human_review_required": bool(human_review_reasons),
            "human_review_reasons": human_review_reasons,
            "missing_evidence": missing_evidence,
            "blocked_formal_decision_reasons": formal_decision_reasons,
            "policy_set_candidate_id": policy_set.policy_set_id if policy_set else None,
            "allowed_decision_kinds": [
                "need_evidence",
                "defer",
                "fix",
                "continue",
            ],
            "case_type": parsed_case.case_type,
            "risk_level": _plain_str(parsed_case.context.get("risk_level")),
        },
    )

    return AdkWorkflowRunnerDecisionCandidateResult(
        policy_set_candidate=parsed_policy_set,
        decision_candidate=decision,
        notes=[
            "Internal ADK2 WorkflowRunner decision candidate only.",
            "No policy execution is performed.",
            "No follow-up outcome is produced.",
        ],
    )


def _decision_kind(
    *,
    governance_case: GovernanceCase,
    governance_evidence: list[GovernanceEvidence],
    policy_set_candidate: AdkWorkflowRunnerPolicySetCandidate | None,
) -> AdkWorkflowRunnerDecisionKindCandidate:
    missing_evidence = _missing_evidence(governance_case, governance_evidence)
    findings = _findings(governance_case)
    severities = {finding.get("severity") for finding in findings}
    risk_level = _plain_str(governance_case.context.get("risk_level"))

    if missing_evidence:
        return "need_evidence"
    if policy_set_candidate is None or not governance_case.policy_refs:
        return "defer"
    if "error" in severities or "warning" in severities or risk_level in {
        "medium",
        "high",
    }:
        return "fix"
    return "continue"


def _missing_evidence(
    governance_case: GovernanceCase,
    governance_evidence: list[GovernanceEvidence],
) -> list[str]:
    missing: list[str] = []
    if not governance_case.evidence_refs:
        missing.append("governance_case.evidence_refs")
    if not governance_evidence:
        missing.append("governance_evidence")
        return missing

    evidence_ids = {item.evidence_id for item in governance_evidence}
    for evidence_ref in governance_case.evidence_refs:
        if evidence_ref not in evidence_ids:
            missing.append(f"governance_evidence:{evidence_ref}")

    for evidence in governance_evidence:
        metadata = evidence.metadata
        run_config = _mapping(metadata.get("run_config"))
        service_bundle = _mapping(metadata.get("service_bundle"))
        artifact_summary = _mapping(metadata.get("artifact_summary"))
        session_summary = _mapping(metadata.get("session_summary"))
        event_summary = _mapping(metadata.get("event_summary"))

        if not run_config:
            missing.append(f"{evidence.evidence_id}.run_config")
        elif not _list(run_config.get("mapped_fields")):
            missing.append(f"{evidence.evidence_id}.run_config.mapped_fields")
        if not service_bundle:
            missing.append(f"{evidence.evidence_id}.service_bundle")
        elif not service_bundle.get("source"):
            missing.append(f"{evidence.evidence_id}.service_bundle.source")
        if not artifact_summary or int(artifact_summary.get("artifact_count") or 0) <= 0:
            missing.append(f"{evidence.evidence_id}.artifact_lifecycle")
        if not session_summary.get("session_id"):
            missing.append(f"{evidence.evidence_id}.session_lifecycle")
        if int(event_summary.get("event_count") or 0) <= 0:
            missing.append(f"{evidence.evidence_id}.event_lifecycle")

    return _dedupe(missing)


def _human_review_reasons(
    *,
    governance_case: GovernanceCase,
    governance_evidence: list[GovernanceEvidence],
    policy_set_candidate: AdkWorkflowRunnerPolicySetCandidate | None,
    missing_evidence: list[str],
) -> list[str]:
    reasons: list[str] = []
    if governance_case.case_type != ADK_WORKFLOW_RUNNER_CASE_TYPE:
        reasons.append("GovernanceCase case_type is not the ADK2 WorkflowRunner case type.")
    if policy_set_candidate is None:
        reasons.append("PolicySet candidate was not provided.")
    if not governance_case.policy_refs:
        reasons.append("GovernanceCase policy_refs is empty.")
    risk_level = _plain_str(governance_case.context.get("risk_level"))
    if risk_level in {"medium", "high"}:
        reasons.append(f"GovernanceCase risk_level is {risk_level}.")
    for finding in _findings(governance_case):
        if finding.get("severity") in {"warning", "error"}:
            reasons.append(
                f"Finding requires review: {finding.get('code') or 'unknown'}."
            )
    if missing_evidence:
        reasons.append("Governance evidence is incomplete.")
    for evidence in governance_evidence:
        metadata_repr = repr(evidence.metadata)
        if "external_runtime_object" in metadata_repr:
            reasons.append("Governance evidence contains summarized external runtime objects.")
        if any(prefix in metadata_repr for prefix in _FORBIDDEN_OBJECT_MODULE_PREFIXES):
            reasons.append("Governance evidence may contain unsanitized runtime module names.")
        if _list(evidence.metadata.get("warnings")):
            reasons.append(f"Governance evidence has warnings: {evidence.evidence_id}.")
    return _dedupe(reasons)


def _formal_decision_reasons(
    *,
    governance_case: GovernanceCase,
    governance_evidence: list[GovernanceEvidence],
    policy_set_candidate: AdkWorkflowRunnerPolicySetCandidate | None,
    missing_evidence: list[str],
) -> list[str]:
    reasons = [
        "Decision output is candidate-only.",
        "PolicySet is candidate-only.",
        "Policy execution is disabled.",
        "Follow-up outcome is out of scope.",
    ]
    if policy_set_candidate is None:
        reasons.append("PolicySet candidate is missing.")
    if not governance_case.policy_refs:
        reasons.append("GovernanceCase is not bound to a policy reference.")
    if any(evidence.content_ref is None for evidence in governance_evidence):
        reasons.append("GovernanceEvidence content_ref is not yet stable.")
    if missing_evidence:
        reasons.append("Governance evidence completeness checks are not satisfied.")
    return _dedupe(reasons)


def _rationale(
    *,
    governance_case: GovernanceCase,
    governance_evidence: list[GovernanceEvidence],
    decision_kind: str,
    policy_set: GovernancePolicySet | None,
    missing_evidence: list[str],
) -> str:
    policy_text = policy_set.policy_set_id if policy_set else "missing policy candidate"
    evidence_count = len(governance_evidence)
    if missing_evidence:
        return (
            f"ADK2 WorkflowRunner decision candidate is {decision_kind} for "
            f"{governance_case.case_id}: evidence completeness needs attention "
            f"under {policy_text}; evidence_count={evidence_count}."
        )
    return (
        f"ADK2 WorkflowRunner decision candidate is {decision_kind} for "
        f"{governance_case.case_id}: case and evidence summaries were evaluated "
        f"under {policy_text}; evidence_count={evidence_count}."
    )


def _evidence_ids(
    governance_case: GovernanceCase,
    governance_evidence: list[GovernanceEvidence],
) -> list[str]:
    ids = list(governance_case.evidence_refs)
    ids.extend(evidence.evidence_id for evidence in governance_evidence)
    return _dedupe(ids)


def _findings(governance_case: GovernanceCase) -> list[dict[str, Any]]:
    return [_mapping(item) for item in _list(governance_case.metadata.get("findings"))]


def _as_governance_case(value: GovernanceCase | dict[str, Any]) -> GovernanceCase:
    if isinstance(value, GovernanceCase):
        return value
    if isinstance(value, dict):
        return GovernanceCase.model_validate(value)
    raise TypeError("GovernanceCase or compatible mapping is required.")


def _as_governance_evidence_list(
    value: GovernanceEvidence
    | dict[str, Any]
    | list[GovernanceEvidence | dict[str, Any]],
) -> list[GovernanceEvidence]:
    values = value if isinstance(value, list) else [value]
    return [_as_governance_evidence(item) for item in values]


def _as_governance_evidence(
    value: GovernanceEvidence | dict[str, Any],
) -> GovernanceEvidence:
    if isinstance(value, GovernanceEvidence):
        return value
    if isinstance(value, dict):
        return GovernanceEvidence.model_validate(value)
    raise TypeError("GovernanceEvidence or compatible mapping is required.")


def _as_policy_set_candidate(
    value: AdkWorkflowRunnerPolicySetCandidate | GovernancePolicySet | dict[str, Any] | None,
) -> AdkWorkflowRunnerPolicySetCandidate | None:
    if value is None:
        return None
    if isinstance(value, AdkWorkflowRunnerPolicySetCandidate):
        return value
    if isinstance(value, GovernancePolicySet):
        return AdkWorkflowRunnerPolicySetCandidate(policy_set=value)
    if isinstance(value, dict):
        if "policy_set" in value:
            return AdkWorkflowRunnerPolicySetCandidate.model_validate(value)
        return AdkWorkflowRunnerPolicySetCandidate(
            policy_set=GovernancePolicySet.model_validate(value)
        )
    raise TypeError("PolicySet candidate, GovernancePolicySet, or mapping is required.")


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _plain_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped
