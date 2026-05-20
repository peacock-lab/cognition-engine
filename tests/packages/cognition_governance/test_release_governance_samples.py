from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_SRC = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "cognition_governance"
    / "src"
)
sys.path.insert(0, str(PACKAGE_SRC))

from cognition_governance import (  # noqa: E402
    GovernanceCase,
    GovernanceDecision,
    GovernanceEvidence,
    GovernanceOutcome,
    GovernancePolicySet,
)


def test_release_governance_sample_can_model_block_decision() -> None:
    case = GovernanceCase(
        case_id="release-governance-001",
        title="Review release candidate before public publishing",
        case_type="release_governance",
        subject="v0.6.0 release candidate",
        context={
            "release_target": "public_repo_and_pypi",
            "checks": {
                "release_safety_check": "failed",
                "tag_exists": True,
                "release_note_matches_tag": False,
                "github_release_exists": True,
                "public_surface_check": "passed",
                "pypi_verification": "not_run",
            },
            "risk": "release note and tag mismatch",
        },
        evidence_refs=[
            "evidence-release-safety-check",
            "evidence-github-release",
            "evidence-public-surface",
        ],
        policy_refs=["policy-release-governance"],
        metadata={
            "phase": "v0.6.0",
            "review_kind": "pre_release_gate",
        },
    )

    release_safety = GovernanceEvidence(
        evidence_id="evidence-release-safety-check",
        evidence_type="release_check_output",
        source="scripts/release_safety_check.py",
        summary="Release safety check failed because release note did not match tag.",
        metadata={
            "check": "release_safety_check",
            "passed": False,
            "failed_rule": "release_note_tag_consistency",
        },
    )

    github_release = GovernanceEvidence(
        evidence_id="evidence-github-release",
        evidence_type="release_platform_check",
        source="GitHub Release",
        summary="GitHub Release exists for the target tag.",
        metadata={
            "platform": "github",
            "exists": True,
        },
    )

    public_surface = GovernanceEvidence(
        evidence_id="evidence-public-surface",
        evidence_type="public_surface_check_output",
        source="scripts/check_public_surface.py",
        summary="Public surface check passed with no private governance materials exposed.",
        metadata={
            "passed": True,
            "private_materials_exposed": False,
        },
    )

    policy_set = GovernancePolicySet(
        policy_set_id="policy-release-governance",
        name="Release governance policy",
        policies=[
            "Release note must match tag before public release.",
            "Public surface must not expose private governance materials.",
            "Failed release safety checks should block release.",
        ],
    )

    decision = GovernanceDecision(
        decision_id="decision-release-governance-001",
        case_id=case.case_id,
        decision="block",
        rationale=(
            "The public surface check passed, but release_safety_check failed "
            "because the release note did not match the tag. The release must "
            "be blocked until evidence is corrected."
        ),
        evidence_ids=[
            release_safety.evidence_id,
            github_release.evidence_id,
            public_surface.evidence_id,
        ],
        policy_set_id=policy_set.policy_set_id,
        metadata={
            "can_publish": False,
            "required_action": "fix release note and rerun safety check",
        },
    )

    outcome = GovernanceOutcome(
        outcome_id="outcome-release-governance-001",
        decision_id=decision.decision_id,
        status="open",
        summary="Release remains blocked until consistency evidence is fixed.",
        metadata={"next_review": "after_release_safety_check_passes"},
    )

    assert case.case_type == "release_governance"
    assert case.context["checks"]["release_safety_check"] == "failed"
    assert release_safety.metadata["failed_rule"] == "release_note_tag_consistency"
    assert public_surface.metadata["private_materials_exposed"] is False
    assert decision.decision == "block"
    assert decision.metadata["can_publish"] is False
    assert outcome.status == "open"


def test_release_governance_sample_can_model_release_decision() -> None:
    case = GovernanceCase(
        case_id="release-governance-002",
        title="Review release candidate after evidence is complete",
        case_type="release_governance",
        subject="v0.6.0 release candidate",
        context={
            "release_target": "public_repo_and_pypi",
            "checks": {
                "release_safety_check": "passed",
                "tag_exists": True,
                "release_note_matches_tag": True,
                "github_release_exists": True,
                "public_surface_check": "passed",
                "pypi_verification": "passed",
            },
        },
        evidence_refs=[
            "evidence-release-safety-check",
            "evidence-public-surface",
            "evidence-pypi-verify",
        ],
        policy_refs=["policy-release-governance"],
    )

    policy_set = GovernancePolicySet(
        policy_set_id="policy-release-governance",
        name="Release governance policy",
        policies=[
            "Release safety check must pass.",
            "Public surface check must pass.",
            "PyPI verification must pass when package publishing is in scope.",
        ],
    )

    decision = GovernanceDecision(
        decision_id="decision-release-governance-002",
        case_id=case.case_id,
        decision="release",
        rationale=(
            "Release safety, public surface, and PyPI verification evidence "
            "all satisfy the selected release governance policy."
        ),
        evidence_ids=case.evidence_refs,
        policy_set_id=policy_set.policy_set_id,
        metadata={
            "can_publish": True,
            "git_action": "tag_release_and_publish",
        },
    )

    outcome = GovernanceOutcome(
        outcome_id="outcome-release-governance-002",
        decision_id=decision.decision_id,
        status="validated",
        summary="Release was completed and verified after governance approval.",
    )

    assert case.context["checks"]["release_safety_check"] == "passed"
    assert decision.decision == "release"
    assert decision.metadata["can_publish"] is True
    assert outcome.status == "validated"


def test_release_governance_sample_can_model_need_evidence_decision() -> None:
    case = GovernanceCase(
        case_id="release-governance-003",
        title="Review release candidate with missing PyPI evidence",
        case_type="release_governance",
        subject="v0.6.0 package release",
        context={
            "release_target": "pypi",
            "checks": {
                "release_safety_check": "passed",
                "public_surface_check": "passed",
                "pypi_verification": "missing",
            },
        },
        evidence_refs=[
            "evidence-release-safety-check",
            "evidence-public-surface",
        ],
        policy_refs=["policy-release-governance"],
    )

    decision = GovernanceDecision(
        decision_id="decision-release-governance-003",
        case_id=case.case_id,
        decision="need_evidence",
        rationale=(
            "Release safety and public surface checks passed, but PyPI "
            "verification evidence is missing, so publishing cannot be closed."
        ),
        evidence_ids=case.evidence_refs,
        policy_set_id="policy-release-governance",
        metadata={
            "missing_evidence": ["pypi_verification"],
            "can_publish": False,
        },
    )

    assert decision.decision == "need_evidence"
    assert decision.metadata["missing_evidence"] == ["pypi_verification"]
    assert decision.metadata["can_publish"] is False
