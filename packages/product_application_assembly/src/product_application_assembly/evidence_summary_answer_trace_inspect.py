"""Build product-level trace inspect views for evidence summary answers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import json
from typing import Any

from schemas.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_REF_PREFIX,
    EvidenceSummaryAnswerArtifactSchema,
    EvidenceSummaryAnswerObservabilitySummarySchema,
    EvidenceSummaryAnswerRawBoundarySummarySchema,
    EvidenceSummaryAnswerTraceInspectSchema,
    EvidenceSummaryAnswerTraceSchema,
)


PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_SOURCE = (
    "product_application_assembly.evidence_summary_answer_trace_inspect"
)
PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_POLICY_REF = (
    "policy://product-application-assembly/evidence-summary-answer/"
    "trace-inspect-v1"
)


def build_evidence_summary_answer_trace_inspect(
    *,
    request_id: str,
    answer_status: str | None = None,
    readonly_refs_status: str | None = None,
    blocking_reasons: Iterable[str] = (),
    warnings: Iterable[str] = (),
    recovery_hints: Iterable[str] = (),
    answer_trace: EvidenceSummaryAnswerTraceSchema | Mapping[str, Any] | None = None,
    answer_trace_summary: Mapping[str, Any] | None = None,
    answer_artifact: (
        EvidenceSummaryAnswerArtifactSchema | Mapping[str, Any] | None
    ) = None,
    answer_artifact_summary: Mapping[str, Any] | None = None,
    observability_summary: (
        EvidenceSummaryAnswerObservabilitySummarySchema | Mapping[str, Any] | None
    ) = None,
    safe_observability_summary: Mapping[str, Any] | None = None,
    evidence_refs: Iterable[Mapping[str, Any]] = (),
    additional_refs: Iterable[Mapping[str, Any]] = (),
    unavailable_reason: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceSummaryAnswerTraceInspectSchema:
    """Build a safe product-level trace inspect view."""

    trace_model = _trace_model(answer_trace)
    artifact_model = _artifact_model(answer_artifact)
    observability_model = _observability_model(observability_summary)
    trace_summary = _summary_from_trace(trace_model, answer_trace_summary)
    artifact_summary = _summary_from_artifact(artifact_model, answer_artifact_summary)
    observability_gateway = _safe_mapping(safe_observability_summary)
    if not observability_gateway and observability_model is not None:
        observability_gateway = {
            "summary_ref": observability_model.summary_ref,
            "summary_status": observability_model.status,
            "reason": observability_model.reason,
            "user_explanation": observability_model.user_explanation,
            "ref_count": len(observability_model.refs),
        }
    status = _inspect_status(
        answer_status=answer_status,
        unavailable_reason=unavailable_reason,
    )
    reason = _inspect_reason(
        status=status,
        unavailable_reason=unavailable_reason,
        blocking_reasons=blocking_reasons,
        observability_gateway=observability_gateway,
        answer_status=answer_status,
    )
    trace_ref = _optional_string(trace_summary.get("trace_ref"))
    artifact_ref = _optional_string(artifact_summary.get("artifact_ref"))
    observability_ref = _optional_string(observability_gateway.get("summary_ref"))
    trace_inspect_id = _trace_inspect_id(
        request_id=request_id,
        status=status,
        reason=reason,
        trace_ref=trace_ref,
        artifact_ref=artifact_ref,
        observability_ref=observability_ref,
    )
    return EvidenceSummaryAnswerTraceInspectSchema(
        trace_inspect_id=trace_inspect_id,
        trace_inspect_ref=(
            f"{EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_REF_PREFIX}{trace_inspect_id}"
        ),
        request_id=request_id,
        inspect_status=status,  # type: ignore[arg-type]
        inspect_reason=reason,
        answer_status=_answer_status(answer_status),
        user_explanation=_user_explanation(
            status=status,
            reason=reason,
            unavailable_reason=unavailable_reason,
            observability_gateway=observability_gateway,
        ),
        developer_facts_summary=_developer_facts_summary(
            answer_status=answer_status,
            readonly_refs_status=readonly_refs_status,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
            trace_summary=trace_summary,
            artifact_summary=artifact_summary,
            observability_gateway=observability_gateway,
        ),
        refs_summary=_refs_summary(
            trace_ref=trace_ref,
            artifact_ref=artifact_ref,
            observability_ref=observability_ref,
            evidence_refs=evidence_refs,
            additional_refs=additional_refs,
        ),
        event_facts_summary=_event_facts_summary(
            status=status,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
        ),
        artifact_handoff_summary=_artifact_handoff_summary(
            artifact_summary=artifact_summary,
            artifact_ref=artifact_ref,
        ),
        raw_boundary_summary=EvidenceSummaryAnswerRawBoundarySummarySchema(
            restricted_payload_absent=True,
            restricted_boundary_intact=True,
            blocked_field_count=_blocked_field_count(observability_gateway),
            boundary_note="restricted details excluded",
        ),
        evaluation_summary=_evaluation_summary(observability_gateway),
        governance_summary=_governance_summary(
            status=status,
            reason=reason,
            blocking_reasons=blocking_reasons,
        ),
        unavailable_reason=unavailable_reason,
        recovery_hints=_string_items(recovery_hints),
        task_compatible=True,
        workflow_compatible=True,
        runtime_backed=False,
        backed_by_adk_task_runtime=False,
        backed_by_adk_workflow_runtime=False,
        durable_session=False,
        memory_enabled=False,
        metadata={
            "source": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_SOURCE,
            "policy_ref": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_POLICY_REF,
            "task_api_fact_gate": "compatible_not_runtime_backed",
            "workflow_runtime_fact_gate": "compatible_not_runtime_backed",
            "event_stream_fact_gate": "product_summary_only",
            "artifact_service_fact_gate": "handoff_summary_only",
            **_compact_metadata(metadata or {}),
        },
    )


def evidence_summary_answer_trace_inspect_status_dict(
    trace_inspect: EvidenceSummaryAnswerTraceInspectSchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-ready trace inspect dict."""

    model = (
        EvidenceSummaryAnswerTraceInspectSchema.model_validate(trace_inspect)
        if isinstance(trace_inspect, Mapping)
        else trace_inspect
    )
    return model.model_dump(mode="json")


