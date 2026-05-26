from __future__ import annotations

import pytest
from cognition_governance import create_memory_approved_projection_candidate

from product_gateway.contracts import ProductGatewayResponse
from product_gateway.memory_projection import (
    build_product_gateway_memory_deletion_request,
    build_product_gateway_memory_projection_view,
    build_product_gateway_memory_tombstone_view,
)


def test_product_gateway_real_sample_builds_view_and_delete_request() -> None:
    projection = _product_visible_projection()

    view = build_product_gateway_memory_projection_view(projection)
    deletion_request = build_product_gateway_memory_deletion_request(
        projection,
        delete_request_id="delete-request://memory/project-summary-style",
        requested_action="request_tombstone",
        request_reason_summary=(
            "User wants the product view to stop showing this memory projection."
        ),
        requested_by_ref="user://project-owner",
        audit_ref="audit://memory/delete-request/project-summary-style",
    )

    assert view.projection_id == projection.projection_id
    assert view.memory_id == projection.memory_id
    assert view.visibility == "user_visible"
    assert "verification commands" in view.display_summary
    assert view.store_read_enabled is False
    assert view.store_write_enabled is False
    assert view.runtime_enabled is False
    assert view.public_schema_enabled is False
    assert view.metadata["source_review_id"] == projection.source_review_id
    assert view.metadata["source_result_id"] == projection.source_result_id
    assert "projection_requires_periodic_review" in view.warnings

    assert deletion_request.projection_id == projection.projection_id
    assert deletion_request.requested_action == "request_tombstone"
    assert deletion_request.governance_review_required is True
    assert deletion_request.formal_decision_enabled is False
    assert deletion_request.formal_outcome_enabled is False
    assert deletion_request.store_write_enabled is False

    assert "memory" not in ProductGatewayResponse.model_fields
    assert "memory_projection" not in ProductGatewayResponse.model_fields


def test_product_gateway_real_tombstone_sample_hides_original_content() -> None:
    tombstone_projection = _product_tombstone_projection()

    tombstone_view = build_product_gateway_memory_tombstone_view(tombstone_projection)

    assert tombstone_view.projection_id == tombstone_projection.projection_id
    assert tombstone_view.memory_id == tombstone_projection.memory_id
    assert tombstone_view.tombstone_summary == (
        "Project summary style preference revoked by user request."
    )
    assert tombstone_view.allowed_actions == ("request_review",)
    assert tombstone_view.store_read_enabled is False
    assert tombstone_view.store_write_enabled is False
    assert tombstone_view.runtime_enabled is False

    payload_text = repr(tombstone_view.model_dump()).lower()
    assert "verification commands" not in payload_text
    assert "raw prompt" not in payload_text
    assert "secret" not in payload_text


def test_product_gateway_real_sample_rejects_operator_only_projection() -> None:
    projection = _operator_only_projection()

    with pytest.raises(ValueError, match="product_gateway consumer"):
        build_product_gateway_memory_projection_view(projection)

    product_visible_but_operator_only = projection.model_copy(
        update={"allowed_consumers": ("product_gateway", "audit_report")}
    )
    with pytest.raises(ValueError, match="user_visible visibility"):
        build_product_gateway_memory_projection_view(product_visible_but_operator_only)


def test_product_gateway_prompt_context_candidate_stays_warning_only() -> None:
    projection = _product_visible_projection(prompt_context_allowed=True)

    view = build_product_gateway_memory_projection_view(projection)

    assert projection.prompt_context_allowed is True
    assert projection.prompt_context_enabled is False
    assert view.metadata["prompt_context_allowed"] is True
    assert view.metadata["prompt_context_enabled"] is False
    assert "prompt_context_allowed_but_not_enabled" in view.warnings
    assert "enable_prompt_context" in view.disabled_actions
    assert view.runtime_enabled is False


