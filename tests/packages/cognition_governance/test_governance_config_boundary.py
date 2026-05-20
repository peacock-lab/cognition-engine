from __future__ import annotations

import re
import sys
from pathlib import Path

CONFIG_CONTEXTS_SRC = (
    Path(__file__).resolve().parents[3] / "packages" / "config_contexts" / "src"
)
PACKAGE_SRC = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "cognition_governance"
    / "src"
)
sys.path.insert(0, str(CONFIG_CONTEXTS_SRC))
sys.path.insert(0, str(PACKAGE_SRC))

from cognition_governance import (  # noqa: E402
    GOVERNANCE_CONFIG_DECISION_BUILDER,
    GOVERNANCE_CONFIG_DECISION_SHAPE_VERSION,
    GovernanceCase,
    GovernanceDecision,
    GovernancePolicySet,
    build_governance_decision_from_config,
    build_governance_policy_set_from_config,
    make_governance_config_decision_candidate,
)
from config_contexts.governance import GovernanceConfigContext  # noqa: E402


def test_governance_config_boundary_reuses_policy_set_and_decision_models() -> None:
    config_context = GovernanceConfigContext(
        governance_profile="runtime",
        mode="blocking",
        decision_level="human_review",
        policy_refs=("policy:adk-run-config",),
        required_evidence_refs=("evidence:adk-run-config",),
        block_on_violation=True,
    )
    case = GovernanceCase(
        case_id="case-runtime-001",
        title="Review runtime governance config",
        case_type="runtime_governance",
    )

    policy_set = build_governance_policy_set_from_config(config_context)
    decision = build_governance_decision_from_config(
        config_context=config_context,
        case=case,
    )

    assert isinstance(policy_set, GovernancePolicySet)
    assert isinstance(decision, GovernanceDecision)
    assert policy_set.policy_set_id == "governance-config:runtime"
    assert policy_set.policies == ["policy:adk-run-config"]
    assert decision.decision == "need_evidence"
    assert decision.metadata["decision_shape_version"] == (
        GOVERNANCE_CONFIG_DECISION_SHAPE_VERSION
    )
    assert decision.metadata["decision_builder"] == GOVERNANCE_CONFIG_DECISION_BUILDER
    assert decision.metadata["decision_semantics"] == "candidate_only"
    assert decision.metadata["formal_decision_enabled"] is False
    assert decision.metadata["policy_execution_enabled"] is False
    assert decision.metadata["governance_outcome_enabled"] is False
    assert decision.metadata["candidate_only"] is True
    assert decision.metadata["composition_precondition_allowed"] is False
    assert decision.metadata["missing_evidence_refs"] == ["evidence:adk-run-config"]


def test_legacy_governance_config_candidate_builder_keeps_same_decision_shape() -> None:
    case = GovernanceCase(
        case_id="case-runtime-legacy",
        title="Review runtime governance legacy builder",
        case_type="runtime_governance",
    )

    decision = make_governance_config_decision_candidate(
        config_context={"governance_profile": "runtime"},
        case=case,
    )

    assert isinstance(decision, GovernanceDecision)
    assert decision.metadata["decision_builder"] == GOVERNANCE_CONFIG_DECISION_BUILDER
    assert decision.metadata["decision_semantics"] == "candidate_only"


def test_governance_config_boundary_accepts_structural_mapping() -> None:
    case = GovernanceCase(
        case_id="case-runtime-002",
        title="Review runtime governance mapping",
        case_type="runtime_governance",
        evidence_refs=["evidence:runtime"],
    )

    decision = make_governance_config_decision_candidate(
        config_context={
            "governance_profile": "runtime",
            "policy_refs": ["policy:runtime"],
            "required_evidence_refs": ["evidence:runtime"],
        },
        case=case,
    )

    assert decision.decision == "continue"
    assert decision.policy_set_id == "governance-config:runtime"


def test_governance_config_boundary_keeps_source_imports_layer_neutral() -> None:
    source_path = PACKAGE_SRC / "cognition_governance" / "governance_config.py"
    source = source_path.read_text(encoding="utf-8")
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:config_contexts|config_assembly|composition|runtime_container|"
        r"adk_adapter|google\.adk)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None
