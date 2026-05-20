from __future__ import annotations

import re
from pathlib import Path

from cognition_governance import (
    ADK_WORKFLOW_RUNNER_POLICY_SET_ID,
    AdkWorkflowRunnerDecisionCandidateResult,
    AdkWorkflowRunnerPolicySetCandidate,
    GovernanceCase,
    GovernanceDecision,
    GovernanceEvidence,
    build_adk_workflow_runner_policy_set_candidate,
    make_adk_workflow_runner_decision_candidate,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
GOVERNANCE_SOURCE_ROOT = REPO_ROOT / "packages" / "cognition_governance" / "src"
OBSERVABILITY_BRIDGE = (
    GOVERNANCE_SOURCE_ROOT / "cognition_governance" / "observability_bridge.py"
)


def _policy_set() -> AdkWorkflowRunnerPolicySetCandidate:
    return build_adk_workflow_runner_policy_set_candidate()


def _governance_evidence() -> GovernanceEvidence:
    return GovernanceEvidence(
        evidence_id="evidence-adk2-decision-001",
        evidence_type="adk_workflow_runner_execution",
        source="observability_hub.adk_workflow_runner_evidence",
        summary="ADK2 WorkflowRunner evidence for decision candidate tests.",
        metadata={
            "runtime_kind": "adk2_workflow_runner",
            "status": "success",
            "run_config": {
                "mapped_fields": ["max_llm_calls"],
                "unmapped_fields": [],
            },
            "service_bundle": {
                "source": "in_memory",
                "artifact_service": {"adk_service_type": "InMemoryArtifactService"},
                "session_service": {"adk_service_type": "InMemorySessionService"},
            },
            "artifact_summary": {
                "artifact_count": 1,
                "has_artifacts": True,
            },
            "session_summary": {
                "session_id": "session-adk2-decision-001",
            },
            "event_summary": {
                "event_count": 2,
                "has_error": False,
            },
            "warnings": [],
        },
    )


def _governance_case(*, findings: list[dict[str, str]] | None = None) -> GovernanceCase:
    policy_set = _policy_set().policy_set
    return GovernanceCase(
        case_id="review-adk2-decision-001",
        title="ADK2 WorkflowRunner governance review",
        case_type="adk_workflow_runner_governance_review",
        subject="adk2-decision-workflow",
        context={
            "workflow_name": "adk2-decision-workflow",
            "status": "success",
            "risk_level": "low" if not findings else "medium",
            "evidence_id": "evidence-adk2-decision-001",
        },
        evidence_refs=["evidence-adk2-decision-001"],
        policy_refs=[policy_set.policy_set_id],
        metadata={
            "findings": findings
            or [
                {
                    "code": "ADK2_WORKFLOW_RUNNER_CHAIN_OBSERVED",
                    "severity": "info",
                    "message": "ADK2 WorkflowRunner evidence candidate was observed.",
                    "evidence_path": "runtime_kind",
                    "recommendation": "Keep this evidence as a candidate input.",
                }
            ],
            "required_followups": [],
        },
    )


def test_builds_adk2_workflow_runner_policy_set_candidate() -> None:
    candidate = build_adk_workflow_runner_policy_set_candidate()

    assert isinstance(candidate, AdkWorkflowRunnerPolicySetCandidate)
    assert candidate.policy_set.policy_set_id == ADK_WORKFLOW_RUNNER_POLICY_SET_ID
    assert candidate.policy_set.metadata["policy_status"] == "candidate_only"
    assert candidate.policy_set.metadata["formal_decision_enabled"] is False
    assert candidate.policy_set.metadata["governance_outcome_enabled"] is False
    assert set(candidate.policy_set.policies) >= {
        "evidence_completeness",
        "run_config_mapping_completeness",
        "service_bundle_source_completeness",
        "artifact_session_event_lifecycle_completeness",
        "adk_native_object_leakage_guard",
        "governance_boundary_guard",
        "policy_set_presence_guard",
    }


def test_makes_continue_decision_candidate_from_complete_case_and_evidence() -> None:
    result = make_adk_workflow_runner_decision_candidate(
        _governance_case(),
        _governance_evidence(),
        policy_set_candidate=_policy_set(),
    )

    assert isinstance(result, AdkWorkflowRunnerDecisionCandidateResult)
    decision = result.decision_candidate
    assert isinstance(decision, GovernanceDecision)
    assert decision.decision == "continue"
    assert decision.policy_set_id == ADK_WORKFLOW_RUNNER_POLICY_SET_ID
    assert decision.evidence_ids == ["evidence-adk2-decision-001"]
    assert decision.metadata["decision_semantics"] == "candidate_only"
    assert decision.metadata["human_review_required"] is False
    assert decision.metadata["missing_evidence"] == []
    assert decision.metadata["policy_execution_enabled"] is False
    assert decision.metadata["governance_outcome_enabled"] is False
    assert "governance_outcome" not in result.model_dump(mode="python")
    assert decision.decision not in {"release", "block"}
    assert "can_publish" not in repr(result.model_dump(mode="python"))
    assert "can_release" not in repr(result.model_dump(mode="python"))


def test_missing_policy_set_or_policy_refs_requires_human_review() -> None:
    governance_case = _governance_case()
    governance_case.policy_refs.clear()

    result = make_adk_workflow_runner_decision_candidate(
        governance_case,
        _governance_evidence(),
        policy_set_candidate=None,
    )

    decision = result.decision_candidate
    assert decision.decision == "defer"
    assert decision.policy_set_id is None
    assert decision.metadata["human_review_required"] is True
    assert "PolicySet candidate was not provided." in decision.metadata[
        "human_review_reasons"
    ]
    assert "GovernanceCase policy_refs is empty." in decision.metadata[
        "human_review_reasons"
    ]
    assert decision.metadata["policy_set_candidate_id"] is None


def test_warning_finding_enters_human_review_reasons() -> None:
    warning_finding = {
        "code": "SERVICE_BUNDLE_SOURCE_MISSING",
        "severity": "warning",
        "message": "ServiceBundle source is not explicit.",
        "evidence_path": "service_bundle.source",
        "recommendation": "Record ServiceBundle source.",
    }

    result = make_adk_workflow_runner_decision_candidate(
        _governance_case(findings=[warning_finding]),
        _governance_evidence(),
        policy_set_candidate=_policy_set(),
    )

    decision = result.decision_candidate
    assert decision.decision == "fix"
    assert decision.metadata["human_review_required"] is True
    assert "Finding requires review: SERVICE_BUNDLE_SOURCE_MISSING." in decision.metadata[
        "human_review_reasons"
    ]
    assert "GovernanceCase risk_level is medium." in decision.metadata[
        "human_review_reasons"
    ]


def test_missing_lifecycle_evidence_enters_missing_evidence() -> None:
    governance_evidence = _governance_evidence()
    governance_evidence.metadata["artifact_summary"] = {"artifact_count": 0}
    governance_evidence.metadata["session_summary"] = {}
    governance_evidence.metadata["event_summary"] = {"event_count": 0}

    result = make_adk_workflow_runner_decision_candidate(
        _governance_case(),
        governance_evidence,
        policy_set_candidate=_policy_set(),
    )

    decision = result.decision_candidate
    assert decision.decision == "need_evidence"
    assert decision.metadata["human_review_required"] is True
    assert decision.metadata["missing_evidence"] == [
        "evidence-adk2-decision-001.artifact_lifecycle",
        "evidence-adk2-decision-001.session_lifecycle",
        "evidence-adk2-decision-001.event_lifecycle",
    ]


def test_decision_candidate_source_keeps_adk_and_assembly_layers_out() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+(?:google\.adk|adk_adapter|runtime_container|composition)\b",
        re.MULTILINE,
    )

    for source_path in GOVERNANCE_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path

    bridge_source = OBSERVABILITY_BRIDGE.read_text(encoding="utf-8")
    assert "AdkWorkflowRunnerEvidence" not in bridge_source
    assert "adk_workflow_runner" not in bridge_source
