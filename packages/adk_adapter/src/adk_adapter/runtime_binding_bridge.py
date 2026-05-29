"""Bridge ADK runtime safe projections to product-level binding contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from behavior_contracts.continuable_evidence_session import (
    guard_continuable_evidence_session_runtime_binding,
)
from behavior_contracts.governance_candidate import CandidateGuardResult
from schemas.continuable_evidence_session import (
    CONTINUABLE_EVIDENCE_SESSION_PRODUCT,
    CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_PAYLOAD_TYPE,
    CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_REF_PREFIX,
    CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_VERSION,
    ContinuableEvidenceSessionRuntimeBindingSchema,
    validate_continuable_evidence_session_runtime_binding,
)

from adk_adapter.runtime_binding_probe import AdkRuntimeBindingSafeProjection


@dataclass(frozen=True)
class AdkRuntimeBindingProductBridgeResult:
    """Result of mapping an ADK safe projection into a product contract."""

    runtime_binding_payload: dict[str, Any]
    guard_result: CandidateGuardResult
    source_projection_ref: str
    runtime_binding: ContinuableEvidenceSessionRuntimeBindingSchema | None = None
    schema_validation_passed: bool = False
    schema_validation_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Return whether adapter-local contract gates passed."""

        return self.schema_validation_passed and self.guard_result.passed


def build_continuable_evidence_session_runtime_binding_from_adk_projection(
    projection: AdkRuntimeBindingSafeProjection,
    *,
    continuable_evidence_session_ref: str,
    runtime_binding_ref: str | None = None,
    runtime_binding_status: str = "probed",
    runtime_binding_evaluation_summary_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ContinuableEvidenceSessionRuntimeBindingSchema:
    """Build a validated product-level runtime binding from a safe projection."""

    payload = _runtime_binding_payload_from_projection(
        projection,
        continuable_evidence_session_ref=continuable_evidence_session_ref,
        runtime_binding_ref=runtime_binding_ref,
        runtime_binding_status=runtime_binding_status,
        runtime_binding_evaluation_summary_ref=runtime_binding_evaluation_summary_ref,
        metadata=metadata,
    )
    return validate_continuable_evidence_session_runtime_binding(payload)


def validate_adk_runtime_binding_product_bridge(
    projection: AdkRuntimeBindingSafeProjection,
    *,
    continuable_evidence_session_ref: str,
    runtime_binding_ref: str | None = None,
    runtime_binding_status: str = "probed",
    runtime_binding_evaluation_summary_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AdkRuntimeBindingProductBridgeResult:
    """Run adapter-local schema and guard gates for an ADK binding projection."""

    payload = _runtime_binding_payload_from_projection(
        projection,
        continuable_evidence_session_ref=continuable_evidence_session_ref,
        runtime_binding_ref=runtime_binding_ref,
        runtime_binding_status=runtime_binding_status,
        runtime_binding_evaluation_summary_ref=runtime_binding_evaluation_summary_ref,
        metadata=metadata,
    )
    runtime_binding: ContinuableEvidenceSessionRuntimeBindingSchema | None = None
    schema_error: str | None = None
    try:
        runtime_binding = validate_continuable_evidence_session_runtime_binding(payload)
        schema_payload = runtime_binding.model_dump(mode="python")
        schema_validation_passed = True
    except ValueError as error:
        schema_payload = payload
        schema_error = str(error)
        schema_validation_passed = False

    guard_result = guard_continuable_evidence_session_runtime_binding(schema_payload)
    return AdkRuntimeBindingProductBridgeResult(
        runtime_binding_payload=schema_payload,
        runtime_binding=runtime_binding,
        guard_result=guard_result,
        source_projection_ref=projection.probe_ref,
        schema_validation_passed=schema_validation_passed,
        schema_validation_error=schema_error,
        metadata={
            "bridge_type": "adk_runtime_binding_product_bridge",
            "adapter_contract_gate": "schema_guard",
            **dict(metadata or {}),
        },
    )


def _runtime_binding_payload_from_projection(
    projection: AdkRuntimeBindingSafeProjection,
    *,
    continuable_evidence_session_ref: str,
    runtime_binding_ref: str | None,
    runtime_binding_status: str,
    runtime_binding_evaluation_summary_ref: str | None,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    binding_ref = runtime_binding_ref or _runtime_binding_ref_for_session(
        continuable_evidence_session_ref
    )
    binding_base = binding_ref.rstrip("/")
    event_refs = [
        f"{binding_base}/event-review/{index + 1}"
        for index, event in enumerate(projection.event_summaries)
        if event.get("event_ref")
    ]
    artifact_refs = []
    if projection.artifact_summary.get("artifact_ref"):
        artifact_refs.append(f"{binding_base}/artifact-summary/1")
    evaluation_ref = runtime_binding_evaluation_summary_ref or (
        f"evaluation://continuable-evidence-session/runtime-binding/"
        f"{_safe_slug(binding_ref)}"
    )
    return {
        "product": CONTINUABLE_EVIDENCE_SESSION_PRODUCT,
        "payload_type": CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_PAYLOAD_TYPE,
        "payload_version": CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_VERSION,
        "runtime_binding_ref": binding_ref,
        "continuable_evidence_session_ref": continuable_evidence_session_ref,
        "runtime_binding_status": runtime_binding_status,
        "runtime_binding_scope": "agent_session_event_artifactservice",
        "runtime_binding_summary_ref": f"{binding_base}/summary",
        "agent_binding_ref": f"{binding_base}/agent",
        "session_binding_ref": f"{binding_base}/session",
        "event_review_refs": event_refs,
        "artifact_binding_summary_refs": artifact_refs,
        "runtime_binding_evaluation_summary_ref": evaluation_ref,
        "raw_runtime_object_included": projection.raw_object_included,
        "raw_event_payload_included": False,
        "artifact_body_included": bool(
            projection.artifact_summary.get("body_included", False)
        ),
        "adk_eval_raw_data_included": False,
        "user_product_runtime_path_enabled": projection.user_product_path_enabled,
        "default_local_state_dir_enabled": projection.default_local_state_dir_enabled,
        "auto_resume_answer_enabled": projection.auto_resume_enabled,
        "skills_loaded": projection.skills_loaded,
        "memory_enabled": projection.memory_enabled,
        "tools_mcp_enabled": False,
        "callbacks_enabled": False,
        "plugins_enabled": False,
        "metadata": {
            "bridge_type": "adk_runtime_binding_product_bridge",
            "source_projection_kind": "adk_runtime_binding_safe_projection",
            "source_event_count": projection.event_count,
            "source_artifact_present": bool(
                projection.artifact_summary.get("artifact_ref")
            ),
            "source_services_in_memory": bool(
                projection.service_summary.get("in_memory_services")
            ),
            **dict(metadata or {}),
        },
    }


def _runtime_binding_ref_for_session(continuable_evidence_session_ref: str) -> str:
    return (
        f"{CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_REF_PREFIX}"
        f"adk-bridge/{_safe_slug(continuable_evidence_session_ref)}"
    )


def _safe_slug(value: str) -> str:
    slug = "".join(char if char.isalnum() else "-" for char in value.lower())
    return "-".join(part for part in slug.split("-") if part) or "unavailable"
