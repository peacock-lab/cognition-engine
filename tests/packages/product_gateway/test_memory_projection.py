from __future__ import annotations

from pathlib import Path

import pytest
from cognition_governance import create_memory_approved_projection_candidate
from pydantic import ValidationError

import product_gateway.memory_projection as memory_projection_module
from product_gateway.contracts import ProductGatewayResponse
from product_gateway.memory_projection import (
    build_product_gateway_memory_deletion_request,
    build_product_gateway_memory_projection_view,
    build_product_gateway_memory_tombstone_view,
)


PRODUCT_GATEWAY_ROOT = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "product_gateway"
    / "src"
    / "product_gateway"
)


def test_memory_projection_candidate_public_surface_is_explicit() -> None:
    assert tuple(memory_projection_module.__all__) == (
        "ProductGatewayMemoryDeletionRequestCandidate",
        "ProductGatewayMemoryProjectionViewCandidate",
        "ProductGatewayMemoryTombstoneViewCandidate",
        "build_product_gateway_memory_deletion_request",
        "build_product_gateway_memory_projection_view",
        "build_product_gateway_memory_tombstone_view",
    )
    assert "_coerce_projection_data" not in memory_projection_module.__all__
    assert "_validate_projection_for_product_gateway" not in (
        memory_projection_module.__all__
    )
    assert "_reject_forbidden_memory_text" not in memory_projection_module.__all__


def _visible_projection():
    return create_memory_approved_projection_candidate(
        projection_id="memory-projection://candidate/product-view",
        source_review_id="memory-review://product-view",
        source_result_id="memory-result://product-view",
        memory_id="memory-product-view",
        memory_kind="durable",
        subject_scope="project",
        projection_status_candidate="approved_candidate",
        display_summary=(
            "Project prefers concise task summaries with verification commands."
        ),
        fact_boundary_summary="Preference is backed by explicit task-chain approval.",
        behavior_effect_summary=(
            "May guide product-facing summaries without changing approvals."
        ),
        value_boundary_summary="User-visible and revocable governed preference.",
        use_boundary="Read-only product display; no prompt injection.",
        provenance_refs=("tasks/b1/377-result",),
        evidence_refs=("evidence://memory/product-view",),
        approval_ref="approval://memory/product-view",
        audit_ref="audit://memory/product-view",
        retention_policy="retain_until_user_revoke",
        deletion_policy="user_can_revoke_with_tombstone",
        visibility="user_visible",
        sensitivity="low",
        confidence="high",
        allowed_consumers=("product_gateway", "audit_report"),
        denied_consumers=("cognition_agent", "prompt_context", "model_memory"),
        review_after="2026-08-15",
        decay_policy="review_before_reuse_after_90_days",
    )


def _tombstone_projection():
    return create_memory_approved_projection_candidate(
        projection_id="memory-projection://candidate/product-view-tombstone",
        source_review_id="memory-review://product-view-tombstone",
        source_result_id="memory-result://product-view-tombstone",
        memory_id="memory-product-view",
        memory_kind="durable",
        subject_scope="project",
        projection_status_candidate="tombstone_candidate",
        display_summary="Project summary style preference was revoked.",
        fact_boundary_summary="Revocation is recorded by deletion review reference.",
        behavior_effect_summary="Future tasks must not use this preference.",
        value_boundary_summary="Deletion keeps only a tombstone.",
        use_boundary="Display deletion status only; do not reuse preference.",
        provenance_refs=("tasks/b1/377-result",),
        evidence_refs=("evidence://memory/product-view",),
        approval_ref="approval://memory/delete/product-view",
        audit_ref="audit://memory/delete/product-view",
        retention_policy="retain_tombstone_for_audit_only",
        deletion_policy="exclude_from_future_use",
        visibility="user_visible",
        sensitivity="low",
        confidence="high",
        allowed_consumers=("product_gateway", "audit_report"),
        denied_consumers=("cognition_agent", "runtime_container", "prompt_context"),
        review_after="2026-08-15",
        decay_policy="no_reuse_after_tombstone",
        revoke_ref="deletion://memory/product-view",
        tombstone_summary="Project summary style preference revoked by user request.",
    )


