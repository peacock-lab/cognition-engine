"""Build product-safe observability summaries for evidence summary answers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import json
from typing import Any

from schemas.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_REF_PREFIX,
    EvidenceSummaryAnswerArtifactSchema,
    EvidenceSummaryAnswerObservabilitySummarySchema,
    EvidenceSummaryAnswerRawBoundarySummarySchema,
    EvidenceSummaryAnswerRefSchema,
    EvidenceSummaryAnswerTraceSchema,
)


PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_SOURCE = (
    "product_application_assembly.evidence_summary_answer_observability_summary"
)
PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_POLICY_REF = (
    "policy://product-application-assembly/evidence-summary-answer/"
    "observability-summary-v1"
)


def build_evidence_summary_answer_observability_summary(
    *,
    request_id: str,
    answer_status: str,
    blocking_reasons: Iterable[str] = (),
    warnings: Iterable[str] = (),
    recovery_hints: Iterable[str] = (),
    readonly_refs_status: str | None = None,
    answer_result: Mapping[str, Any] | None = None,
    answer_trace: EvidenceSummaryAnswerTraceSchema | Mapping[str, Any] | None = None,
    answer_artifact: (
        EvidenceSummaryAnswerArtifactSchema | Mapping[str, Any] | None
    ) = None,
    evidence_refs: Iterable[Mapping[str, Any]] = (),
    additional_refs: Iterable[Mapping[str, Any]] = (),
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceSummaryAnswerObservabilitySummarySchema:
    """Build a safe product-level summary without importing runtime internals."""

    trace_model = _trace_model(answer_trace)
    artifact_model = _artifact_model(answer_artifact)
    result = dict(answer_result or {})
    reason = _reason(
        answer_status=answer_status,
        blocking_reasons=blocking_reasons,
        answer_result=result,
    )
    summary_id = _summary_id(
        request_id=request_id,
        status=answer_status,
        reason=reason,
        trace_ref=trace_model.trace_ref if trace_model else None,
        artifact_ref=artifact_model.artifact_ref if artifact_model else None,
    )
    summary_ref = (
        f"{EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_REF_PREFIX}{summary_id}"
    )
    return EvidenceSummaryAnswerObservabilitySummarySchema(
        summary_id=summary_id,
        summary_ref=summary_ref,
        request_id=request_id,
        status=answer_status,  # type: ignore[arg-type]
        reason=reason,
        user_explanation=_user_explanation(
            answer_status=answer_status,
            reason=reason,
            answer_result=result,
        ),
        recovery_hints=_string_items(recovery_hints),
        refs=_observability_refs(
            trace_model=trace_model,
            artifact_model=artifact_model,
            evidence_refs=evidence_refs,
            additional_refs=additional_refs,
        ),
        raw_boundary_summary=EvidenceSummaryAnswerRawBoundarySummarySchema(
            restricted_payload_absent=True,
            restricted_boundary_intact=True,
            blocked_field_count=0,
            boundary_note="restricted body excluded",
        ),
        evaluation_findings_summary=_evaluation_summary(result),
        task_compatible=True,
        workflow_compatible=True,
        runtime_backed=False,
        backed_by_adk_task_runtime=False,
        backed_by_adk_workflow_runtime=False,
        durable_session=False,
        memory_enabled=False,
        metadata={
            "source": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_SOURCE,
            "policy_ref": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_POLICY_REF,
            "readonly_refs_status": readonly_refs_status,
            "warning_count": len(_string_items(warnings)),
            "task_api_fact_gate": "compatible_not_runtime_backed",
            "workflow_runtime_fact_gate": "compatible_not_runtime_backed",
            **_compact_metadata(metadata or {}),
        },
    )


def evidence_summary_answer_observability_summary_status_dict(
    summary: EvidenceSummaryAnswerObservabilitySummarySchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-ready observability summary dict."""

    model = (
        EvidenceSummaryAnswerObservabilitySummarySchema.model_validate(summary)
        if isinstance(summary, Mapping)
        else summary
    )
    return model.model_dump(mode="json")


