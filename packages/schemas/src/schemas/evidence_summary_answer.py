"""Public evidence summary answer contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


EVIDENCE_SUMMARY_ANSWER_PRODUCT = "evidence_summary_answer"
GOVERNED_EVIDENCE_DIGEST_PAYLOAD_TYPE = "governed_evidence_digest"
GOVERNED_EVIDENCE_DIGEST_VERSION = "governed_evidence_digest_v1"
EVIDENCE_SUMMARY_ANSWER_CONTEXT_PAYLOAD_TYPE = "evidence_summary_answer_context"
EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION = "evidence_summary_answer_context_v1"
EVIDENCE_SUMMARY_ANSWER_RESULT_PAYLOAD_TYPE = "evidence_summary_answer_result"
EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION = "evidence_summary_answer_result_v1"

GOVERNED_EVIDENCE_DIGEST_REF_PREFIX = "governed-evidence-digest://"
EXTERNAL_READONLY_EVIDENCE_REF_PREFIX = "evidence://external-readonly/"
SUMMARY_FACT_MAX_ITEMS = 24
SUMMARY_FACT_MAX_CHARS = 4000
SUMMARY_FACT_ITEM_MAX_CHARS = 500

GovernedEvidenceDigestStatus = Literal["ready", "blocked", "empty"]
GovernedEvidenceAnswerability = Literal[
    "answerable",
    "insufficient_evidence",
    "blocked",
    "unknown",
]
EvidenceSummaryAnswerResultStatus = Literal[
    "success",
    "insufficient_evidence",
    "blocked",
    "failed",
]

GOVERNED_EVIDENCE_DIGEST_STATUSES = frozenset({"ready", "blocked", "empty"})
GOVERNED_EVIDENCE_ANSWERABILITY_VALUES = frozenset(
    {"answerable", "insufficient_evidence", "blocked", "unknown"}
)
EVIDENCE_SUMMARY_ANSWER_RESULT_STATUSES = frozenset(
    {"success", "insufficient_evidence", "blocked", "failed"}
)

FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_KEYS = frozenset(
    {
        "api_key",
        "config_context",
        "config_context_value",
        "content",
        "cookie",
        "credential",
        "credentials",
        "full_product_gateway_response",
        "full_response",
        "message",
        "messages",
        "observability_candidate_body",
        "payload",
        "productgatewayresponse",
        "prompt",
        "provider_payload",
        "provider_response",
        "raw",
        "raw_api_payload",
        "raw_html",
        "raw_input",
        "raw_output",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_provider_response",
        "raw_response",
        "response",
        "response_headers",
        "response_text",
        "sanitized_excerpt_preview",
        "secret",
        "system_prompt",
        "token",
    }
)

FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_OBJECT_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "runtime_container",
    "composition",
    "product_runtime_assembly",
    "litellm",
)

STRING_MARKER_EXEMPT_PATHS = frozenset(
    {
        "$.answer",
        "$.answer_preview",
        "$.insufficient_evidence_reason",
        "$.user_question",
    }
)


class EvidenceSummaryAnswerBaseModel(BaseModel):
    """Base model for evidence summary answer public contracts."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_answer_public_boundary(self) -> "EvidenceSummaryAnswerBaseModel":
        violations = _answer_boundary_violations(self.model_dump(mode="python"))
        if violations:
            raise ValueError("; ".join(violations))
        return self


class EvidenceSummaryAnswerRefSchema(EvidenceSummaryAnswerBaseModel):
    """Sanitized reference carried by evidence summary answer contracts."""

    ref: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1)
    purpose: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceSummaryAnswerRawBoundaryFlagsSchema(EvidenceSummaryAnswerBaseModel):
    """Declared raw boundary facts for evidence summary answer contracts."""

    raw_payload_included: bool = False
    raw_provider_response_included: bool = False
    raw_html_included: bool = False
    response_headers_included: bool = False
    sanitized_excerpt_preview_included: bool = False
    full_product_gateway_response_included: bool = False
    config_context_value_included: bool = False
    observability_candidate_body_included: bool = False
    prompt_or_messages_included: bool = False

    def any_included(self) -> bool:
        """Return whether any forbidden raw boundary was declared present."""

        return any(self.model_dump(mode="python").values())