def _product_visible_projection(*, prompt_context_allowed: bool = False):
    prompt_context_approval_ref = None
    if prompt_context_allowed:
        prompt_context_approval_ref = (
            "approval://memory/prompt-context/project-summary-style"
        )
    return create_memory_approved_projection_candidate(
        projection_id="memory-projection://candidate/project-summary-style",
        source_review_id="memory-use-review-candidate-project-summary-style",
        source_result_id="memory-result-candidate-project-summary-style",
        memory_id="memory-project-summary-style",
        memory_kind="durable",
        subject_scope="project",
        projection_status_candidate="approved_candidate",
        display_summary=(
            "Project prefers concise task summaries with verification commands."
        ),
        fact_boundary_summary=(
            "Preference comes from explicit user approval in the task chain."
        ),
        behavior_effect_summary=(
            "May guide future product-facing summaries without changing approvals."
        ),
        value_boundary_summary=(
            "User-visible, revocable, and not allowed to override safety boundaries."
        ),
        use_boundary="Read-only product display and audit; no model prompt injection.",
        provenance_refs=(
            "tasks/b1/381-v0.7.0-Memory-approved-projection-candidate真实样例复验与外部入口前置判断结果包-v1.zh-CN.md",
        ),
        evidence_refs=("evidence://memory/project-summary-style",),
        approval_ref="approval://memory/project-summary-style",
        audit_ref="audit://memory/project-summary-style",
        retention_policy="retain_until_user_revoke",
        deletion_policy="user_can_revoke_with_tombstone",
        visibility="user_visible",
        sensitivity="low",
        confidence="high",
        allowed_consumers=("product_gateway", "audit_report"),
        denied_consumers=("cognition_agent", "model_memory"),
        prompt_context_allowed=prompt_context_allowed,
        prompt_context_approval_ref=prompt_context_approval_ref,
        review_after="2026-08-15",
        decay_policy="review_before_reuse_after_90_days",
    )


def _product_tombstone_projection():
    return create_memory_approved_projection_candidate(
        projection_id="memory-projection://candidate/project-summary-style-tombstone",
        source_review_id="memory-delete-review-candidate-project-summary-style",
        source_result_id="memory-delete-result-candidate-project-summary-style",
        memory_id="memory-project-summary-style",
        memory_kind="durable",
        subject_scope="project",
        projection_status_candidate="tombstone_candidate",
        display_summary="Project summary style preference was revoked.",
        fact_boundary_summary="Revocation is recorded by deletion review reference.",
        behavior_effect_summary="Future tasks must not use this preference.",
        value_boundary_summary="Deletion keeps only a deletion placeholder.",
        use_boundary="Display deletion status only; do not reuse preference.",
        provenance_refs=(
            "tasks/b1/381-v0.7.0-Memory-approved-projection-candidate真实样例复验与外部入口前置判断结果包-v1.zh-CN.md",
        ),
        evidence_refs=("evidence://memory/project-summary-style",),
        approval_ref="approval://memory/delete/project-summary-style",
        audit_ref="audit://memory/delete/project-summary-style",
        retention_policy="retain_tombstone_for_audit_only",
        deletion_policy="exclude_from_future_use",
        visibility="user_visible",
        sensitivity="low",
        confidence="high",
        allowed_consumers=("product_gateway", "audit_report"),
        denied_consumers=("cognition_agent", "runtime_container", "prompt_context"),
        review_after="2026-08-15",
        decay_policy="no_reuse_after_tombstone",
        revoke_ref="deletion://memory/project-summary-style",
        tombstone_summary="Project summary style preference revoked by user request.",
    )


def _operator_only_projection():
    return create_memory_approved_projection_candidate(
        projection_id="memory-projection://candidate/agent-review-boundary",
        source_review_id="memory-use-review-candidate-agent-review-boundary",
        source_result_id="memory-result-candidate-agent-review-boundary",
        memory_id="memory-agent-review-boundary",
        memory_kind="evidence",
        subject_scope="project",
        projection_status_candidate="approved_candidate",
        display_summary=(
            "Agent may reference the project rule that Memory is not private state."
        ),
        fact_boundary_summary="Rule is backed by task-chain Memory governance results.",
        behavior_effect_summary=(
            "Agent should treat Memory as read-only governed input."
        ),
        value_boundary_summary=(
            "Prevents private long-term memory and preserves user control."
        ),
        use_boundary="Read-only planning reference; no prompt injection.",
        provenance_refs=(
            "tasks/b1/378-v0.7.0-Memory治理审查内部模型公共化前置条件与路线选择判断结果包-v1.zh-CN.md",
        ),
        evidence_refs=("evidence://memory/agent-review-boundary",),
        retention_policy="retain_as_task_chain_index",
        deletion_policy="expire_with_task_chain_evidence",
        visibility="operator_visible",
        sensitivity="none",
        confidence="medium",
        allowed_consumers=("cognition_agent", "cognition_governance"),
        denied_consumers=("product_gateway", "prompt_context", "model_memory"),
        review_after="2026-08-15",
        decay_policy="review_before_agent_consumption",
    )
