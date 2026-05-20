"""Product application assembly for external-readonly refs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from composition import build_external_readonly_evidence_readonly_product_bundle
from product_gateway.external_readonly_refs import (
    execute_external_readonly_refs_gateway_request,
)


PRODUCT_APPLICATION_EXTERNAL_READONLY_REFS_SOURCE = (
    "product_application_assembly.external_readonly_refs"
)


@dataclass(frozen=True)
class ExternalReadonlyRefsProductApplicationAssemblyResult:
    """Product application result that only exposes public summaries."""

    request_id: str
    product_response_summary: dict[str, Any]
    readonly_public_refs_status: dict[str, Any]
    application_metadata: dict[str, Any]


def assemble_external_readonly_refs_product_application(
    read_context: Any,
    *,
    request_id: str,
    metadata: Mapping[str, Any] | None = None,
) -> ExternalReadonlyRefsProductApplicationAssemblyResult:
    """Assemble composition readonly refs into a ProductGateway summary."""

    application_metadata = _application_metadata(metadata or {})
    readonly_bundle = build_external_readonly_evidence_readonly_product_bundle(
        read_context,
        metadata=application_metadata,
    )
    readonly_public_refs = readonly_bundle.to_public_contract()
    readonly_public_refs_status = readonly_bundle.to_public_refs()
    gateway_result = execute_external_readonly_refs_gateway_request(
        {
            "request_id": request_id,
            "readonly_public_refs": readonly_public_refs,
            "metadata": application_metadata,
        }
    )
    return ExternalReadonlyRefsProductApplicationAssemblyResult(
        request_id=request_id,
        product_response_summary=dict(gateway_result.product_response_summary),
        readonly_public_refs_status=dict(readonly_public_refs_status),
        application_metadata=application_metadata,
    )


def _application_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        "source": PRODUCT_APPLICATION_EXTERNAL_READONLY_REFS_SOURCE,
        "readonly": True,
        "refs_only": True,
        "summary_only": True,
        "does_not_read_files": True,
        "does_not_write_files": True,
        "does_not_call_network": True,
        "does_not_call_model": True,
        "does_not_call_runtime": True,
    }
    compact.update(_compact_metadata(metadata))
    return compact


def _compact_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in metadata.items():
        if not isinstance(key, str):
            continue
        if _sensitive_text(key):
            continue
        if not isinstance(value, bool | int | float | str):
            continue
        if isinstance(value, str) and _sensitive_text(value):
            continue
        compact[key] = value
    return compact


def _sensitive_text(value: str) -> bool:
    normalized = value.lower()
    return any(
        marker in normalized
        for marker in (
            "authorization",
            "config",
            "cookie",
            "header",
            "html",
            "password",
            "raw",
            "secret",
            "token",
        )
    )


__all__ = (
    "ExternalReadonlyRefsProductApplicationAssemblyResult",
    "PRODUCT_APPLICATION_EXTERNAL_READONLY_REFS_SOURCE",
    "assemble_external_readonly_refs_product_application",
)
