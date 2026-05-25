"""Assemble product-level output facts for evidence summary answers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from product_gateway.external_readonly_ask import (
    execute_external_readonly_ask_gateway_request,
)

from product_application_assembly.evidence_summary_answer_artifact import (
    build_evidence_summary_answer_artifact,
    evidence_summary_answer_artifact_status_dict,
    evidence_summary_answer_artifact_summary_dict,
)
from product_application_assembly.evidence_summary_answer_observability_summary import (
    build_evidence_summary_answer_observability_summary,
    evidence_summary_answer_observability_summary_gateway_dict,
    evidence_summary_answer_observability_summary_status_dict,
)
from product_application_assembly.evidence_summary_answer_run import (
    build_evidence_summary_answer_run,
    evidence_summary_answer_run_status_dict,
    evidence_summary_answer_run_summary_dict,
)
from product_application_assembly.evidence_summary_answer_trace import (
    build_evidence_summary_answer_trace,
    evidence_summary_answer_trace_status_dict,
    evidence_summary_answer_trace_summary_dict,
)
from product_application_assembly.evidence_summary_answer_trace_inspect import (
    build_evidence_summary_answer_trace_inspect,
    evidence_summary_answer_trace_inspect_gateway_dict,
    evidence_summary_answer_trace_inspect_status_dict,
)


PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_PRODUCT_OUTPUT_SOURCE = (
    "product_application_assembly.evidence_summary_answer_product_output"
)


@dataclass(frozen=True)
class EvidenceSummaryAnswerProductOutputAssemblyResult:
    """Application-level product output facts for one evidence answer turn."""

    evidence_refs: tuple[dict[str, Any], ...]
    additional_refs: tuple[dict[str, Any], ...]
    evidence_lineage_summary: dict[str, Any]
    answer_trace: dict[str, Any]
    answer_trace_summary: dict[str, Any]
    answer_artifact: dict[str, Any]
    answer_artifact_summary: dict[str, Any]
    observability_summary: dict[str, Any]
    safe_observability_summary: dict[str, Any]
    trace_inspect: dict[str, Any]
    trace_inspect_summary: dict[str, Any]
    answer_run: dict[str, Any]
    answer_run_summary: dict[str, Any]
    product_response_summary: dict[str, Any]


@dataclass(frozen=True)
class EvidenceSummaryAnswerProductSummaryAssemblyResult:
    """ProductGateway-safe product response summary for one ask turn."""

    product_response_summary: dict[str, Any]


def assemble_evidence_summary_answer_product_output(
    context: Any,
    answer_result: Mapping[str, Any],
    *,
    request_id: str,
    readonly_refs_status: str,
    blocking_reasons: tuple[str, ...],
    warnings: tuple[str, ...],
    recovery_hints: tuple[str, ...],
    source_url_present: bool,
    evidence_path_count: int,
    model_name: str | None,
    llm_call_allowed: bool,
    llm_call_attempted: bool,
    llm_runtime_call_performed: bool,
    external_readonly_fetch_performed: bool,
    external_readonly_network_call_performed: bool,
    external_network_call_performed: bool,
    follow_up: bool = False,
    follow_up_turn_index: int | None = None,
    follow_up_seed_ref: str | None = None,
    answer_trace_follow_up_seed_ref: str | None = None,
    llm_trace_metadata: Mapping[str, Any] | None = None,
    product_path: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceSummaryAnswerProductOutputAssemblyResult:
    """Assemble product output facts and a ProductGateway public summary."""

    evidence_lineage_summary = _evidence_lineage_summary(context)
    product_summary_refs = _product_refs(answer_result, context)
    product_metadata = _product_metadata(
        metadata,
        product_path=product_path,
        evidence_lineage_summary=evidence_lineage_summary,
    )
    trace_metadata = {
        **product_metadata,
        **_safe_scalar_mapping(llm_trace_metadata or {}),
    }
    answer_trace_model = build_evidence_summary_answer_trace(
        context,
        answer_result,
        readonly_refs_status=readonly_refs_status,
        evidence_refs=product_summary_refs["evidence_refs"],
        additional_refs=product_summary_refs["additional_refs"],
        follow_up=follow_up,
        follow_up_turn_index=follow_up_turn_index,
        follow_up_seed_ref=answer_trace_follow_up_seed_ref,
        metadata=trace_metadata,
    )
    answer_trace = evidence_summary_answer_trace_status_dict(answer_trace_model)
    answer_trace_summary = evidence_summary_answer_trace_summary_dict(
        answer_trace_model
    )
    answer_artifact_model = build_evidence_summary_answer_artifact(
        context,
        answer_result,
        answer_trace_model,
        metadata=product_metadata,
    )
    answer_artifact = evidence_summary_answer_artifact_status_dict(
        answer_artifact_model
    )
    answer_artifact_summary = evidence_summary_answer_artifact_summary_dict(
        answer_artifact_model
    )
    observability_summary_model = build_evidence_summary_answer_observability_summary(
        request_id=request_id,
        answer_status=str(answer_result.get("status") or "failed"),
        blocking_reasons=blocking_reasons,
        warnings=warnings,
        recovery_hints=recovery_hints,
        readonly_refs_status=readonly_refs_status,
        answer_result=answer_result,
        answer_trace=answer_trace_model,
        answer_artifact=answer_artifact_model,
        evidence_refs=product_summary_refs["evidence_refs"],
        additional_refs=product_summary_refs["additional_refs"],
        metadata=product_metadata,
    )
    observability_summary = (
        evidence_summary_answer_observability_summary_status_dict(
            observability_summary_model
        )
    )
    safe_observability_summary = (
        evidence_summary_answer_observability_summary_gateway_dict(
            observability_summary_model
        )
    )
    trace_inspect_model = build_evidence_summary_answer_trace_inspect(
        request_id=request_id,
        answer_status=str(answer_result.get("status") or "failed"),
        readonly_refs_status=readonly_refs_status,
        blocking_reasons=blocking_reasons,
        warnings=warnings,
        recovery_hints=recovery_hints,
        answer_trace=answer_trace_model,
        answer_trace_summary=answer_trace_summary,
        answer_artifact=answer_artifact_model,
        answer_artifact_summary=answer_artifact_summary,
        observability_summary=observability_summary_model,
        safe_observability_summary=safe_observability_summary,
        evidence_refs=product_summary_refs["evidence_refs"],
        additional_refs=product_summary_refs["additional_refs"],
        metadata=product_metadata,
    )
    trace_inspect = evidence_summary_answer_trace_inspect_status_dict(
        trace_inspect_model
    )
    trace_inspect_summary = evidence_summary_answer_trace_inspect_gateway_dict(
        trace_inspect_model
    )
    answer_run_model = build_evidence_summary_answer_run(
        request_id=request_id,
        answer_status=str(answer_result.get("status") or "failed"),
        readonly_refs_status=readonly_refs_status,
        evidence_refs=product_summary_refs["evidence_refs"],
        additional_refs=product_summary_refs["additional_refs"],
        answer_trace_ref=str(answer_trace["trace_ref"]),
        answer_artifact_ref=str(answer_artifact["artifact_ref"]),
        observability_summary_ref=str(observability_summary["summary_ref"]),
        trace_inspect_ref=str(trace_inspect["trace_inspect_ref"]),
        follow_up_seed_ref=follow_up_seed_ref,
        blocking_reasons=blocking_reasons,
        warnings=warnings,
        recovery_hints=recovery_hints,
        follow_up=follow_up,
        follow_up_turn_index=follow_up_turn_index,
        metadata=product_metadata,
    )
    answer_run = evidence_summary_answer_run_status_dict(answer_run_model)
    answer_run_summary = evidence_summary_answer_run_summary_dict(answer_run_model)
    product_response_summary = assemble_evidence_summary_answer_product_summary(
        request_id=request_id,
        answer_status=str(answer_result.get("status") or "failed"),
        evidence_refs=product_summary_refs["evidence_refs"],
        additional_refs=product_summary_refs["additional_refs"],
        blocking_reasons=blocking_reasons,
        warnings=warnings,
        readonly_refs_status=readonly_refs_status,
        source_url_present=source_url_present,
        evidence_path_count=evidence_path_count,
        model_name=model_name,
        llm_call_allowed=llm_call_allowed,
        llm_call_attempted=llm_call_attempted,
        llm_runtime_call_performed=llm_runtime_call_performed,
        external_readonly_fetch_performed=external_readonly_fetch_performed,
        external_readonly_network_call_performed=(
            external_readonly_network_call_performed
        ),
        external_network_call_performed=external_network_call_performed,
        follow_up=follow_up,
        follow_up_turn_index=follow_up_turn_index,
        follow_up_seed_ref=follow_up_seed_ref,
        answer_trace_ref=str(answer_trace["trace_ref"]),
        answer_trace_status=str(answer_trace["answer_status"]),
        answer_trace_summary=answer_trace_summary,
        answer_artifact_ref=str(answer_artifact["artifact_ref"]),
        answer_artifact_status=str(answer_artifact["artifact_status"]),
        answer_artifact_summary=answer_artifact_summary,
        observability_summary_ref=str(observability_summary["summary_ref"]),
        observability_summary_status=str(observability_summary["status"]),
        safe_observability_summary=safe_observability_summary,
        trace_inspect_ref=str(trace_inspect["trace_inspect_ref"]),
        trace_inspect_status=str(trace_inspect["inspect_status"]),
        trace_inspect_summary=trace_inspect_summary,
        answer_run_ref=str(answer_run["answer_run_ref"]),
        answer_run_status=str(answer_run["answer_run_status"]),
        answer_run_summary=answer_run_summary,
        answer_run_unavailable_reason=_optional_string(
            answer_run.get("unavailable_reason")
        ),
        evidence_lineage_summary=evidence_lineage_summary,
        product_path=product_path,
        metadata=metadata,
    ).product_response_summary
    return EvidenceSummaryAnswerProductOutputAssemblyResult(
        evidence_refs=product_summary_refs["evidence_refs"],
        additional_refs=product_summary_refs["additional_refs"],
        evidence_lineage_summary=evidence_lineage_summary,
        answer_trace=answer_trace,
        answer_trace_summary=answer_trace_summary,
        answer_artifact=answer_artifact,
        answer_artifact_summary=answer_artifact_summary,
        observability_summary=observability_summary,
        safe_observability_summary=safe_observability_summary,
        trace_inspect=trace_inspect,
        trace_inspect_summary=trace_inspect_summary,
        answer_run=answer_run,
        answer_run_summary=answer_run_summary,
        product_response_summary=product_response_summary,
    )


def assemble_evidence_summary_answer_product_summary(
    *,
    request_id: str,
    answer_status: str,
    evidence_refs: tuple[Mapping[str, Any], ...],
    additional_refs: tuple[Mapping[str, Any], ...],
    blocking_reasons: tuple[str, ...],
    warnings: tuple[str, ...],
    readonly_refs_status: str,
    source_url_present: bool,
    evidence_path_count: int,
    model_name: str | None,
    llm_call_allowed: bool,
    llm_call_attempted: bool,
    llm_runtime_call_performed: bool,
    external_readonly_fetch_performed: bool,
    external_readonly_network_call_performed: bool,
    external_network_call_performed: bool,
    follow_up: bool = False,
    follow_up_turn_index: int | None = None,
    follow_up_seed_ref: str | None = None,
    answer_trace_ref: str | None = None,
    answer_trace_status: str | None = None,
    answer_trace_summary: Mapping[str, Any] | None = None,
    answer_artifact_ref: str | None = None,
    answer_artifact_status: str | None = None,
    answer_artifact_summary: Mapping[str, Any] | None = None,
    observability_summary_ref: str | None = None,
    observability_summary_status: str | None = None,
    safe_observability_summary: Mapping[str, Any] | None = None,
    trace_inspect_ref: str | None = None,
    trace_inspect_status: str | None = None,
    trace_inspect_summary: Mapping[str, Any] | None = None,
    trace_inspect_unavailable_reason: str | None = None,
    answer_run_ref: str | None = None,
    answer_run_status: str | None = None,
    answer_run_summary: Mapping[str, Any] | None = None,
    answer_run_unavailable_reason: str | None = None,
    parent_answer_run_ref: str | None = None,
    evidence_lineage_summary: Mapping[str, Any] | None = None,
    product_path: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceSummaryAnswerProductSummaryAssemblyResult:
    """Build a ProductGateway public response summary from safe ask facts."""

    lineage_summary = _safe_scalar_mapping(evidence_lineage_summary or {})
    product_metadata = _product_metadata(
        metadata,
        product_path=product_path,
        evidence_lineage_summary=lineage_summary,
    )
    observability_summary_payload = dict(safe_observability_summary or {})
    if not observability_summary_payload:
        fallback_summary_model = build_evidence_summary_answer_observability_summary(
            request_id=f"{request_id}/product",
            answer_status=answer_status,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
            readonly_refs_status=readonly_refs_status,
            evidence_refs=evidence_refs,
            additional_refs=additional_refs,
            metadata=product_metadata,
        )
        fallback_summary = (
            evidence_summary_answer_observability_summary_status_dict(
                fallback_summary_model
            )
        )
        observability_summary_ref = fallback_summary["summary_ref"]
        observability_summary_status = fallback_summary["status"]
        observability_summary_payload = (
            evidence_summary_answer_observability_summary_gateway_dict(
                fallback_summary_model
            )
        )

    trace_inspect_payload = dict(trace_inspect_summary or {})
    if not trace_inspect_payload:
        if (
            trace_inspect_unavailable_reason is None
            and answer_trace_ref is None
            and not answer_trace_summary
        ):
            trace_inspect_unavailable_reason = "trace_inspect_requires_answer_context"
        fallback_trace_inspect_model = build_evidence_summary_answer_trace_inspect(
            request_id=f"{request_id}/product",
            answer_status=answer_status,
            readonly_refs_status=readonly_refs_status,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
            recovery_hints=(),
            answer_trace_summary=answer_trace_summary,
            answer_artifact_summary=answer_artifact_summary,
            safe_observability_summary=observability_summary_payload,
            evidence_refs=evidence_refs,
            additional_refs=additional_refs,
            unavailable_reason=trace_inspect_unavailable_reason,
            metadata=product_metadata,
        )
        fallback_trace_inspect = evidence_summary_answer_trace_inspect_status_dict(
            fallback_trace_inspect_model
        )
        trace_inspect_ref = fallback_trace_inspect["trace_inspect_ref"]
        trace_inspect_status = fallback_trace_inspect["inspect_status"]
        trace_inspect_unavailable_reason = fallback_trace_inspect.get(
            "unavailable_reason"
        )
        trace_inspect_payload = evidence_summary_answer_trace_inspect_gateway_dict(
            fallback_trace_inspect_model
        )

    answer_run_payload = dict(answer_run_summary or {})
    if not answer_run_payload:
        fallback_answer_run_model = build_evidence_summary_answer_run(
            request_id=request_id,
            answer_status=answer_status,
            readonly_refs_status=readonly_refs_status,
            evidence_refs=evidence_refs,
            additional_refs=additional_refs,
            answer_trace_ref=answer_trace_ref,
            answer_artifact_ref=answer_artifact_ref,
            observability_summary_ref=observability_summary_ref,
            trace_inspect_ref=trace_inspect_ref,
            follow_up_seed_ref=follow_up_seed_ref,
            parent_answer_run_ref=parent_answer_run_ref,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
            recovery_hints=(),
            unavailable_reason=answer_run_unavailable_reason,
            follow_up=follow_up,
            follow_up_turn_index=follow_up_turn_index,
            metadata=product_metadata,
        )
        fallback_answer_run = evidence_summary_answer_run_status_dict(
            fallback_answer_run_model
        )
        answer_run_ref = fallback_answer_run["answer_run_ref"]
        answer_run_status = fallback_answer_run["answer_run_status"]
        answer_run_unavailable_reason = fallback_answer_run.get(
            "unavailable_reason"
        )
        answer_run_payload = evidence_summary_answer_run_summary_dict(
            fallback_answer_run_model
        )

    gateway_result = execute_external_readonly_ask_gateway_request(
        {
            "request_id": f"{request_id}/product",
            "answer_status": answer_status,
            "evidence_refs": [dict(ref) for ref in evidence_refs],
            "additional_refs": [dict(ref) for ref in additional_refs],
            "blocking_reasons": list(blocking_reasons),
            "warnings": list(warnings),
            "readonly_refs_status": readonly_refs_status,
            "source_url_present": source_url_present,
            "evidence_path_count": evidence_path_count,
            "model_name": model_name,
            "llm_call_allowed": llm_call_allowed,
            "llm_call_attempted": llm_call_attempted,
            "llm_runtime_call_performed": llm_runtime_call_performed,
            "external_readonly_fetch_performed": external_readonly_fetch_performed,
            "external_readonly_network_call_performed": (
                external_readonly_network_call_performed
            ),
            "external_network_call_performed": external_network_call_performed,
            "follow_up": follow_up,
            "follow_up_turn_index": follow_up_turn_index,
            "follow_up_seed_ref": follow_up_seed_ref,
            "answer_trace_ref": answer_trace_ref,
            "answer_trace_status": answer_trace_status,
            "answer_trace_summary": dict(answer_trace_summary or {}),
            "answer_artifact_ref": answer_artifact_ref,
            "answer_artifact_status": answer_artifact_status,
            "answer_artifact_summary": dict(answer_artifact_summary or {}),
            "observability_summary_ref": observability_summary_ref,
            "observability_summary_status": observability_summary_status,
            "safe_observability_summary": observability_summary_payload,
            "trace_inspect_ref": trace_inspect_ref,
            "trace_inspect_status": trace_inspect_status,
            "trace_inspect_summary": trace_inspect_payload,
            "trace_inspect_unavailable_reason": trace_inspect_unavailable_reason,
            "answer_run_ref": answer_run_ref,
            "answer_run_status": answer_run_status,
            "answer_run_summary": answer_run_payload,
            "answer_run_unavailable_reason": answer_run_unavailable_reason,
            "parent_answer_run_ref": parent_answer_run_ref,
            "temporary_follow_up": True,
            "durable_session": False,
            "memory_enabled": False,
            "metadata": product_metadata,
        }
    )
    return EvidenceSummaryAnswerProductSummaryAssemblyResult(
        product_response_summary=dict(gateway_result.product_response_summary)
    )


def _product_refs(
    answer_result: Mapping[str, Any],
    context: Any,
) -> dict[str, tuple[dict[str, Any], ...]]:
    evidence_refs = tuple(_allowed_refs(answer_result.get("evidence_refs_used")))
    additional_refs = tuple(_allowed_refs(answer_result.get("additional_refs_used")))
    if not evidence_refs:
        evidence_refs = tuple(
            ref.model_dump(mode="python") for ref in getattr(context, "evidence_refs", ())
        )
    if not additional_refs:
        additional_refs = tuple(
            ref.model_dump(mode="python")
            for ref in getattr(context, "additional_refs", ())
        )
    return {"evidence_refs": evidence_refs, "additional_refs": additional_refs}


def _evidence_lineage_summary(context: Any) -> dict[str, Any]:
    digests = tuple(getattr(context, "digests", ()) or ())
    summary_fact_count = 0
    fact_slice_count = 0
    chunked_source_item_count = 0
    evidence_chunked = False

    for digest in digests:
        summary_facts = getattr(digest, "summary_facts", ()) or ()
        summary_fact_count += len(summary_facts)
        metadata = getattr(digest, "metadata", {}) or {}
        if not isinstance(metadata, Mapping):
            continue
        evidence_chunked = (
            evidence_chunked or metadata.get("upstream_chunked") is True
        )
        fact_slice_count += _metadata_nonnegative_int(
            metadata.get("upstream_fact_slice_count")
        )
        chunked_source_item_count += _metadata_nonnegative_int(
            metadata.get("upstream_chunked_source_item_count")
        )

    if fact_slice_count <= 0:
        fact_slice_count = summary_fact_count
    return {
        "digest_count": len(digests),
        "summary_fact_count": summary_fact_count,
        "evidence_chunked": evidence_chunked,
        "fact_slice_count": fact_slice_count,
        "chunked_source_item_count": chunked_source_item_count,
    }


def _allowed_refs(value: Any) -> tuple[dict[str, Any], ...]:
    refs: list[dict[str, Any]] = []
    for item in _list_value(value):
        if not isinstance(item, Mapping):
            continue
        ref = item.get("ref")
        kind = item.get("kind")
        if not isinstance(ref, str) or not ref:
            continue
        if not isinstance(kind, str) or not kind:
            continue
        refs.append(
            {
                "ref": ref,
                "kind": kind,
                "purpose": _optional_string(item.get("purpose")),
                "metadata": _safe_scalar_mapping(item.get("metadata") or {}),
            }
        )
    return tuple(refs)


def _product_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    product_path: str | None,
    evidence_lineage_summary: Mapping[str, Any],
) -> dict[str, Any]:
    product_metadata = {
        "source": PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_PRODUCT_OUTPUT_SOURCE,
        "summary_only": True,
        "does_not_read_files": True,
        "does_not_write_files": True,
        "does_not_call_network": True,
        "does_not_call_model": True,
        "does_not_call_runtime": True,
        **_safe_scalar_mapping(evidence_lineage_summary),
    }
    if isinstance(product_path, str) and product_path:
        product_metadata["product_path"] = product_path
    product_metadata.update(_safe_scalar_mapping(metadata or {}))
    return product_metadata


def _safe_scalar_mapping(value: Mapping[str, Any] | Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {
        key: item
        for key, item in value.items()
        if isinstance(key, str)
        and not _sensitive_text(key)
        and isinstance(item, bool | int | float | str)
        and not (isinstance(item, str) and _sensitive_text(item))
    }


def _list_value(value: Any) -> tuple[Any, ...]:
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    return ()


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _metadata_nonnegative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value if value >= 0 else 0


def _sensitive_text(value: str) -> bool:
    normalized = value.lower()
    return any(
        marker in normalized
        for marker in (
            "authorization",
            "config",
            "cookie",
            "credential",
            "header",
            "html",
            "password",
            "raw",
            "secret",
            "token",
        )
    )


__all__ = (
    "EvidenceSummaryAnswerProductOutputAssemblyResult",
    "EvidenceSummaryAnswerProductSummaryAssemblyResult",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_PRODUCT_OUTPUT_SOURCE",
    "assemble_evidence_summary_answer_product_output",
    "assemble_evidence_summary_answer_product_summary",
)
