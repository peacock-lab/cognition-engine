"""Read-only summaries for archived external-readonly evidence outputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
import ipaddress
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

EXTERNAL_READONLY_CONTROLLED_OUTPUT_ROOT = "outputs/external-readonly"
EXTERNAL_READONLY_EVIDENCE_REF_PREFIX = "evidence://external-readonly/"
EXTERNAL_READONLY_EXCERPT_FORBIDDEN_MARKERS = (
    "api_key=",
    "authorization:",
    "begin private key",
    "password=",
    "private_key=",
    "secret=",
    "service_account_json",
)
EXTERNAL_READONLY_MAX_EXCERPT_CHARS = 2_000
EXTERNAL_READONLY_EVIDENCE_SUMMARY_STAGES = (
    "controlled_path_review",
    "archive_json_review",
    "raw_payload_boundary_review",
    "sanitized_summary_projection",
    "reference_review_preparation",
)
EXTERNAL_READONLY_EVIDENCE_SUMMARY_MODE = "prepared_only"
EXTERNAL_READONLY_MAX_TOTAL_EXCERPT_CHARS = 8_000
EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_PAYLOAD_TYPE = (
    "external_readonly_evidence_readonly_public_refs"
)
EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_VERSION = (
    "external_readonly_evidence_readonly_public_refs_v1"
)
EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_STATUSES = frozenset(
    {"ready", "blocked", "mixed", "empty"}
)
EXTERNAL_READONLY_EVIDENCE_OBSERVATION_REF_PREFIX = (
    "external-readonly-evidence-observation://"
)
EXTERNAL_READONLY_EVIDENCE_READ_CONTEXT_INVALID_STATUS_REASON = (
    "external_readonly_evidence_context_status_invalid"
)
EXTERNAL_READONLY_EVIDENCE_FORBIDDEN_RAW_KEYS = frozenset(
    {
        "api_key",
        "auth_headers",
        "authorization",
        "body",
        "cookie",
        "cookies",
        "full_page_content",
        "headers",
        "html",
        "password",
        "raw_html",
        "raw_network_response",
        "raw_request_payload",
        "raw_response",
        "raw_url_context",
        "request_body",
        "request_payload",
        "response_body",
        "response_headers",
        "secret",
        "set_cookie",
        "token",
        "tokens",
    }
)
EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_FORBIDDEN_METADATA_KEYS = (
    "authorization",
    "auth_headers",
    "body",
    "config_assembly",
    "config_context",
    "config_contexts",
    "cookie",
    "headers",
    "html",
    "password",
    "raw_html",
    "raw_payload",
    "raw_provider_response",
    "raw_request_payload",
    "raw_response",
    "request_payload",
    "response_headers",
    "sanitized_excerpt_preview",
    "secret",
    "set_cookie",
    "token",
)
EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_FORBIDDEN_METADATA_VALUES = (
    "authorization",
    "composition",
    "config_context",
    "config_contexts",
    "cookie",
    "google.adk",
    "litellm",
    "observability_hub",
    "password",
    "product_gateway",
    "raw-html",
    "raw-payload",
    "raw-response",
    "raw_html",
    "raw_payload",
    "raw_response",
    "runtime_container",
    "secret",
    "token",
)
EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_FORBIDDEN_METADATA_KEY_NAMES = (
    "authorization",
    "auth_headers",
    "cookie",
    "headers",
    "password",
    "raw_html",
    "raw_payload",
    "raw_response",
    "response_headers",
    "sanitized_excerpt_preview",
    "secret",
    "set_cookie",
    "token",
)


@dataclass(frozen=True)
class ExternalReadonlyEvidenceSummary:
    """Sanitized read-only summary of one archived external evidence output."""

    evidence_output_path: str
    status: str
    reference_review_ready: bool
    evidence_ref: str | None = None
    source_url: str | None = None
    runtime_status: str | None = None
    allowed_for_model_context: bool = False
    evidence_written: bool = False
    runtime_fetch_performed: bool = False
    transport_called: bool = False
    external_network_call_performed: bool = False
    raw_response_included: bool = False
    raw_html_included: bool = False
    response_headers_included: bool = False
    uploads_content: bool = False
    writes_files: bool = False
    content_hash: str | None = None
    sanitized_excerpt_preview: str | None = None
    total_excerpt_chars: int = 0
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalReadonlyEvidenceReadContext:
    """Aggregate prepared-only context for reference-review integration."""

    status: str
    reference_review_ready: bool
    summaries: tuple[ExternalReadonlyEvidenceSummary, ...] = ()
    evidence_output_paths: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    source_urls: tuple[str, ...] = ()
    total_excerpt_chars: int = 0
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalReadonlyEvidenceReadonlyRawBoundaryFlags:
    """Raw-boundary facts exposed as booleans only."""

    raw_response_included: bool = False
    raw_html_included: bool = False
    response_headers_included: bool = False


@dataclass(frozen=True)
class ExternalReadonlyEvidenceReadonlyFacts:
    """Public readonly facts for external-readonly evidence refs."""

    observation_candidate_ids: tuple[str, ...]
    evidence_output_paths: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    source_urls: tuple[str, ...]
    status: str
    reference_review_ready: bool
    allowed_for_model_context: bool
    candidate_count: int
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata_keys: tuple[str, ...] = ()
    raw_boundary_flags: ExternalReadonlyEvidenceReadonlyRawBoundaryFlags = field(
        default_factory=ExternalReadonlyEvidenceReadonlyRawBoundaryFlags
    )
    readonly: bool = True
    candidate_only: bool = True
    does_not_read_files: bool = True
    does_not_write_files: bool = True
    does_not_call_network: bool = True
    does_not_call_model: bool = True
    does_not_call_runtime: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalReadonlyEvidenceReadonlyPublicRefs:
    """Stable public refs/facts contract for readonly evidence consumption."""

    payload_type: str
    payload_version: str
    external_readonly_evidence_observation_refs: tuple[str, ...]
    external_readonly_evidence_refs: tuple[str, ...]
    facts: ExternalReadonlyEvidenceReadonlyFacts
    readonly: bool = True
    refs_only: bool = True
    candidate_only: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


def read_external_readonly_evidence_summary(
    evidence_path: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> ExternalReadonlyEvidenceSummary:
    """Read one archived evidence JSON and project a sanitized summary."""

    path_text = str(evidence_path).strip()
    root = Path(repo_root or Path.cwd()).expanduser().resolve()
    path_issue = validate_external_readonly_evidence_path(
        evidence_path=path_text,
        repo_root=root,
    )
    if path_issue:
        return _blocked_summary(
            evidence_output_path=path_text,
            blocking_reasons=(path_issue,),
            metadata={"controlled_path_review": "blocked"},
        )

    target = (root / path_text).resolve()
    if not target.exists():
        return _blocked_summary(
            evidence_output_path=path_text,
            blocking_reasons=("evidence_file_missing",),
            metadata={"controlled_path_review": "passed"},
        )
    if not target.is_file():
        return _blocked_summary(
            evidence_output_path=path_text,
            blocking_reasons=("evidence_path_not_file",),
            metadata={"controlled_path_review": "passed"},
        )

    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _blocked_summary(
            evidence_output_path=path_text,
            blocking_reasons=("evidence_json_invalid",),
            metadata={"controlled_path_review": "passed"},
        )
    if not isinstance(payload, Mapping):
        return _blocked_summary(
            evidence_output_path=path_text,
            blocking_reasons=("evidence_payload_not_object",),
            metadata={"controlled_path_review": "passed"},
        )
    return build_external_readonly_evidence_summary(
        payload,
        evidence_output_path=path_text,
    )


def build_external_readonly_evidence_read_context(
    evidence_paths: Sequence[str | Path],
    *,
    repo_root: str | Path | None = None,
) -> ExternalReadonlyEvidenceReadContext:
    """Build a prepared-only aggregate context without network or file writes."""

    summaries = tuple(
        read_external_readonly_evidence_summary(path, repo_root=repo_root)
        for path in evidence_paths
    )
    blocking: list[str] = []
    warnings: list[str] = []
    for summary in summaries:
        warnings.extend(
            f"{summary.evidence_output_path}:{reason}"
            for reason in summary.warnings
        )
        if summary.status != "ready":
            blocking.extend(
                f"{summary.evidence_output_path}:{reason}"
                for reason in summary.blocking_reasons
            )

    evidence_refs = tuple(
        _ordered_unique(
            summary.evidence_ref
            for summary in summaries
            if summary.evidence_ref
        )
    )
    source_urls = tuple(
        _ordered_unique(
            summary.source_url for summary in summaries if summary.source_url
        )
    )
    evidence_output_paths = tuple(
        _ordered_unique(summary.evidence_output_path for summary in summaries)
    )
    total_excerpt_chars = sum(summary.total_excerpt_chars for summary in summaries)
    if total_excerpt_chars > EXTERNAL_READONLY_MAX_TOTAL_EXCERPT_CHARS:
        blocking.append("total_excerpt_chars_exceeds_budget")

    if not summaries:
        status = "empty"
    else:
        status = "blocked" if blocking else "ready"
    reference_review_ready = status == "ready"
    return ExternalReadonlyEvidenceReadContext(
        status=status,
        reference_review_ready=reference_review_ready,
        summaries=summaries,
        evidence_output_paths=evidence_output_paths,
        evidence_refs=evidence_refs,
        source_urls=source_urls,
        total_excerpt_chars=total_excerpt_chars,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "external_readonly_core": True,
            "candidate_only": True,
            "reference_only": True,
            "integration_mode": EXTERNAL_READONLY_EVIDENCE_SUMMARY_MODE,
            "reference_review_prepared": reference_review_ready,
            "prompt_injection_enabled": False,
            "does_not_access_network": True,
            "does_not_perform_external_network_calls": True,
            "does_not_write_files": True,
            "does_not_call_model": True,
            "summary_count": len(summaries),
            "stages": list(EXTERNAL_READONLY_EVIDENCE_SUMMARY_STAGES),
        },
    )


def build_external_readonly_evidence_readonly_facts(
    *,
    observation_candidate_ids: Sequence[str | None] = (),
    evidence_output_paths: Sequence[str | None] = (),
    evidence_refs: Sequence[str | None] = (),
    source_urls: Sequence[str | None] = (),
    status: str = "empty",
    reference_review_ready: bool = False,
    allowed_for_model_context: bool = False,
    candidate_count: int = 0,
    blocking_reasons: Sequence[str | None] = (),
    warnings: Sequence[str | None] = (),
    metadata_keys: Sequence[str | None] = (),
    raw_boundary_flags: (
        ExternalReadonlyEvidenceReadonlyRawBoundaryFlags
        | Mapping[str, Any]
        | None
    ) = None,
    readonly: bool = True,
    candidate_only: bool = True,
    does_not_read_files: bool = True,
    does_not_write_files: bool = True,
    does_not_call_network: bool = True,
    does_not_call_model: bool = True,
    does_not_call_runtime: bool = True,
    metadata: Mapping[str, Any] | None = None,
) -> ExternalReadonlyEvidenceReadonlyFacts:
    """Build readonly public facts without carrying raw/config values."""

    facts = ExternalReadonlyEvidenceReadonlyFacts(
        observation_candidate_ids=tuple(
            _ordered_unique_texts(observation_candidate_ids)
        ),
        evidence_output_paths=tuple(_ordered_unique_texts(evidence_output_paths)),
        evidence_refs=tuple(_ordered_unique_texts(evidence_refs)),
        source_urls=tuple(_ordered_unique_texts(source_urls)),
        status=_readonly_public_refs_status(status),
        reference_review_ready=_strict_bool(
            reference_review_ready,
            "reference_review_ready",
        ),
        allowed_for_model_context=_strict_bool(
            allowed_for_model_context,
            "allowed_for_model_context",
        ),
        candidate_count=_non_negative_candidate_count(candidate_count),
        blocking_reasons=tuple(_ordered_unique_texts(blocking_reasons)),
        warnings=tuple(_ordered_unique_texts(warnings)),
        metadata_keys=tuple(_readonly_public_metadata_key_names(metadata_keys)),
        raw_boundary_flags=_readonly_raw_boundary_flags(raw_boundary_flags),
        readonly=_strict_bool(readonly, "readonly"),
        candidate_only=_strict_bool(candidate_only, "candidate_only"),
        does_not_read_files=_strict_bool(
            does_not_read_files,
            "does_not_read_files",
        ),
        does_not_write_files=_strict_bool(
            does_not_write_files,
            "does_not_write_files",
        ),
        does_not_call_network=_strict_bool(
            does_not_call_network,
            "does_not_call_network",
        ),
        does_not_call_model=_strict_bool(
            does_not_call_model,
            "does_not_call_model",
        ),
        does_not_call_runtime=_strict_bool(
            does_not_call_runtime,
            "does_not_call_runtime",
        ),
        metadata=_compact_readonly_public_metadata(metadata or {}),
    )
    _validate_external_readonly_evidence_readonly_facts(facts)
    return facts


def build_external_readonly_evidence_readonly_public_refs(
    *,
    external_readonly_evidence_observation_refs: Sequence[str | None] = (),
    external_readonly_evidence_refs: Sequence[str | None] = (),
    facts: ExternalReadonlyEvidenceReadonlyFacts | Mapping[str, Any],
    payload_type: str = (
        EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_PAYLOAD_TYPE
    ),
    payload_version: str = (
        EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_VERSION
    ),
    readonly: bool = True,
    refs_only: bool = True,
    candidate_only: bool = True,
    metadata: Mapping[str, Any] | None = None,
) -> ExternalReadonlyEvidenceReadonlyPublicRefs:
    """Build the stable readonly public refs/facts contract."""

    contract = ExternalReadonlyEvidenceReadonlyPublicRefs(
        payload_type=_required_exact_text(
            payload_type,
            EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_PAYLOAD_TYPE,
            "payload_type",
        ),
        payload_version=_required_exact_text(
            payload_version,
            EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_VERSION,
            "payload_version",
        ),
        external_readonly_evidence_observation_refs=tuple(
            _ordered_unique_texts(external_readonly_evidence_observation_refs)
        ),
        external_readonly_evidence_refs=tuple(
            _ordered_unique_texts(external_readonly_evidence_refs)
        ),
        facts=_readonly_facts_from_value(facts),
        readonly=_strict_bool(readonly, "readonly"),
        refs_only=_strict_bool(refs_only, "refs_only"),
        candidate_only=_strict_bool(candidate_only, "candidate_only"),
        metadata=_compact_readonly_public_metadata(metadata or {}),
    )
    validate_external_readonly_evidence_readonly_public_refs(contract)
    return contract


def build_external_readonly_evidence_readonly_public_refs_from_read_context(
    read_context: ExternalReadonlyEvidenceReadContext | Mapping[str, Any],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> ExternalReadonlyEvidenceReadonlyPublicRefs:
    """Project prepared-only read context into readonly public refs."""

    context = _contract_mapping(read_context)
    status = _read_context_status(context.get("status"))
    blocking_reasons = _read_context_texts(context.get("blocking_reasons"))
    if status not in EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_STATUSES:
        status = "blocked"
        blocking_reasons = tuple(
            _ordered_unique(
                (
                    *blocking_reasons,
                    EXTERNAL_READONLY_EVIDENCE_READ_CONTEXT_INVALID_STATUS_REASON,
                )
            )
        )

    evidence_refs = _read_context_texts(context.get("evidence_refs"))
    evidence_output_paths = _read_context_texts(
        context.get("evidence_output_paths")
    )
    source_urls = _read_context_texts(context.get("source_urls"))
    if status == "empty":
        evidence_refs = ()
        evidence_output_paths = ()
        source_urls = ()

    reference_review_ready = context.get("reference_review_ready") is True
    facts = build_external_readonly_evidence_readonly_facts(
        evidence_output_paths=evidence_output_paths,
        evidence_refs=evidence_refs,
        source_urls=source_urls,
        status=status,
        reference_review_ready=reference_review_ready,
        allowed_for_model_context=(
            status == "ready" and reference_review_ready
        ),
        candidate_count=_read_context_candidate_count(
            context,
            evidence_refs=evidence_refs,
        ),
        blocking_reasons=blocking_reasons,
        warnings=_read_context_texts(context.get("warnings")),
        metadata_keys=_read_context_metadata_keys(context),
        raw_boundary_flags=_read_context_raw_boundary_flags(context),
        metadata=metadata,
    )
    return build_external_readonly_evidence_readonly_public_refs(
        external_readonly_evidence_observation_refs=(),
        external_readonly_evidence_refs=evidence_refs,
        facts=facts,
        metadata=metadata,
    )


def external_readonly_evidence_readonly_public_refs_status_dict(
    public_refs: ExternalReadonlyEvidenceReadonlyPublicRefs | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-ready readonly public refs/facts payload."""

    contract = _readonly_public_refs_from_value(public_refs)
    validate_external_readonly_evidence_readonly_public_refs(contract)
    return {
        "payload_type": contract.payload_type,
        "payload_version": contract.payload_version,
        "external_readonly_evidence_observation_refs": list(
            contract.external_readonly_evidence_observation_refs
        ),
        "external_readonly_evidence_refs": list(
            contract.external_readonly_evidence_refs
        ),
        "external_readonly_evidence_readonly_facts": {
            "observation_candidate_ids": list(
                contract.facts.observation_candidate_ids
            ),
            "evidence_output_paths": list(contract.facts.evidence_output_paths),
            "evidence_refs": list(contract.facts.evidence_refs),
            "source_urls": list(contract.facts.source_urls),
            "status": contract.facts.status,
            "reference_review_ready": contract.facts.reference_review_ready,
            "allowed_for_model_context": (
                contract.facts.allowed_for_model_context
            ),
            "candidate_count": contract.facts.candidate_count,
            "blocking_reasons": list(contract.facts.blocking_reasons),
            "warnings": list(contract.facts.warnings),
            "metadata_keys": list(contract.facts.metadata_keys),
            "raw_boundary_flags": {
                "raw_response_included": (
                    contract.facts.raw_boundary_flags.raw_response_included
                ),
                "raw_html_included": (
                    contract.facts.raw_boundary_flags.raw_html_included
                ),
                "response_headers_included": (
                    contract.facts.raw_boundary_flags.response_headers_included
                ),
            },
            "readonly": contract.facts.readonly,
            "candidate_only": contract.facts.candidate_only,
            "does_not_read_files": contract.facts.does_not_read_files,
            "does_not_write_files": contract.facts.does_not_write_files,
            "does_not_call_network": contract.facts.does_not_call_network,
            "does_not_call_model": contract.facts.does_not_call_model,
            "does_not_call_runtime": contract.facts.does_not_call_runtime,
            "metadata": dict(contract.facts.metadata),
        },
        "readonly": contract.readonly,
        "refs_only": contract.refs_only,
        "candidate_only": contract.candidate_only,
        "metadata": dict(contract.metadata),
    }