class GovernedEvidenceDigestSchema(EvidenceSummaryAnswerBaseModel):
    """Model-consumable governed evidence digest contract."""

    product: Literal["evidence_summary_answer"] = EVIDENCE_SUMMARY_ANSWER_PRODUCT
    payload_type: Literal["governed_evidence_digest"] = (
        GOVERNED_EVIDENCE_DIGEST_PAYLOAD_TYPE
    )
    payload_version: Literal["governed_evidence_digest_v1"] = (
        GOVERNED_EVIDENCE_DIGEST_VERSION
    )
    digest_id: str = Field(..., min_length=1)
    digest_ref: str = Field(..., min_length=1)
    evidence_ref: str = Field(..., min_length=1)
    evidence_output_ref: str | None = None
    source_url_host: str | None = None
    source_url_scheme: Literal["https"] | None = None
    runtime_status: str | None = None
    status: GovernedEvidenceDigestStatus
    reference_review_ready: bool
    allowed_for_model_context: bool
    evidence_written: bool
    content_hash: str | None = None
    total_excerpt_chars: int = Field(..., ge=0)
    raw_boundary_flags: EvidenceSummaryAnswerRawBoundaryFlagsSchema = Field(
        default_factory=EvidenceSummaryAnswerRawBoundaryFlagsSchema
    )
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary_facts: list[str] = Field(
        default_factory=list,
        max_length=SUMMARY_FACT_MAX_ITEMS,
    )
    topic_labels: list[str] = Field(default_factory=list)
    risk_labels: list[str] = Field(default_factory=list)
    answerability: GovernedEvidenceAnswerability
    digest_generation_policy_ref: str | None = None
    digest_budget: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_digest(self) -> "GovernedEvidenceDigestSchema":
        if not self.digest_ref.startswith(GOVERNED_EVIDENCE_DIGEST_REF_PREFIX):
            raise ValueError(
                "digest_ref must start with "
                f"{GOVERNED_EVIDENCE_DIGEST_REF_PREFIX!r}."
            )
        if not self.evidence_ref.startswith(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX):
            raise ValueError(
                "evidence_ref must start with "
                f"{EXTERNAL_READONLY_EVIDENCE_REF_PREFIX!r}."
            )
        if self.source_url_host is not None:
            _validate_source_url_host(self.source_url_host)
        if self.status == "blocked" and not self.blocking_reasons:
            raise ValueError("blocked digests require blocking_reasons.")
        if not self.allowed_for_model_context and self.answerability == "answerable":
            raise ValueError(
                "digests not allowed for model context cannot be answerable."
            )
        if self.raw_boundary_flags.any_included() and self.answerability == "answerable":
            raise ValueError(
                "digests with raw boundary flags cannot be answerable."
            )
        if self.answerability == "answerable" and not self.summary_facts:
            raise ValueError("answerable digests require summary_facts.")
        _validate_summary_facts(self.summary_facts)
        return self


class EvidenceSummaryAnswerContextSchema(EvidenceSummaryAnswerBaseModel):
    """Structured input context for evidence summary answer generation."""

    product: Literal["evidence_summary_answer"] = EVIDENCE_SUMMARY_ANSWER_PRODUCT
    payload_type: Literal["evidence_summary_answer_context"] = (
        EVIDENCE_SUMMARY_ANSWER_CONTEXT_PAYLOAD_TYPE
    )
    payload_version: Literal["evidence_summary_answer_context_v1"] = (
        EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION
    )
    request_id: str = Field(..., min_length=1)
    user_question: str = Field(..., min_length=1)
    digests: list[GovernedEvidenceDigestSchema] = Field(default_factory=list)
    evidence_refs: list[EvidenceSummaryAnswerRefSchema] = Field(default_factory=list)
    additional_refs: list[EvidenceSummaryAnswerRefSchema] = Field(default_factory=list)
    answer_policy_ref: str | None = None
    citation_policy_ref: str | None = None
    model_context_budget: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_context(self) -> "EvidenceSummaryAnswerContextSchema":
        if not self.digests:
            raise ValueError("evidence summary answer contexts require digests.")
        digest_evidence_refs = {digest.evidence_ref for digest in self.digests}
        provided_evidence_refs = {ref.ref for ref in self.evidence_refs}
        missing = sorted(digest_evidence_refs - provided_evidence_refs)
        if missing:
            raise ValueError(
                "evidence_refs must cover digest evidence_ref values: "
                + ", ".join(missing)
            )
        return self


class EvidenceSummaryAnswerResultSchema(EvidenceSummaryAnswerBaseModel):
    """Structured result for evidence summary answer generation."""

    product: Literal["evidence_summary_answer"] = EVIDENCE_SUMMARY_ANSWER_PRODUCT
    payload_type: Literal["evidence_summary_answer_result"] = (
        EVIDENCE_SUMMARY_ANSWER_RESULT_PAYLOAD_TYPE
    )
    payload_version: Literal["evidence_summary_answer_result_v1"] = (
        EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION
    )
    request_id: str = Field(..., min_length=1)
    status: EvidenceSummaryAnswerResultStatus
    answer: str | None = None
    answer_preview: str | None = None
    evidence_refs_used: list[EvidenceSummaryAnswerRefSchema] = Field(
        default_factory=list
    )
    digest_refs_used: list[str] = Field(default_factory=list)
    additional_refs_used: list[EvidenceSummaryAnswerRefSchema] = Field(
        default_factory=list
    )
    insufficient_evidence_reason: str | None = None
    citation_failures: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    llm_call_allowed: bool = False
    llm_call_attempted: bool = False
    llm_runtime_call_performed: bool = False
    raw_boundary_flags: EvidenceSummaryAnswerRawBoundaryFlagsSchema = Field(
        default_factory=EvidenceSummaryAnswerRawBoundaryFlagsSchema
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_result(self) -> "EvidenceSummaryAnswerResultSchema":
        if self.status == "success":
            if not self.answer:
                raise ValueError("successful answer results require answer.")
            if not self.evidence_refs_used:
                raise ValueError(
                    "successful answer results require evidence_refs_used."
                )
            if self.raw_boundary_flags.any_included():
                raise ValueError(
                    "successful answer results cannot include raw boundary flags."
                )
        if self.status == "insufficient_evidence" and (
            not self.insufficient_evidence_reason
        ):
            raise ValueError(
                "insufficient_evidence results require insufficient_evidence_reason."
            )
        if self.status == "blocked" and not self.blocking_reasons:
            raise ValueError("blocked answer results require blocking_reasons.")
        if self.status == "failed" and not (
            self.blocking_reasons or self.citation_failures
        ):
            raise ValueError(
                "failed answer results require blocking_reasons or citation_failures."
            )
        if self.llm_runtime_call_performed and not (
            self.llm_call_allowed and self.llm_call_attempted
        ):
            raise ValueError(
                "llm_runtime_call_performed requires llm_call_allowed and "
                "llm_call_attempted."
            )
        return self


def validate_governed_evidence_digest(
    digest: dict[str, Any],
) -> GovernedEvidenceDigestSchema:
    """Validate a plain dict as a governed evidence digest contract."""

    return GovernedEvidenceDigestSchema.model_validate(digest)


def validate_evidence_summary_answer_context(
    context: dict[str, Any],
) -> EvidenceSummaryAnswerContextSchema:
    """Validate a plain dict as an evidence summary answer context contract."""

    return EvidenceSummaryAnswerContextSchema.model_validate(context)


def validate_evidence_summary_answer_result(
    result: dict[str, Any],
) -> EvidenceSummaryAnswerResultSchema:
    """Validate a plain dict as an evidence summary answer result contract."""

    return EvidenceSummaryAnswerResultSchema.model_validate(result)


def _validate_source_url_host(source_url_host: str) -> None:
    if not source_url_host.strip():
        raise ValueError("source_url_host cannot be blank.")
    forbidden_host_chars = ("://", "/", "?", "#", "@", ":")
    if any(marker in source_url_host for marker in forbidden_host_chars):
        raise ValueError("source_url_host must be a host without path or query.")


def _validate_summary_facts(summary_facts: list[str]) -> None:
    total_chars = 0
    for index, fact in enumerate(summary_facts):
        if not fact.strip():
            raise ValueError(f"summary_facts[{index}] cannot be blank.")
        if len(fact) > SUMMARY_FACT_ITEM_MAX_CHARS:
            raise ValueError(
                f"summary_facts[{index}] exceeds "
                f"{SUMMARY_FACT_ITEM_MAX_CHARS} characters."
            )
        if _looks_like_forbidden_answer_marker(fact):
            raise ValueError(
                f"summary_facts[{index}] contains forbidden raw boundary marker."
            )
        total_chars += len(fact)
    if total_chars > SUMMARY_FACT_MAX_CHARS:
        raise ValueError(
            f"summary_facts total exceeds {SUMMARY_FACT_MAX_CHARS} characters."
        )


def _answer_boundary_violations(value: Any, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}"
            if _is_forbidden_answer_key(str(key)):
                violations.append(f"raw or sensitive field is forbidden at {key_path}")
            if key == "object_module" and isinstance(item, str) and _is_runtime_module(
                item
            ):
                violations.append(f"runtime object module is forbidden at {key_path}")
            violations.extend(_answer_boundary_violations(item, key_path))
        return violations
    if isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(_answer_boundary_violations(item, f"{path}[{index}]"))
        return violations
    if _is_runtime_object(value):
        violations.append(f"runtime object is forbidden at {path}")
    if (
        isinstance(value, str)
        and path not in STRING_MARKER_EXEMPT_PATHS
        and _looks_like_forbidden_answer_marker(value)
    ):
        violations.append(f"raw boundary marker is forbidden at {path}")
    return violations


def _is_forbidden_answer_key(key: str) -> bool:
    lowered = key.lower()
    return (
        lowered in FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_KEYS
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


def _looks_like_forbidden_answer_marker(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in (
            "api_key",
            "config_context",
            "config context value",
            "full productgatewayresponse",
            "full_product_gateway_response",
            "observability_candidate_body",
            "prompt_or_messages",
            "raw html",
            "raw payload",
            "raw provider response",
            "raw_payload",
            "raw_provider_response",
            "response_headers",
            "response_text",
            "sanitized_excerpt_preview",
            "system_prompt",
        )
    )


__all__ = [
    "EVIDENCE_SUMMARY_ANSWER_CONTEXT_PAYLOAD_TYPE",
    "EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION",
    "EVIDENCE_SUMMARY_ANSWER_PRODUCT",
    "EVIDENCE_SUMMARY_ANSWER_RESULT_PAYLOAD_TYPE",
    "EVIDENCE_SUMMARY_ANSWER_RESULT_STATUSES",
    "EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION",
    "EXTERNAL_READONLY_EVIDENCE_REF_PREFIX",
    "FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_KEYS",
    "FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_OBJECT_MODULE_PREFIXES",
    "GOVERNED_EVIDENCE_ANSWERABILITY_VALUES",
    "GOVERNED_EVIDENCE_DIGEST_PAYLOAD_TYPE",
    "GOVERNED_EVIDENCE_DIGEST_REF_PREFIX",
    "GOVERNED_EVIDENCE_DIGEST_STATUSES",
    "GOVERNED_EVIDENCE_DIGEST_VERSION",
    "SUMMARY_FACT_ITEM_MAX_CHARS",
    "SUMMARY_FACT_MAX_CHARS",
    "SUMMARY_FACT_MAX_ITEMS",
    "EvidenceSummaryAnswerContextSchema",
    "EvidenceSummaryAnswerRawBoundaryFlagsSchema",
    "EvidenceSummaryAnswerRefSchema",
    "EvidenceSummaryAnswerResultSchema",
    "EvidenceSummaryAnswerResultStatus",
    "GovernedEvidenceAnswerability",
    "GovernedEvidenceDigestSchema",
    "GovernedEvidenceDigestStatus",
    "validate_evidence_summary_answer_context",
    "validate_evidence_summary_answer_result",
    "validate_governed_evidence_digest",
]
