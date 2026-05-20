"""Product gateway package-local response summary projection."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from schemas.product_gateway_response_summary import (
    validate_product_gateway_response_summary,
)

from product_gateway.contracts import ProductGatewayRef, ProductGatewayResponse


def project_product_gateway_response_summary(
    response: ProductGatewayResponse,
    *,
    product_gateway_response_ref: str | None = None,
) -> dict[str, Any]:
    """Project a package-local response into a public response summary dict."""

    output_refs = response.output_refs
    summary = {
        "request_id": response.request_id,
        "entry_kind": _value(response.entry_kind),
        "status": _value(response.status),
        "exit_code": response.exit_code,
        "product_gateway_response_ref": product_gateway_response_ref,
        "governance_summary_ref": (
            response.governance_summary_ref or output_refs.governance_summary_ref
        ),
        "evidence_refs": _merge_refs(output_refs.evidence_refs, response.evidence_refs),
        "audit_refs": _merge_refs(output_refs.audit_refs, response.audit_refs),
        "agent_advice_refs": _merge_refs(
            output_refs.agent_advice_refs,
            response.agent_advice_refs,
        ),
        "tool_audit_refs": _merge_refs(
            output_refs.tool_audit_refs,
            response.tool_audit_refs,
        ),
        "additional_refs": _merge_refs(output_refs.additional_refs),
        "blocking_reasons": list(response.blocking_reasons),
        "warnings": list(response.warnings),
        "metadata": _summary_metadata(response.metadata),
        "readonly": True,
        "summary_only": True,
        "refs_only": True,
        "candidate_only": True,
        "execution_enabled": False,
        "runtime_permission_granted": False,
        "llm_call_enabled": False,
        "tool_execution_enabled": False,
        "action_execution_enabled": False,
        "gateway_enabled": False,
    }
    return validate_product_gateway_response_summary(summary).model_dump(mode="python")


def _merge_refs(*ref_groups: Iterable[Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str | None]] = set()
    for ref_group in ref_groups:
        for ref in ref_group or ():
            ref_summary = _ref_summary(ref)
            key = (
                ref_summary["ref"],
                ref_summary["kind"],
                ref_summary.get("purpose"),
            )
            if key in seen:
                continue
            seen.add(key)
            refs.append(ref_summary)
    return refs


def _ref_summary(ref: Any) -> dict[str, Any]:
    if isinstance(ref, ProductGatewayRef):
        return {
            "ref": ref.ref,
            "kind": ref.kind,
            "purpose": ref.purpose,
            "metadata": dict(ref.metadata),
        }
    if isinstance(ref, Mapping):
        return {
            "ref": str(ref["ref"]),
            "kind": str(ref["kind"]),
            "purpose": ref.get("purpose"),
            "metadata": dict(ref.get("metadata") or {}),
        }
    return {
        "ref": str(getattr(ref, "ref")),
        "kind": str(getattr(ref, "kind")),
        "purpose": getattr(ref, "purpose", None),
        "metadata": dict(getattr(ref, "metadata", {}) or {}),
    }


def _summary_metadata(response_metadata: Mapping[str, Any]) -> dict[str, Any]:
    metadata = {"source": "product_gateway.response_summary_projection"}
    response_source = response_metadata.get("source")
    if response_source is not None:
        metadata["product_gateway_response_source"] = str(response_source)
    return metadata


def _value(value: Any) -> Any:
    return getattr(value, "value", value)


__all__ = ["project_product_gateway_response_summary"]
