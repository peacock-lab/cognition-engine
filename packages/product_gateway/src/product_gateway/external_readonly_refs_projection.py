"""ProductGateway projection for external-readonly readonly public refs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from contract_core.external_readonly_evidence import (
    ExternalReadonlyEvidenceReadonlyPublicRefs,
    external_readonly_evidence_readonly_public_refs_status_dict,
    validate_external_readonly_evidence_readonly_public_refs,
)

from product_gateway.contracts import ProductGatewayOutputRefs, ProductGatewayRef


EXTERNAL_READONLY_REFS_PROJECTION_SOURCE = (
    "product_gateway.external_readonly_refs_projection"
)
EXTERNAL_READONLY_READONLY_PUBLIC_REFS_PURPOSE = (
    "external_readonly_readonly_public_refs"
)
EXTERNAL_READONLY_EVIDENCE_REF_KIND = "external_readonly_evidence"
EXTERNAL_READONLY_EVIDENCE_OBSERVATION_REF_KIND = (
    "external_readonly_evidence_observation"
)

_FORBIDDEN_INPUT_KEYS = frozenset(
    {
        "authorization",
        "body",
        "config" + "_assembly",
        "config" + "_context",
        "config" + "_contexts",
        "content_hash",
        "cookie",
        "headers",
        "object_module",
        "password",
        "raw_html",
        "raw_payload",
        "raw_response",
        "response_headers",
        "sanitized_excerpt_preview",
        "secret",
        "set_cookie",
        "token",
    }
)


def project_external_readonly_readonly_public_refs_to_product_gateway_output_refs(
    public_refs: ExternalReadonlyEvidenceReadonlyPublicRefs | Mapping[str, Any],
) -> ProductGatewayOutputRefs:
    """Map readonly external evidence refs into ProductGateway output refs."""

    if isinstance(public_refs, Mapping):
        _raise_if_forbidden_input_payload(public_refs)
    validate_external_readonly_evidence_readonly_public_refs(public_refs)
    status = external_readonly_evidence_readonly_public_refs_status_dict(
        public_refs
    )
    facts = status["external_readonly_evidence_readonly_facts"]
    metadata = _ref_metadata(status, facts)
    return ProductGatewayOutputRefs(
        evidence_refs=[
            ProductGatewayRef(
                ref=ref,
                kind=EXTERNAL_READONLY_EVIDENCE_REF_KIND,
                purpose=EXTERNAL_READONLY_READONLY_PUBLIC_REFS_PURPOSE,
                metadata=metadata,
            )
            for ref in _ordered_unique(status["external_readonly_evidence_refs"])
        ],
        additional_refs=[
            ProductGatewayRef(
                ref=ref,
                kind=EXTERNAL_READONLY_EVIDENCE_OBSERVATION_REF_KIND,
                purpose=EXTERNAL_READONLY_READONLY_PUBLIC_REFS_PURPOSE,
                metadata=metadata,
            )
            for ref in _ordered_unique(
                status["external_readonly_evidence_observation_refs"]
            )
        ],
    )


def _ref_metadata(
    status: Mapping[str, Any],
    facts: Mapping[str, Any],
) -> dict[str, Any]:
    raw_boundary_flags = _mapping(facts.get("raw_boundary_flags"))
    return {
        "source": EXTERNAL_READONLY_REFS_PROJECTION_SOURCE,
        "payload_type": str(status["payload_type"]),
        "payload_version": str(status["payload_version"]),
        "status": str(facts["status"]),
        "candidate_count": _int_value(facts.get("candidate_count")),
        "reference_review_ready": facts.get("reference_review_ready") is True,
        "allowed_for_model_context": (
            facts.get("allowed_for_model_context") is True
        ),
        "readonly": True,
        "refs_only": True,
        "candidate_only": True,
        "blocking_reason_count": len(_list_value(facts.get("blocking_reasons"))),
        "warning_count": len(_list_value(facts.get("warnings"))),
        "raw_response_included": (
            raw_boundary_flags.get("raw_response_included") is True
        ),
        "raw_html_included": raw_boundary_flags.get("raw_html_included") is True,
        "response_headers_included": (
            raw_boundary_flags.get("response_headers_included") is True
        ),
    }


def _raise_if_forbidden_input_payload(
    value: Mapping[str, Any],
    *,
    path: str = "$",
) -> None:
    violations: list[str] = []

    def visit(item: Any, item_path: str) -> None:
        if isinstance(item, Mapping):
            for raw_key, raw_value in item.items():
                key = _normalize_key(raw_key)
                next_path = f"{item_path}.{raw_key}"
                if _forbidden_input_key(key):
                    violations.append(next_path)
                visit(raw_value, next_path)
        elif isinstance(item, list | tuple):
            for index, raw_value in enumerate(item):
                visit(raw_value, f"{item_path}[{index}]")

    visit(value, path)
    if violations:
        joined = ", ".join(violations)
        raise ValueError(f"forbidden external-readonly refs payload keys: {joined}")


def _forbidden_input_key(key: str) -> bool:
    return (
        key in _FORBIDDEN_INPUT_KEYS
        or key.endswith("_token")
        or key.endswith("_secret")
        or key.endswith("_credential")
    )


def _ordered_unique(values: Any) -> list[str]:
    seen: set[str] = set()
    refs: list[str] = []
    for value in _list_value(values):
        ref = str(value)
        if ref and ref not in seen:
            seen.add(ref)
            refs.append(ref)
    return refs


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int_value(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _normalize_key(value: Any) -> str:
    return str(value).strip().replace("-", "_").replace(" ", "_").lower()


__all__ = [
    "EXTERNAL_READONLY_EVIDENCE_OBSERVATION_REF_KIND",
    "EXTERNAL_READONLY_EVIDENCE_REF_KIND",
    "EXTERNAL_READONLY_READONLY_PUBLIC_REFS_PURPOSE",
    "EXTERNAL_READONLY_REFS_PROJECTION_SOURCE",
    "project_external_readonly_readonly_public_refs_to_product_gateway_output_refs",
]
