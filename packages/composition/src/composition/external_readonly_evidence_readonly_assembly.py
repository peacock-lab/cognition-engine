"""Read-only product assembly for external-readonly evidence facts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from contract_core.external_readonly_evidence import (
    ExternalReadonlyEvidenceReadonlyPublicRefs,
    build_external_readonly_evidence_readonly_facts,
    build_external_readonly_evidence_readonly_public_refs,
    external_readonly_evidence_readonly_public_refs_status_dict,
)
from observability_hub import (
    ExternalReadonlyEvidenceObservationCandidate,
    build_external_readonly_evidence_observation_candidates_from_read_context,
)


@dataclass(frozen=True)
class ExternalReadonlyEvidenceReadonlyProductBundle:
    """Compact product bundle for read-only external evidence consumption."""

    observation_candidates: tuple[
        ExternalReadonlyEvidenceObservationCandidate,
        ...,
    ]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_public_refs(self) -> dict[str, Any]:
        """Return refs and compact facts without exposing full candidates."""

        return external_readonly_evidence_readonly_public_refs_status_dict(
            self.to_public_contract()
        )

    def to_public_contract(self) -> ExternalReadonlyEvidenceReadonlyPublicRefs:
        """Return the stable readonly refs/facts behavior contract."""

        observation_refs = [
            _observation_ref(candidate)
            for candidate in self.observation_candidates
        ]
        evidence_refs = _ordered_unique(
            candidate.evidence_ref
            for candidate in self.observation_candidates
            if candidate.evidence_ref
        )
        evidence_output_paths = _ordered_unique(
            candidate.evidence_output_path
            for candidate in self.observation_candidates
        )
        source_urls = _ordered_unique(
            candidate.source_url
            for candidate in self.observation_candidates
            if candidate.source_url
        )

        facts = build_external_readonly_evidence_readonly_facts(
            observation_candidate_ids=(
                candidate.observation_id
                for candidate in self.observation_candidates
            ),
            evidence_output_paths=evidence_output_paths,
            evidence_refs=evidence_refs,
            source_urls=source_urls,
            status=_bundle_status(self.observation_candidates),
            reference_review_ready=_all_candidates_true(
                self.observation_candidates,
                "reference_review_ready",
            ),
            allowed_for_model_context=_all_candidates_true(
                self.observation_candidates,
                "allowed_for_model_context",
            ),
            candidate_count=len(self.observation_candidates),
            blocking_reasons=_merged_text_list(
                self.observation_candidates,
                "blocking_reasons",
            ),
            warnings=_merged_text_list(
                self.observation_candidates,
                "warnings",
            ),
            metadata_keys=_merged_text_list(
                self.observation_candidates,
                "metadata_keys",
            ),
            raw_boundary_flags={
                "raw_response_included": _any_candidate_true(
                    self.observation_candidates,
                    "raw_response_included",
                ),
                "raw_html_included": _any_candidate_true(
                    self.observation_candidates,
                    "raw_html_included",
                ),
                "response_headers_included": _any_candidate_true(
                    self.observation_candidates,
                    "response_headers_included",
                ),
            },
            metadata=self.metadata,
        )
        return build_external_readonly_evidence_readonly_public_refs(
            external_readonly_evidence_observation_refs=observation_refs,
            external_readonly_evidence_refs=evidence_refs,
            facts=facts,
            metadata=self.metadata,
        )


def build_external_readonly_evidence_readonly_product_bundle(
    read_context: Any,
    *,
    metadata: dict[str, Any] | None = None,
) -> ExternalReadonlyEvidenceReadonlyProductBundle:
    """Build a read-only bundle from a prepared-only evidence read context."""

    observation_candidates = (
        build_external_readonly_evidence_observation_candidates_from_read_context(
            read_context
        )
    )
    return ExternalReadonlyEvidenceReadonlyProductBundle(
        observation_candidates=observation_candidates,
        metadata={
            "assembly": (
                "composition.external_readonly_evidence_readonly_assembly"
            ),
            "readonly": True,
            "candidate_only": True,
            "does_not_read_files": True,
            "does_not_write_files": True,
            "does_not_call_network": True,
            "does_not_call_model": True,
            "does_not_call_runtime": True,
            **_compact_metadata(metadata or {}),
        },
    )


def _observation_ref(
    candidate: ExternalReadonlyEvidenceObservationCandidate,
) -> str:
    return (
        "external-readonly-evidence-observation://"
        f"{candidate.observation_id}"
    )


def _bundle_status(
    candidates: Sequence[ExternalReadonlyEvidenceObservationCandidate],
) -> str:
    if not candidates:
        return "empty"
    statuses = tuple(candidate.status for candidate in candidates)
    if all(status == "ready" for status in statuses):
        return "ready"
    if all(status != "ready" for status in statuses):
        return "blocked"
    return "mixed"


def _all_candidates_true(
    candidates: Sequence[ExternalReadonlyEvidenceObservationCandidate],
    attribute_name: str,
) -> bool:
    return bool(candidates) and all(
        bool(getattr(candidate, attribute_name))
        for candidate in candidates
    )


def _any_candidate_true(
    candidates: Sequence[ExternalReadonlyEvidenceObservationCandidate],
    attribute_name: str,
) -> bool:
    return any(
        bool(getattr(candidate, attribute_name))
        for candidate in candidates
    )


def _merged_text_list(
    candidates: Sequence[ExternalReadonlyEvidenceObservationCandidate],
    attribute_name: str,
) -> list[str]:
    values: list[str] = []
    for candidate in candidates:
        value = getattr(candidate, attribute_name)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, Iterable):
            values.extend(str(item) for item in value if item is not None)
    return _ordered_unique(values)


def _ordered_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _compact_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in metadata.items():
        if not isinstance(key, str):
            continue
        if _sensitive_metadata_key(key):
            continue
        if not isinstance(value, bool | int | float | str):
            continue
        if isinstance(value, str) and _sensitive_metadata_value(value):
            continue
        compact[key] = value
    return compact


def _sensitive_metadata_key(key: str) -> bool:
    normalized = key.lower()
    return any(
        marker in normalized
        for marker in (
            "authorization",
            "auth_headers",
            "config_assembly",
            "config_context",
            "config_contexts",
            "cookie",
            "headers",
            "password",
            "raw_html",
            "raw_payload",
            "raw_response",
            "request_payload",
            "response_headers",
            "secret",
            "token",
        )
    )


def _sensitive_metadata_value(value: str) -> bool:
    normalized = value.lower()
    return any(
        marker in normalized
        for marker in (
            "authorization",
            "config_context",
            "cookie",
            "password",
            "raw-html",
            "raw-response",
            "secret",
            "token",
        )
    )
