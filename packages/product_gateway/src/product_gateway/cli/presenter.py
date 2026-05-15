"""CLI presentation helpers for product gateway responses."""

from __future__ import annotations

import json
from typing import Any

from product_gateway.contracts import ProductGatewayRef, ProductGatewayResponse


def product_gateway_response_to_json_text(response: ProductGatewayResponse) -> str:
    """Serialize a product gateway response as stable JSON text."""

    return json.dumps(
        response.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
    )


def product_gateway_response_to_text(response: ProductGatewayResponse) -> str:
    """Render a product gateway response as compact CLI text."""

    lines = [
        f"request_id: {response.request_id}",
        f"entry_kind: {response.entry_kind.value}",
        f"status: {response.status.value}",
        f"exit_code: {response.exit_code}",
    ]
    if response.blocking_reasons:
        lines.append("blocking_reasons:")
        lines.extend(f"- {item}" for item in response.blocking_reasons)
    if response.warnings:
        lines.append("warnings:")
        lines.extend(f"- {item}" for item in response.warnings)
    if response.governance_summary_ref:
        lines.append(f"governance_summary_ref: {response.governance_summary_ref}")
    lines.extend(_ref_lines("evidence_refs", response.evidence_refs))
    lines.extend(_ref_lines("audit_refs", response.audit_refs))
    lines.extend(_ref_lines("tool_audit_refs", response.tool_audit_refs))
    if response.metadata:
        lines.append("metadata:")
        for key in sorted(response.metadata):
            value = response.metadata[key]
            if _text_metadata_value_allowed(value):
                lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _ref_lines(label: str, refs: list[ProductGatewayRef]) -> list[str]:
    if not refs:
        return []
    lines = [f"{label}:"]
    lines.extend(f"- {item.kind}: {item.ref}" for item in refs)
    return lines


def _text_metadata_value_allowed(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


__all__ = [
    "product_gateway_response_to_json_text",
    "product_gateway_response_to_text",
]