def validate_external_readonly_evidence_readonly_public_refs(
    public_refs: ExternalReadonlyEvidenceReadonlyPublicRefs | Mapping[str, Any],
) -> None:
    """Validate readonly public refs/facts and fail on boundary regressions."""

    contract = _readonly_public_refs_from_value(public_refs)
    if (
        contract.payload_type
        != EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_PAYLOAD_TYPE
    ):
        raise ValueError("payload_type must be external-readonly readonly refs.")
    if (
        contract.payload_version
        != EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_VERSION
    ):
        raise ValueError("payload_version must be readonly public refs v1.")
    if not contract.readonly:
        raise ValueError("readonly must be true.")
    if not contract.refs_only:
        raise ValueError("refs_only must be true.")
    if not contract.candidate_only:
        raise ValueError("candidate_only must be true.")
    _validate_refs_with_prefix(
        contract.external_readonly_evidence_observation_refs,
        EXTERNAL_READONLY_EVIDENCE_OBSERVATION_REF_PREFIX,
        "external_readonly_evidence_observation_refs",
    )
    _validate_refs_with_prefix(
        contract.external_readonly_evidence_refs,
        EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
        "external_readonly_evidence_refs",
    )
    _validate_external_readonly_evidence_readonly_facts(contract.facts)
    if (
        contract.external_readonly_evidence_refs
        != contract.facts.evidence_refs
    ):
        raise ValueError("external_readonly_evidence_refs must match facts.")
    if (
        contract.facts.status == "empty"
        and contract.external_readonly_evidence_observation_refs
    ):
        raise ValueError("empty refs must not include observation refs.")
    _validate_readonly_public_metadata(contract.metadata, "metadata")


