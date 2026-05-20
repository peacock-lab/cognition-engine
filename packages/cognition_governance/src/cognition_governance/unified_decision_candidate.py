"""Unified internal governance decision candidates."""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from cognition_governance.adk_workflow_runner_case_mapping import (
    ADK_WORKFLOW_RUNNER_CASE_TYPE,
)
from cognition_governance.adk_workflow_runner_decision_candidate import (
    ADK_WORKFLOW_RUNNER_DECISION_CANDIDATE_SCOPE,
    ADK_WORKFLOW_RUNNER_POLICY_SET_ID,
)
from cognition_governance.models import (
    GovernanceCase,
    GovernanceDecision,
    GovernanceEvidence,
    GovernancePolicySet,
)
from cognition_governance.product_agent_output_governance_mapping import (
    AGENT_TASK_ADVICE_PAYLOAD_EVIDENCE_TYPE,
    POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE,
    PRODUCT_AGENT_OUTPUT_GOVERNANCE_CASE_TYPE,
    PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_REF,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_EVIDENCE_TYPE,
)
from cognition_governance.release_governance_case_mapping import (
    RELEASE_GOVERNANCE_CASE_TYPE,
    RELEASE_GOVERNANCE_POLICY_REF,
)


POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER = "adk2_workflow_runner"
POLICY_DOMAIN_RELEASE_GOVERNANCE = "release_governance"
UNIFIED_DECISION_CANDIDATE_SCOPE = "unified_governance_decision_candidate"
RELEASE_GOVERNANCE_DECISION_CANDIDATE_SCOPE = (
    "release_governance_decision_candidate"
)
PRODUCT_AGENT_OUTPUT_GOVERNANCE_DECISION_CANDIDATE_SCOPE = (
    "product_agent_output_governance_decision_candidate"
)
RELEASE_GOVERNANCE_POLICY_SET_ID = RELEASE_GOVERNANCE_POLICY_REF
PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_SET_ID = (
    PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_REF
)

UnifiedGovernanceDecisionKindCandidate = Literal[
    "need_evidence",
    "defer",
    "fix",
    "continue",
]
UnifiedGovernancePolicyDomain = Literal[
    "adk2_workflow_runner",
    "release_governance",
    "product_agent_output_governance",
]

ALLOWED_UNIFIED_DECISION_KINDS = [
    "need_evidence",
    "defer",
    "fix",
    "continue",
]

_COMMON_RULE_CANDIDATES = [
    "evidence_completeness",
    "policy_set_presence_guard",
    "governance_boundary_guard",
    "human_review_required_guard",
    "candidate_only_guard",
    "formal_decision_disabled_guard",
    "governance_outcome_deferred_guard",
]

_ADK2_RULE_CANDIDATES = [
    "run_config_mapping_completeness",
    "service_bundle_source_completeness",
    "artifact_session_event_lifecycle_completeness",
    "adk_native_object_leakage_guard",
    "runtime_module_sanitization_guard",
]

_RELEASE_RULE_CANDIDATES = [
    "release_check_output_completeness",
    "release_provider_coverage",
    "public_surface_boundary_guard",
    "pypi_version_phase_guard",
    "release_note_tag_github_release_consistency_guard",
    "trusted_publishing_config_guard",
    "credential_presence_review_guard",
    "sensitive_release_output_redaction_guard",
]

_PRODUCT_AGENT_OUTPUT_RULE_CANDIDATES = [
    "product_gateway_summary_header_guard",
    "agent_task_advice_payload_header_guard",
    "product_agent_evidence_alignment_guard",
    "product_gateway_status_review_guard",
    "agent_recommendation_review_guard",
    "summary_only_guard",
    "refs_only_guard",
]

