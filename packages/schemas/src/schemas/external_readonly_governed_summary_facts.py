"""Public governed summary facts contracts for external-readonly evidence."""

from __future__ import annotations

import re
from string import hexdigits
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.evidence_summary_answer import (
    EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
    FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_KEYS,
    FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_OBJECT_MODULE_PREFIXES,
    SUMMARY_FACT_ITEM_MAX_CHARS,
    SUMMARY_FACT_MAX_CHARS,
    SUMMARY_FACT_MAX_ITEMS,
)


EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE = (
    "external_readonly_governed_summary_facts"
)
EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION = (
    "external_readonly_governed_summary_facts_v1"
)
EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX = (
    "external-readonly-governed-summary-fact://"
)

ExternalReadonlyGovernedSummaryFactsStatus = Literal["ready", "blocked", "empty"]

EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_STATUSES = frozenset(
    {"ready", "blocked", "empty"}
)
EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_EXTRA_FORBIDDEN_KEYS = frozenset(
    {
        "authorization",
        "auth_header",
        "auth_headers",
        "password",
        "sanitized_excerpt",
        "set_cookie",
    }
)


class ExternalReadonlyGovernedSummaryFactsBaseModel(BaseModel):
    """Base model for governed summary facts public contracts."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_governed_summary_facts_boundary(
        self,
    ) -> "ExternalReadonlyGovernedSummaryFactsBaseModel":
        violations = _boundary_violations(self.model_dump(mode="python"))
        if violations:
            raise ValueError("; ".join(violations))
        return self


class ExternalReadonlyGovernedSummaryFactsRawBoundaryFlagsSchema(
    ExternalReadonlyGovernedSummaryFactsBaseModel
):
    """Declared raw boundary facts for governed summary facts."""

    raw_payload_included: Literal[False] = False
    raw_provider_response_included: Literal[False] = False
    raw_html_included: Literal[False] = False
    response_headers_included: Literal[False] = False
    sanitized_excerpt_preview_included: Literal[False] = False
    full_product_gateway_response_included: Literal[False] = False
    config_context_value_included: Literal[False] = False
    observability_candidate_body_included: Literal[False] = False
    prompt_or_messages_included: Literal[False] = False

    def any_included(self) -> bool:
        """Return whether any forbidden raw boundary was declared present."""

        return any(self.model_dump(mode="python").values())


class ExternalReadonlyGovernedSummaryFactSchema(
    ExternalReadonlyGovernedSummaryFactsBaseModel
):
    """One model-consumable governed fact derived from external-readonly evidence."""

    fact_ref: str = Field(..., min_length=1)
    fact_text: str = Field(..., min_length=1, max_length=SUMMARY_FACT_ITEM_MAX_CHARS)
    fact_index: int = Field(..., ge=1)
    evidence_ref: str = Field(..., min_length=1)
    source_url_host: str | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_fact(self) -> "ExternalReadonlyGovernedSummaryFactSchema":
        if not self.fact_ref.startswith(EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX):
            raise ValueError(
                "fact_ref must start with "
                f"{EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX!r}."
            )
        if not self.fact_text.strip():
            raise ValueError("fact_text cannot be blank.")
        if not self.evidence_ref.startswith(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX):
            raise ValueError(
                "evidence_ref must start with "
                f"{EXTERNAL_READONLY_EVIDENCE_REF_PREFIX!r}."
            )
        if self.source_url_host is not None:
            _validate_source_url_host(self.source_url_host)
        if self.content_hash is not None:
            _validate_content_hash(self.content_hash)
        return self


class ExternalReadonlyGovernedSummaryFactsSchema(
    ExternalReadonlyGovernedSummaryFactsBaseModel
):
    """Model-consumable governed facts bundle for external-readonly evidence."""

    payload_type: Literal["external_readonly_governed_summary_facts"] = (
        EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE
    )
    payload_version: Literal["external_readonly_governed_summary_facts_v1"] = (
        EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION
    )
    status: ExternalReadonlyGovernedSummaryFactsStatus
    evidence_ref: str = Field(..., min_length=1)
    evidence_output_path: str | None = None
    source_url_host: str | None = None
    source_url_scheme: Literal["https"] | None = None
    reference_review_ready: bool = False
    allowed_for_model_context: bool = False
    evidence_written: bool = False
    content_hash: str | None = None
    facts: list[ExternalReadonlyGovernedSummaryFactSchema] = Field(
        default_factory=list,
        max_length=SUMMARY_FACT_MAX_ITEMS,
    )
    fact_count: int = Field(default=0, ge=0, le=SUMMARY_FACT_MAX_ITEMS)
    total_fact_chars: int = Field(default=0, ge=0, le=SUMMARY_FACT_MAX_CHARS)
    raw_boundary_flags: ExternalReadonlyGovernedSummaryFactsRawBoundaryFlagsSchema = (
        Field(default_factory=ExternalReadonlyGovernedSummaryFactsRawBoundaryFlagsSchema)
    )
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generation_policy_ref: str | None = None
    facts_budget: int = Field(
        default=SUMMARY_FACT_MAX_CHARS,
        ge=1,
        le=SUMMARY_FACT_MAX_CHARS,
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_facts_bundle(self) -> "ExternalReadonlyGovernedSummaryFactsSchema":
        if not self.evidence_ref.startswith(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX):
            raise ValueError(
                "evidence_ref must start with "
                f"{EXTERNAL_READONLY_EVIDENCE_REF_PREFIX!r}."
            )
        if self.source_url_host is not None:
            _validate_source_url_host(self.source_url_host)
        if self.content_hash is not None:
            _validate_content_hash(self.content_hash)
        if self.raw_boundary_flags.any_included():
            raise ValueError("raw_boundary_flags must all be false.")

        if self.fact_count != len(self.facts):
            raise ValueError("fact_count must equal the number of facts.")
        actual_total_fact_chars = sum(len(fact.fact_text) for fact in self.facts)
        if self.total_fact_chars != actual_total_fact_chars:
            raise ValueError("total_fact_chars must equal facts text length total.")
        if self.total_fact_chars > self.facts_budget:
            raise ValueError("total_fact_chars must not exceed facts_budget.")

        fact_refs: set[str] = set()
        for index, fact in enumerate(self.facts, start=1):
            if fact.fact_index != index:
                raise ValueError("fact_index values must be consecutive from 1.")
            if fact.fact_ref in fact_refs:
                raise ValueError("fact_ref values must be unique.")
            fact_refs.add(fact.fact_ref)
            if fact.evidence_ref != self.evidence_ref:
                raise ValueError("facts must use the bundle evidence_ref.")
            if (
                self.source_url_host is not None
                and fact.source_url_host is not None
                and fact.source_url_host != self.source_url_host
            ):
                raise ValueError("fact source_url_host must match bundle source_url_host.")
            if (
                self.content_hash is not None
                and fact.content_hash is not None
                and fact.content_hash != self.content_hash
            ):
                raise ValueError("fact content_hash must match bundle content_hash.")

        if self.status == "ready":
            if not self.reference_review_ready:
                raise ValueError("ready facts require reference_review_ready=true.")
            if not self.evidence_written:
                raise ValueError("ready facts require evidence_written=true.")
            if not self.facts:
                raise ValueError("ready facts require at least one fact.")
        elif self.status == "blocked":
            if not _has_nonempty_string_item(self.blocking_reasons):
                raise ValueError("blocked facts require blocking_reasons.")
            if self.allowed_for_model_context:
                raise ValueError("blocked facts cannot be allowed for model context.")
        elif self.status == "empty":
            if self.facts or self.fact_count or self.total_fact_chars:
                raise ValueError("empty facts must not carry fact content.")
            if self.allowed_for_model_context:
                raise ValueError("empty facts cannot be allowed for model context.")

        if self.allowed_for_model_context and self.status != "ready":
            raise ValueError("model context is only allowed for ready facts.")
        return self


def validate_external_readonly_governed_summary_facts(
    payload: dict[str, Any],
) -> ExternalReadonlyGovernedSummaryFactsSchema:
    """Validate a plain dict as governed summary facts."""

    return ExternalReadonlyGovernedSummaryFactsSchema.model_validate(payload)


def _validate_source_url_host(source_url_host: str) -> None:
    if not source_url_host.strip():
        raise ValueError("source_url_host cannot be blank.")
    forbidden_host_chars = ("://", "/", "?", "#", "@", ":")
    if any(marker in source_url_host for marker in forbidden_host_chars):
        raise ValueError("source_url_host must be a host without path or query.")


def _validate_content_hash(content_hash: str) -> None:
    if len(content_hash) != 64 or any(char not in hexdigits for char in content_hash):
        raise ValueError("content_hash must be a sha256 hex digest.")


def _has_nonempty_string_item(value: list[str]) -> bool:
    return any(isinstance(item, str) and bool(item.strip()) for item in value)


def _boundary_violations(value: Any, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}"
            if _is_forbidden_key(str(key)):
                violations.append(f"raw or sensitive field is forbidden at {key_path}")
            if key == "object_module" and isinstance(item, str) and _is_runtime_module(
                item
            ):
                violations.append(f"runtime object module is forbidden at {key_path}")
            violations.extend(_boundary_violations(item, key_path))
        return violations
    if isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(_boundary_violations(item, f"{path}[{index}]"))
        return violations
    if _is_runtime_object(value):
        violations.append(f"runtime object is forbidden at {path}")
    if isinstance(value, str) and _looks_like_forbidden_marker(value):
        violations.append(f"raw boundary marker is forbidden at {path}")
    return violations


def _is_forbidden_key(key: str) -> bool:
    lowered = key.lower()
    return (
        lowered in FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_KEYS
        or lowered in EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_EXTRA_FORBIDDEN_KEYS
        or lowered.endswith("_token")
        or lowered.endswith("_credential")
        or lowered.endswith("_secret")
    )


def _is_runtime_object(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool, dict, list, tuple)):
        return False
    return _is_runtime_module(type(value).__module__)


def _is_runtime_module(module_name: str) -> bool:
    return module_name.startswith(FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_OBJECT_MODULE_PREFIXES)


def _looks_like_forbidden_marker(value: str) -> bool:
    lowered = value.lower()
    if any(
        marker in lowered
        for marker in (
            "config context value",
            "full productgatewayresponse",
            "raw html",
            "raw payload",
            "raw provider response",
            "set-cookie",
        )
    ):
        return True
    return any(
        _contains_forbidden_token(lowered, marker)
        for marker in (
            "api_key",
            "authorization",
            "config_context",
            "full_product_gateway_response",
            "observability_candidate_body",
            "prompt_or_messages",
            "raw_payload",
            "raw_provider_response",
            "response_headers",
            "response_text",
            "sanitized_excerpt",
            "sanitized_excerpt_preview",
            "system_prompt",
        )
    )


def _contains_forbidden_token(value: str, marker: str) -> bool:
    pattern = rf"(?<![a-z0-9_]){re.escape(marker)}(?![a-z0-9_])"
    return re.search(pattern, value) is not None


__all__ = [
    "EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE",
    "EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_STATUSES",
    "EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION",
    "EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX",
    "ExternalReadonlyGovernedSummaryFactSchema",
    "ExternalReadonlyGovernedSummaryFactsRawBoundaryFlagsSchema",
    "ExternalReadonlyGovernedSummaryFactsSchema",
    "ExternalReadonlyGovernedSummaryFactsStatus",
    "validate_external_readonly_governed_summary_facts",
]