def build_external_readonly_evidence_summary(
    payload: Mapping[str, Any],
    *,
    evidence_output_path: str | None = None,
) -> ExternalReadonlyEvidenceSummary:
    """Project a sanitized summary from a CLI evidence-output payload."""

    runtime = payload.get("runtime")
    runtime_payload = runtime if isinstance(runtime, Mapping) else {}
    output_path = _string_value(
        evidence_output_path or payload.get("evidence_output_path")
    )
    evidence_ref = _string_value(payload.get("evidence_ref"))
    source_url = _first_present_string(
        payload.get("source_url"),
        _first_sequence_string(runtime_payload.get("source_urls")),
    )
    runtime_status = _string_value(runtime_payload.get("status"))
    content_hash = _string_value(runtime_payload.get("content_hash"))
    sanitized_excerpt_preview = _string_value(
        runtime_payload.get("sanitized_excerpt_preview")
    )
    total_excerpt_chars = _int_value(runtime_payload.get("total_excerpt_chars"))

    raw_response_included = _truthy(payload.get("raw_response_included")) or _truthy(
        runtime_payload.get("raw_response_included")
    )
    raw_html_included = _truthy(payload.get("raw_html_included")) or _truthy(
        runtime_payload.get("raw_html_included")
    )
    response_headers_included = _truthy(
        payload.get("response_headers_included")
    ) or _truthy(runtime_payload.get("response_headers_included"))
    uploads_content = _truthy(payload.get("uploads_content"))
    writes_files = _truthy(payload.get("writes_files"))
    evidence_written = _truthy(payload.get("evidence_written"))
    allowed_for_model_context = _truthy(
        payload.get("allowed_for_model_context")
    ) and _truthy(runtime_payload.get("allowed_for_model_context"))
    runtime_fetch_performed = _truthy(payload.get("runtime_fetch_performed")) or _truthy(
        runtime_payload.get("runtime_fetch_performed")
    )
    transport_called = _truthy(payload.get("transport_called")) or _truthy(
        runtime_payload.get("transport_called")
    )
    external_network_call_performed = _truthy(
        payload.get("external_network_call_performed")
    ) or _truthy(runtime_payload.get("external_network_call_performed"))

    blocking: list[str] = []
    warnings: list[str] = []
    if not output_path:
        blocking.append("evidence_output_path_required")
    else:
        path_issue = validate_external_readonly_evidence_path(
            evidence_path=output_path
        )
        if path_issue:
            blocking.append(path_issue)
    payload_output_path = _string_value(payload.get("evidence_output_path"))
    if evidence_output_path and payload_output_path and payload_output_path != output_path:
        blocking.append("evidence_output_path_mismatch")
    if _string_value(payload.get("status")) != "success" or not _truthy(
        payload.get("success")
    ):
        blocking.append("evidence_status_not_success")
    if not evidence_written:
        blocking.append("evidence_written_required")
    if not _evidence_ref_allowed(evidence_ref):
        blocking.append("evidence_ref_not_external_readonly")
    if not _external_https_url_allowed(source_url or ""):
        blocking.append("source_url_not_external_https")
    if not isinstance(runtime, Mapping):
        blocking.append("runtime_summary_required")
    if runtime_status != "completed":
        blocking.append("runtime_status_not_completed")
    if not allowed_for_model_context:
        blocking.append("allowed_for_model_context_required")
    if raw_response_included:
        blocking.append("raw_response_forbidden")
    if raw_html_included:
        blocking.append("raw_html_forbidden")
    if response_headers_included:
        blocking.append("response_headers_forbidden")
    if uploads_content:
        blocking.append("upload_forbidden")
    if writes_files:
        blocking.append("writes_files_forbidden")
    if not sanitized_excerpt_preview:
        blocking.append("sanitized_excerpt_preview_required")
    elif len(sanitized_excerpt_preview) > EXTERNAL_READONLY_MAX_EXCERPT_CHARS:
        blocking.append("sanitized_excerpt_preview_too_large")
    if sanitized_excerpt_preview and _excerpt_contains_forbidden_marker(
        sanitized_excerpt_preview
    ):
        blocking.append("sanitized_excerpt_preview_contains_secret_marker")
    if not content_hash:
        blocking.append("content_hash_required")
    elif not re.fullmatch(r"[0-9a-f]{64}", content_hash):
        blocking.append("content_hash_invalid")
    if total_excerpt_chars <= 0:
        blocking.append("total_excerpt_chars_required")
    elif total_excerpt_chars > EXTERNAL_READONLY_MAX_TOTAL_EXCERPT_CHARS:
        blocking.append("total_excerpt_chars_exceeds_budget")

    raw_key_paths = _forbidden_raw_key_paths(payload)
    if raw_key_paths:
        blocking.append("raw_payload_keys_forbidden")
    if not runtime_fetch_performed:
        warnings.append("runtime_fetch_not_performed")
    if not transport_called:
        warnings.append("transport_not_called")
    if not external_network_call_performed:
        warnings.append("external_network_call_not_performed")

    ready = not blocking
    return ExternalReadonlyEvidenceSummary(
        evidence_output_path=output_path,
        status="ready" if ready else "blocked",
        reference_review_ready=ready,
        evidence_ref=evidence_ref or None,
        source_url=source_url or None,
        runtime_status=runtime_status or None,
        allowed_for_model_context=allowed_for_model_context,
        evidence_written=evidence_written,
        runtime_fetch_performed=runtime_fetch_performed,
        transport_called=transport_called,
        external_network_call_performed=external_network_call_performed,
        raw_response_included=raw_response_included,
        raw_html_included=raw_html_included,
        response_headers_included=response_headers_included,
        uploads_content=uploads_content,
        writes_files=writes_files,
        content_hash=content_hash or None,
        sanitized_excerpt_preview=sanitized_excerpt_preview or None,
        total_excerpt_chars=total_excerpt_chars,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "external_readonly_core": True,
            "candidate_only": True,
            "reference_only": True,
            "integration_mode": EXTERNAL_READONLY_EVIDENCE_SUMMARY_MODE,
            "reference_review_prepared": ready,
            "prompt_injection_enabled": False,
            "raw_payload_keys_included": False,
            "forbidden_raw_key_paths": list(raw_key_paths),
            "does_not_access_network": True,
            "does_not_perform_external_network_calls": True,
            "does_not_write_files": True,
            "does_not_call_model": True,
            "stages": list(EXTERNAL_READONLY_EVIDENCE_SUMMARY_STAGES),
        },
    )


