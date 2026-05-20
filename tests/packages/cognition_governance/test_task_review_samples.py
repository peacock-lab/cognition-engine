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


def test_task_review_sample_can_model_fix_decision() -> None:
    case = GovernanceCase(
        case_id="task-review-001",
        title="Review agent task result before closing the task",
        case_type="task_result_review",
        subject="cognition_governance skeleton implementation",
        context={
            "task_type": "implementation_result_review",
            "expected_outputs": [
                "package skeleton",
                "targeted tests",
                "progress record",
            ],
            "reported_outputs": [
                "package skeleton",
                "targeted tests",
            ],
            "missing_outputs": [
                "progress record",
            ],
        },
        evidence_refs=[
            "evidence-git-status",
            "evidence-pytest-output",
            "evidence-record-check",
        ],
        policy_refs=["policy-task-result-review"],
        metadata={
            "phase": "v0.6.0",
            "review_kind": "before_close",
        },
    )

    git_status = GovernanceEvidence(
        evidence_id="evidence-git-status",
        evidence_type="terminal_output",
        source="git status --short --branch",
        summary="Working tree contains expected implementation changes.",
        metadata={"is_terminal_evidence": True},
    )

    pytest_output = GovernanceEvidence(
        evidence_id="evidence-pytest-output",
        evidence_type="test_output",
        source=".venv/bin/python -m pytest tests/packages/cognition_governance -q",
        summary="Targeted cognition_governance tests passed.",
        metadata={"passed": 5},
    )

    record_check = GovernanceEvidence(
        evidence_id="evidence-record-check",
        evidence_type="file_check",
        source="records/000-v0.6.0认知系统架构建设推进记录-v1.zh-CN.md",
        summary="Progress record section for the implementation result is missing.",
        metadata={"missing_section": "implementation result record"},
    )

    policy_set = GovernancePolicySet(
        policy_set_id="policy-task-result-review",
        name="Task result review policy",
        policies=[
            "Do not close a task when expected records are missing.",
            "Terminal evidence must be considered before close or commit.",
            "Missing required outputs should lead to a fix decision.",
        ],
    )

    decision = GovernanceDecision(
        decision_id="decision-task-review-001",
        case_id=case.case_id,
        decision="fix",
        rationale=(
            "The package skeleton and targeted tests are present, but the "
            "required progress record is missing, so the task should be fixed "
            "before close."
        ),
        evidence_ids=[
            git_status.evidence_id,
            pytest_output.evidence_id,
            record_check.evidence_id,
        ],
        policy_set_id=policy_set.policy_set_id,
        metadata={
            "required_action": "add progress record",
            "can_commit_now": False,
        },
    )

    outcome = GovernanceOutcome(
        outcome_id="outcome-task-review-001",
        decision_id=decision.decision_id,
        status="open",
        summary="Task remains open until the missing progress record is added.",
        metadata={"next_review": "after_fix"},
    )

    assert case.case_type == "task_result_review"
    assert "progress record" in case.context["missing_outputs"]
    assert pytest_output.metadata["passed"] == 5
    assert record_check.metadata["missing_section"] == "implementation result record"
    assert decision.decision == "fix"
    assert decision.metadata["can_commit_now"] is False
    assert outcome.status == "open"


def test_task_review_sample_can_model_close_decision_after_evidence_is_complete() -> None:
    case = GovernanceCase(
        case_id="task-review-002",
        title="Review completed task result before commit",
        case_type="task_result_review",
        subject="architecture boundary sample test",
        context={
            "task_type": "test_result_review",
            "expected_outputs": [
                "sample test file",
                "targeted test pass",
                "progress record",
            ],
            "reported_outputs": [
                "sample test file",
                "targeted test pass",
                "progress record",
            ],
            "missing_outputs": [],
        },
        evidence_refs=[
            "evidence-file-created",
            "evidence-pytest-output",
            "evidence-progress-record",
        ],
        policy_refs=["policy-task-result-review"],
    )

    policy_set = GovernancePolicySet(
        policy_set_id="policy-task-result-review",
        name="Task result review policy",
        policies=[
            "All expected outputs must be present.",
            "Tests must pass before close.",
            "Progress record must be updated before commit.",
        ],
    )

    decision = GovernanceDecision(
        decision_id="decision-task-review-002",
        case_id=case.case_id,
        decision="close",
        rationale=(
            "All expected outputs are present, targeted tests passed, and the "
            "progress record was updated."
        ),
        evidence_ids=case.evidence_refs,
        policy_set_id=policy_set.policy_set_id,
        metadata={
            "can_commit_now": True,
            "git_action": "commit_and_push",
        },
    )

    outcome = GovernanceOutcome(
        outcome_id="outcome-task-review-002",
        decision_id=decision.decision_id,
        status="validated",
        summary="Task was closed after evidence completion and commit.",
    )

    assert case.context["missing_outputs"] == []
    assert decision.decision == "close"
    assert decision.metadata["can_commit_now"] is True
    assert decision.metadata["git_action"] == "commit_and_push"
    assert outcome.status == "validated"


def test_task_review_sample_round_trips_decision_metadata() -> None:
    decision = GovernanceDecision(
        decision_id="decision-task-review-003",
        case_id="task-review-003",
        decision="need_evidence",
        rationale="The result cannot be reviewed without terminal evidence.",
        metadata={
            "missing_evidence": [
                "git status",
                "targeted pytest output",
            ],
        },
    )

    dumped = decision.model_dump()
    restored = GovernanceDecision.model_validate(dumped)

    assert restored == decision
    assert restored.decision == "need_evidence"
    assert restored.metadata["missing_evidence"] == [
        "git status",
        "targeted pytest output",
    ]
