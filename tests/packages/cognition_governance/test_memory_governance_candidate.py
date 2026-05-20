from __future__ import annotations

import pytest
from pydantic import ValidationError

from cognition_governance import (
    MemoryDeleteReviewCandidate,
    MemoryGovernanceReviewResultCandidate,
    MemoryRecordReviewCandidate,
    MemoryUseReviewCandidate,
    create_memory_delete_review_candidate,
    create_memory_governance_review_result_candidate,
    create_memory_record_review_candidate,
    create_memory_use_review_candidate,
)


def test_creates_durable_memory_record_review_candidate_without_store_write() -> None:
    candidate = create_memory_record_review_candidate(
        memory_id="memory-record-001",
        memory_kind="durable",
        subject_scope="project",
        content_summary="User approved project preference for concise summaries.",
        provenance_refs=["task://memory-source-001"],
        evidence_refs=["evidence://memory-source-001"],
        approval_ref="approval://memory-record-001",
        audit_ref="audit://memory-record-001",
        memory_write_ref="memory-write://candidate-001",
        retention_policy="retain_until_user_revoke",
        deletion_policy="user_can_revoke_with_tombstone",
        visibility="user_visible",
        review_result="approve_candidate",
    )

    assert isinstance(candidate, MemoryRecordReviewCandidate)
    assert candidate.candidate_only is True
    assert candidate.memory_write_enabled is False
    assert candidate.runtime_enabled is False
    assert candidate.store_write_enabled is False
    assert candidate.metadata["review_kind"] == "memory_record_write"


def test_durable_memory_record_requires_approval_and_audit_refs() -> None:
    with pytest.raises(ValidationError, match="durable memory requires approval_ref"):
        create_memory_record_review_candidate(
            memory_id="memory-record-missing-approval",
            memory_kind="durable",
            subject_scope="user",
            content_summary="User approved preference for project status summaries.",
            audit_ref="audit://memory-record-missing-approval",
            retention_policy="retain_until_user_revoke",
            deletion_policy="user_can_revoke_with_tombstone",
            visibility="user_visible",
            review_result="request_user_approval",
        )


def test_memory_record_rejects_raw_or_secret_content() -> None:
    with pytest.raises(ValidationError, match="content_summary must be sanitized"):
        create_memory_record_review_candidate(
            memory_id="memory-record-raw-content",
            memory_kind="evidence",
            subject_scope="task",
            content_summary="Raw prompt: remember the secret token.",
            retention_policy="task_evidence_index_only",
            deletion_policy="expire_with_task_evidence",
            visibility="operator_visible",
            review_result="reject_candidate",
        )


def test_memory_use_review_keeps_prompt_context_disabled_by_default() -> None:
    candidate = create_memory_use_review_candidate(
        memory_id="memory-record-001",
        use_purpose="support governance review continuity for task 376",
        target_workflow_name="memory_governance_review",
        subject_scope="project",
        allowed_for_governance_review=True,
        review_result="approve_candidate",
    )

    assert isinstance(candidate, MemoryUseReviewCandidate)
    assert candidate.allowed_for_prompt_context is False
    assert candidate.prompt_context_enabled is False
    assert candidate.memory_read_enabled is False
    assert candidate.runtime_enabled is False


def test_prompt_context_candidate_requires_approval_and_audit_refs() -> None:
    with pytest.raises(
        ValidationError,
        match="allowed_for_prompt_context requires approval_ref",
    ):
        create_memory_use_review_candidate(
            memory_id="memory-record-prompt-context",
            use_purpose="provide project preference summary to a live model",
            target_workflow_name="future_live_memory_context",
            subject_scope="project",
            allowed_for_prompt_context=True,
            review_result="request_user_approval",
        )


def test_memory_delete_review_keeps_tombstone_and_does_not_delete_store() -> None:
    candidate = create_memory_delete_review_candidate(
        memory_id="memory-record-001",
        delete_mode="tombstone",
        subject_scope="project",
        delete_reason="User revoked the project preference.",
        tombstone_summary="Project preference revoked by user request.",
        review_result="approve_candidate",
    )

    assert isinstance(candidate, MemoryDeleteReviewCandidate)
    assert candidate.retain_tombstone is True
    assert candidate.memory_delete_enabled is False
    assert candidate.store_delete_enabled is False
    assert candidate.runtime_enabled is False


def test_purge_candidate_requires_approval_and_audit_refs() -> None:
    with pytest.raises(ValidationError, match="purge_candidate requires approval_ref"):
        create_memory_delete_review_candidate(
            memory_id="memory-record-purge",
            delete_mode="purge_candidate",
            subject_scope="user",
            delete_reason="User requested full purge candidate review.",
            review_result="request_user_approval",
        )


def test_forbidden_metadata_keys_are_rejected() -> None:
    with pytest.raises(ValidationError, match="raw_prompt is forbidden"):
        create_memory_use_review_candidate(
            memory_id="memory-record-forbidden-metadata",
            use_purpose="support governance review with a sanitized preference",
            target_workflow_name="memory_governance_review",
            subject_scope="project",
            review_result="reject_candidate",
            metadata={"raw_prompt": "do not keep this"},
        )


def test_runtime_object_leakage_is_rejected() -> None:
    RuntimeObject = type("RuntimeObject", (), {"__module__": "google.adk.sessions"})

    with pytest.raises(ValidationError, match="leaks a runtime object"):
        create_memory_use_review_candidate(
            memory_id="memory-record-runtime-object",
            use_purpose="support governance review with sanitized refs",
            target_workflow_name="memory_governance_review",
            subject_scope="project",
            review_result="reject_candidate",
            metadata={"object": RuntimeObject()},
        )


def test_governance_review_result_candidate_never_enables_runtime_or_outcome() -> None:
    review = create_memory_use_review_candidate(
        memory_id="memory-record-001",
        use_purpose="support governance review continuity for task 376",
        target_workflow_name="memory_governance_review",
        subject_scope="project",
        allowed_for_product_display=True,
        review_result="approve_candidate",
    )

    result = create_memory_governance_review_result_candidate(
        review,
        approved_projection_ref="memory-projection://candidate-001",
    )

    assert isinstance(result, MemoryGovernanceReviewResultCandidate)
    assert result.review_kind == "memory_projection"
    assert result.status_candidate == "approved_candidate"
    assert result.candidate_only is True
    assert result.formal_decision_enabled is False
    assert result.formal_outcome_enabled is False
    assert result.memory_runtime_enabled is False
    assert result.memory_store_enabled is False
    assert result.prompt_context_enabled is False
    assert "Prompt context injection is disabled." in result.blocked_formal_outcome_reasons