def validate_external_readonly_evidence_path(
    *,
    evidence_path: str,
    repo_root: str | Path | None = None,
) -> str | None:
    """Return a blocking reason when an evidence path is outside the archive root."""

    if not evidence_path:
        return "evidence_output_path_required"
    path = Path(evidence_path)
    if path.is_absolute():
        return "evidence_output_path_must_be_relative"
    if path.suffix != ".json":
        return "evidence_output_path_must_be_json"
    if any(part in {"", ".", ".."} for part in path.parts):
        return "evidence_output_path_unsafe"
    controlled_root = Path(EXTERNAL_READONLY_CONTROLLED_OUTPUT_ROOT)
    if path.parts[: len(controlled_root.parts)] != controlled_root.parts:
        return "evidence_output_path_outside_controlled_root"
    if repo_root is None:
        return None
    root = Path(repo_root).expanduser().resolve()
    target = (root / path).resolve()
    allowed_root = (root / controlled_root).resolve()
    if not target.is_relative_to(allowed_root):
        return "evidence_output_path_outside_controlled_root"
    return None


def external_readonly_evidence_summary_status_dict(
    summary: ExternalReadonlyEvidenceSummary,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized summary status."""

    return {
        "evidence_output_path": summary.evidence_output_path,
        "status": summary.status,
        "reference_review_ready": summary.reference_review_ready,
        "evidence_ref": summary.evidence_ref,
        "source_url": summary.source_url,
        "runtime_status": summary.runtime_status,
        "allowed_for_model_context": summary.allowed_for_model_context,
        "evidence_written": summary.evidence_written,
        "runtime_fetch_performed": summary.runtime_fetch_performed,
        "transport_called": summary.transport_called,
        "external_network_call_performed": summary.external_network_call_performed,
        "raw_response_included": summary.raw_response_included,
        "raw_html_included": summary.raw_html_included,
        "response_headers_included": summary.response_headers_included,
        "uploads_content": summary.uploads_content,
        "writes_files": summary.writes_files,
        "content_hash": summary.content_hash,
        "sanitized_excerpt_preview": summary.sanitized_excerpt_preview,
        "total_excerpt_chars": summary.total_excerpt_chars,
        "blocking_reasons": list(summary.blocking_reasons),
        "warnings": list(summary.warnings),
        "metadata": dict(summary.metadata),
    }


def external_readonly_evidence_read_context_status_dict(
    context: ExternalReadonlyEvidenceReadContext,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized read context status."""

    return {
        "status": context.status,
        "reference_review_ready": context.reference_review_ready,
        "evidence_output_paths": list(context.evidence_output_paths),
        "evidence_refs": list(context.evidence_refs),
        "source_urls": list(context.source_urls),
        "total_excerpt_chars": context.total_excerpt_chars,
        "blocking_reasons": list(context.blocking_reasons),
        "warnings": list(context.warnings),
        "summaries": [
            external_readonly_evidence_summary_status_dict(summary)
            for summary in context.summaries
        ],
        "metadata": dict(context.metadata),
    }


def _blocked_summary(
    *,
    evidence_output_path: str,
    blocking_reasons: Sequence[str],
    metadata: Mapping[str, Any] | None = None,
) -> ExternalReadonlyEvidenceSummary:
    return ExternalReadonlyEvidenceSummary(
        evidence_output_path=evidence_output_path,
        status="blocked",
        reference_review_ready=False,
        blocking_reasons=tuple(_ordered_unique(blocking_reasons)),
        metadata={
            "external_readonly_core": True,
            "candidate_only": True,
            "reference_only": True,
            "integration_mode": EXTERNAL_READONLY_EVIDENCE_SUMMARY_MODE,
            "reference_review_prepared": False,
            "prompt_injection_enabled": False,
            "does_not_access_network": True,
            "does_not_perform_external_network_calls": True,
            "does_not_write_files": True,
            "does_not_call_model": True,
            "stages": list(EXTERNAL_READONLY_EVIDENCE_SUMMARY_STAGES),
            **dict(metadata or {}),
        },
    )


def _validate_external_readonly_evidence_readonly_facts(
    facts: ExternalReadonlyEvidenceReadonlyFacts,
) -> None:
    if facts.status not in EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_STATUSES:
        raise ValueError("status is invalid.")
    if facts.candidate_count < 0:
        raise ValueError("candidate_count must be non-negative.")
    if not facts.readonly:
        raise ValueError("facts.readonly must be true.")
    if not facts.candidate_only:
        raise ValueError("facts.candidate_only must be true.")
    for field_name in (
        "does_not_read_files",
        "does_not_write_files",
        "does_not_call_network",
        "does_not_call_model",
        "does_not_call_runtime",
    ):
        if not getattr(facts, field_name):
            raise ValueError(f"{field_name} must be true.")
    _validate_refs_with_prefix(
        facts.evidence_refs,
        EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
        "facts.evidence_refs",
    )
    if facts.status == "empty":
        if facts.candidate_count != 0:
            raise ValueError("empty facts must have candidate_count 0.")
        if facts.observation_candidate_ids:
            raise ValueError("empty facts must not include candidate ids.")
        if facts.evidence_refs:
            raise ValueError("empty facts must not include evidence refs.")
    _validate_readonly_public_metadata(facts.metadata, "facts.metadata")


def _readonly_public_refs_from_value(
    value: ExternalReadonlyEvidenceReadonlyPublicRefs | Mapping[str, Any],
) -> ExternalReadonlyEvidenceReadonlyPublicRefs:
    if isinstance(value, ExternalReadonlyEvidenceReadonlyPublicRefs):
        return value
    data = _contract_mapping(value)
    facts_value = data.get("facts")
    if facts_value is None:
        facts_value = data.get("external_readonly_evidence_readonly_facts")
    if facts_value is None:
        raise ValueError("facts is required.")
    return build_external_readonly_evidence_readonly_public_refs(
        external_readonly_evidence_observation_refs=_sequence_texts(
            data.get("external_readonly_evidence_observation_refs")
        ),
        external_readonly_evidence_refs=_sequence_texts(
            data.get("external_readonly_evidence_refs")
        ),
        facts=_readonly_facts_from_value(facts_value),
        payload_type=_string_value(
            data.get("payload_type")
            or EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_PAYLOAD_TYPE
        ),
        payload_version=_string_value(
            data.get("payload_version")
            or EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_VERSION
        ),
        readonly=data.get("readonly", True),
        refs_only=data.get("refs_only", True),
        candidate_only=data.get("candidate_only", True),
        metadata=_contract_mapping(data.get("metadata")),
    )


def _readonly_facts_from_value(
    value: ExternalReadonlyEvidenceReadonlyFacts | Mapping[str, Any],
) -> ExternalReadonlyEvidenceReadonlyFacts:
    if isinstance(value, ExternalReadonlyEvidenceReadonlyFacts):
        return value
    data = _contract_mapping(value)
    return build_external_readonly_evidence_readonly_facts(
        observation_candidate_ids=_sequence_texts(
            data.get("observation_candidate_ids")
        ),
        evidence_output_paths=_sequence_texts(data.get("evidence_output_paths")),
        evidence_refs=_sequence_texts(data.get("evidence_refs")),
        source_urls=_sequence_texts(data.get("source_urls")),
        status=_string_value(data.get("status") or "empty"),
        reference_review_ready=data.get("reference_review_ready", False),
        allowed_for_model_context=data.get("allowed_for_model_context", False),
        candidate_count=data.get("candidate_count", 0),
        blocking_reasons=_sequence_texts(data.get("blocking_reasons")),
        warnings=_sequence_texts(data.get("warnings")),
        metadata_keys=_sequence_texts(data.get("metadata_keys")),
        raw_boundary_flags=data.get("raw_boundary_flags"),
        readonly=data.get("readonly", True),
        candidate_only=data.get("candidate_only", True),
        does_not_read_files=data.get("does_not_read_files", True),
        does_not_write_files=data.get("does_not_write_files", True),
        does_not_call_network=data.get("does_not_call_network", True),
        does_not_call_model=data.get("does_not_call_model", True),
        does_not_call_runtime=data.get("does_not_call_runtime", True),
        metadata=_contract_mapping(data.get("metadata")),
    )


def _readonly_raw_boundary_flags(
    value: ExternalReadonlyEvidenceReadonlyRawBoundaryFlags
    | Mapping[str, Any]
    | None,
) -> ExternalReadonlyEvidenceReadonlyRawBoundaryFlags:
    if value is None:
        return ExternalReadonlyEvidenceReadonlyRawBoundaryFlags()
    if isinstance(value, ExternalReadonlyEvidenceReadonlyRawBoundaryFlags):
        flags = value
    else:
        data = _contract_mapping(value)
        flags = ExternalReadonlyEvidenceReadonlyRawBoundaryFlags(
            raw_response_included=data.get("raw_response_included", False),
            raw_html_included=data.get("raw_html_included", False),
            response_headers_included=data.get(
                "response_headers_included",
                False,
            ),
        )
    for field_name in (
        "raw_response_included",
        "raw_html_included",
        "response_headers_included",
    ):
        if not isinstance(getattr(flags, field_name), bool):
            raise ValueError(f"{field_name} must be bool.")
    return flags


def _read_context_status(value: Any) -> str:
    text = str(value).strip().lower() if value is not None else ""
    return text or "empty"


def _read_context_texts(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    return tuple(_ordered_unique_texts(_sequence_texts(value)))


def _read_context_candidate_count(
    context: Mapping[str, Any],
    *,
    evidence_refs: Sequence[str],
) -> int:
    if _read_context_status(context.get("status")) == "empty":
        return 0
    summaries = context.get("summaries")
    if isinstance(summaries, Sequence) and not isinstance(summaries, str):
        return len(summaries)
    return len(evidence_refs)


def _read_context_metadata_keys(context: Mapping[str, Any]) -> tuple[str, ...]:
    metadata = context.get("metadata")
    if not isinstance(metadata, Mapping):
        return ()
    return tuple(
        key
        for key in _read_context_texts(tuple(metadata))
        if not _readonly_public_metadata_key_blocked(key)
    )


def _read_context_raw_boundary_flags(
    context: Mapping[str, Any],
) -> dict[str, bool]:
    summaries = context.get("summaries")
    if not isinstance(summaries, Sequence) or isinstance(summaries, str):
        return {
            "raw_response_included": False,
            "raw_html_included": False,
            "response_headers_included": False,
        }
    summary_mappings = tuple(
        _contract_mapping(summary)
        for summary in summaries
    )
    return {
        "raw_response_included": any(
            summary.get("raw_response_included") is True
            for summary in summary_mappings
        ),
        "raw_html_included": any(
            summary.get("raw_html_included") is True
            for summary in summary_mappings
        ),
        "response_headers_included": any(
            summary.get("response_headers_included") is True
            for summary in summary_mappings
        ),
    }


def _contract_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {
            str(key): item
            for key, item in value.items()
            if isinstance(key, str)
        }
    if is_dataclass(value) and not isinstance(value, type):
        mapped = asdict(value)
        return _contract_mapping(mapped)
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        if isinstance(dumped, Mapping):
            return _contract_mapping(dumped)
    return {}


def _sequence_texts(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence) and not isinstance(value, bytes):
        return tuple(str(item) for item in value if item is not None)
    return ()


def _ordered_unique_texts(values: Sequence[str | None]) -> list[str]:
    return _ordered_unique(
        tuple(value.strip() if isinstance(value, str) else None for value in values)
    )


def _readonly_public_metadata_key_names(
    values: Sequence[str | None],
) -> list[str]:
    allowed: list[str] = []
    for value in _ordered_unique_texts(values):
        normalized = _normalize_key(value)
        if any(
            marker in normalized
            for marker in (
                EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_FORBIDDEN_METADATA_KEY_NAMES
            )
        ):
            continue
        allowed.append(value)
    return allowed


def _compact_readonly_public_metadata(
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in metadata.items():
        if not isinstance(key, str):
            continue
        if _readonly_public_metadata_key_blocked(key):
            continue
        if not isinstance(value, bool | int | float | str):
            continue
        if isinstance(value, str) and _readonly_public_metadata_value_blocked(
            value
        ):
            continue
        compact[key] = value
    return compact


def _validate_readonly_public_metadata(
    metadata: Mapping[str, Any],
    field_name: str,
) -> None:
    for key, value in metadata.items():
        if not isinstance(key, str):
            raise ValueError(f"{field_name} keys must be strings.")
        if _readonly_public_metadata_key_blocked(key):
            raise ValueError(f"{field_name}.{key} is forbidden.")
        if not isinstance(value, bool | int | float | str):
            raise ValueError(f"{field_name}.{key} must be compact scalar.")
        if isinstance(value, str) and _readonly_public_metadata_value_blocked(
            value
        ):
            raise ValueError(f"{field_name}.{key} contains forbidden marker.")


def _readonly_public_metadata_key_blocked(key: str) -> bool:
    normalized = _normalize_key(key)
    return any(
        marker in normalized
        for marker in (
            EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_FORBIDDEN_METADATA_KEYS
        )
    )


def _readonly_public_metadata_value_blocked(value: str) -> bool:
    normalized = value.lower()
    return any(
        marker in normalized
        for marker in (
            EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_FORBIDDEN_METADATA_VALUES
        )
    )


def _validate_refs_with_prefix(
    values: Sequence[str],
    prefix: str,
    field_name: str,
) -> None:
    for value in values:
        if not value.startswith(prefix) or len(value) <= len(prefix):
            raise ValueError(f"{field_name} must use {prefix} refs.")


def _readonly_public_refs_status(value: str) -> str:
    status = _string_value(value)
    if status not in EXTERNAL_READONLY_EVIDENCE_READONLY_PUBLIC_REFS_STATUSES:
        raise ValueError("status is invalid.")
    return status


def _non_negative_candidate_count(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("candidate_count must be non-negative int.")
    try:
        count = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("candidate_count must be non-negative int.") from exc
    if count < 0:
        raise ValueError("candidate_count must be non-negative int.")
    return count


def _required_exact_text(value: str, expected: str, field_name: str) -> str:
    text = _string_value(value)
    if text != expected:
        raise ValueError(f"{field_name} must be {expected}.")
    return text


def _strict_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be bool.")
    return value


def _forbidden_raw_key_paths(payload: Mapping[str, Any]) -> tuple[str, ...]:
    paths: list[str] = []

    def visit(value: Any, path: tuple[str, ...]) -> None:
        if isinstance(value, Mapping):
            for raw_key, raw_value in value.items():
                key = _normalize_key(raw_key)
                next_path = (*path, str(raw_key))
                if key in EXTERNAL_READONLY_EVIDENCE_FORBIDDEN_RAW_KEYS:
                    paths.append(".".join(next_path))
                visit(raw_value, next_path)
        elif isinstance(value, list | tuple):
            for index, item in enumerate(value):
                visit(item, (*path, str(index)))

    visit(payload, ())
    return tuple(_ordered_unique(paths))


def _evidence_ref_allowed(value: str | None) -> bool:
    return value is not None and value.startswith(
        EXTERNAL_READONLY_EVIDENCE_REF_PREFIX
    ) and len(value) > len(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX)


def _external_https_url_allowed(value: str) -> bool:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    host = parsed.hostname.lower()
    if (
        host in {"localhost"}
        or host.endswith(".localhost")
        or host.endswith(".local")
        or host.endswith(".internal")
    ):
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _excerpt_contains_forbidden_marker(value: str) -> bool:
    lower = value.lower()
    return any(
        marker in lower for marker in EXTERNAL_READONLY_EXCERPT_FORBIDDEN_MARKERS
    )


def _string_value(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _first_present_string(*values: Any) -> str:
    for value in values:
        text = _string_value(value)
        if text:
            return text
    return ""


def _first_sequence_string(value: Any) -> str:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return ""
    for item in value:
        text = _string_value(item)
        if text:
            return text
    return ""


def _int_value(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _truthy(value: Any) -> bool:
    return value is True


def _normalize_key(value: Any) -> str:
    return str(value).strip().replace("-", "_").replace(" ", "_").lower()


def _ordered_unique(values: Sequence[str | None]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
