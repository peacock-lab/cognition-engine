from __future__ import annotations

import pytest
from pydantic import ValidationError

from cognition_governance import (
    MemoryApprovedProjectionCandidate,
    create_memory_approved_projection_candidate,
    create_memory_governance_review_result_candidate,
    create_memory_use_review_candidate,
)


def _valid_projection_kwargs() -> dict:
    return {
        "projection_id": "memory-projection://candidate/project-brief-style",
        "source_review_id": "memory-use-review-candidate-source-001",
        "source_result_id": "memory-governance-result-source-001",
        "memory_id": "memory-project-brief-style",
        "memory_kind": "durable",
        "subject_scope": "project",
        "display_summary": "Project prefers concise result summaries with verification lines.",
        "fact_boundary_summary": "Preference is explicitly approved and project-scoped.",
        "behavior_effect_summary": (
            "May guide future summaries toward concise closure without changing decisions."
        ),
        "value_boundary_summary": (
            "User-visible, revocable, and not allowed to override safety boundaries."
        ),
        "use_boundary": (
            "Only for read-only display, governance review, and workflow planning."
        ),
        "provenance_refs": ("task://memory/project-brief-style",),
        "evidence_refs": ("evidence://memory/project-brief-style",),
        "approval_ref": "approval://memory/project-brief-style",
        "audit_ref": "audit://memory/project-brief-style",
        "retention_policy": "retain_until_user_revoke",
        "deletion_policy": "user_can_revoke_with_tombstone",
        "visibility": "user_visible",
        "sensitivity": "low",
        "confidence": "high",
        "allowed_consumers": (
            "product_gateway",
            "cognition_governance",
            "audit_report",
        ),
        "denied_consumers": ("prompt_context", "model_memory"),
        "expires_at": None,
        "review_after": "2026-08-15",
        "decay_policy": "review_before_reuse_after_90_days",
    }


def test_creates_durable_approved_projection_candidate_without_runtime_or_store() -> None:
    use_review = create_memory_use_review_candidate(
        memory_id="memory-project-brief-style",
        use_purpose="display approved project summary style as a read-only projection",
        target_workflow_name="memory_projection_review",
        subject_scope="project",
        allowed_for_product_display=True,
        approval_ref="approval://memory/project-brief-style",
        audit_ref="audit://memory/project-brief-style",
        provenance_refs=("task://memory/project-brief-style",),
        evidence_refs=("evidence://memory/project-brief-style",),
        review_result="approve_candidate",
    )
    review_result = create_memory_governance_review_result_candidate(
        use_review,
        approved_projection_ref="memory-projection://candidate/project-brief-style",
    )

    projection = create_memory_approved_projection_candidate(
        **{
            **_valid_projection_kwargs(),
            "source_review_id": use_review.review_id,
            "source_result_id": review_result.result_id,
        }
    )

    assert isinstance(projection, MemoryApprovedProjectionCandidate)
    assert projection.projection_id == review_result.approved_projection_ref
    assert projection.candidate_only is True
    assert projection.runtime_enabled is False
    assert projection.store_read_enabled is False
    assert projection.store_write_enabled is False
    assert projection.prompt_context_enabled is False
    assert projection.public_schema_enabled is False
    assert projection.formal_decision_enabled is False
    assert projection.formal_outcome_enabled is False
    assert projection.metadata["projection_kind"] == (
        "approved_memory_projection_candidate"
    )


def test_projection_rejects_raw_or_secret_display_summary() -> None:
    with pytest.raises(ValidationError, match="display_summary must be sanitized"):
        create_memory_approved_projection_candidate(
            **{
                **_valid_projection_kwargs(),
                "display_summary": "Raw response included a secret token.",
            }
        )


def test_projection_rejects_unknown_allowed_consumer() -> None:
    with pytest.raises(ValidationError, match="Input should be"):
        create_memory_approved_projection_candidate(
            **{
                **_valid_projection_kwargs(),
                "allowed_consumers": ("unknown_consumer",),
            }
        )


def test_projection_requires_allowed_consumers() -> None:
    with pytest.raises(ValidationError, match="allowed_consumers must not be empty"):
        create_memory_approved_projection_candidate(
            **{
                **_valid_projection_kwargs(),
                "allowed_consumers": (),
            }
        )


def test_prompt_context_allowed_requires_separate_projection_approval_ref() -> None:
    with pytest.raises(
        ValidationError,
        match="prompt_context_allowed requires prompt_context_approval_ref",
    ):
        create_memory_approved_projection_candidate(
            **{
                **_valid_projection_kwargs(),
                "prompt_context_allowed": True,
            }
        )


def test_projection_keeps_prompt_context_disabled_even_when_allowed() -> None:
    projection = create_memory_approved_projection_candidate(
        **{
            **_valid_projection_kwargs(),
            "prompt_context_allowed": True,
            "prompt_context_approval_ref": (
                "approval://memory/prompt-context/project-brief-style"
            ),
            "allowed_consumers": ("runtime_container", "cognition_governance"),
        }
    )

    assert projection.prompt_context_allowed is True
    assert projection.prompt_context_enabled is False


def test_tombstone_projection_requires_tombstone_summary() -> None:
    with pytest.raises(
        ValidationError,
        match="tombstone_candidate requires tombstone_summary",
    ):
        create_memory_approved_projection_candidate(
            **{
                **_valid_projection_kwargs(),
                "projection_status_candidate": "tombstone_candidate",
            }
        )


def test_tombstone_projection_does_not_expose_deleted_content() -> None:
    with pytest.raises(
        ValidationError,
        match="tombstone_summary must not expose deleted content",
    ):
        create_memory_approved_projection_candidate(
            **{
                **_valid_projection_kwargs(),
                "projection_status_candidate": "tombstone_candidate",
                "tombstone_summary": "Deleted raw prompt contained a secret.",
            }
        )


def test_projection_invariants_cannot_be_enabled() -> None:
    with pytest.raises(ValidationError, match="runtime_enabled must remain false"):
        MemoryApprovedProjectionCandidate(
            **{
                **_valid_projection_kwargs(),
                "runtime_enabled": True,
            }
        )


def test_purge_candidate_does_not_generate_user_visible_projection() -> None:
    with pytest.raises(
        ValidationError,
        match="purge_candidate must not generate user_visible projection",
    ):
        create_memory_approved_projection_candidate(
            **{
                **_valid_projection_kwargs(),
                "metadata": {"delete_mode": "purge_candidate"},
            }
        )


def test_projection_rejects_forbidden_metadata_keys() -> None:
    with pytest.raises(ValidationError, match="raw_prompt is forbidden"):
        create_memory_approved_projection_candidate(
            **{
                **_valid_projection_kwargs(),
                "metadata": {"raw_prompt": "do not keep this"},
            }
        )


def test_projection_rejects_runtime_object_leakage() -> None:
    RuntimeObject = type("RuntimeObject", (), {"__module__": "google.adk.sessions"})

    with pytest.raises(ValidationError, match="leaks a runtime object"):
        create_memory_approved_projection_candidate(
            **{
                **_valid_projection_kwargs(),
                "metadata": {"object": RuntimeObject()},
            }
        )