def evidence_summary_answer_trace_inspect_gateway_dict(
    trace_inspect: EvidenceSummaryAnswerTraceInspectSchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return ProductGateway-safe trace inspect facts."""

    payload = evidence_summary_answer_trace_inspect_status_dict(trace_inspect)
    return {
        "trace_inspect_ref": payload["trace_inspect_ref"],
        "trace_inspect_status": payload["inspect_status"],
        "inspect_reason": payload["inspect_reason"],
        "user_explanation": payload["user_explanation"],
        "unavailable_reason": payload.get("unavailable_reason"),
        "recovery_hints": _string_items(payload.get("recovery_hints")),
        "developer_facts_summary": _safe_scalar_mapping(
            payload.get("developer_facts_summary")
        ),
        "refs_summary": _safe_scalar_mapping(payload.get("refs_summary")),
        "event_facts_summary": _safe_scalar_mapping(
            payload.get("event_facts_summary")
        ),
        "artifact_handoff_summary": _safe_scalar_mapping(
            payload.get("artifact_handoff_summary")
        ),
        "raw_boundary_summary": _raw_boundary_gateway_dict(
            payload.get("raw_boundary_summary")
        ),
        "evaluation_summary": _safe_scalar_mapping(payload.get("evaluation_summary")),
        "governance_summary": _safe_scalar_mapping(payload.get("governance_summary")),
        "task_compatible": payload["task_compatible"],
        "workflow_compatible": payload["workflow_compatible"],
        "runtime_backed": False,
        "backed_by_adk_task_runtime": False,
        "backed_by_adk_workflow_runtime": False,
        "durable_session": False,
        "memory_enabled": False,
    }


def _inspect_status(
    *,
    answer_status: str | None,
    unavailable_reason: str | None,
) -> str:
    if unavailable_reason:
        return "unavailable"
    if answer_status == "success":
        return "success"
    if answer_status in {"blocked", "insufficient_evidence"}:
        return "blocked"
    return "failed"


def _inspect_reason(
    *,
    status: str,
    unavailable_reason: str | None,
    blocking_reasons: Iterable[str],
    observability_gateway: Mapping[str, Any],
    answer_status: str | None,
) -> str:
    if unavailable_reason:
        return unavailable_reason
    observed_reason = _optional_string(observability_gateway.get("reason"))
    if observed_reason:
        return observed_reason
    reasons = _string_items(blocking_reasons)
    if reasons:
        return reasons[0]
    if answer_status == "success":
        return "answer_ready"
    if answer_status == "insufficient_evidence":
        return "insufficient_evidence"
    if status == "blocked":
        return "governance_blocked"
    return "answer_failed"


def _user_explanation(
    *,
    status: str,
    reason: str,
    unavailable_reason: str | None,
    observability_gateway: Mapping[str, Any],
) -> str:
    observed = _optional_string(observability_gateway.get("user_explanation"))
    if observed:
        return observed
    if unavailable_reason:
        return f"本轮可回放解释不可用：{unavailable_reason}。"
    if status == "success":
        return "本轮已形成可复查解释视图，可查看证据、追踪、产物与治理摘要。"
    if status == "blocked":
        return f"本轮被治理条件拦截，可回放解释记录了阻断原因：{reason}。"
    return f"本轮执行失败，可回放解释记录了失败原因：{reason}。"


def _developer_facts_summary(
    *,
    answer_status: str | None,
    readonly_refs_status: str | None,
    blocking_reasons: Iterable[str],
    warnings: Iterable[str],
    trace_summary: Mapping[str, Any],
    artifact_summary: Mapping[str, Any],
    observability_gateway: Mapping[str, Any],
) -> dict[str, Any]:
    return _safe_scalar_mapping(
        {
            "answer_status": answer_status,
            "readonly_refs_status": readonly_refs_status,
            "blocking_reason_count": len(_string_items(blocking_reasons)),
            "warning_count": len(_string_items(warnings)),
            "trace_available": bool(trace_summary.get("trace_ref")),
            "artifact_available": bool(artifact_summary.get("artifact_ref")),
            "observability_available": bool(observability_gateway.get("summary_ref")),
            "evidence_ref_count": _nonnegative_int(
                trace_summary.get("evidence_ref_count")
            ),
            "additional_ref_count": _nonnegative_int(
                trace_summary.get("additional_ref_count")
            ),
            "digest_ref_count": _nonnegative_int(trace_summary.get("digest_ref_count")),
            "llm_call_attempted": trace_summary.get("llm_call_attempted") is True,
            "llm_runtime_call_performed": (
                trace_summary.get("llm_runtime_call_performed") is True
            ),
            "answerability_preflight_applied": (
                trace_summary.get("answerability_preflight_applied") is True
            ),
        }
    )


def _refs_summary(
    *,
    trace_ref: str | None,
    artifact_ref: str | None,
    observability_ref: str | None,
    evidence_refs: Iterable[Mapping[str, Any]],
    additional_refs: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    return _safe_scalar_mapping(
        {
            "trace_ref": trace_ref,
            "artifact_ref": artifact_ref,
            "observability_summary_ref": observability_ref,
            "evidence_ref_count": len(tuple(evidence_refs)),
            "additional_ref_count": len(tuple(additional_refs)),
        }
    )


def _event_facts_summary(
    *,
    status: str,
    blocking_reasons: Iterable[str],
    warnings: Iterable[str],
) -> dict[str, Any]:
    return {
        "event_summary_kind": "product_level_summary",
        "event_stream_enabled": False,
        "runtime_backed": False,
        "inspect_status": status,
        "event_fact_count": len(_string_items(blocking_reasons))
        + len(_string_items(warnings))
        + 1,
    }


def _artifact_handoff_summary(
    *,
    artifact_summary: Mapping[str, Any],
    artifact_ref: str | None,
) -> dict[str, Any]:
    return _safe_scalar_mapping(
        {
            "artifact_ref": artifact_ref,
            "artifact_status": artifact_summary.get("artifact_status"),
            "artifact_service_enabled": False,
            "artifact_saved": False,
            "export_allowed": artifact_summary.get("export_allowed") is True,
            "delete_supported": artifact_summary.get("delete_supported") is True,
            "answer_present": artifact_summary.get("answer_present") is True,
            "answer_preview_present": (
                artifact_summary.get("answer_preview_present") is True
            ),
        }
    )


def _evaluation_summary(observability_gateway: Mapping[str, Any]) -> dict[str, Any]:
    evaluation = observability_gateway.get("evaluation_findings_summary")
    summary = _safe_scalar_mapping(evaluation)
    return {
        "evaluation_only": True,
        "governance_decision": False,
        **summary,
    }


def _governance_summary(
    *,
    status: str,
    reason: str,
    blocking_reasons: Iterable[str],
) -> dict[str, Any]:
    return {
        "governance_summary_only": True,
        "inspect_status": status,
        "decision_reason": reason,
        "blocking_reason_count": len(_string_items(blocking_reasons)),
    }


def _trace_inspect_id(
    *,
    request_id: str,
    status: str,
    reason: str,
    trace_ref: str | None,
    artifact_ref: str | None,
    observability_ref: str | None,
) -> str:
    seed = json.dumps(
        {
            "artifact_ref": artifact_ref,
            "observability_ref": observability_ref,
            "reason": reason,
            "request_id": request_id,
            "status": status,
            "trace_ref": trace_ref,
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return f"trace-inspect-{digest}"


def _summary_from_trace(
    trace_model: EvidenceSummaryAnswerTraceSchema | None,
    trace_summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(trace_summary, Mapping) and trace_summary:
        return _safe_scalar_mapping(trace_summary)
    if trace_model is None:
        return {}
    return _safe_scalar_mapping(
        {
            "trace_ref": trace_model.trace_ref,
            "trace_status": trace_model.answer_status,
            "request_id": trace_model.request_id,
            "readonly_refs_status": trace_model.readonly_refs_status,
            "evidence_ref_count": trace_model.evidence_ref_count,
            "additional_ref_count": trace_model.additional_ref_count,
            "digest_ref_count": trace_model.digest_ref_count,
            "blocking_reason_count": len(trace_model.blocking_reasons),
            "warning_count": len(trace_model.warnings),
            "llm_call_attempted": trace_model.llm_call_attempted,
            "llm_runtime_call_performed": trace_model.llm_runtime_call_performed,
            "answerability_preflight_applied": (
                trace_model.answerability_preflight_applied
            ),
            "follow_up": trace_model.follow_up,
            "task_compatible": trace_model.task_compatible,
            "workflow_compatible": trace_model.workflow_compatible,
            "backed_by_adk_task_runtime": False,
            "backed_by_adk_workflow_runtime": False,
        }
    )


def _summary_from_artifact(
    artifact_model: EvidenceSummaryAnswerArtifactSchema | None,
    artifact_summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(artifact_summary, Mapping) and artifact_summary:
        return _safe_scalar_mapping(artifact_summary)
    if artifact_model is None:
        return {}
    return _safe_scalar_mapping(
        {
            "artifact_ref": artifact_model.artifact_ref,
            "artifact_status": artifact_model.artifact_status,
            "trace_ref": artifact_model.trace_ref,
            "export_allowed": artifact_model.export_allowed,
            "delete_supported": artifact_model.delete_supported,
            "answer_present": bool(artifact_model.answer),
            "answer_preview_present": bool(artifact_model.answer_preview),
            "task_compatible": artifact_model.task_compatible,
            "workflow_compatible": artifact_model.workflow_compatible,
            "backed_by_adk_task_runtime": False,
            "backed_by_adk_workflow_runtime": False,
        }
    )


def _trace_model(
    trace: EvidenceSummaryAnswerTraceSchema | Mapping[str, Any] | None,
) -> EvidenceSummaryAnswerTraceSchema | None:
    if trace is None:
        return None
    if isinstance(trace, EvidenceSummaryAnswerTraceSchema):
        return trace
    if trace.get("payload_type") != "evidence_summary_answer_trace":
        return None
    return EvidenceSummaryAnswerTraceSchema.model_validate(trace)


def _artifact_model(
    artifact: EvidenceSummaryAnswerArtifactSchema | Mapping[str, Any] | None,
) -> EvidenceSummaryAnswerArtifactSchema | None:
    if artifact is None:
        return None
    if isinstance(artifact, EvidenceSummaryAnswerArtifactSchema):
        return artifact
    if artifact.get("payload_type") != "evidence_summary_answer_artifact":
        return None
    return EvidenceSummaryAnswerArtifactSchema.model_validate(artifact)


def _observability_model(
    summary: EvidenceSummaryAnswerObservabilitySummarySchema | Mapping[str, Any] | None,
) -> EvidenceSummaryAnswerObservabilitySummarySchema | None:
    if summary is None:
        return None
    if isinstance(summary, EvidenceSummaryAnswerObservabilitySummarySchema):
        return summary
    if summary.get("payload_type") != "evidence_summary_answer_observability_summary":
        return None
    return EvidenceSummaryAnswerObservabilitySummarySchema.model_validate(summary)


def _raw_boundary_gateway_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {
            "restricted_payload_absent": True,
            "restricted_boundary_intact": True,
            "blocked_field_count": 0,
        }
    return {
        "restricted_payload_absent": value.get("restricted_payload_absent") is True,
        "restricted_boundary_intact": value.get("restricted_boundary_intact") is True,
        "blocked_field_count": _nonnegative_int(value.get("blocked_field_count")),
    }


def _blocked_field_count(observability_gateway: Mapping[str, Any]) -> int:
    boundary = observability_gateway.get("raw_boundary_summary")
    if not isinstance(boundary, Mapping):
        return 0
    return _nonnegative_int(boundary.get("blocked_field_count"))


def _answer_status(value: str | None) -> str | None:
    if value in {"success", "insufficient_evidence", "blocked", "failed"}:
        return value
    return None


def _safe_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_scalar_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    output: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            continue
        if item is not None and isinstance(item, bool | int | float | str):
            output[key] = item
    return output


def _compact_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return _safe_scalar_mapping(metadata)


def _string_items(value: Any) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [str(item) for item in value if isinstance(item, str) and item.strip()]


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _nonnegative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value if value >= 0 else 0


__all__ = [
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_SOURCE",
    "build_evidence_summary_answer_trace_inspect",
    "evidence_summary_answer_trace_inspect_gateway_dict",
    "evidence_summary_answer_trace_inspect_status_dict",
]