def evidence_summary_answer_observability_summary_gateway_dict(
    summary: EvidenceSummaryAnswerObservabilitySummarySchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return ProductGateway-safe observability facts."""

    payload = evidence_summary_answer_observability_summary_status_dict(summary)
    boundary = payload.get("raw_boundary_summary")
    boundary = boundary if isinstance(boundary, Mapping) else {}
    evaluation_summary = payload.get("evaluation_findings_summary")
    evaluation_summary = (
        evaluation_summary if isinstance(evaluation_summary, Mapping) else {}
    )
    return {
        "summary_ref": payload["summary_ref"],
        "summary_status": payload["status"],
        "reason": payload["reason"],
        "user_explanation": payload["user_explanation"],
        "recovery_hints": _string_items(payload.get("recovery_hints")),
        "ref_count": len(payload.get("refs") or []),
        "raw_boundary_summary": {
            "restricted_payload_absent": boundary.get(
                "restricted_payload_absent"
            )
            is True,
            "restricted_boundary_intact": boundary.get(
                "restricted_boundary_intact"
            )
            is True,
            "blocked_field_count": _nonnegative_int(
                boundary.get("blocked_field_count")
            ),
        },
        "evaluation_findings_summary": {
            key: item
            for key, item in evaluation_summary.items()
            if isinstance(key, str) and isinstance(item, bool | int | float | str)
        },
        "task_compatible": payload["task_compatible"],
        "workflow_compatible": payload["workflow_compatible"],
        "runtime_backed": False,
        "backed_by_adk_task_runtime": False,
        "backed_by_adk_workflow_runtime": False,
        "durable_session": False,
        "memory_enabled": False,
    }


def _reason(
    *,
    answer_status: str,
    blocking_reasons: Iterable[str],
    answer_result: Mapping[str, Any],
) -> str:
    reasons = _string_items(blocking_reasons) or _string_items(
        answer_result.get("blocking_reasons")
    )
    if answer_status == "success":
        metadata = answer_result.get("metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        if answer_result.get("llm_call_attempted") is False and (
            metadata.get("answerability_preflight") is True
            or metadata.get("over_scope_requested") is True
        ):
            return str(
                metadata.get("answerability_preflight_reason")
                or "answerability_preflight"
            )
        return "answer_ready"
    if answer_status == "insufficient_evidence":
        return str(
            answer_result.get("insufficient_evidence_reason")
            or "insufficient_evidence"
        )
    if reasons:
        return reasons[0]
    if answer_status == "blocked":
        return "governance_blocked"
    return "answer_failed"


def _user_explanation(
    *,
    answer_status: str,
    reason: str,
    answer_result: Mapping[str, Any],
) -> str:
    if answer_status == "success":
        if answer_result.get("llm_call_attempted") is False:
            return "本轮由治理前置检查直接形成可返回说明，未调用模型。"
        return "本轮受治理资料问答已形成可返回答案。"
    if answer_status == "insufficient_evidence":
        return "本轮证据不足，系统未编造答案。"
    if answer_status == "blocked":
        if reason in {
            "transport_error",
            "http_status_not_success",
            "response_body_empty",
        }:
            return (
                "本轮未能成功读取外部资料，可能是网络、远端服务或 URL "
                "临时不可用导致。请稍后重试，或确认 URL 可访问。"
            )
        return f"本轮请求被治理条件拦截：{reason}。"
    return f"本轮请求执行失败：{reason}。"


def _evaluation_summary(answer_result: Mapping[str, Any]) -> dict[str, Any]:
    blocking_reasons = _string_items(answer_result.get("blocking_reasons"))
    return {
        "finding_count": len(blocking_reasons),
        "quality_blocked": "llm_answer_quality_contract_violation"
        in blocking_reasons,
        "model_called": answer_result.get("llm_call_attempted") is True,
    }


def _observability_refs(
    *,
    trace_model: EvidenceSummaryAnswerTraceSchema | None,
    artifact_model: EvidenceSummaryAnswerArtifactSchema | None,
    evidence_refs: Iterable[Mapping[str, Any]],
    additional_refs: Iterable[Mapping[str, Any]],
) -> list[EvidenceSummaryAnswerRefSchema]:
    refs: list[EvidenceSummaryAnswerRefSchema] = []
    if trace_model is not None:
        refs.append(
            EvidenceSummaryAnswerRefSchema(
                ref=trace_model.trace_ref,
                kind="evidence_summary_answer_trace",
                purpose="answer_trace",
            )
        )
    if artifact_model is not None:
        refs.append(
            EvidenceSummaryAnswerRefSchema(
                ref=artifact_model.artifact_ref,
                kind="evidence_summary_answer_artifact",
                purpose="answer_artifact",
            )
        )
    refs.extend(_refs(evidence_refs))
    refs.extend(_refs(additional_refs))
    return refs


def _refs(values: Iterable[Mapping[str, Any]]) -> list[EvidenceSummaryAnswerRefSchema]:
    refs: list[EvidenceSummaryAnswerRefSchema] = []
    for value in values:
        ref = value.get("ref")
        kind = value.get("kind")
        if isinstance(ref, str) and ref and isinstance(kind, str) and kind:
            refs.append(
                EvidenceSummaryAnswerRefSchema(
                    ref=ref,
                    kind=kind,
                    purpose=_optional_string(value.get("purpose")),
                )
            )
    return refs


def _summary_id(
    *,
    request_id: str,
    status: str,
    reason: str,
    trace_ref: str | None,
    artifact_ref: str | None,
) -> str:
    seed = json.dumps(
        {
            "artifact_ref": artifact_ref,
            "reason": reason,
            "request_id": request_id,
            "status": status,
            "trace_ref": trace_ref,
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return f"summary-{digest}"


def _trace_model(
    trace: EvidenceSummaryAnswerTraceSchema | Mapping[str, Any] | None,
) -> EvidenceSummaryAnswerTraceSchema | None:
    if trace is None:
        return None
    if isinstance(trace, EvidenceSummaryAnswerTraceSchema):
        return trace
    return EvidenceSummaryAnswerTraceSchema.model_validate(trace)


def _artifact_model(
    artifact: EvidenceSummaryAnswerArtifactSchema | Mapping[str, Any] | None,
) -> EvidenceSummaryAnswerArtifactSchema | None:
    if artifact is None:
        return None
    if isinstance(artifact, EvidenceSummaryAnswerArtifactSchema):
        return artifact
    return EvidenceSummaryAnswerArtifactSchema.model_validate(artifact)


def _compact_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, item in metadata.items():
        if isinstance(key, str) and isinstance(item, bool | int | float | str):
            output[key] = item
    return output


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
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_POLICY_REF",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_SOURCE",
    "build_evidence_summary_answer_observability_summary",
    "evidence_summary_answer_observability_summary_gateway_dict",
    "evidence_summary_answer_observability_summary_status_dict",
]
