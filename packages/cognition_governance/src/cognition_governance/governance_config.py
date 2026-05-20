"""Governance configuration consumption boundary.

The boundary is intentionally structural: cognition_governance can consume a
governance config view without importing config_contexts or runtime/composition
packages.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from cognition_governance.models import (
    GovernanceCase,
    GovernanceDecision,
    GovernancePolicySet,
)

GOVERNANCE_CONFIG_DECISION_SHAPE_VERSION = "governance_config_decision_shape_v1"
GOVERNANCE_CONFIG_DECISION_BUILDER = "build_governance_decision_from_config"
GOVERNANCE_CONFIG_DECISION_CANDIDATE_SCOPE = "governance_config_decision_candidate"


def build_governance_policy_set_from_config(
    config_context: Any,
) -> GovernancePolicySet:
    """Build an existing governance policy set from a config context view."""

    profile = str(_read_value(config_context, "governance_profile", "default"))
    policy_refs = _as_string_list(_read_value(config_context, "policy_refs", ()))
    custom_metadata = _as_mapping(_read_value(config_context, "custom_metadata", {}))

    return GovernancePolicySet(
        policy_set_id=f"governance-config:{profile}",
        name=f"Governance Config Context: {profile}",
        policies=policy_refs,
        metadata={
            "config_context_kind": _read_value(
                config_context,
                "config_context_kind",
                "governance_config",
            ),
            "enabled": bool(_read_value(config_context, "enabled", True)),
            "mode": _read_value(config_context, "mode", "advisory"),
            "decision_level": _read_value(config_context, "decision_level", "candidate"),
            "required_evidence_refs": _as_string_list(
                _read_value(config_context, "required_evidence_refs", ())
            ),
            "block_on_violation": bool(
                _read_value(config_context, "block_on_violation", False)
            ),
            "audit_required": bool(_read_value(config_context, "audit_required", True)),
            "custom_metadata": custom_metadata,
            "config_context_consumed": True,
        },
    )


def build_governance_decision_from_config(
    *,
    config_context: Any,
    case: GovernanceCase,
    evidence_ids: Sequence[str] | None = None,
) -> GovernanceDecision:
    """Build a governance decision from config using existing governance models."""

    policy_set = build_governance_policy_set_from_config(config_context)
    enabled = bool(policy_set.metadata["enabled"])
    block_on_violation = bool(policy_set.metadata["block_on_violation"])
    required_evidence_refs = _as_string_list(
        policy_set.metadata.get("required_evidence_refs", ())
    )
    provided_evidence_ids = list(evidence_ids or case.evidence_refs)
    missing_evidence_refs = [
        evidence_ref
        for evidence_ref in required_evidence_refs
        if evidence_ref not in set(provided_evidence_ids)
    ]

    decision = "continue"
    rationale = "Governance config context is enabled and no blocking gap was found."
    composition_precondition_allowed = True

    if not enabled:
        decision = "defer"
        rationale = "Governance config context is disabled."
        composition_precondition_allowed = False
    elif missing_evidence_refs and block_on_violation:
        decision = "need_evidence"
        rationale = "Governance config context requires missing evidence."
        composition_precondition_allowed = False

    return GovernanceDecision(
        decision_id=f"{case.case_id}:governance-config",
        case_id=case.case_id,
        decision=decision,
        rationale=rationale,
        evidence_ids=provided_evidence_ids,
        policy_set_id=policy_set.policy_set_id,
        metadata={
            "decision_shape_version": GOVERNANCE_CONFIG_DECISION_SHAPE_VERSION,
            "decision_builder": GOVERNANCE_CONFIG_DECISION_BUILDER,
            "candidate_scope": GOVERNANCE_CONFIG_DECISION_CANDIDATE_SCOPE,
            "decision_semantics": "candidate_only",
            "candidate_only": True,
            "formal_decision_enabled": False,
            "policy_execution_enabled": False,
            "governance_outcome_enabled": False,
            "config_context_consumed": True,
            "composition_precondition_allowed": composition_precondition_allowed,
            "mode": policy_set.metadata["mode"],
            "decision_level": policy_set.metadata["decision_level"],
            "policy_refs": list(policy_set.policies),
            "required_evidence_refs": required_evidence_refs,
            "missing_evidence_refs": missing_evidence_refs,
            "block_on_violation": block_on_violation,
            "audit_required": policy_set.metadata["audit_required"],
            "custom_metadata": policy_set.metadata["custom_metadata"],
        },
    )


def make_governance_config_decision_candidate(
    *,
    config_context: Any,
    case: GovernanceCase,
    evidence_ids: Sequence[str] | None = None,
) -> GovernanceDecision:
    """Make a config governance decision candidate.

    Kept for backward-compatible candidate wording; the stable builder above
    owns the decision shape.
    """

    return build_governance_decision_from_config(
        config_context=config_context,
        case=case,
        evidence_ids=evidence_ids,
    )


def _read_value(source: Any, key: str, default: Any) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    if hasattr(source, "model_dump"):
        dumped = source.model_dump()
        if isinstance(dumped, Mapping):
            return dumped.get(key, default)
    return getattr(source, key, default)


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item) for item in value]
    return [str(value)]


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}
