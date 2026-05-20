"""Memory governance review candidates.

These models are internal cognition_governance candidates. They do not create
Memory records, read or write a Memory store, call ADK memory_service, or inject
content into model prompt context.
"""

from __future__ import annotations

from typing import Any, Literal, Mapping
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


MemoryKindCandidate = Literal["session", "durable", "evidence"]
MemorySubjectScopeCandidate = Literal["user", "project", "workspace", "task", "system"]
MemoryVisibilityCandidate = Literal[
    "user_visible",
    "operator_visible",
    "system_internal",
]
MemorySensitivityCandidate = Literal["none", "low", "medium", "high"]
MemoryConfidenceCandidate = Literal["low", "medium", "high"]
MemoryReviewKind = Literal[
    "memory_record_write",
    "memory_use",
    "memory_delete",
    "memory_projection",
]
MemoryReviewResultCandidate = Literal[
    "approve_candidate",
    "reject_candidate",
    "request_evidence",
    "request_scope_change",
    "request_user_approval",
    "defer",
]
MemoryGovernanceStatusCandidate = Literal[
    "proposed",
    "reviewed",
    "approved_candidate",
    "rejected_candidate",
    "needs_evidence",
    "needs_user_approval",
    "deferred",
    "superseded",
]
MemoryRecordStatusCandidate = Literal[
    "proposed",
    "approved_candidate",
    "active_candidate",
    "revoked_candidate",
    "expired_candidate",
    "deleted_candidate",
    "tombstone_candidate",
]
MemoryDeleteModeCandidate = Literal[
    "revoke",
    "expire",
    "tombstone",
    "purge_candidate",
]
MemoryProjectionStatusCandidate = Literal[
    "proposed",
    "approved_candidate",
    "revoked_candidate",
    "expired_candidate",
    "tombstone_candidate",
    "superseded",
]
MemoryProjectionConsumerCandidate = Literal[
    "product_gateway",
    "cognition_agent",
    "runtime_container",
    "cognition_governance",
    "audit_report",
]

ALLOWED_MEMORY_REVIEW_KINDS = [
    "memory_record_write",
    "memory_use",
    "memory_delete",
    "memory_projection",
]
ALLOWED_MEMORY_REVIEW_RESULTS = [
    "approve_candidate",
    "reject_candidate",
    "request_evidence",
    "request_scope_change",
    "request_user_approval",
    "defer",
]
ALLOWED_MEMORY_GOVERNANCE_STATUS_CANDIDATES = [
    "proposed",
    "reviewed",
    "approved_candidate",
    "rejected_candidate",
    "needs_evidence",
    "needs_user_approval",
    "deferred",
    "superseded",
]
ALLOWED_MEMORY_PROJECTION_STATUS_CANDIDATES = [
    "proposed",
    "approved_candidate",
    "revoked_candidate",
    "expired_candidate",
    "tombstone_candidate",
    "superseded",
]
ALLOWED_MEMORY_PROJECTION_CONSUMER_CANDIDATES = [
    "product_gateway",
    "cognition_agent",
    "runtime_container",
    "cognition_governance",
    "audit_report",
]

_FORBIDDEN_MEMORY_KEYS = frozenset(
    {
        "api_key",
        "credential",
        "credentials",
        "full_response",
        "memory_body",
        "memory_raw_body",
        "memory_store_payload",
        "message",
        "messages",
        "payload",
        "prompt",
        "provider_payload",
        "provider_response",
        "raw",
        "raw_input",
        "raw_output",
        "raw_payload",
        "raw_prompt",
        "raw_response",
        "raw_user_message",
        "response",
        "response_text",
        "secret",
        "system_prompt",
        "text",
        "token",
        "tool_input",
        "tool_output",
        "user_message",
    }
)
_SENSITIVE_KEY_EXCEPTIONS = frozenset(
    {
        "raw_output_digest",
        "sensitive_fields_omitted",
    }
)
_FORBIDDEN_TEXT_FRAGMENTS = (
    "api_key",
    "credential",
    "raw prompt",
    "raw response",
    "secret",
    "system prompt",
    "token",
)
_FORBIDDEN_OBJECT_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "runtime_container",
    "composition",
    "litellm",
)
_GENERIC_USE_PURPOSES = frozenset(
    {
        "personalization",
        "personalisation",
        "personalize",
        "remember",
        "use memory",
    }
)
_PRODUCT_GATEWAY_DELETE_MODE_BY_ACTION: dict[str, MemoryDeleteModeCandidate] = {
    "request_revoke": "revoke",
    "request_tombstone": "tombstone",
}
_PRODUCT_GATEWAY_UNSUPPORTED_DELETE_ACTIONS = frozenset(
    {
        "request_hide_from_product_view",
        "request_review",
    }
)
_PRODUCT_GATEWAY_FORBIDDEN_DELETE_ACTIONS = frozenset(
    {
        "delete_store_record",
        "enable_prompt_context",
        "purge_now",
        "rewrite_memory",
        "share_with_agent",
    }
)
_DEFAULT_PRODUCT_GATEWAY_TOMBSTONE_SUMMARY = (
    "Memory projection deletion requested by user; original content is not exposed."
)
_TOMBSTONE_ALLOWED_CONSUMER_CANDIDATES = ("product_gateway", "audit_report")
_TOMBSTONE_DENIED_CONSUMER_CANDIDATES = (
    "cognition_agent",
    "runtime_container",
    "prompt_context",
    "model_memory",
)


