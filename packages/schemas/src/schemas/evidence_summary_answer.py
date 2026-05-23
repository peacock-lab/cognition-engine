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
EVIDENCE_SUMMARY_ANSWER_TRACE_PAYLOAD_TYPE = "evidence_summary_answer_trace"
EVIDENCE_SUMMARY_ANSWER_TRACE_VERSION = "evidence_summary_answer_trace_v1"
EVIDENCE_SUMMARY_ANSWER_ARTIFACT_PAYLOAD_TYPE = "evidence_summary_answer_artifact"
EVIDENCE_SUMMARY_ANSWER_ARTIFACT_VERSION = "evidence_summary_answer_artifact_v1"
EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SEED_PAYLOAD_TYPE = (
    "evidence_summary_answer_follow_up_seed"
)
EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SEED_VERSION = (
    "evidence_summary_answer_follow_up_seed_v1"
)

GOVERNED_EVIDENCE_DIGEST_REF_PREFIX = "governed-evidence-digest://"
EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_REF_PREFIX = (
    "evidence-summary-answer-follow-up://"
)
EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX = "evidence-summary-answer-trace://"
EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX = (
    "evidence-summary-answer-artifact://"
)
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


class EvidenceSummaryAnswerFollowUpSeedSchema(EvidenceSummaryAnswerBaseModel):
    """Same-process follow-up seed for an evidence summary answer result."""

    product: Literal["evidence_summary_answer"] = EVIDENCE_SUMMARY_ANSWER_PRODUCT
    payload_type: Literal["evidence_summary_answer_follow_up_seed"] = (
        EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SEED_PAYLOAD_TYPE
    )
    payload_version: Literal["evidence_summary_answer_follow_up_seed_v1"] = (
        EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SEED_VERSION
    )
    seed_id: str = Field(..., min_length=1)
    seed_ref: str = Field(..., min_length=1)
    source_request_id: str = Field(..., min_length=1)
    source_result_status: EvidenceSummaryAnswerResultStatus
    digest_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceSummaryAnswerRefSchema] = Field(default_factory=list)
    additional_refs: list[EvidenceSummaryAnswerRefSchema] = Field(
        default_factory=list
    )
    follow_up_allowed: bool = False
    temporary_only: bool = True
    durable_session: bool = False
    memory_enabled: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_follow_up_seed(self) -> "EvidenceSummaryAnswerFollowUpSeedSchema":
        if not self.seed_ref.startswith(EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_REF_PREFIX):
            raise ValueError(
                "seed_ref must start with "
                f"{EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_REF_PREFIX!r}."
            )
        if self.temporary_only is not True:
            raise ValueError("follow-up seeds are current-process temporary only.")
        if self.durable_session:
            raise ValueError("follow-up seeds must not declare durable session use.")
        if self.memory_enabled:
            raise ValueError("follow-up seeds must not declare Memory runtime use.")
        for index, digest_ref in enumerate(self.digest_refs):
            if not digest_ref.startswith(GOVERNED_EVIDENCE_DIGEST_REF_PREFIX):
                raise ValueError(
                    f"digest_refs[{index}] must start with "
                    f"{GOVERNED_EVIDENCE_DIGEST_REF_PREFIX!r}."
                )
        for index, ref in enumerate(self.evidence_refs):
            if not ref.ref.startswith(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX):
                raise ValueError(
                    f"evidence_refs[{index}].ref must start with "
                    f"{EXTERNAL_READONLY_EVIDENCE_REF_PREFIX!r}."
                )
        if self.follow_up_allowed:
            if self.source_result_status != "success":
                raise ValueError("follow-up requires a successful source result.")
            if not self.digest_refs:
                raise ValueError("follow-up requires digest_refs.")
            if not self.evidence_refs:
                raise ValueError("follow-up requires evidence_refs.")
            if self.blocking_reasons:
                raise ValueError("allowed follow-up seeds must not carry blockers.")
        return self


class EvidenceSummaryAnswerTraceSchema(EvidenceSummaryAnswerBaseModel):
    """Product-level trace facts for one evidence summary answer turn."""

    product: Literal["evidence_summary_answer"] = EVIDENCE_SUMMARY_ANSWER_PRODUCT
    payload_type: Literal["evidence_summary_answer_trace"] = (
        EVIDENCE_SUMMARY_ANSWER_TRACE_PAYLOAD_TYPE
    )
    payload_version: Literal["evidence_summary_answer_trace_v1"] = (
        EVIDENCE_SUMMARY_ANSWER_TRACE_VERSION
    )
    trace_id: str = Field(..., min_length=1)
    trace_ref: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    answer_status: EvidenceSummaryAnswerResultStatus
    readonly_refs_status: str | None = None
    evidence_ref_count: int = Field(default=0, ge=0)
    additional_ref_count: int = Field(default=0, ge=0)
    digest_ref_count: int = Field(default=0, ge=0)
    evidence_refs: list[EvidenceSummaryAnswerRefSchema] = Field(default_factory=list)
    additional_refs: list[EvidenceSummaryAnswerRefSchema] = Field(default_factory=list)
    digest_refs: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    insufficient_evidence_reason: str | None = None
    citation_failures: list[str] = Field(default_factory=list)
    llm_call_allowed: bool = False
    llm_call_attempted: bool = False
    llm_runtime_call_performed: bool = False
    llm_route_provider: str | None = None
    llm_route_model: str | None = None
    provider_profile_ref: str | None = None
    model_profile_ref: str | None = None
    output_governance_profile_ref: str | None = None
    answerability_preflight_applied: bool = False
    answerability_preflight_reason: str | None = None
    answer_ref: str | None = None
    answer_preview: str | None = None
    follow_up: bool = False
    follow_up_turn_index: int | None = Field(default=None, ge=1)
    follow_up_seed_ref: str | None = None
    temporary_follow_up: bool = True
    durable_session: bool = False
    memory_enabled: bool = False
    task_compatible: bool = True
    workflow_compatible: bool = True
    backed_by_adk_task_runtime: bool = False
    backed_by_adk_workflow_runtime: bool = False
    raw_boundary_flags: EvidenceSummaryAnswerRawBoundaryFlagsSchema = Field(
        default_factory=EvidenceSummaryAnswerRawBoundaryFlagsSchema
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_trace(self) -> "EvidenceSummaryAnswerTraceSchema":
        if not self.trace_ref.startswith(EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX):
            raise ValueError(
                "trace_ref must start with "
                f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX!r}."
            )
        if self.evidence_ref_count != len(self.evidence_refs):
            raise ValueError("evidence_ref_count must match evidence_refs length.")
        if self.additional_ref_count != len(self.additional_refs):
            raise ValueError("additional_ref_count must match additional_refs length.")
        if self.digest_ref_count != len(self.digest_refs):
            raise ValueError("digest_ref_count must match digest_refs length.")
        for index, digest_ref in enumerate(self.digest_refs):
            if not digest_ref.startswith(GOVERNED_EVIDENCE_DIGEST_REF_PREFIX):
                raise ValueError(
                    f"digest_refs[{index}] must start with "
                    f"{GOVERNED_EVIDENCE_DIGEST_REF_PREFIX!r}."
                )
        for index, ref in enumerate(self.evidence_refs):
            if not ref.ref.startswith(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX):
                raise ValueError(
                    f"evidence_refs[{index}].ref must start with "
                    f"{EXTERNAL_READONLY_EVIDENCE_REF_PREFIX!r}."
                )
        if self.answer_status == "success" and not self.evidence_refs:
            raise ValueError("successful answer traces require evidence_refs.")
        if self.answer_status == "insufficient_evidence" and (
            not self.insufficient_evidence_reason
        ):
            raise ValueError(
                "insufficient_evidence traces require insufficient_evidence_reason."
            )
        if self.answer_status == "blocked" and not self.blocking_reasons:
            raise ValueError("blocked answer traces require blocking_reasons.")
        if self.answer_status == "failed" and not (
            self.blocking_reasons or self.citation_failures
        ):
            raise ValueError(
                "failed answer traces require blocking_reasons or citation_failures."
            )
        if self.llm_runtime_call_performed and not (
            self.llm_call_allowed and self.llm_call_attempted
        ):
            raise ValueError(
                "llm_runtime_call_performed requires llm_call_allowed and "
                "llm_call_attempted."
            )
        if self.follow_up:
            if self.temporary_follow_up is not True:
                raise ValueError("follow-up traces are current-process temporary only.")
            if self.follow_up_turn_index is None:
                raise ValueError("follow-up traces require follow_up_turn_index.")
        if self.durable_session:
            raise ValueError("answer traces must not declare durable session use.")
        if self.memory_enabled:
            raise ValueError("answer traces must not declare Memory runtime use.")
        if self.backed_by_adk_task_runtime:
            raise ValueError("answer traces are not backed by ADK Task runtime.")
        if self.backed_by_adk_workflow_runtime:
            raise ValueError("answer traces are not backed by ADK Workflow Runtime.")
        if self.task_compatible is not True:
            raise ValueError("answer traces must remain Task-compatible.")
        if self.workflow_compatible is not True:
            raise ValueError("answer traces must remain Workflow-compatible.")
        if self.raw_boundary_flags.any_included():
            raise ValueError("answer traces must not include raw boundary flags.")
        return self


class EvidenceSummaryAnswerArtifactSchema(EvidenceSummaryAnswerBaseModel):
    """Product-level answer artifact facts for a reviewable answer turn."""

    product: Literal["evidence_summary_answer"] = EVIDENCE_SUMMARY_ANSWER_PRODUCT
    payload_type: Literal["evidence_summary_answer_artifact"] = (
        EVIDENCE_SUMMARY_ANSWER_ARTIFACT_PAYLOAD_TYPE
    )
    payload_version: Literal["evidence_summary_answer_artifact_v1"] = (
        EVIDENCE_SUMMARY_ANSWER_ARTIFACT_VERSION
    )
    artifact_id: str = Field(..., min_length=1)
    artifact_ref: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    answer_status: EvidenceSummaryAnswerResultStatus
    artifact_status: EvidenceSummaryAnswerResultStatus
    trace_ref: str = Field(..., min_length=1)
    artifact_policy_ref: str = Field(..., min_length=1)
    evidence_ref_count: int = Field(default=0, ge=0)
    additional_ref_count: int = Field(default=0, ge=0)
    digest_ref_count: int = Field(default=0, ge=0)
    evidence_refs: list[EvidenceSummaryAnswerRefSchema] = Field(default_factory=list)
    additional_refs: list[EvidenceSummaryAnswerRefSchema] = Field(default_factory=list)
    digest_refs: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    insufficient_evidence_reason: str | None = None
    citation_failures: list[str] = Field(default_factory=list)
    llm_call_allowed: bool = False
    llm_call_attempted: bool = False
    llm_runtime_call_performed: bool = False
    llm_route_provider: str | None = None
    llm_route_model: str | None = None
    provider_profile_ref: str | None = None
    model_profile_ref: str | None = None
    output_governance_profile_ref: str | None = None
    answerability_preflight_applied: bool = False
    answerability_preflight_reason: str | None = None
    answer_ref: str | None = None
    answer: str | None = None
    answer_preview: str | None = None
    export_allowed: bool = False
    delete_supported: bool = True
    retention_policy_ref: str | None = None
    durable_session: bool = False
    memory_enabled: bool = False
    task_compatible: bool = True
    workflow_compatible: bool = True
    backed_by_adk_task_runtime: bool = False
    backed_by_adk_workflow_runtime: bool = False
    raw_boundary_flags: EvidenceSummaryAnswerRawBoundaryFlagsSchema = Field(
        default_factory=EvidenceSummaryAnswerRawBoundaryFlagsSchema
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_artifact(self) -> "EvidenceSummaryAnswerArtifactSchema":
        if not self.artifact_ref.startswith(
            EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX
        ):
            raise ValueError(
                "artifact_ref must start with "
                f"{EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX!r}."
            )
        if self.artifact_status != self.answer_status:
            raise ValueError("artifact_status must match answer_status.")
        if not self.trace_ref.startswith(EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX):
            raise ValueError(
                "trace_ref must start with "
                f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX!r}."
            )
        if not self.artifact_policy_ref.startswith("policy://"):
            raise ValueError("artifact_policy_ref must be a policy ref.")
        if self.evidence_ref_count != len(self.evidence_refs):
            raise ValueError("evidence_ref_count must match evidence_refs length.")
        if self.additional_ref_count != len(self.additional_refs):
            raise ValueError("additional_ref_count must match additional_refs length.")
        if self.digest_ref_count != len(self.digest_refs):
            raise ValueError("digest_ref_count must match digest_refs length.")
        for index, digest_ref in enumerate(self.digest_refs):
            if not digest_ref.startswith(GOVERNED_EVIDENCE_DIGEST_REF_PREFIX):
                raise ValueError(
                    f"digest_refs[{index}] must start with "
                    f"{GOVERNED_EVIDENCE_DIGEST_REF_PREFIX!r}."
                )
        for index, ref in enumerate(self.evidence_refs):
            if not ref.ref.startswith(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX):
                raise ValueError(
                    f"evidence_refs[{index}].ref must start with "
                    f"{EXTERNAL_READONLY_EVIDENCE_REF_PREFIX!r}."
                )
        if self.answer_status == "success":
            if not self.evidence_refs:
                raise ValueError("successful answer artifacts require evidence_refs.")
            if not (self.answer or self.answer_preview):
                raise ValueError(
                    "successful answer artifacts require answer or answer_preview."
                )
        if self.answer_status == "insufficient_evidence" and (
            not self.insufficient_evidence_reason
        ):
            raise ValueError(
                "insufficient_evidence artifacts require "
                "insufficient_evidence_reason."
            )
        if self.answer_status == "blocked" and not self.blocking_reasons:
            raise ValueError("blocked answer artifacts require blocking_reasons.")
        if self.answer_status == "failed" and not (
            self.blocking_reasons or self.citation_failures
        ):
            raise ValueError(
                "failed answer artifacts require blocking_reasons or "
                "citation_failures."
            )
        if self.llm_runtime_call_performed and not (
            self.llm_call_allowed and self.llm_call_attempted
        ):
            raise ValueError(
                "llm_runtime_call_performed requires llm_call_allowed and "
                "llm_call_attempted."
            )
        if self.durable_session:
            raise ValueError("answer artifacts must not declare durable session use.")
        if self.memory_enabled:
            raise ValueError("answer artifacts must not declare Memory runtime use.")
        if self.backed_by_adk_task_runtime:
            raise ValueError(
                "answer artifacts are not backed by ADK Task runtime."
            )
        if self.backed_by_adk_workflow_runtime:
            raise ValueError(
                "answer artifacts are not backed by ADK Workflow Runtime."
            )
        if self.task_compatible is not True:
            raise ValueError("answer artifacts must remain Task-compatible.")
        if self.workflow_compatible is not True:
            raise ValueError("answer artifacts must remain Workflow-compatible.")
        if self.raw_boundary_flags.any_included():
            raise ValueError("answer artifacts must not include raw boundary flags.")
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


def validate_evidence_summary_answer_follow_up_seed(
    seed: dict[str, Any],
) -> EvidenceSummaryAnswerFollowUpSeedSchema:
    """Validate a plain dict as an evidence summary answer follow-up seed."""

    return EvidenceSummaryAnswerFollowUpSeedSchema.model_validate(seed)


def validate_evidence_summary_answer_trace(
    trace: dict[str, Any],
) -> EvidenceSummaryAnswerTraceSchema:
    """Validate a plain dict as an evidence summary answer trace."""

    return EvidenceSummaryAnswerTraceSchema.model_validate(trace)


def validate_evidence_summary_answer_artifact(
    artifact: dict[str, Any],
) -> EvidenceSummaryAnswerArtifactSchema:
    """Validate a plain dict as an evidence summary answer artifact."""

    return EvidenceSummaryAnswerArtifactSchema.model_validate(artifact)


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
    "EVIDENCE_SUMMARY_ANSWER_ARTIFACT_PAYLOAD_TYPE",
    "EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX",
    "EVIDENCE_SUMMARY_ANSWER_ARTIFACT_VERSION",
    "EVIDENCE_SUMMARY_ANSWER_CONTEXT_PAYLOAD_TYPE",
    "EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION",
    "EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_REF_PREFIX",
    "EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SEED_PAYLOAD_TYPE",
    "EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SEED_VERSION",
    "EVIDENCE_SUMMARY_ANSWER_PRODUCT",
    "EVIDENCE_SUMMARY_ANSWER_RESULT_PAYLOAD_TYPE",
    "EVIDENCE_SUMMARY_ANSWER_RESULT_STATUSES",
    "EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION",
    "EVIDENCE_SUMMARY_ANSWER_TRACE_PAYLOAD_TYPE",
    "EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX",
    "EVIDENCE_SUMMARY_ANSWER_TRACE_VERSION",
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
    "EvidenceSummaryAnswerArtifactSchema",
    "EvidenceSummaryAnswerFollowUpSeedSchema",
    "EvidenceSummaryAnswerRawBoundaryFlagsSchema",
    "EvidenceSummaryAnswerRefSchema",
    "EvidenceSummaryAnswerResultSchema",
    "EvidenceSummaryAnswerResultStatus",
    "EvidenceSummaryAnswerTraceSchema",
    "GovernedEvidenceAnswerability",
    "GovernedEvidenceDigestSchema",
    "GovernedEvidenceDigestStatus",
    "validate_evidence_summary_answer_artifact",
    "validate_evidence_summary_answer_context",
    "validate_evidence_summary_answer_follow_up_seed",
    "validate_evidence_summary_answer_result",
    "validate_evidence_summary_answer_trace",
    "validate_governed_evidence_digest",
]