def test_product_gateway_memory_projection_view_is_sanitized_candidate_only() -> None:
    view = build_product_gateway_memory_projection_view(_visible_projection())

    assert view.projection_id == "memory-projection://candidate/product-view"
    assert view.memory_id == "memory-product-view"
    assert view.projection_status == "approved_candidate"
    assert "verification commands" in view.display_summary
    assert view.allowed_actions == (
        "request_revoke",
        "request_tombstone",
        "request_hide_from_product_view",
        "request_review",
    )
    assert "delete_store_record" in view.disabled_actions
    assert view.candidate_only is True
    assert view.store_read_enabled is False
    assert view.store_write_enabled is False
    assert view.runtime_enabled is False
    assert view.public_schema_enabled is False
    assert view.metadata["source"] == "product_gateway.memory_projection"
    assert view.metadata["source_projection_id"] == view.projection_id


def test_product_gateway_memory_deletion_request_does_not_execute_delete() -> None:
    deletion_request = build_product_gateway_memory_deletion_request(
        _visible_projection(),
        delete_request_id="delete-request://memory/product-view",
        requested_action="request_tombstone",
        request_reason_summary="User requested revocation from product view.",
        requested_by_ref="user://peacock",
        audit_ref="audit://memory/delete-request/product-view",
    )

    assert deletion_request.requested_action == "request_tombstone"
    assert deletion_request.governance_review_required is True
    assert deletion_request.store_write_enabled is False
    assert deletion_request.runtime_enabled is False
    assert deletion_request.formal_decision_enabled is False
    assert deletion_request.formal_outcome_enabled is False
    assert deletion_request.metadata["source_projection_id"] == (
        "memory-projection://candidate/product-view"
    )


def test_product_gateway_memory_tombstone_view_hides_original_content() -> None:
    tombstone = build_product_gateway_memory_tombstone_view(_tombstone_projection())

    assert tombstone.projection_id == (
        "memory-projection://candidate/product-view-tombstone"
    )
    assert tombstone.tombstone_summary == (
        "Project summary style preference revoked by user request."
    )
    assert tombstone.allowed_actions == ("request_review",)
    assert tombstone.store_read_enabled is False
    assert tombstone.store_write_enabled is False
    assert tombstone.runtime_enabled is False
    payload_text = repr(tombstone.model_dump())
    assert "raw" not in payload_text.lower()
    assert "secret" not in payload_text.lower()


def test_product_gateway_memory_projection_requires_allowed_consumer() -> None:
    projection = _visible_projection().model_copy(
        update={"allowed_consumers": ("audit_report",)}
    )

    with pytest.raises(ValueError, match="product_gateway consumer"):
        build_product_gateway_memory_projection_view(projection)


def test_product_gateway_memory_projection_blocks_tombstone_in_regular_view() -> None:
    with pytest.raises(ValueError, match="tombstone_candidate requires tombstone view"):
        build_product_gateway_memory_projection_view(_tombstone_projection())


def test_product_gateway_memory_deletion_request_rejects_forbidden_actions() -> None:
    with pytest.raises(ValidationError):
        build_product_gateway_memory_deletion_request(
            _visible_projection(),
            delete_request_id="delete-request://memory/product-view",
            requested_action="purge_now",  # type: ignore[arg-type]
            request_reason_summary="User requested deletion review.",
            requested_by_ref="user://peacock",
            audit_ref="audit://memory/delete-request/product-view",
        )


def test_product_gateway_response_has_no_memory_fields() -> None:
    assert "memory" not in ProductGatewayResponse.model_fields
    assert "memory_refs" not in ProductGatewayResponse.model_fields
    assert "memory_projection" not in ProductGatewayResponse.model_fields


def test_memory_projection_module_has_no_execution_layer_imports() -> None:
    source = (PRODUCT_GATEWAY_ROOT / "memory_projection.py").read_text(encoding="utf-8")

    assert "google.adk" not in source
    assert "runtime_container" not in source
    assert "cognition_governance" not in source
    assert "Memory store" not in source