class MemoryGovernanceCandidateBaseModel(BaseModel):
    """Base model for internal Memory governance review candidates."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_memory_candidate_boundary(self) -> "MemoryGovernanceCandidateBaseModel":
        violations = _memory_boundary_violations(self.model_dump(mode="python"))
        if violations:
            raise ValueError("; ".join(violations))
        return self


class MemoryRecordReviewCandidate(MemoryGovernanceCandidateBaseModel):
    """Review whether a Memory record candidate may be proposed or approved."""

    review_id: str = Field(..., min_length=1)
    memory_id: str = Field(..., min_length=1)
    memory_kind: MemoryKindCandidate
    subject_scope: MemorySubjectScopeCandidate
    content_summary: str = Field(..., min_length=1)
    provenance_refs: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    approval_ref: str | None = None
    audit_ref: str | None = None
    memory_write_ref: str | None = None
    retention_policy: str = Field(..., min_length=1)
    deletion_policy: str = Field(..., min_length=1)
    visibility: MemoryVisibilityCandidate
    sensitivity: MemorySensitivityCandidate = "none"
    confidence: MemoryConfidenceCandidate = "medium"
    record_status_candidate: MemoryRecordStatusCandidate = "proposed"
    review_result: MemoryReviewResultCandidate
    review_reasons: tuple[str, ...] = Field(default_factory=tuple)
    blocking_reasons: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)
    candidate_only: bool = True
    memory_write_enabled: bool = False
    runtime_enabled: bool = False
    store_write_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_record_review(self) -> "MemoryRecordReviewCandidate":
        _require_false(self.candidate_only is not True, "candidate_only must be true.")
        _require_false(
            self.memory_write_enabled,
            "memory_write_enabled must remain false.",
        )
        _require_false(self.runtime_enabled, "runtime_enabled must remain false.")
        _require_false(
            self.store_write_enabled,
            "store_write_enabled must remain false.",
        )
        if self.memory_kind == "durable":
            _require_present(self.approval_ref, "durable memory requires approval_ref.")
            _require_present(self.audit_ref, "durable memory requires audit_ref.")
            _require_present(
                self.retention_policy,
                "durable memory requires retention_policy.",
            )
            _require_present(
                self.deletion_policy,
                "durable memory requires deletion_policy.",
            )
        _reject_sensitive_text(
            self.content_summary,
            "content_summary must be sanitized.",
        )
        return self


class MemoryUseReviewCandidate(MemoryGovernanceCandidateBaseModel):
    """Review whether a Memory candidate may be used by a task."""

    review_id: str = Field(..., min_length=1)
    memory_id: str = Field(..., min_length=1)
    use_purpose: str = Field(..., min_length=1)
    target_workflow_name: str = Field(..., min_length=1)
    target_session_id: str | None = None
    subject_scope: MemorySubjectScopeCandidate
    allowed_for_governance_review: bool = False
    allowed_for_product_display: bool = False
    allowed_for_workflow_planning: bool = False
    allowed_for_prompt_context: bool = False
    approval_ref: str | None = None
    audit_ref: str | None = None
    provenance_refs: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    review_result: MemoryReviewResultCandidate
    review_reasons: tuple[str, ...] = Field(default_factory=tuple)
    blocking_reasons: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)
    candidate_only: bool = True
    memory_read_enabled: bool = False
    prompt_context_enabled: bool = False
    runtime_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_use_review(self) -> "MemoryUseReviewCandidate":
        _require_false(self.candidate_only is not True, "candidate_only must be true.")
        _require_false(
            self.memory_read_enabled,
            "memory_read_enabled must remain false.",
        )
        _require_false(
            self.prompt_context_enabled,
            "prompt_context_enabled must remain false.",
        )
        _require_false(self.runtime_enabled, "runtime_enabled must remain false.")
        if self.allowed_for_prompt_context:
            _require_present(
                self.approval_ref,
                "allowed_for_prompt_context requires approval_ref.",
            )
            _require_present(
                self.audit_ref,
                "allowed_for_prompt_context requires audit_ref.",
            )
        if self.use_purpose.strip().lower() in _GENERIC_USE_PURPOSES:
            raise ValueError("use_purpose must be specific.")
        return self


class MemoryDeleteReviewCandidate(MemoryGovernanceCandidateBaseModel):
    """Review whether a Memory candidate may be revoked, expired, or tombstoned."""

    review_id: str = Field(..., min_length=1)
    memory_id: str = Field(..., min_length=1)
    delete_mode: MemoryDeleteModeCandidate
    deletion_ref: str | None = None
    approval_ref: str | None = None
    audit_ref: str | None = None
    requester_ref: str | None = None
    subject_scope: MemorySubjectScopeCandidate
    delete_reason: str = Field(..., min_length=1)
    retain_tombstone: bool = True
    tombstone_summary: str | None = None
    review_result: MemoryReviewResultCandidate
    review_reasons: tuple[str, ...] = Field(default_factory=tuple)
    blocking_reasons: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)
    candidate_only: bool = True
    memory_delete_enabled: bool = False
    store_delete_enabled: bool = False
    runtime_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_delete_review(self) -> "MemoryDeleteReviewCandidate":
        _require_false(self.candidate_only is not True, "candidate_only must be true.")
        _require_false(
            self.memory_delete_enabled,
            "memory_delete_enabled must remain false.",
        )
        _require_false(
            self.store_delete_enabled,
            "store_delete_enabled must remain false.",
        )
        _require_false(self.runtime_enabled, "runtime_enabled must remain false.")
        if self.delete_mode == "purge_candidate":
            _require_present(
                self.approval_ref,
                "purge_candidate requires approval_ref.",
            )
            _require_present(self.audit_ref, "purge_candidate requires audit_ref.")
        if self.tombstone_summary:
            _reject_sensitive_text(
                self.tombstone_summary,
                "tombstone_summary must not expose deleted content.",
            )
        return self


class MemoryGovernanceReviewResultCandidate(MemoryGovernanceCandidateBaseModel):
    """Candidate-only result for a Memory governance review."""

    result_id: str = Field(..., min_length=1)
    review_kind: MemoryReviewKind
    review_id: str = Field(..., min_length=1)
    memory_id: str = Field(..., min_length=1)
    status_candidate: MemoryGovernanceStatusCandidate
    result_summary: str = Field(..., min_length=1)
    approved_projection_ref: str | None = None
    approval_ref: str | None = None
    audit_ref: str | None = None
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    blocked_formal_outcome_reasons: tuple[str, ...] = Field(default_factory=tuple)
    required_followups: tuple[str, ...] = Field(default_factory=tuple)
    candidate_only: bool = True
    formal_decision_enabled: bool = False
    formal_outcome_enabled: bool = False
    memory_runtime_enabled: bool = False
    memory_store_enabled: bool = False
    prompt_context_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_result_candidate(self) -> "MemoryGovernanceReviewResultCandidate":
        _require_false(self.candidate_only is not True, "candidate_only must be true.")
        _require_false(
            self.formal_decision_enabled,
            "formal_decision_enabled must remain false.",
        )
        _require_false(
            self.formal_outcome_enabled,
            "formal_outcome_enabled must remain false.",
        )
        _require_false(
            self.memory_runtime_enabled,
            "memory_runtime_enabled must remain false.",
        )
        _require_false(
            self.memory_store_enabled,
            "memory_store_enabled must remain false.",
        )
        _require_false(
            self.prompt_context_enabled,
            "prompt_context_enabled must remain false.",
        )
        return self


class MemoryApprovedProjectionCandidate(MemoryGovernanceCandidateBaseModel):
    """Candidate-only sanitized projection for read-only Memory consumers."""

    projection_id: str = Field(..., min_length=1)
    source_review_id: str = Field(..., min_length=1)
    source_result_id: str | None = None
    memory_id: str = Field(..., min_length=1)
    memory_kind: MemoryKindCandidate
    subject_scope: MemorySubjectScopeCandidate
    projection_status_candidate: MemoryProjectionStatusCandidate = "proposed"
    display_summary: str = Field(..., min_length=1)
    fact_boundary_summary: str = Field(..., min_length=1)
    behavior_effect_summary: str = Field(..., min_length=1)
    value_boundary_summary: str = Field(..., min_length=1)
    use_boundary: str = Field(..., min_length=1)
    provenance_refs: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    approval_ref: str | None = None
    audit_ref: str | None = None
    retention_policy: str = Field(..., min_length=1)
    deletion_policy: str = Field(..., min_length=1)
    visibility: MemoryVisibilityCandidate
    sensitivity: MemorySensitivityCandidate = "none"
    confidence: MemoryConfidenceCandidate = "medium"
    allowed_consumers: tuple[MemoryProjectionConsumerCandidate, ...]
    denied_consumers: tuple[str, ...] = Field(default_factory=tuple)
    prompt_context_allowed: bool = False
    prompt_context_approval_ref: str | None = None
    expires_at: str | None = None
    review_after: str | None = None
    decay_policy: str = Field(..., min_length=1)
    revoke_ref: str | None = None
    tombstone_summary: str | None = None
    superseded_by_projection_ref: str | None = None
    candidate_only: bool = True
    runtime_enabled: bool = False
    store_read_enabled: bool = False
    store_write_enabled: bool = False
    prompt_context_enabled: bool = False
    public_schema_enabled: bool = False
    formal_decision_enabled: bool = False
    formal_outcome_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_projection_candidate(self) -> "MemoryApprovedProjectionCandidate":
        _require_false(self.candidate_only is not True, "candidate_only must be true.")
        _require_false(self.runtime_enabled, "runtime_enabled must remain false.")
        _require_false(
            self.store_read_enabled,
            "store_read_enabled must remain false.",
        )
        _require_false(
            self.store_write_enabled,
            "store_write_enabled must remain false.",
        )
        _require_false(
            self.prompt_context_enabled,
            "prompt_context_enabled must remain false.",
        )
        _require_false(
            self.public_schema_enabled,
            "public_schema_enabled must remain false.",
        )
        _require_false(
            self.formal_decision_enabled,
            "formal_decision_enabled must remain false.",
        )
        _require_false(
            self.formal_outcome_enabled,
            "formal_outcome_enabled must remain false.",
        )
        if not self.allowed_consumers:
            raise ValueError("allowed_consumers must not be empty.")
        if self.memory_kind == "durable":
            _require_present(
                self.approval_ref,
                "durable memory projection requires approval_ref.",
            )
            _require_present(
                self.audit_ref,
                "durable memory projection requires audit_ref.",
            )
            _require_present(
                self.retention_policy,
                "durable memory projection requires retention_policy.",
            )
            _require_present(
                self.deletion_policy,
                "durable memory projection requires deletion_policy.",
            )
        if self.prompt_context_allowed:
            _require_present(
                self.prompt_context_approval_ref,
                "prompt_context_allowed requires prompt_context_approval_ref.",
            )
            _require_present(
                self.approval_ref,
                "prompt_context_allowed requires approval_ref.",
            )
            _require_present(
                self.audit_ref,
                "prompt_context_allowed requires audit_ref.",
            )
        if self.projection_status_candidate == "tombstone_candidate":
            _require_present(
                self.tombstone_summary,
                "tombstone_candidate requires tombstone_summary.",
            )
        if (
            self.metadata.get("delete_mode") == "purge_candidate"
            and self.visibility == "user_visible"
        ):
            raise ValueError("purge_candidate must not generate user_visible projection.")
        _reject_sensitive_text(
            self.display_summary,
            "display_summary must be sanitized.",
        )
        _reject_sensitive_text(
            self.fact_boundary_summary,
            "fact_boundary_summary must be sanitized.",
        )
        _reject_sensitive_text(
            self.behavior_effect_summary,
            "behavior_effect_summary must be sanitized.",
        )
        _reject_sensitive_text(
            self.value_boundary_summary,
            "value_boundary_summary must be sanitized.",
        )
        _reject_sensitive_text(
            self.use_boundary,
            "use_boundary must be sanitized.",
        )
        if self.tombstone_summary:
            _reject_sensitive_text(
                self.tombstone_summary,
                "tombstone_summary must not expose deleted content.",
            )
        return self


def create_memory_record_review_candidate(
    *,
    memory_id: str,
    memory_kind: MemoryKindCandidate,
    subject_scope: MemorySubjectScopeCandidate,
    content_summary: str,
    retention_policy: str,
    deletion_policy: str,
    visibility: MemoryVisibilityCandidate,
    review_result: MemoryReviewResultCandidate,
    provenance_refs: tuple[str, ...] | list[str] | None = None,
    evidence_refs: tuple[str, ...] | list[str] | None = None,
    approval_ref: str | None = None,
    audit_ref: str | None = None,
    memory_write_ref: str | None = None,
    sensitivity: MemorySensitivityCandidate = "none",
    confidence: MemoryConfidenceCandidate = "medium",
    record_status_candidate: MemoryRecordStatusCandidate = "proposed",
    review_reasons: tuple[str, ...] | list[str] | None = None,
    blocking_reasons: tuple[str, ...] | list[str] | None = None,
    warnings: tuple[str, ...] | list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> MemoryRecordReviewCandidate:
    """Create a candidate-only Memory record review."""

    return MemoryRecordReviewCandidate(
        review_id=f"memory-record-review-candidate-{uuid4()}",
        memory_id=memory_id,
        memory_kind=memory_kind,
        subject_scope=subject_scope,
        content_summary=content_summary,
        provenance_refs=_str_tuple(provenance_refs),
        evidence_refs=_str_tuple(evidence_refs),
        approval_ref=approval_ref,
        audit_ref=audit_ref,
        memory_write_ref=memory_write_ref,
        retention_policy=retention_policy,
        deletion_policy=deletion_policy,
        visibility=visibility,
        sensitivity=sensitivity,
        confidence=confidence,
        record_status_candidate=record_status_candidate,
        review_result=review_result,
        review_reasons=_str_tuple(review_reasons),
        blocking_reasons=_str_tuple(blocking_reasons),
        warnings=_str_tuple(warnings),
        metadata={
            "review_kind": "memory_record_write",
            "candidate_only": True,
            "memory_write_enabled": False,
            "runtime_enabled": False,
            "store_write_enabled": False,
            **(metadata or {}),
        },
    )


def create_memory_use_review_candidate(
    *,
    memory_id: str,
    use_purpose: str,
    target_workflow_name: str,
    subject_scope: MemorySubjectScopeCandidate,
    review_result: MemoryReviewResultCandidate,
    target_session_id: str | None = None,
    allowed_for_governance_review: bool = False,
    allowed_for_product_display: bool = False,
    allowed_for_workflow_planning: bool = False,
    allowed_for_prompt_context: bool = False,
    approval_ref: str | None = None,
    audit_ref: str | None = None,
    provenance_refs: tuple[str, ...] | list[str] | None = None,
    evidence_refs: tuple[str, ...] | list[str] | None = None,
    review_reasons: tuple[str, ...] | list[str] | None = None,
    blocking_reasons: tuple[str, ...] | list[str] | None = None,
    warnings: tuple[str, ...] | list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> MemoryUseReviewCandidate:
    """Create a candidate-only Memory use review."""

    return MemoryUseReviewCandidate(
        review_id=f"memory-use-review-candidate-{uuid4()}",
        memory_id=memory_id,
        use_purpose=use_purpose,
        target_workflow_name=target_workflow_name,
        target_session_id=target_session_id,
        subject_scope=subject_scope,
        allowed_for_governance_review=allowed_for_governance_review,
        allowed_for_product_display=allowed_for_product_display,
        allowed_for_workflow_planning=allowed_for_workflow_planning,
        allowed_for_prompt_context=allowed_for_prompt_context,
        approval_ref=approval_ref,
        audit_ref=audit_ref,
        provenance_refs=_str_tuple(provenance_refs),
        evidence_refs=_str_tuple(evidence_refs),
        review_result=review_result,
        review_reasons=_str_tuple(review_reasons),
        blocking_reasons=_str_tuple(blocking_reasons),
        warnings=_str_tuple(warnings),
        metadata={
            "review_kind": "memory_use",
            "candidate_only": True,
            "memory_read_enabled": False,
            "prompt_context_enabled": False,
            "runtime_enabled": False,
            **(metadata or {}),
        },
    )


def create_memory_delete_review_candidate(
    *,
    memory_id: str,
    delete_mode: MemoryDeleteModeCandidate,
    subject_scope: MemorySubjectScopeCandidate,
    delete_reason: str,
    review_result: MemoryReviewResultCandidate,
    deletion_ref: str | None = None,
    approval_ref: str | None = None,
    audit_ref: str | None = None,
    requester_ref: str | None = None,
    retain_tombstone: bool = True,
    tombstone_summary: str | None = None,
    review_reasons: tuple[str, ...] | list[str] | None = None,
    blocking_reasons: tuple[str, ...] | list[str] | None = None,
    warnings: tuple[str, ...] | list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> MemoryDeleteReviewCandidate:
    """Create a candidate-only Memory delete review."""

    return MemoryDeleteReviewCandidate(
        review_id=f"memory-delete-review-candidate-{uuid4()}",
        memory_id=memory_id,
        delete_mode=delete_mode,
        deletion_ref=deletion_ref,
        approval_ref=approval_ref,
        audit_ref=audit_ref,
        requester_ref=requester_ref,
        subject_scope=subject_scope,
        delete_reason=delete_reason,
        retain_tombstone=retain_tombstone,
        tombstone_summary=tombstone_summary,
        review_result=review_result,
        review_reasons=_str_tuple(review_reasons),
        blocking_reasons=_str_tuple(blocking_reasons),
        warnings=_str_tuple(warnings),
        metadata={
            "review_kind": "memory_delete",
            "candidate_only": True,
            "memory_delete_enabled": False,
            "store_delete_enabled": False,
            "runtime_enabled": False,
            **(metadata or {}),
        },
    )


def create_memory_delete_review_from_product_gateway_request(
    deletion_request: Mapping[str, Any] | Any,
    projection: Mapping[str, Any] | Any,
) -> MemoryDeleteReviewCandidate:
    """Map a product-facing deletion request into a Memory delete review."""

    request_data = _coerce_mapping_like(
        deletion_request,
        "deletion_request",
    )
    projection_data = _coerce_mapping_like(projection, "projection")
    _validate_product_gateway_delete_request_boundary(request_data)
    _validate_product_gateway_projection_boundary(projection_data)
    _require_matching_value(
        request_data,
        projection_data,
        "memory_id",
        "deletion request memory_id must match projection memory_id.",
    )
    _require_matching_value(
        request_data,
        projection_data,
        "projection_id",
        "deletion request projection_id must match projection projection_id.",
    )

    requested_action = str(request_data.get("requested_action", ""))
    if requested_action in _PRODUCT_GATEWAY_FORBIDDEN_DELETE_ACTIONS:
        raise ValueError("requested_action is forbidden for Memory delete review.")
    if requested_action in _PRODUCT_GATEWAY_UNSUPPORTED_DELETE_ACTIONS:
        raise ValueError("requested_action does not map to Memory delete review.")
    delete_mode = _PRODUCT_GATEWAY_DELETE_MODE_BY_ACTION.get(requested_action)
    if delete_mode is None:
        raise ValueError("requested_action is not supported.")

    delete_reason = _required_text(
        request_data,
        "request_reason_summary",
        "deletion request requires request_reason_summary.",
    )
    _reject_sensitive_text(delete_reason, "delete_reason must be sanitized.")
    tombstone_summary = _product_gateway_tombstone_summary(
        delete_mode,
        projection_data,
    )

    warnings: list[str] = []
    if projection_data.get("prompt_context_allowed"):
        warnings.append("source_projection_prompt_context_allowed_but_disabled")

    return create_memory_delete_review_candidate(
        memory_id=_required_text(
            request_data,
            "memory_id",
            "deletion request requires memory_id.",
        ),
        delete_mode=delete_mode,
        subject_scope=_required_text(
            projection_data,
            "subject_scope",
            "projection requires subject_scope.",
        ),
        delete_reason=delete_reason,
        review_result="approve_candidate",
        approval_ref=request_data.get("approval_ref"),
        audit_ref=_required_text(
            request_data,
            "audit_ref",
            "deletion request requires audit_ref.",
        ),
        requester_ref=_required_text(
            request_data,
            "requested_by_ref",
            "deletion request requires requested_by_ref.",
        ),
        retain_tombstone=True,
        tombstone_summary=tombstone_summary,
        review_reasons=(
            "Product Gateway deletion request admitted into Memory delete review.",
        ),
        warnings=tuple(warnings),
        metadata={
            "source": "product_gateway_memory_deletion_request",
            "source_delete_request_id": request_data.get("delete_request_id"),
            "source_projection_id": request_data.get("projection_id"),
            "source_projection_status_candidate": projection_data.get(
                "projection_status_candidate"
            ),
            "source_projection_visibility": projection_data.get("visibility"),
            "requested_action": requested_action,
            "product_gateway_request_candidate_only": True,
            "source_projection_candidate_only": True,
            "prompt_context_allowed": bool(
                projection_data.get("prompt_context_allowed", False)
            ),
            "prompt_context_enabled": False,
            "store_delete_enabled": False,
            "memory_delete_enabled": False,
            "runtime_enabled": False,
        },
    )


def create_memory_governance_review_result_candidate(
    review_candidate: MemoryRecordReviewCandidate
    | MemoryUseReviewCandidate
    | MemoryDeleteReviewCandidate
    | dict[str, Any],
    *,
    status_candidate: MemoryGovernanceStatusCandidate | None = None,
    result_summary: str | None = None,
    approved_projection_ref: str | None = None,
    approval_ref: str | None = None,
    audit_ref: str | None = None,
    evidence_refs: tuple[str, ...] | list[str] | None = None,
    blocked_formal_outcome_reasons: tuple[str, ...] | list[str] | None = None,
    required_followups: tuple[str, ...] | list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> MemoryGovernanceReviewResultCandidate:
    """Create a candidate-only Memory governance review result."""

    review = _as_review_candidate(review_candidate)
    review_kind = _review_kind(review)
    resolved_status = status_candidate or _status_from_review_result(
        review.review_result
    )
    return MemoryGovernanceReviewResultCandidate(
        result_id=f"memory-governance-review-result-candidate-{uuid4()}",
        review_kind=review_kind,
        review_id=review.review_id,
        memory_id=review.memory_id,
        status_candidate=resolved_status,
        result_summary=result_summary
        or _default_result_summary(review_kind, review.memory_id, resolved_status),
        approved_projection_ref=approved_projection_ref,
        approval_ref=approval_ref or getattr(review, "approval_ref", None),
        audit_ref=audit_ref or getattr(review, "audit_ref", None),
        evidence_refs=_str_tuple(evidence_refs) or getattr(review, "evidence_refs", ()),
        blocked_formal_outcome_reasons=_str_tuple(blocked_formal_outcome_reasons)
        or _blocked_formal_outcome_reasons(review),
        required_followups=_str_tuple(required_followups),
        metadata={
            "candidate_only": True,
            "formal_decision_enabled": False,
            "formal_outcome_enabled": False,
            "memory_runtime_enabled": False,
            "memory_store_enabled": False,
            "prompt_context_enabled": False,
            "source_review_result": review.review_result,
            **(metadata or {}),
        },
    )


def create_tombstone_projection_from_memory_delete_review_result(
    delete_review: Mapping[str, Any] | Any,
    delete_result: Mapping[str, Any] | Any,
    source_projection: Mapping[str, Any] | Any,
    *,
    projection_id: str | None = None,
) -> MemoryApprovedProjectionCandidate:
    """Create a tombstone projection from a candidate Memory delete review."""

    review_data = _coerce_mapping_like(delete_review, "delete_review")
    result_data = _coerce_mapping_like(delete_result, "delete_result")
    source_data = _coerce_mapping_like(source_projection, "source_projection")
    _validate_tombstone_delete_review(review_data)
    _validate_tombstone_delete_result(result_data, review_data)
    _validate_tombstone_source_projection(source_data, review_data)

    tombstone_summary = _required_text(
        review_data,
        "tombstone_summary",
        "tombstone projection requires tombstone_summary.",
    )
    _reject_sensitive_text(
        tombstone_summary,
        "tombstone_summary must not expose deleted content.",
    )
    allowed_consumers = _tombstone_allowed_consumers(source_data)
    denied_consumers = _tombstone_denied_consumers(source_data)
    resolved_projection_id = projection_id or (
        f"memory-projection://candidate/tombstone-{uuid4()}"
    )

    return create_memory_approved_projection_candidate(
        projection_id=resolved_projection_id,
        source_review_id=_required_text(
            review_data,
            "review_id",
            "delete review requires review_id.",
        ),
        source_result_id=_required_text(
            result_data,
            "result_id",
            "delete result requires result_id.",
        ),
        memory_id=_required_text(
            source_data,
            "memory_id",
            "source projection requires memory_id.",
        ),
        memory_kind=_required_text(
            source_data,
            "memory_kind",
            "source projection requires memory_kind.",
        ),
        subject_scope=_required_text(
            source_data,
            "subject_scope",
            "source projection requires subject_scope.",
        ),
        projection_status_candidate="tombstone_candidate",
        display_summary="Memory projection was deleted by governed user request.",
        fact_boundary_summary=(
            "Deletion is backed by Memory delete review and review result candidates."
        ),
        behavior_effect_summary=(
            "Future consumers must not reuse the deleted Memory projection."
        ),
        value_boundary_summary=(
            "User deletion intent is preserved as a deletion placeholder."
        ),
        use_boundary=(
            "Display deletion status only; no prompt injection, runtime use, or reuse."
        ),
        provenance_refs=(
            _required_text(
                review_data,
                "review_id",
                "delete review requires review_id.",
            ),
        ),
        evidence_refs=(
            _required_text(
                result_data,
                "result_id",
                "delete result requires result_id.",
            ),
        ),
        approval_ref=review_data.get("approval_ref"),
        audit_ref=review_data.get("audit_ref"),
        retention_policy="retain_tombstone_for_audit_only",
        deletion_policy="exclude_from_future_use",
        visibility="user_visible",
        sensitivity=str(source_data.get("sensitivity", "none")),
        confidence=str(source_data.get("confidence", "medium")),
        allowed_consumers=allowed_consumers,
        denied_consumers=denied_consumers,
        decay_policy="no_reuse_after_tombstone",
        revoke_ref=review_data.get("deletion_ref")
        or review_data.get("metadata", {}).get("source_delete_request_id"),
        tombstone_summary=tombstone_summary,
        metadata={
            "delete_mode": "tombstone",
            "source_delete_review_id": review_data.get("review_id"),
            "source_delete_result_id": result_data.get("result_id"),
            "source_projection_id": source_data.get("projection_id"),
            "candidate_only": True,
            "runtime_enabled": False,
            "store_read_enabled": False,
            "store_write_enabled": False,
            "prompt_context_enabled": False,
            "public_schema_enabled": False,
        },
    )


def create_memory_approved_projection_candidate(
    *,
    projection_id: str,
    source_review_id: str,
    memory_id: str,
    memory_kind: MemoryKindCandidate,
    subject_scope: MemorySubjectScopeCandidate,
    display_summary: str,
    fact_boundary_summary: str,
    behavior_effect_summary: str,
    value_boundary_summary: str,
    use_boundary: str,
    retention_policy: str,
    deletion_policy: str,
    visibility: MemoryVisibilityCandidate,
    allowed_consumers: tuple[MemoryProjectionConsumerCandidate, ...]
    | list[MemoryProjectionConsumerCandidate],
    source_result_id: str | None = None,
    projection_status_candidate: MemoryProjectionStatusCandidate = "proposed",
    provenance_refs: tuple[str, ...] | list[str] | None = None,
    evidence_refs: tuple[str, ...] | list[str] | None = None,
    approval_ref: str | None = None,
    audit_ref: str | None = None,
    sensitivity: MemorySensitivityCandidate = "none",
    confidence: MemoryConfidenceCandidate = "medium",
    denied_consumers: tuple[str, ...] | list[str] | None = None,
    prompt_context_allowed: bool = False,
    prompt_context_approval_ref: str | None = None,
    expires_at: str | None = None,
    review_after: str | None = None,
    decay_policy: str = "no_automatic_decay_before_review",
    revoke_ref: str | None = None,
    tombstone_summary: str | None = None,
    superseded_by_projection_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> MemoryApprovedProjectionCandidate:
    """Create a candidate-only approved Memory projection."""

    return MemoryApprovedProjectionCandidate(
        projection_id=projection_id,
        source_review_id=source_review_id,
        source_result_id=source_result_id,
        memory_id=memory_id,
        memory_kind=memory_kind,
        subject_scope=subject_scope,
        projection_status_candidate=projection_status_candidate,
        display_summary=display_summary,
        fact_boundary_summary=fact_boundary_summary,
        behavior_effect_summary=behavior_effect_summary,
        value_boundary_summary=value_boundary_summary,
        use_boundary=use_boundary,
        provenance_refs=_str_tuple(provenance_refs),
        evidence_refs=_str_tuple(evidence_refs),
        approval_ref=approval_ref,
        audit_ref=audit_ref,
        retention_policy=retention_policy,
        deletion_policy=deletion_policy,
        visibility=visibility,
        sensitivity=sensitivity,
        confidence=confidence,
        allowed_consumers=tuple(allowed_consumers),
        denied_consumers=_str_tuple(denied_consumers),
        prompt_context_allowed=prompt_context_allowed,
        prompt_context_approval_ref=prompt_context_approval_ref,
        expires_at=expires_at,
        review_after=review_after,
        decay_policy=decay_policy,
        revoke_ref=revoke_ref,
        tombstone_summary=tombstone_summary,
        superseded_by_projection_ref=superseded_by_projection_ref,
        metadata={
            "projection_kind": "approved_memory_projection_candidate",
            "candidate_only": True,
            "runtime_enabled": False,
            "store_read_enabled": False,
            "store_write_enabled": False,
            "prompt_context_enabled": False,
            "public_schema_enabled": False,
            "formal_decision_enabled": False,
            "formal_outcome_enabled": False,
            **(metadata or {}),
        },
    )


def _as_review_candidate(
    value: MemoryRecordReviewCandidate
    | MemoryUseReviewCandidate
    | MemoryDeleteReviewCandidate
    | dict[str, Any],
) -> MemoryRecordReviewCandidate | MemoryUseReviewCandidate | MemoryDeleteReviewCandidate:
    if isinstance(
        value,
        (
            MemoryRecordReviewCandidate,
            MemoryUseReviewCandidate,
            MemoryDeleteReviewCandidate,
        ),
    ):
        return value
    if isinstance(value, dict):
        review_kind = value.get("metadata", {}).get("review_kind")
        if review_kind == "memory_use":
            return MemoryUseReviewCandidate.model_validate(value)
        if review_kind == "memory_delete":
            return MemoryDeleteReviewCandidate.model_validate(value)
        return MemoryRecordReviewCandidate.model_validate(value)
    raise TypeError("Memory review candidate or compatible mapping is required.")


def _review_kind(
    review: MemoryRecordReviewCandidate
    | MemoryUseReviewCandidate
    | MemoryDeleteReviewCandidate,
) -> MemoryReviewKind:
    if isinstance(review, MemoryUseReviewCandidate):
        if review.allowed_for_product_display or review.allowed_for_prompt_context:
            return "memory_projection"
        return "memory_use"
    if isinstance(review, MemoryDeleteReviewCandidate):
        return "memory_delete"
    return "memory_record_write"


def _status_from_review_result(
    review_result: MemoryReviewResultCandidate,
) -> MemoryGovernanceStatusCandidate:
    if review_result == "approve_candidate":
        return "approved_candidate"
    if review_result == "reject_candidate":
        return "rejected_candidate"
    if review_result == "request_evidence":
        return "needs_evidence"
    if review_result == "request_user_approval":
        return "needs_user_approval"
    if review_result in {"request_scope_change", "defer"}:
        return "deferred"
    return "reviewed"


def _default_result_summary(
    review_kind: MemoryReviewKind,
    memory_id: str,
    status_candidate: MemoryGovernanceStatusCandidate,
) -> str:
    return (
        f"Memory governance review candidate for {memory_id}: "
        f"review_kind={review_kind}, status_candidate={status_candidate}."
    )


def _blocked_formal_outcome_reasons(
    review: MemoryRecordReviewCandidate
    | MemoryUseReviewCandidate
    | MemoryDeleteReviewCandidate,
) -> tuple[str, ...]:
    reasons = [
        "Memory governance review output is candidate-only.",
        "Formal GovernanceDecision is not produced.",
        "Formal GovernanceOutcome is disabled.",
        "Memory runtime is disabled.",
        "Memory store is disabled.",
    ]
    if isinstance(review, MemoryUseReviewCandidate):
        reasons.append("Prompt context injection is disabled.")
    if isinstance(review, MemoryDeleteReviewCandidate):
        reasons.append("Memory delete action is disabled.")
    if isinstance(review, MemoryRecordReviewCandidate):
        reasons.append("Memory write action is disabled.")
    return tuple(reasons)


def _coerce_mapping_like(value: Mapping[str, Any] | Any, label: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return dict(model_dump(mode="python"))
    raise TypeError(f"{label} must be a mapping or model_dump-compatible object.")


def _validate_product_gateway_delete_request_boundary(
    data: Mapping[str, Any],
) -> None:
    if data.get("governance_review_required") is not True:
        raise ValueError("deletion request must require governance review.")
    if data.get("candidate_only") is not True:
        raise ValueError("deletion request candidate_only must be true.")
    for flag_name in (
        "store_write_enabled",
        "runtime_enabled",
        "formal_decision_enabled",
        "formal_outcome_enabled",
    ):
        if data.get(flag_name):
            raise ValueError(f"deletion request {flag_name} must remain false.")
    _required_text(data, "delete_request_id", "deletion request requires id.")
    _required_text(data, "projection_id", "deletion request requires projection_id.")
    _required_text(data, "memory_id", "deletion request requires memory_id.")


def _validate_product_gateway_projection_boundary(data: Mapping[str, Any]) -> None:
    if "product_gateway" not in tuple(data.get("allowed_consumers", ())):
        raise ValueError("projection must allow product_gateway consumer.")
    if data.get("visibility") != "user_visible":
        raise ValueError("projection must be user_visible for product_gateway intake.")
    if data.get("candidate_only") is not True:
        raise ValueError("projection candidate_only must be true.")
    for flag_name in (
        "runtime_enabled",
        "store_read_enabled",
        "store_write_enabled",
        "prompt_context_enabled",
        "public_schema_enabled",
        "formal_decision_enabled",
        "formal_outcome_enabled",
    ):
        if data.get(flag_name):
            raise ValueError(f"projection {flag_name} must remain false.")
    _required_text(data, "projection_id", "projection requires projection_id.")
    _required_text(data, "memory_id", "projection requires memory_id.")
    _required_text(data, "subject_scope", "projection requires subject_scope.")


def _require_matching_value(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
    field_name: str,
    message: str,
) -> None:
    if str(first.get(field_name, "")) != str(second.get(field_name, "")):
        raise ValueError(message)


def _product_gateway_tombstone_summary(
    delete_mode: MemoryDeleteModeCandidate,
    projection_data: Mapping[str, Any],
) -> str | None:
    if delete_mode != "tombstone":
        return None
    tombstone_summary = projection_data.get("tombstone_summary")
    if tombstone_summary:
        summary = str(tombstone_summary)
        _reject_sensitive_text(
            summary,
            "tombstone_summary must not expose deleted content.",
        )
        return summary
    return _DEFAULT_PRODUCT_GATEWAY_TOMBSTONE_SUMMARY


def _validate_tombstone_delete_review(data: Mapping[str, Any]) -> None:
    if data.get("delete_mode") != "tombstone":
        raise ValueError("tombstone projection requires delete_mode=tombstone.")
    _required_text(data, "tombstone_summary", "delete review requires tombstone_summary.")
    if data.get("candidate_only") is not True:
        raise ValueError("delete review candidate_only must be true.")
    for flag_name in ("memory_delete_enabled", "store_delete_enabled", "runtime_enabled"):
        if data.get(flag_name):
            raise ValueError(f"delete review {flag_name} must remain false.")
    delete_reason = _required_text(
        data,
        "delete_reason",
        "delete review requires delete_reason.",
    )
    _reject_sensitive_text(delete_reason, "delete_reason must be sanitized.")


def _validate_tombstone_delete_result(
    result_data: Mapping[str, Any],
    review_data: Mapping[str, Any],
) -> None:
    if result_data.get("review_kind") != "memory_delete":
        raise ValueError("delete result review_kind must be memory_delete.")
    if result_data.get("status_candidate") != "approved_candidate":
        raise ValueError("delete result status_candidate must be approved_candidate.")
    if result_data.get("candidate_only") is not True:
        raise ValueError("delete result candidate_only must be true.")
    _require_matching_value(
        result_data,
        review_data,
        "review_id",
        "delete result review_id must match delete review review_id.",
    )
    _require_matching_value(
        result_data,
        review_data,
        "memory_id",
        "delete result memory_id must match delete review memory_id.",
    )
    for flag_name in (
        "formal_decision_enabled",
        "formal_outcome_enabled",
        "memory_runtime_enabled",
        "memory_store_enabled",
        "prompt_context_enabled",
    ):
        if result_data.get(flag_name):
            raise ValueError(f"delete result {flag_name} must remain false.")
    blocked_reasons = tuple(result_data.get("blocked_formal_outcome_reasons", ()))
    if "Memory delete action is disabled." not in blocked_reasons:
        raise ValueError("delete result must keep Memory delete action disabled.")


def _validate_tombstone_source_projection(
    source_data: Mapping[str, Any],
    review_data: Mapping[str, Any],
) -> None:
    _require_matching_value(
        source_data,
        review_data,
        "memory_id",
        "source projection memory_id must match delete review memory_id.",
    )
    if source_data.get("candidate_only") is not True:
        raise ValueError("source projection candidate_only must be true.")
    for flag_name in (
        "runtime_enabled",
        "store_read_enabled",
        "store_write_enabled",
        "prompt_context_enabled",
        "public_schema_enabled",
        "formal_decision_enabled",
        "formal_outcome_enabled",
    ):
        if source_data.get(flag_name):
            raise ValueError(f"source projection {flag_name} must remain false.")
    if not tuple(source_data.get("allowed_consumers", ())):
        raise ValueError("source projection allowed_consumers must not be empty.")
    _required_text(
        source_data,
        "projection_id",
        "source projection requires projection_id.",
    )


def _tombstone_allowed_consumers(
    source_data: Mapping[str, Any],
) -> tuple[MemoryProjectionConsumerCandidate, ...]:
    source_consumers = tuple(source_data.get("allowed_consumers", ()))
    allowed = tuple(
        consumer
        for consumer in _TOMBSTONE_ALLOWED_CONSUMER_CANDIDATES
        if consumer in source_consumers
    )
    if not allowed:
        raise ValueError("tombstone projection requires product_gateway or audit_report.")
    return allowed


def _tombstone_denied_consumers(source_data: Mapping[str, Any]) -> tuple[str, ...]:
    denied: list[str] = []
    for consumer in _TOMBSTONE_DENIED_CONSUMER_CANDIDATES + tuple(
        source_data.get("denied_consumers", ())
    ):
        consumer_text = str(consumer)
        if consumer_text not in denied:
            denied.append(consumer_text)
    return tuple(denied)


def _required_text(data: Mapping[str, Any], field_name: str, message: str) -> str:
    value = data.get(field_name)
    if value is None or str(value).strip() == "":
        raise ValueError(message)
    return str(value)


def _memory_boundary_violations(value: Any, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, nested_value in value.items():
            key_text = str(key)
            normalized_key = key_text.lower()
            child_path = f"{path}.{key_text}"
            if (
                normalized_key in _FORBIDDEN_MEMORY_KEYS
                and normalized_key not in _SENSITIVE_KEY_EXCEPTIONS
            ):
                violations.append(f"{child_path} is forbidden in Memory candidates.")
            violations.extend(_memory_boundary_violations(nested_value, child_path))
        return violations
    if isinstance(value, (list, tuple, set)):
        for index, item in enumerate(value):
            violations.extend(_memory_boundary_violations(item, f"{path}[{index}]"))
        return violations
    if _is_runtime_object(value):
        violations.append(f"{path} leaks a runtime object.")
    return violations


def _is_runtime_object(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return False
    module_name = type(value).__module__
    return module_name.startswith(_FORBIDDEN_OBJECT_MODULE_PREFIXES)


def _reject_sensitive_text(value: str, message: str) -> None:
    normalized = value.lower()
    if any(fragment in normalized for fragment in _FORBIDDEN_TEXT_FRAGMENTS):
        raise ValueError(message)


def _require_present(value: str | None, message: str) -> None:
    if not value:
        raise ValueError(message)


def _require_false(condition: bool, message: str) -> None:
    if condition:
        raise ValueError(message)


def _str_tuple(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    return tuple(str(value) for value in values or ())