_ADK2_DOMAIN_METADATA_KEYS = [
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

_RELEASE_DOMAIN_METADATA_KEYS = [
    "script_name",
    "script_path",
    "provider_supported",
    "phase",
    "target_version",
    "final_status",
    "failure_codes",
    "issues_summary",
    "checks_summary",
    "status_counts",
    "sensitive_fields_omitted",
    "raw_output_digest",
    "release_target",
    "providers",
]

_PRODUCT_AGENT_OUTPUT_DOMAIN_METADATA_KEYS = [
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

_FORBIDDEN_OBJECT_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "runtime_container",
    "composition",
)


class UnifiedGovernancePolicySetCandidate(BaseModel):
    """Unified policy-set candidate wrapper; this is not a policy executor."""

    model_config = ConfigDict(extra="forbid")

    policy_set: GovernancePolicySet
    candidate_scope: str = UNIFIED_DECISION_CANDIDATE_SCOPE
    policy_domain: UnifiedGovernancePolicyDomain
    policy_status: str = "candidate_only"
    formal_decision_enabled: bool = False
    policy_execution_enabled: bool = False
    governance_outcome_enabled: bool = False
    public_contract: bool = False
    rule_candidates: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    domain_metadata: dict[str, Any] = Field(default_factory=dict)


class UnifiedGovernanceDecisionCandidateResult(BaseModel):
    """Unified internal decision candidate result; no outcome is produced."""

    model_config = ConfigDict(extra="forbid")

    policy_set_candidate: UnifiedGovernancePolicySetCandidate | None = None
    decision_candidate: GovernanceDecision
    notes: list[str] = Field(default_factory=list)


def build_unified_policy_set_candidate(
    *,
    policy_domain: UnifiedGovernancePolicyDomain,
    candidate_scope: str | None = None,
    policy_set_id: str | None = None,
    name: str | None = None,
    rule_candidates: list[str] | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> UnifiedGovernancePolicySetCandidate:
    """Build a unified policy-set candidate for a supported policy domain."""

    resolved_scope = candidate_scope or _default_candidate_scope(policy_domain)
    rules = rule_candidates or _default_rule_candidates(policy_domain)
    policy_set = GovernancePolicySet(
        policy_set_id=policy_set_id or _default_policy_set_id(policy_domain),
        name=name or _default_policy_set_name(policy_domain),
        policies=rules,
        metadata={
            "candidate_scope": resolved_scope,
            "policy_domain": policy_domain,
            "policy_status": "candidate_only",
            "formal_decision_enabled": False,
            "policy_execution_enabled": False,
            "governance_outcome_enabled": False,
            "public_contract": False,
            "rule_candidates": rules,
        },
    )
    return UnifiedGovernancePolicySetCandidate(
        policy_set=policy_set,
        candidate_scope=resolved_scope,
        policy_domain=policy_domain,
        rule_candidates=rules,
        notes=[
            "Internal unified policy-set candidate only.",
            "No policy execution is performed.",
            "No GovernanceOutcome is produced.",
        ],
        domain_metadata=_sanitize_mapping(domain_metadata or {}),
    )


def build_release_governance_policy_set_candidate() -> (
    UnifiedGovernancePolicySetCandidate
):
    """Build the Release Governance policy-set candidate."""

    return build_unified_policy_set_candidate(
        policy_domain=POLICY_DOMAIN_RELEASE_GOVERNANCE,
        candidate_scope=RELEASE_GOVERNANCE_DECISION_CANDIDATE_SCOPE,
        policy_set_id=RELEASE_GOVERNANCE_POLICY_SET_ID,
        name="Release Governance policy candidate",
    )


def build_product_agent_output_governance_policy_set_candidate() -> (
    UnifiedGovernancePolicySetCandidate
):
    """Build the Product-Agent output Governance policy-set candidate."""

    return build_unified_policy_set_candidate(
        policy_domain=POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE,
        candidate_scope=PRODUCT_AGENT_OUTPUT_GOVERNANCE_DECISION_CANDIDATE_SCOPE,
        policy_set_id=PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_SET_ID,
        name="Product-Agent output Governance policy candidate",
    )


def make_unified_governance_decision_candidate(
    governance_case: GovernanceCase | dict[str, Any],
    governance_evidence: GovernanceEvidence
    | dict[str, Any]
    | list[GovernanceEvidence | dict[str, Any]],
    *,
    policy_set_candidate: UnifiedGovernancePolicySetCandidate
    | GovernancePolicySet
    | dict[str, Any]
    | Any
    | None = None,
    candidate_scope: str | None = None,
    policy_domain: UnifiedGovernancePolicyDomain | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> UnifiedGovernanceDecisionCandidateResult:
    """Create a unified GovernanceDecision candidate for supported domains."""

    parsed_case = _as_governance_case(governance_case)
    evidence_items = _as_governance_evidence_list(governance_evidence)
    resolved_domain = policy_domain or _infer_policy_domain(parsed_case)
    parsed_policy_set = _as_unified_policy_set_candidate(
        policy_set_candidate,
        fallback_policy_domain=resolved_domain,
    )
    resolved_scope = (
        candidate_scope
        or (parsed_policy_set.candidate_scope if parsed_policy_set else None)
        or _default_candidate_scope(resolved_domain)
    )
    missing_evidence = _missing_evidence(
        governance_case=parsed_case,
        governance_evidence=evidence_items,
        policy_domain=resolved_domain,
    )
    human_review_reasons = _human_review_reasons(
        governance_case=parsed_case,
        governance_evidence=evidence_items,
        policy_set_candidate=parsed_policy_set,
        policy_domain=resolved_domain,
        missing_evidence=missing_evidence,
    )
    blocked_formal_decision_reasons = _blocked_formal_decision_reasons(
        governance_case=parsed_case,
        governance_evidence=evidence_items,
        policy_set_candidate=parsed_policy_set,
        missing_evidence=missing_evidence,
    )
    decision_kind = _decision_kind(
        governance_case=parsed_case,
        governance_evidence=evidence_items,
        policy_set_candidate=parsed_policy_set,
        policy_domain=resolved_domain,
        missing_evidence=missing_evidence,
        human_review_reasons=human_review_reasons,
    )
    policy_set = parsed_policy_set.policy_set if parsed_policy_set else None
    merged_domain_metadata = _domain_metadata(
        governance_case=parsed_case,
        governance_evidence=evidence_items,
        policy_domain=resolved_domain,
        extra=domain_metadata,
    )

    decision = GovernanceDecision(
        decision_id=(
            f"{resolved_domain.replace('_', '-')}-unified-decision-candidate-"
            f"{uuid4()}"
        ),
        case_id=parsed_case.case_id,
        decision=decision_kind,
        rationale=_rationale(
            governance_case=parsed_case,
            governance_evidence=evidence_items,
            policy_domain=resolved_domain,
            decision_kind=decision_kind,
            policy_set=policy_set,
            missing_evidence=missing_evidence,
        ),
        evidence_ids=_evidence_ids(parsed_case, evidence_items),
        policy_set_id=policy_set.policy_set_id if policy_set else None,
        metadata={
            "candidate_scope": resolved_scope,
            "decision_semantics": "candidate_only",
            "formal_decision_enabled": False,
            "policy_execution_enabled": False,
            "governance_outcome_enabled": False,
            "human_review_required": bool(human_review_reasons),
            "human_review_reasons": human_review_reasons,
            "missing_evidence": missing_evidence,
            "blocked_formal_decision_reasons": blocked_formal_decision_reasons,
            "policy_set_candidate_id": policy_set.policy_set_id if policy_set else None,
            "allowed_decision_kinds": list(ALLOWED_UNIFIED_DECISION_KINDS),
            "policy_domain": resolved_domain,
            "case_type": parsed_case.case_type,
            "domain_metadata": merged_domain_metadata,
            "continue_semantics": (
                "continue means the candidate can proceed to later governance "
                "review; it is not a pass or publishing permission."
            ),
        },
    )

    return UnifiedGovernanceDecisionCandidateResult(
        policy_set_candidate=parsed_policy_set,
        decision_candidate=decision,
        notes=[
            "Internal unified GovernanceDecision candidate only.",
            "No formal decision is produced.",
            "No policy execution is performed.",
            "No GovernanceOutcome is produced.",
        ],
    )


def _decision_kind(
    *,
    governance_case: GovernanceCase,
    governance_evidence: list[GovernanceEvidence],
    policy_set_candidate: UnifiedGovernancePolicySetCandidate | None,
    policy_domain: UnifiedGovernancePolicyDomain,
    missing_evidence: list[str],
    human_review_reasons: list[str],
) -> UnifiedGovernanceDecisionKindCandidate:
    if missing_evidence:
        return "need_evidence"
    if policy_set_candidate is None or not governance_case.policy_refs:
        return "defer"
    if human_review_reasons:
        return "fix"
    if policy_domain == POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER:
        if _risk_level(governance_case) in {"medium", "high"}:
            return "fix"
        if _findings_by_severity(governance_case, {"warning", "error"}):
            return "fix"
    return "continue"


def _missing_evidence(
    *,
    governance_case: GovernanceCase,
    governance_evidence: list[GovernanceEvidence],
    policy_domain: UnifiedGovernancePolicyDomain,
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

    if policy_domain == POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER:
        missing.extend(_missing_adk2_evidence(governance_evidence))
    elif policy_domain == POLICY_DOMAIN_RELEASE_GOVERNANCE:
        missing.extend(_missing_release_evidence(governance_case))
    elif policy_domain == POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE:
        missing.extend(_missing_product_agent_output_evidence(governance_case))
    return _dedupe(missing)


def _missing_adk2_evidence(
    governance_evidence: list[GovernanceEvidence],
) -> list[str]:
    missing: list[str] = []
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
    return missing


def _missing_release_evidence(governance_case: GovernanceCase) -> list[str]:
    value = governance_case.metadata.get("missing_evidence")
    return [str(item) for item in _list(value) if item]


def _missing_product_agent_output_evidence(
    governance_case: GovernanceCase,
) -> list[str]:
    value = governance_case.metadata.get("missing_evidence")
    return [str(item) for item in _list(value) if item]


def _human_review_reasons(
    *,
    governance_case: GovernanceCase,
    governance_evidence: list[GovernanceEvidence],
    policy_set_candidate: UnifiedGovernancePolicySetCandidate | None,
    policy_domain: UnifiedGovernancePolicyDomain,
    missing_evidence: list[str],
) -> list[str]:
    reasons: list[str] = []
    if policy_set_candidate is None:
        reasons.append("PolicySet candidate was not provided.")
    elif policy_set_candidate.policy_domain != policy_domain:
        reasons.append("PolicySet candidate policy_domain does not match the case.")
    if not governance_case.policy_refs:
        reasons.append("GovernanceCase policy_refs is empty.")
    if missing_evidence:
        reasons.append("Governance evidence is incomplete.")

    case_human_review_reasons = _list(governance_case.metadata.get("human_review_reasons"))
    reasons.extend(str(reason) for reason in case_human_review_reasons if reason)
    reasons.extend(_candidate_list_reasons(governance_case.metadata, "warning_candidates"))
    reasons.extend(_candidate_list_reasons(governance_case.metadata, "block_candidates"))

    if policy_domain == POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER:
        if governance_case.case_type != ADK_WORKFLOW_RUNNER_CASE_TYPE:
            reasons.append("GovernanceCase case_type is not the ADK2 WorkflowRunner case type.")
        risk_level = _risk_level(governance_case)
        if risk_level in {"medium", "high"}:
            reasons.append(f"GovernanceCase risk_level is {risk_level}.")
        for finding in _findings_by_severity(governance_case, {"warning", "error"}):
            reasons.append(
                f"Finding requires review: {finding.get('code') or 'unknown'}."
            )
    elif policy_domain == POLICY_DOMAIN_RELEASE_GOVERNANCE:
        if governance_case.case_type != RELEASE_GOVERNANCE_CASE_TYPE:
            reasons.append("GovernanceCase case_type is not the Release Governance case type.")
    elif policy_domain == POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE:
        if governance_case.case_type != PRODUCT_AGENT_OUTPUT_GOVERNANCE_CASE_TYPE:
            reasons.append(
                "GovernanceCase case_type is not the Product-Agent output case type."
            )
        if governance_case.metadata.get("summary_only") is not True:
            reasons.append("Product-agent output case must remain summary_only.")
        if governance_case.metadata.get("refs_only") is not True:
            reasons.append("Product-agent output case must remain refs_only.")

    for evidence in governance_evidence:
        metadata_repr = repr(evidence.metadata)
        if "external_runtime_object" in metadata_repr:
            reasons.append("Governance evidence contains summarized external runtime objects.")
        if any(prefix in metadata_repr for prefix in _FORBIDDEN_OBJECT_MODULE_PREFIXES):
            reasons.append("Governance evidence may contain unsanitized runtime module names.")
        if _list(evidence.metadata.get("warnings")):
            reasons.append(f"Governance evidence has warnings: {evidence.evidence_id}.")
        if policy_domain == POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE:
            if evidence.evidence_type not in {
                PRODUCT_GATEWAY_RESPONSE_SUMMARY_EVIDENCE_TYPE,
                AGENT_TASK_ADVICE_PAYLOAD_EVIDENCE_TYPE,
            }:
                reasons.append(
                    f"Unsupported product-agent output evidence: {evidence.evidence_id}."
                )
            if evidence.metadata.get("summary_only") is not True:
                reasons.append(
                    f"Product-agent evidence must remain summary_only: {evidence.evidence_id}."
                )
            if evidence.metadata.get("refs_only") is not True:
                reasons.append(
                    f"Product-agent evidence must remain refs_only: {evidence.evidence_id}."
                )
        reasons.extend(_candidate_list_reasons(evidence.metadata, "warning_candidates"))
        reasons.extend(_candidate_list_reasons(evidence.metadata, "block_candidates"))
        reasons.extend(
            str(reason)
            for reason in _list(evidence.metadata.get("human_review_reasons"))
            if reason
        )
    return _dedupe(reasons)


def _blocked_formal_decision_reasons(
    *,
    governance_case: GovernanceCase,
    governance_evidence: list[GovernanceEvidence],
    policy_set_candidate: UnifiedGovernancePolicySetCandidate | None,
    missing_evidence: list[str],
) -> list[str]:
    reasons = [
        "Decision output is candidate-only.",
        "PolicySet is candidate-only.",
        "Policy execution is disabled.",
        "GovernanceOutcome is out of scope.",
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
    policy_domain: str,
    decision_kind: str,
    policy_set: GovernancePolicySet | None,
    missing_evidence: list[str],
) -> str:
    policy_text = policy_set.policy_set_id if policy_set else "missing policy candidate"
    evidence_count = len(governance_evidence)
    if missing_evidence:
        return (
            f"Unified decision candidate is {decision_kind} for "
            f"{governance_case.case_id} in {policy_domain}: evidence completeness "
            f"needs attention under {policy_text}; evidence_count={evidence_count}."
        )
    return (
        f"Unified decision candidate is {decision_kind} for "
        f"{governance_case.case_id} in {policy_domain}: case and evidence summaries "
        f"were evaluated under {policy_text}; evidence_count={evidence_count}."
    )


def _domain_metadata(
    *,
    governance_case: GovernanceCase,
    governance_evidence: list[GovernanceEvidence],
    policy_domain: UnifiedGovernancePolicyDomain,
    extra: dict[str, Any] | None,
) -> dict[str, Any]:
    if policy_domain == POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER:
        keys = _ADK2_DOMAIN_METADATA_KEYS
    elif policy_domain == POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE:
        keys = _PRODUCT_AGENT_OUTPUT_DOMAIN_METADATA_KEYS
    else:
        keys = _RELEASE_DOMAIN_METADATA_KEYS
    collected: dict[str, Any] = {}
    for key in keys:
        case_value = governance_case.context.get(key, governance_case.metadata.get(key))
        if case_value is not None:
            collected[key] = _sanitize(case_value)

    evidence_items: list[dict[str, Any]] = []
    for evidence in governance_evidence:
        evidence_summary: dict[str, Any] = {"evidence_id": evidence.evidence_id}
        for key in keys:
            value = evidence.metadata.get(key)
            if value is not None:
                evidence_summary[key] = _sanitize(value)
        evidence_items.append(evidence_summary)
    if evidence_items:
        collected["evidence"] = evidence_items
    if extra:
        collected["extra"] = _sanitize_mapping(extra)
    return collected


def _as_unified_policy_set_candidate(
    value: UnifiedGovernancePolicySetCandidate
    | GovernancePolicySet
    | dict[str, Any]
    | Any
    | None,
    *,
    fallback_policy_domain: UnifiedGovernancePolicyDomain,
) -> UnifiedGovernancePolicySetCandidate | None:
    if value is None:
        return None
    if isinstance(value, UnifiedGovernancePolicySetCandidate):
        return value
    if isinstance(value, GovernancePolicySet):
        return _wrap_policy_set(value, fallback_policy_domain=fallback_policy_domain)
    if isinstance(value, dict):
        if "policy_set" in value and "policy_domain" in value:
            return UnifiedGovernancePolicySetCandidate.model_validate(value)
        if "policy_set" in value:
            policy_set = GovernancePolicySet.model_validate(value["policy_set"])
            return _wrap_policy_set(policy_set, fallback_policy_domain=fallback_policy_domain)
        return _wrap_policy_set(
            GovernancePolicySet.model_validate(value),
            fallback_policy_domain=fallback_policy_domain,
        )
    if hasattr(value, "policy_set"):
        policy_set = getattr(value, "policy_set")
        if isinstance(policy_set, GovernancePolicySet):
            return _wrap_policy_set(policy_set, fallback_policy_domain=fallback_policy_domain)
    raise TypeError("PolicySet candidate, GovernancePolicySet, or mapping is required.")


def _wrap_policy_set(
    policy_set: GovernancePolicySet,
    *,
    fallback_policy_domain: UnifiedGovernancePolicyDomain,
) -> UnifiedGovernancePolicySetCandidate:
    domain = _infer_policy_domain_from_policy_set(policy_set) or fallback_policy_domain
    scope = _plain_str(policy_set.metadata.get("candidate_scope")) or _default_candidate_scope(domain)
    rules = list(policy_set.policies)
    return UnifiedGovernancePolicySetCandidate(
        policy_set=policy_set,
        candidate_scope=scope,
        policy_domain=domain,
        policy_status=_plain_str(policy_set.metadata.get("policy_status"))
        or "candidate_only",
        formal_decision_enabled=False,
        policy_execution_enabled=False,
        governance_outcome_enabled=False,
        public_contract=False,
        rule_candidates=rules,
        notes=[
            "Wrapped existing policy-set candidate in the unified candidate shell.",
            "No policy execution is performed.",
        ],
        domain_metadata=_sanitize_mapping(policy_set.metadata),
    )


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


def _default_candidate_scope(policy_domain: UnifiedGovernancePolicyDomain) -> str:
    if policy_domain == POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER:
        return ADK_WORKFLOW_RUNNER_DECISION_CANDIDATE_SCOPE
    if policy_domain == POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE:
        return PRODUCT_AGENT_OUTPUT_GOVERNANCE_DECISION_CANDIDATE_SCOPE
    return RELEASE_GOVERNANCE_DECISION_CANDIDATE_SCOPE


def _default_policy_set_id(policy_domain: UnifiedGovernancePolicyDomain) -> str:
    if policy_domain == POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER:
        return ADK_WORKFLOW_RUNNER_POLICY_SET_ID
    if policy_domain == POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE:
        return PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_SET_ID
    return RELEASE_GOVERNANCE_POLICY_SET_ID


def _default_policy_set_name(policy_domain: UnifiedGovernancePolicyDomain) -> str:
    if policy_domain == POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER:
        return "ADK2 WorkflowRunner governance policy candidate"
    if policy_domain == POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE:
        return "Product-Agent output Governance policy candidate"
    return "Release Governance policy candidate"


def _default_rule_candidates(policy_domain: UnifiedGovernancePolicyDomain) -> list[str]:
    if policy_domain == POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER:
        return list(_COMMON_RULE_CANDIDATES + _ADK2_RULE_CANDIDATES)
    if policy_domain == POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE:
        return list(_COMMON_RULE_CANDIDATES + _PRODUCT_AGENT_OUTPUT_RULE_CANDIDATES)
    return list(_COMMON_RULE_CANDIDATES + _RELEASE_RULE_CANDIDATES)


def _infer_policy_domain(governance_case: GovernanceCase) -> UnifiedGovernancePolicyDomain:
    if governance_case.case_type == ADK_WORKFLOW_RUNNER_CASE_TYPE:
        return POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER
    if governance_case.case_type == RELEASE_GOVERNANCE_CASE_TYPE:
        return POLICY_DOMAIN_RELEASE_GOVERNANCE
    if governance_case.case_type == PRODUCT_AGENT_OUTPUT_GOVERNANCE_CASE_TYPE:
        return POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE
    metadata_domain = _plain_str(governance_case.metadata.get("policy_domain"))
    if metadata_domain in {
        POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER,
        POLICY_DOMAIN_RELEASE_GOVERNANCE,
        POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE,
    }:
        return metadata_domain
    return POLICY_DOMAIN_RELEASE_GOVERNANCE


def _infer_policy_domain_from_policy_set(
    policy_set: GovernancePolicySet,
) -> UnifiedGovernancePolicyDomain | None:
    metadata_domain = _plain_str(policy_set.metadata.get("policy_domain"))
    if metadata_domain in {
        POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER,
        POLICY_DOMAIN_RELEASE_GOVERNANCE,
        POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE,
    }:
        return metadata_domain
    if policy_set.policy_set_id == ADK_WORKFLOW_RUNNER_POLICY_SET_ID:
        return POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER
    if policy_set.policy_set_id == RELEASE_GOVERNANCE_POLICY_SET_ID:
        return POLICY_DOMAIN_RELEASE_GOVERNANCE
    if policy_set.policy_set_id == PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_SET_ID:
        return POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE
    return None


def _evidence_ids(
    governance_case: GovernanceCase,
    governance_evidence: list[GovernanceEvidence],
) -> list[str]:
    ids = list(governance_case.evidence_refs)
    ids.extend(evidence.evidence_id for evidence in governance_evidence)
    return _dedupe(ids)


def _findings_by_severity(
    governance_case: GovernanceCase,
    severities: set[str],
) -> list[dict[str, Any]]:
    return [
        finding
        for finding in _findings(governance_case)
        if finding.get("severity") in severities
    ]


def _findings(governance_case: GovernanceCase) -> list[dict[str, Any]]:
    return [_mapping(item) for item in _list(governance_case.metadata.get("findings"))]


def _risk_level(governance_case: GovernanceCase) -> str | None:
    return _plain_str(governance_case.context.get("risk_level"))


def _candidate_list_reasons(metadata: dict[str, Any], key: str) -> list[str]:
    values = _list(metadata.get(key))
    return [f"{key} requires review: {value}." for value in values if value]


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _plain_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


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
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped
