"""Candidate-only Memory projection views for product_gateway."""

from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_gateway.contracts import _raise_if_raw_payload_found


PRODUCT_GATEWAY_MEMORY_CONSUMER = "product_gateway"
PRODUCT_GATEWAY_MEMORY_SOURCE = "product_gateway.memory_projection"

MemoryProjectionStatus = Literal[
    "proposed",
    "approved_candidate",
    "rejected_candidate",
    "tombstone_candidate",
    "superseded_candidate",
]
ProductGatewayMemoryAction = Literal[
    "request_revoke",
    "request_tombstone",
    "request_hide_from_product_view",
    "request_review",
]

FORBIDDEN_MEMORY_TEXT_MARKERS = frozenset(
    {
        "api_key",
        "credential",
        "password",
        "raw prompt",
        "raw response",
        "raw user",
        "secret",
        "token",
    }
)
FORBIDDEN_DELETE_ACTIONS = frozenset(
    {
        "delete_store_record",
        "enable_prompt_context",
        "purge_now",
        "rewrite_memory",
        "share_with_agent",
    }
)


class ProductGatewayMemoryProjectionBase(BaseModel):
    """Shared product-facing invariants for Memory projection candidates."""

    model_config = ConfigDict(extra="forbid")

    candidate_only: bool = True
    store_read_enabled: bool = False
    store_write_enabled: bool = False
    runtime_enabled: bool = False
    public_schema_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_base_boundary(self) -> "ProductGatewayMemoryProjectionBase":
        if self.candidate_only is not True:
            raise ValueError("candidate_only must be true.")
        if self.store_read_enabled:
            raise ValueError("store_read_enabled must remain false.")
        if self.store_write_enabled:
            raise ValueError("store_write_enabled must remain false.")
        if self.runtime_enabled:
            raise ValueError("runtime_enabled must remain false.")
        if self.public_schema_enabled:
            raise ValueError("public_schema_enabled must remain false.")
        _raise_if_raw_payload_found(self.metadata, field_name="metadata")
        return self


class ProductGatewayMemoryProjectionViewCandidate(ProductGatewayMemoryProjectionBase):
    """User-visible read-only view over a governed Memory projection."""

    view_id: str = Field(..., min_length=1)
    projection_id: str = Field(..., min_length=1)
    memory_id: str = Field(..., min_length=1)
    projection_status: MemoryProjectionStatus
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
    visibility: str = Field(..., min_length=1)
    sensitivity: str = Field(..., min_length=1)
    confidence: str = Field(..., min_length=1)
    allowed_actions: tuple[ProductGatewayMemoryAction, ...] = Field(
        default_factory=tuple
    )
    disabled_actions: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_view_candidate(self) -> "ProductGatewayMemoryProjectionViewCandidate":
        if self.visibility != "user_visible":
            raise ValueError("product_gateway Memory view requires user_visible projection.")
        if self.projection_status == "tombstone_candidate":
            raise ValueError("tombstone_candidate requires tombstone view.")
        for field_name in (
            "display_summary",
            "fact_boundary_summary",
            "behavior_effect_summary",
            "value_boundary_summary",
            "use_boundary",
        ):
            _reject_forbidden_memory_text(getattr(self, field_name), field_name)
        return self


class ProductGatewayMemoryDeletionRequestCandidate(ProductGatewayMemoryProjectionBase):
    """User-requested Memory deletion intent, not a deletion execution result."""

    delete_request_id: str = Field(..., min_length=1)
    projection_id: str = Field(..., min_length=1)
    memory_id: str = Field(..., min_length=1)
    requested_action: ProductGatewayMemoryAction
    request_reason_summary: str = Field(..., min_length=1)
    requested_by_ref: str = Field(..., min_length=1)
    approval_ref: str | None = None
    audit_ref: str = Field(..., min_length=1)
    deletion_policy: str = Field(..., min_length=1)
    governance_review_required: bool = True
    formal_decision_enabled: bool = False
    formal_outcome_enabled: bool = False

    @model_validator(mode="after")
    def validate_delete_request(self) -> "ProductGatewayMemoryDeletionRequestCandidate":
        if self.governance_review_required is not True:
            raise ValueError("governance_review_required must be true.")
        if self.formal_decision_enabled:
            raise ValueError("formal_decision_enabled must remain false.")
        if self.formal_outcome_enabled:
            raise ValueError("formal_outcome_enabled must remain false.")
        if self.requested_action in FORBIDDEN_DELETE_ACTIONS:
            raise ValueError("requested_action is not allowed for product_gateway.")
        _reject_forbidden_memory_text(
            self.request_reason_summary,
            "request_reason_summary",
        )
        return self


class ProductGatewayMemoryTombstoneViewCandidate(ProductGatewayMemoryProjectionBase):
    """User-visible tombstone status without exposing deleted Memory content."""

    tombstone_view_id: str = Field(..., min_length=1)
    projection_id: str = Field(..., min_length=1)
    memory_id: str = Field(..., min_length=1)
    tombstone_summary: str = Field(..., min_length=1)
    revoke_ref: str | None = None
    audit_ref: str | None = None
    retention_policy: str = Field(..., min_length=1)
    deletion_policy: str = Field(..., min_length=1)
    allowed_actions: tuple[ProductGatewayMemoryAction, ...] = Field(
        default_factory=tuple
    )

    @model_validator(mode="after")
    def validate_tombstone_view(self) -> "ProductGatewayMemoryTombstoneViewCandidate":
        _reject_forbidden_memory_text(self.tombstone_summary, "tombstone_summary")
        return self


def build_product_gateway_memory_projection_view(
    projection: Mapping[str, Any] | Any,
) -> ProductGatewayMemoryProjectionViewCandidate:
    """Build a user-visible read-only Memory projection view candidate."""

    data = _coerce_projection_data(projection)
    _validate_projection_for_product_gateway(data)
    if data.get("projection_status_candidate") == "tombstone_candidate":
        raise ValueError("tombstone_candidate requires tombstone view.")
    return ProductGatewayMemoryProjectionViewCandidate(
        view_id=f"product-gateway-memory-view:{data['projection_id']}",
        projection_id=str(data["projection_id"]),
        memory_id=str(data["memory_id"]),
        projection_status=data["projection_status_candidate"],
        display_summary=str(data["display_summary"]),
        fact_boundary_summary=str(data["fact_boundary_summary"]),
        behavior_effect_summary=str(data["behavior_effect_summary"]),
        value_boundary_summary=str(data["value_boundary_summary"]),
        use_boundary=str(data["use_boundary"]),
        provenance_refs=tuple(data.get("provenance_refs", ())),
        evidence_refs=tuple(data.get("evidence_refs", ())),
        approval_ref=data.get("approval_ref"),
        audit_ref=data.get("audit_ref"),
        retention_policy=str(data["retention_policy"]),
        deletion_policy=str(data["deletion_policy"]),
        visibility=str(data["visibility"]),
        sensitivity=str(data.get("sensitivity", "none")),
        confidence=str(data.get("confidence", "medium")),
        allowed_actions=(
            "request_revoke",
            "request_tombstone",
            "request_hide_from_product_view",
            "request_review",
        ),
        disabled_actions=(
            "purge_now",
            "delete_store_record",
            "rewrite_memory",
            "enable_prompt_context",
            "share_with_agent",
        ),
        warnings=tuple(_view_warnings(data)),
        metadata=_base_metadata(data),
    )


def build_product_gateway_memory_deletion_request(
    projection: Mapping[str, Any] | Any,
    *,
    delete_request_id: str,
    requested_action: ProductGatewayMemoryAction,
    request_reason_summary: str,
    requested_by_ref: str,
    audit_ref: str,
    approval_ref: str | None = None,
) -> ProductGatewayMemoryDeletionRequestCandidate:
    """Build a governed deletion request candidate without executing deletion."""

    data = _coerce_projection_data(projection)
    _validate_projection_for_product_gateway(data)
    return ProductGatewayMemoryDeletionRequestCandidate(
        delete_request_id=delete_request_id,
        projection_id=str(data["projection_id"]),
        memory_id=str(data["memory_id"]),
        requested_action=requested_action,
        request_reason_summary=request_reason_summary,
        requested_by_ref=requested_by_ref,
        approval_ref=approval_ref,
        audit_ref=audit_ref,
        deletion_policy=str(data["deletion_policy"]),
        governance_review_required=True,
        store_write_enabled=False,
        runtime_enabled=False,
        formal_decision_enabled=False,
        formal_outcome_enabled=False,
        metadata=_base_metadata(data),
    )


def build_product_gateway_memory_tombstone_view(
    projection: Mapping[str, Any] | Any,
) -> ProductGatewayMemoryTombstoneViewCandidate:
    """Build a user-visible tombstone view candidate."""

    data = _coerce_projection_data(projection)
    _validate_projection_for_product_gateway(data)
    if data.get("projection_status_candidate") != "tombstone_candidate":
        raise ValueError("tombstone view requires tombstone_candidate projection.")
    tombstone_summary = data.get("tombstone_summary")
    if not tombstone_summary:
        raise ValueError("tombstone view requires tombstone_summary.")
    return ProductGatewayMemoryTombstoneViewCandidate(
        tombstone_view_id=f"product-gateway-memory-tombstone:{data['projection_id']}",
        projection_id=str(data["projection_id"]),
        memory_id=str(data["memory_id"]),
        tombstone_summary=str(tombstone_summary),
        revoke_ref=data.get("revoke_ref"),
        audit_ref=data.get("audit_ref"),
        retention_policy=str(data["retention_policy"]),
        deletion_policy=str(data["deletion_policy"]),
        allowed_actions=("request_review",),
        metadata=_base_metadata(data),
    )


def _coerce_projection_data(projection: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(projection, Mapping):
        return dict(projection)
    model_dump = getattr(projection, "model_dump", None)
    if callable(model_dump):
        return dict(model_dump(mode="python"))
    raise TypeError("projection must be a mapping or model_dump-compatible object.")


def _validate_projection_for_product_gateway(data: Mapping[str, Any]) -> None:
    if PRODUCT_GATEWAY_MEMORY_CONSUMER not in tuple(data.get("allowed_consumers", ())):
        raise ValueError("projection must allow product_gateway consumer.")
    if data.get("visibility") != "user_visible":
        raise ValueError("product_gateway projection requires user_visible visibility.")
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
            raise ValueError(f"{flag_name} must remain false.")
    if data.get("candidate_only") is not True:
        raise ValueError("projection candidate_only must be true.")
    for field_name in (
        "display_summary",
        "fact_boundary_summary",
        "behavior_effect_summary",
        "value_boundary_summary",
        "use_boundary",
    ):
        _reject_forbidden_memory_text(str(data.get(field_name, "")), field_name)


def _base_metadata(data: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source": PRODUCT_GATEWAY_MEMORY_SOURCE,
        "source_projection_id": data.get("projection_id"),
        "source_review_id": data.get("source_review_id"),
        "source_result_id": data.get("source_result_id"),
        "memory_kind": data.get("memory_kind"),
        "subject_scope": data.get("subject_scope"),
        "projection_status_candidate": data.get("projection_status_candidate"),
        "prompt_context_allowed": bool(data.get("prompt_context_allowed", False)),
        "prompt_context_enabled": False,
        "store_read_enabled": False,
        "store_write_enabled": False,
        "runtime_enabled": False,
        "public_schema_enabled": False,
    }


def _view_warnings(data: Mapping[str, Any]) -> tuple[str, ...]:
    warnings: list[str] = []
    if data.get("prompt_context_allowed"):
        warnings.append("prompt_context_allowed_but_not_enabled")
    if data.get("review_after"):
        warnings.append("projection_requires_periodic_review")
    return tuple(warnings)


def _reject_forbidden_memory_text(value: str, field_name: str) -> None:
    lowered = value.lower()
    if any(marker in lowered for marker in FORBIDDEN_MEMORY_TEXT_MARKERS):
        raise ValueError(f"{field_name} must be sanitized.")


__all__ = [
    "ProductGatewayMemoryDeletionRequestCandidate",
    "ProductGatewayMemoryProjectionViewCandidate",
    "ProductGatewayMemoryTombstoneViewCandidate",
    "build_product_gateway_memory_deletion_request",
    "build_product_gateway_memory_projection_view",
    "build_product_gateway_memory_tombstone_view",
]
