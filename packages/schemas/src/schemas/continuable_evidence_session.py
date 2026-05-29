"""Public continuable evidence session product contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CONTINUABLE_EVIDENCE_SESSION_PRODUCT = "continuable_evidence_session"
CONTINUABLE_EVIDENCE_SESSION_PAYLOAD_TYPE = "continuable_evidence_session"
CONTINUABLE_EVIDENCE_SESSION_VERSION = "continuable_evidence_session_v1"
CONTINUABLE_EVIDENCE_SESSION_SEED_PAYLOAD_TYPE = (
    "continuable_evidence_session_seed"
)
CONTINUABLE_EVIDENCE_SESSION_SEED_VERSION = (
    "continuable_evidence_session_seed_v1"
)
CONTINUABLE_EVIDENCE_SESSION_TURN_PAYLOAD_TYPE = (
    "continuable_evidence_session_turn"
)
CONTINUABLE_EVIDENCE_SESSION_TURN_VERSION = (
    "continuable_evidence_session_turn_v1"
)
CONTINUABLE_EVIDENCE_SESSION_SUMMARY_PAYLOAD_TYPE = (
    "continuable_evidence_session_summary"
)
CONTINUABLE_EVIDENCE_SESSION_SUMMARY_VERSION = (
    "continuable_evidence_session_summary_v1"
)
CONTINUABLE_EVIDENCE_SESSION_ARTIFACT_INDEX_PAYLOAD_TYPE = (
    "continuable_evidence_session_artifact_index"
)
CONTINUABLE_EVIDENCE_SESSION_ARTIFACT_INDEX_VERSION = (
    "continuable_evidence_session_artifact_index_v1"
)
CONTINUABLE_EVIDENCE_SESSION_RESUME_POLICY_PAYLOAD_TYPE = (
    "continuable_evidence_session_resume_policy"
)
CONTINUABLE_EVIDENCE_SESSION_RESUME_POLICY_VERSION = (
    "continuable_evidence_session_resume_policy_v1"
)
CONTINUABLE_EVIDENCE_SESSION_TRAJECTORY_PAYLOAD_TYPE = (
    "continuable_evidence_session_trajectory"
)
CONTINUABLE_EVIDENCE_SESSION_TRAJECTORY_VERSION = (
    "continuable_evidence_session_trajectory_v1"
)
CONTINUABLE_EVIDENCE_SESSION_STORAGE_POLICY_PAYLOAD_TYPE = (
    "continuable_evidence_session_storage_policy"
)
CONTINUABLE_EVIDENCE_SESSION_STORAGE_POLICY_VERSION = (
    "continuable_evidence_session_storage_policy_v1"
)
CONTINUABLE_EVIDENCE_SESSION_LOCAL_STATE_ROOT_POLICY_PAYLOAD_TYPE = (
    "continuable_evidence_session_local_state_root_policy"
)
CONTINUABLE_EVIDENCE_SESSION_LOCAL_STATE_ROOT_POLICY_VERSION = (
    "continuable_evidence_session_local_state_root_policy_v1"
)
CONTINUABLE_EVIDENCE_SESSION_RECORD_MANIFEST_PAYLOAD_TYPE = (
    "continuable_evidence_session_record_manifest"
)
CONTINUABLE_EVIDENCE_SESSION_RECORD_MANIFEST_VERSION = (
    "continuable_evidence_session_record_manifest_v1"
)
CONTINUABLE_EVIDENCE_SESSION_INDEX_ENTRY_PAYLOAD_TYPE = (
    "continuable_evidence_session_index_entry"
)
CONTINUABLE_EVIDENCE_SESSION_INDEX_ENTRY_VERSION = (
    "continuable_evidence_session_index_entry_v1"
)
CONTINUABLE_EVIDENCE_SESSION_DELETE_POLICY_PAYLOAD_TYPE = (
    "continuable_evidence_session_delete_policy"
)
CONTINUABLE_EVIDENCE_SESSION_DELETE_POLICY_VERSION = (
    "continuable_evidence_session_delete_policy_v1"
)
CONTINUABLE_EVIDENCE_SESSION_EXPIRATION_POLICY_PAYLOAD_TYPE = (
    "continuable_evidence_session_expiration_policy"
)
CONTINUABLE_EVIDENCE_SESSION_EXPIRATION_POLICY_VERSION = (
    "continuable_evidence_session_expiration_policy_v1"
)
CONTINUABLE_EVIDENCE_SESSION_EXPORT_POLICY_PAYLOAD_TYPE = (
    "continuable_evidence_session_export_policy"
)
CONTINUABLE_EVIDENCE_SESSION_EXPORT_POLICY_VERSION = (
    "continuable_evidence_session_export_policy_v1"
)
CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_PAYLOAD_TYPE = (
    "continuable_evidence_session_runtime_binding"
)
CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_VERSION = (
    "continuable_evidence_session_runtime_binding_v1"
)
CONTINUABLE_EVIDENCE_SESSION_RUNTIME_VISIBLE_SUMMARY_PAYLOAD_TYPE = (
    "continuable_evidence_session_runtime_visible_summary"
)
CONTINUABLE_EVIDENCE_SESSION_RUNTIME_VISIBLE_SUMMARY_VERSION = (
    "continuable_evidence_session_runtime_visible_summary_v1"
)

CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX = "continuable-evidence-session://"
CONTINUABLE_EVIDENCE_SESSION_SEED_REF_PREFIX = (
    "continuable-evidence-session-seed://"
)
CONTINUABLE_EVIDENCE_SESSION_TURN_REF_PREFIX = (
    "continuable-evidence-session-turn://"
)
CONTINUABLE_EVIDENCE_SESSION_SUMMARY_REF_PREFIX = (
    "continuable-evidence-session-summary://"
)
CONTINUABLE_EVIDENCE_SESSION_ARTIFACT_INDEX_REF_PREFIX = (
    "continuable-evidence-session-artifact-index://"
)
CONTINUABLE_EVIDENCE_SESSION_TRAJECTORY_REF_PREFIX = (
    "continuable-evidence-session-trajectory://"
)
CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_REF_PREFIX = (
    "continuable-evidence-session-runtime-binding://"
)

CONTINUABLE_EVIDENCE_SESSION_STATUSES = frozenset(
    {"created", "resumable", "blocked", "expired", "deleted", "unavailable"}
)
CONTINUABLE_EVIDENCE_SESSION_TURN_KINDS = frozenset(
    {
        "initial_question",
        "evidence_follow_up",
        "answer_transformation",
        "resume",
        "export",
        "delete",
        "blocked",
        "system_note",
    }
)
CONTINUABLE_EVIDENCE_SESSION_TURN_STATUSES = frozenset(
    {"success", "blocked", "failed", "unavailable"}
)
CONTINUABLE_EVIDENCE_SESSION_RESUME_STATUSES = frozenset(
    {
        "resumable",
        "requires_confirmation",
        "requires_ref_reload",
        "expired",
        "deleted",
        "blocked",
    }
)
CONTINUABLE_EVIDENCE_SESSION_SUMMARY_KINDS = frozenset(
    {"resume", "trajectory", "export_preview", "deletion_receipt"}
)

ContinuableEvidenceSessionStatus = Literal[
    "created",
    "resumable",
    "blocked",
    "expired",
    "deleted",
    "unavailable",
]
ContinuableEvidenceSessionTurnKind = Literal[
    "initial_question",
    "evidence_follow_up",
    "answer_transformation",
    "resume",
    "export",
    "delete",
    "blocked",
    "system_note",
]
ContinuableEvidenceSessionTurnStatus = Literal[
    "success",
    "blocked",
    "failed",
    "unavailable",
]
ContinuableEvidenceSessionResumeStatus = Literal[
    "resumable",
    "requires_confirmation",
    "requires_ref_reload",
    "expired",
    "deleted",
    "blocked",
]
ContinuableEvidenceSessionSummaryKind = Literal[
    "resume",
    "trajectory",
    "export_preview",
    "deletion_receipt",
]
ContinuableEvidenceSessionSavePolicy = Literal["explicit_user_opt_in"]
ContinuableEvidenceSessionLocalStateRootKind = Literal[
    "platform_app_state",
    "macos_application_support",
    "xdg_state_home",
    "windows_local_app_data",
]
ContinuableEvidenceSessionRecordStatus = Literal[
    "planned",
    "ready_for_store",
    "resumable",
    "expired",
    "deleted",
    "blocked",
    "unavailable",
]
ContinuableEvidenceSessionExportPackageKind = Literal["refs_and_summaries"]
ContinuableEvidenceSessionRuntimeBindingStatus = Literal[
    "unavailable",
    "probed",
    "bindable",
    "bound",
    "failed",
]
ContinuableEvidenceSessionRuntimeBindingScope = Literal[
    "agent_session_event_artifactservice"
]
ContinuableEvidenceSessionRuntimeEvaluationStatus = Literal[
    "passed",
    "warning",
    "failed",
    "not_evaluated",
]

SAFE_REF_PREFIXES = (
    "continuable-evidence-session://",
    "continuable-evidence-session-seed://",
    "continuable-evidence-session-turn://",
    "continuable-evidence-session-summary://",
    "continuable-evidence-session-artifact-index://",
    "continuable-evidence-session-trajectory://",
    "continuable-evidence-session-runtime-binding://",
    "evidence-summary-answer-run://",
    "evidence-summary-answer-trace://",
    "evidence-summary-answer-artifact://",
    "evidence-summary-answer-trace-inspect://",
    "evidence-summary-answer-observability-summary://",
    "evidence-summary-answer-follow-up://",
    "evaluation://",
    "governed-evidence-digest://",
    "evidence://external-readonly/",
    "policy://continuable-evidence-session/",
)

FORBIDDEN_CONTINUABLE_EVIDENCE_SESSION_KEYS = frozenset(
    {
        "api_key",
        "artifact_body",
        "artifact_content",
        "authorization",
        "body",
        "config_context",
        "content",
        "cookie",
        "credential",
        "credentials",
        "adk_eval_raw_data",
        "full_answer",
        "full_prompt",
        "full_response",
        "headers",
        "html",
        "message",
        "messages",
        "password",
        "prompt",
        "provider_payload",
        "provider_response",
        "raw",
        "raw_adk_event",
        "raw_adk_object",
        "raw_adk_session",
        "raw_artifact",
        "raw_evidence",
        "raw_event_payload",
        "raw_html",
        "raw_model_messages",
        "raw_payload",
        "raw_prompt",
        "raw_provider_response",
        "raw_response",
        "raw_runtime_object",
        "response",
        "sanitized_excerpt_preview",
        "secret",
        "system_prompt",
        "token",
        "traceback",
        "user_question",
    }
)

SAFE_METADATA_VALUE_TYPES = (str, int, float, bool, type(None))


class ContinuableEvidenceSessionBaseModel(BaseModel):
    """Base model for continuable evidence session contracts."""

    model_config = ConfigDict(extra="forbid")


class ContinuableEvidenceSessionRawBoundarySummarySchema(
    ContinuableEvidenceSessionBaseModel
):
    """Summary of raw content that must not be stored in session contracts."""

    stores_raw_evidence: bool = False
    stores_raw_prompt: bool = False
    stores_raw_provider_response: bool = False
    stores_raw_model_messages: bool = False
    stores_full_system_prompt: bool = False
    stores_secret: bool = False
    stores_traceback: bool = False
    stores_raw_html: bool = False
    stores_sanitized_excerpt_preview: bool = False
    stores_full_config_context: bool = False
    stores_adk_raw_object: bool = False
    stores_memory: bool = False

    @model_validator(mode="after")
    def validate_raw_boundary(
        self,
    ) -> "ContinuableEvidenceSessionRawBoundarySummarySchema":
        for field_name, value in self.model_dump().items():
            if value:
                raise ValueError(f"{field_name} must be false.")
        return self


class ContinuableEvidenceSessionRefSummarySchema(
    ContinuableEvidenceSessionBaseModel
):
    """Safe reference summary that never carries raw ref body content."""

    ref: str = Field(..., min_length=1)
    kind: str | None = None
    purpose: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_ref_summary(self) -> "ContinuableEvidenceSessionRefSummarySchema":
        _validate_ref(self.ref, field_name="ref")
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionSchema(ContinuableEvidenceSessionBaseModel):
    """Product-level aggregate ref for one continuable evidence session."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PAYLOAD_TYPE
    )
    payload_version: Literal["continuable_evidence_session_v1"] = (
        CONTINUABLE_EVIDENCE_SESSION_VERSION
    )
    session_id: str = Field(..., min_length=1)
    continuable_evidence_session_ref: str = Field(..., min_length=1)
    session_status: ContinuableEvidenceSessionStatus
    source_answer_run_ref: str = Field(..., min_length=1)
    latest_answer_run_ref: str | None = None
    session_seed_ref: str = Field(..., min_length=1)
    session_summary_ref: str | None = None
    session_artifact_index_ref: str | None = None
    session_trajectory_ref: str | None = None
    turn_count: int = Field(default=0, ge=0)
    evidence_ref_count: int = Field(default=0, ge=0)
    digest_ref_count: int = Field(default=0, ge=0)
    created_at: str = Field(..., min_length=1)
    updated_at: str = Field(..., min_length=1)
    expires_at: str | None = None
    resumable: bool = False
    runtime_backed: bool = False
    backed_by_adk_session: bool = False
    backed_by_adk_event_stream: bool = False
    backed_by_adk_artifact_service: bool = False
    backed_by_adk_task_runtime: bool = False
    backed_by_adk_workflow_runtime: bool = False
    memory_enabled: bool = False
    raw_boundary_summary: ContinuableEvidenceSessionRawBoundarySummarySchema = Field(
        default_factory=ContinuableEvidenceSessionRawBoundarySummarySchema
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_session(self) -> "ContinuableEvidenceSessionSchema":
        _validate_ref_prefix(
            self.continuable_evidence_session_ref,
            CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX,
            "continuable_evidence_session_ref",
        )
        _validate_ref(self.source_answer_run_ref, field_name="source_answer_run_ref")
        _validate_optional_ref(
            self.latest_answer_run_ref,
            field_name="latest_answer_run_ref",
        )
        _validate_ref_prefix(
            self.session_seed_ref,
            CONTINUABLE_EVIDENCE_SESSION_SEED_REF_PREFIX,
            "session_seed_ref",
        )
        _validate_optional_ref_prefix(
            self.session_summary_ref,
            CONTINUABLE_EVIDENCE_SESSION_SUMMARY_REF_PREFIX,
            "session_summary_ref",
        )
        _validate_optional_ref_prefix(
            self.session_artifact_index_ref,
            CONTINUABLE_EVIDENCE_SESSION_ARTIFACT_INDEX_REF_PREFIX,
            "session_artifact_index_ref",
        )
        _validate_optional_ref_prefix(
            self.session_trajectory_ref,
            CONTINUABLE_EVIDENCE_SESSION_TRAJECTORY_REF_PREFIX,
            "session_trajectory_ref",
        )
        if self.session_status == "resumable" and not self.resumable:
            raise ValueError("resumable sessions require resumable=true.")
        if self.session_status in {"blocked", "expired", "deleted", "unavailable"}:
            if self.resumable:
                raise ValueError(f"{self.session_status} sessions cannot be resumable.")
        _validate_runtime_flags(self)
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionSeedSchema(ContinuableEvidenceSessionBaseModel):
    """Safe seed used to resume a continuable evidence session."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal["continuable_evidence_session_seed"] = (
        CONTINUABLE_EVIDENCE_SESSION_SEED_PAYLOAD_TYPE
    )
    payload_version: Literal["continuable_evidence_session_seed_v1"] = (
        CONTINUABLE_EVIDENCE_SESSION_SEED_VERSION
    )
    seed_id: str = Field(..., min_length=1)
    session_seed_ref: str = Field(..., min_length=1)
    continuable_evidence_session_ref: str = Field(..., min_length=1)
    source_request_id: str = Field(..., min_length=1)
    source_answer_run_ref: str = Field(..., min_length=1)
    source_answer_status: str = Field(..., min_length=1)
    evidence_refs: list[ContinuableEvidenceSessionRefSummarySchema] = Field(
        default_factory=list
    )
    digest_refs: list[str] = Field(default_factory=list)
    additional_refs: list[ContinuableEvidenceSessionRefSummarySchema] = Field(
        default_factory=list
    )
    answer_trace_ref: str | None = None
    answer_artifact_ref: str | None = None
    trace_inspect_ref: str | None = None
    observability_summary_ref: str | None = None
    resume_summary_ref: str | None = None
    seed_source: Literal["initial_answer_run", "imported_export_package"]
    requires_user_confirmation_on_resume: bool = True
    temporary_follow_up_seed_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_seed(self) -> "ContinuableEvidenceSessionSeedSchema":
        _validate_ref_prefix(
            self.session_seed_ref,
            CONTINUABLE_EVIDENCE_SESSION_SEED_REF_PREFIX,
            "session_seed_ref",
        )
        _validate_ref_prefix(
            self.continuable_evidence_session_ref,
            CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX,
            "continuable_evidence_session_ref",
        )
        _validate_ref(self.source_answer_run_ref, field_name="source_answer_run_ref")
        if not self.evidence_refs:
            raise ValueError("session seed requires evidence_refs.")
        if not self.digest_refs:
            raise ValueError("session seed requires digest_refs.")
        for digest_ref in self.digest_refs:
            _validate_ref(digest_ref, field_name="digest_refs")
        for field_name in (
            "answer_trace_ref",
            "answer_artifact_ref",
            "trace_inspect_ref",
            "observability_summary_ref",
            "resume_summary_ref",
            "temporary_follow_up_seed_ref",
        ):
            _validate_optional_ref(getattr(self, field_name), field_name=field_name)
        if self.requires_user_confirmation_on_resume is not True:
            raise ValueError("resume must require user confirmation.")
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionTurnSchema(ContinuableEvidenceSessionBaseModel):
    """One safe turn in a continuable evidence session."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal["continuable_evidence_session_turn"] = (
        CONTINUABLE_EVIDENCE_SESSION_TURN_PAYLOAD_TYPE
    )
    payload_version: Literal["continuable_evidence_session_turn_v1"] = (
        CONTINUABLE_EVIDENCE_SESSION_TURN_VERSION
    )
    turn_id: str = Field(..., min_length=1)
    session_turn_ref: str = Field(..., min_length=1)
    continuable_evidence_session_ref: str = Field(..., min_length=1)
    turn_index: int = Field(..., ge=1)
    turn_kind: ContinuableEvidenceSessionTurnKind
    turn_status: ContinuableEvidenceSessionTurnStatus
    input_summary: str | None = None
    output_summary: str | None = None
    answer_run_ref: str | None = None
    parent_answer_run_ref: str | None = None
    answer_artifact_ref: str | None = None
    trace_inspect_ref: str | None = None
    observability_summary_ref: str | None = None
    blocked_reason: str | None = None
    requires_reauthorization: bool = False
    created_at: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_turn(self) -> "ContinuableEvidenceSessionTurnSchema":
        _validate_ref_prefix(
            self.session_turn_ref,
            CONTINUABLE_EVIDENCE_SESSION_TURN_REF_PREFIX,
            "session_turn_ref",
        )
        _validate_ref_prefix(
            self.continuable_evidence_session_ref,
            CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX,
            "continuable_evidence_session_ref",
        )
        for field_name in (
            "answer_run_ref",
            "parent_answer_run_ref",
            "answer_artifact_ref",
            "trace_inspect_ref",
            "observability_summary_ref",
        ):
            _validate_optional_ref(getattr(self, field_name), field_name=field_name)
        if self.turn_status in {"blocked", "failed", "unavailable"}:
            if not self.blocked_reason:
                raise ValueError(f"{self.turn_status} turns require blocked_reason.")
        if self.turn_kind == "answer_transformation" and self.requires_reauthorization:
            raise ValueError("answer transformations must not require evidence reload.")
        if self.turn_kind == "evidence_follow_up" and not self.requires_reauthorization:
            raise ValueError("evidence follow-up must require explicit authorization.")
        _validate_safe_summary_text(self.input_summary, field_name="input_summary")
        _validate_safe_summary_text(self.output_summary, field_name="output_summary")
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionSummarySchema(ContinuableEvidenceSessionBaseModel):
    """Safe summary for resuming or explaining a continuable evidence session."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal["continuable_evidence_session_summary"] = (
        CONTINUABLE_EVIDENCE_SESSION_SUMMARY_PAYLOAD_TYPE
    )
    payload_version: Literal["continuable_evidence_session_summary_v1"] = (
        CONTINUABLE_EVIDENCE_SESSION_SUMMARY_VERSION
    )
    session_summary_ref: str = Field(..., min_length=1)
    continuable_evidence_session_ref: str = Field(..., min_length=1)
    summary_kind: ContinuableEvidenceSessionSummaryKind
    summary_text: str = Field(..., min_length=1, max_length=2400)
    source_refs: list[str] = Field(default_factory=list)
    evidence_scope_summary: str | None = None
    last_user_intent_summary: str | None = None
    answer_state_boundary: str | None = None
    evaluation_status: Literal["passed", "warning", "failed", "not_evaluated"] = (
        "not_evaluated"
    )
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_summary(self) -> "ContinuableEvidenceSessionSummarySchema":
        _validate_ref_prefix(
            self.session_summary_ref,
            CONTINUABLE_EVIDENCE_SESSION_SUMMARY_REF_PREFIX,
            "session_summary_ref",
        )
        _validate_ref_prefix(
            self.continuable_evidence_session_ref,
            CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX,
            "continuable_evidence_session_ref",
        )
        if not self.source_refs:
            raise ValueError("session summaries require source_refs.")
        for source_ref in self.source_refs:
            _validate_ref(source_ref, field_name="source_refs")
        for field_name in (
            "summary_text",
            "evidence_scope_summary",
            "last_user_intent_summary",
            "answer_state_boundary",
        ):
            _validate_safe_summary_text(getattr(self, field_name), field_name=field_name)
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionArtifactIndexSchema(
    ContinuableEvidenceSessionBaseModel
):
    """Refs-only artifact index for a continuable evidence session."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal["continuable_evidence_session_artifact_index"] = (
        CONTINUABLE_EVIDENCE_SESSION_ARTIFACT_INDEX_PAYLOAD_TYPE
    )
    payload_version: Literal["continuable_evidence_session_artifact_index_v1"] = (
        CONTINUABLE_EVIDENCE_SESSION_ARTIFACT_INDEX_VERSION
    )
    session_artifact_index_ref: str = Field(..., min_length=1)
    continuable_evidence_session_ref: str = Field(..., min_length=1)
    answer_run_refs: list[str] = Field(default_factory=list)
    answer_artifact_refs: list[str] = Field(default_factory=list)
    trace_inspect_refs: list[str] = Field(default_factory=list)
    observability_summary_refs: list[str] = Field(default_factory=list)
    export_package_refs: list[str] = Field(default_factory=list)
    artifact_service_binding_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_artifact_index(
        self,
    ) -> "ContinuableEvidenceSessionArtifactIndexSchema":
        _validate_ref_prefix(
            self.session_artifact_index_ref,
            CONTINUABLE_EVIDENCE_SESSION_ARTIFACT_INDEX_REF_PREFIX,
            "session_artifact_index_ref",
        )
        _validate_ref_prefix(
            self.continuable_evidence_session_ref,
            CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX,
            "continuable_evidence_session_ref",
        )
        if not self.answer_run_refs:
            raise ValueError("artifact index requires answer_run_refs.")
        for field_name in (
            "answer_run_refs",
            "answer_artifact_refs",
            "trace_inspect_refs",
            "observability_summary_refs",
            "export_package_refs",
        ):
            for ref in getattr(self, field_name):
                _validate_ref(ref, field_name=field_name)
        if self.artifact_service_binding_refs:
            raise ValueError("artifact_service_binding_refs must be empty in v1.")
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionResumePolicySchema(
    ContinuableEvidenceSessionBaseModel
):
    """Resume, delete, export, and expiration policy for one session."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal["continuable_evidence_session_resume_policy"] = (
        CONTINUABLE_EVIDENCE_SESSION_RESUME_POLICY_PAYLOAD_TYPE
    )
    payload_version: Literal["continuable_evidence_session_resume_policy_v1"] = (
        CONTINUABLE_EVIDENCE_SESSION_RESUME_POLICY_VERSION
    )
    policy_ref: str = Field(..., min_length=1)
    continuable_evidence_session_ref: str = Field(..., min_length=1)
    resume_allowed: bool = False
    resume_status: ContinuableEvidenceSessionResumeStatus
    requires_user_confirmation: bool = True
    requires_external_readonly_authorization: bool = True
    requires_model_authorization: bool = True
    retention_policy_ref: str = Field(..., min_length=1)
    export_allowed: bool = False
    delete_allowed: bool = True
    overwrite_allowed: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)
    recovery_hints: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_resume_policy(
        self,
    ) -> "ContinuableEvidenceSessionResumePolicySchema":
        _validate_ref_prefix(
            self.continuable_evidence_session_ref,
            CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX,
            "continuable_evidence_session_ref",
        )
        if self.resume_allowed:
            if self.resume_status not in {"resumable", "requires_confirmation"}:
                raise ValueError("resume_allowed requires resumable status.")
            if self.blocking_reasons:
                raise ValueError("allowed resume policies must not carry blockers.")
        if self.resume_status in {"expired", "deleted", "blocked"}:
            if self.resume_allowed:
                raise ValueError(f"{self.resume_status} policies cannot allow resume.")
            if not self.blocking_reasons:
                raise ValueError(f"{self.resume_status} policies require blockers.")
        if self.requires_user_confirmation is not True:
            raise ValueError("resume requires user confirmation.")
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionTrajectorySchema(
    ContinuableEvidenceSessionBaseModel
):
    """User-safe conversation trajectory summary for one session."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal["continuable_evidence_session_trajectory"] = (
        CONTINUABLE_EVIDENCE_SESSION_TRAJECTORY_PAYLOAD_TYPE
    )
    payload_version: Literal["continuable_evidence_session_trajectory_v1"] = (
        CONTINUABLE_EVIDENCE_SESSION_TRAJECTORY_VERSION
    )
    session_trajectory_ref: str = Field(..., min_length=1)
    continuable_evidence_session_ref: str = Field(..., min_length=1)
    user_visible_turns: list[dict[str, Any]] = Field(default_factory=list)
    developer_review_refs: list[str] = Field(default_factory=list)
    evidence_grounded_turn_count: int = Field(default=0, ge=0)
    answer_transformation_turn_count: int = Field(default=0, ge=0)
    blocked_turn_count: int = Field(default=0, ge=0)
    latest_resume_summary_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_trajectory(self) -> "ContinuableEvidenceSessionTrajectorySchema":
        _validate_ref_prefix(
            self.session_trajectory_ref,
            CONTINUABLE_EVIDENCE_SESSION_TRAJECTORY_REF_PREFIX,
            "session_trajectory_ref",
        )
        _validate_ref_prefix(
            self.continuable_evidence_session_ref,
            CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX,
            "continuable_evidence_session_ref",
        )
        if not self.user_visible_turns:
            raise ValueError("trajectory requires user_visible_turns.")
        for item in self.user_visible_turns:
            _validate_safe_mapping(item, field_name="user_visible_turns")
        for ref in self.developer_review_refs:
            _validate_ref(ref, field_name="developer_review_refs")
        _validate_optional_ref_prefix(
            self.latest_resume_summary_ref,
            CONTINUABLE_EVIDENCE_SESSION_SUMMARY_REF_PREFIX,
            "latest_resume_summary_ref",
        )
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionRuntimeBindingSchema(
    ContinuableEvidenceSessionBaseModel
):
    """Safe product-level runtime binding facts for one continuable session."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal["continuable_evidence_session_runtime_binding"] = (
        CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_PAYLOAD_TYPE
    )
    payload_version: Literal["continuable_evidence_session_runtime_binding_v1"] = (
        CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_VERSION
    )
    runtime_binding_ref: str = Field(..., min_length=1)
    continuable_evidence_session_ref: str = Field(..., min_length=1)
    runtime_binding_status: ContinuableEvidenceSessionRuntimeBindingStatus = (
        "unavailable"
    )
    runtime_binding_scope: ContinuableEvidenceSessionRuntimeBindingScope = (
        "agent_session_event_artifactservice"
    )
    runtime_binding_summary_ref: str | None = None
    agent_binding_ref: str | None = None
    session_binding_ref: str | None = None
    event_review_refs: list[str] = Field(default_factory=list)
    artifact_binding_summary_refs: list[str] = Field(default_factory=list)
    runtime_binding_evaluation_summary_ref: str | None = None
    raw_runtime_object_included: bool = False
    raw_event_payload_included: bool = False
    artifact_body_included: bool = False
    adk_eval_raw_data_included: bool = False
    user_product_runtime_path_enabled: bool = False
    default_local_state_dir_enabled: bool = False
    auto_resume_answer_enabled: bool = False
    skills_loaded: bool = False
    memory_enabled: bool = False
    tools_mcp_enabled: bool = False
    callbacks_enabled: bool = False
    plugins_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_runtime_binding(
        self,
    ) -> "ContinuableEvidenceSessionRuntimeBindingSchema":
        _validate_ref_prefix(
            self.runtime_binding_ref,
            CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_REF_PREFIX,
            "runtime_binding_ref",
        )
        _validate_ref_prefix(
            self.continuable_evidence_session_ref,
            CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX,
            "continuable_evidence_session_ref",
        )
        for field_name in (
            "runtime_binding_summary_ref",
            "agent_binding_ref",
            "session_binding_ref",
            "runtime_binding_evaluation_summary_ref",
        ):
            _validate_optional_ref(getattr(self, field_name), field_name=field_name)
        for field_name in ("event_review_refs", "artifact_binding_summary_refs"):
            for ref in getattr(self, field_name):
                _validate_ref(ref, field_name=field_name)
        for field_name in (
            "raw_runtime_object_included",
            "raw_event_payload_included",
            "artifact_body_included",
            "adk_eval_raw_data_included",
            "user_product_runtime_path_enabled",
            "default_local_state_dir_enabled",
            "auto_resume_answer_enabled",
            "skills_loaded",
            "memory_enabled",
            "tools_mcp_enabled",
            "callbacks_enabled",
            "plugins_enabled",
        ):
            if getattr(self, field_name):
                raise ValueError(f"{field_name} must be false.")
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionRuntimeVisibleSummarySchema(
    ContinuableEvidenceSessionBaseModel
):
    """User-visible safe runtime binding summary for one continuable session."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal[
        "continuable_evidence_session_runtime_visible_summary"
    ] = CONTINUABLE_EVIDENCE_SESSION_RUNTIME_VISIBLE_SUMMARY_PAYLOAD_TYPE
    payload_version: Literal[
        "continuable_evidence_session_runtime_visible_summary_v1"
    ] = CONTINUABLE_EVIDENCE_SESSION_RUNTIME_VISIBLE_SUMMARY_VERSION
    runtime_visible_summary_ref: str = Field(..., min_length=1)
    continuable_evidence_session_ref: str = Field(..., min_length=1)
    runtime_binding_ref: str | None = None
    runtime_binding_status: ContinuableEvidenceSessionRuntimeBindingStatus = (
        "unavailable"
    )
    runtime_availability_hint: str = Field(..., min_length=1, max_length=400)
    trajectory_summary: dict[str, Any] = Field(default_factory=dict)
    artifact_index: list[ContinuableEvidenceSessionRefSummarySchema] = Field(
        default_factory=list
    )
    evaluation_summary_ref: str | None = None
    evaluation_status: ContinuableEvidenceSessionRuntimeEvaluationStatus = (
        "not_evaluated"
    )
    next_actions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    user_product_runtime_path_enabled: bool = False
    default_local_state_dir_enabled: bool = False
    auto_resume_answer_enabled: bool = False
    workflow_replay_enabled: bool = False
    llm_call_enabled: bool = False
    task_runtime_implementation_enabled: bool = False
    raw_runtime_object_included: bool = False
    raw_event_payload_included: bool = False
    artifact_body_included: bool = False
    adk_eval_raw_data_included: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_runtime_visible_summary(
        self,
    ) -> "ContinuableEvidenceSessionRuntimeVisibleSummarySchema":
        _validate_ref_prefix(
            self.runtime_visible_summary_ref,
            CONTINUABLE_EVIDENCE_SESSION_SUMMARY_REF_PREFIX,
            "runtime_visible_summary_ref",
        )
        _validate_ref_prefix(
            self.continuable_evidence_session_ref,
            CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX,
            "continuable_evidence_session_ref",
        )
        _validate_optional_ref_prefix(
            self.runtime_binding_ref,
            CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_REF_PREFIX,
            "runtime_binding_ref",
        )
        _validate_optional_ref(
            self.evaluation_summary_ref,
            field_name="evaluation_summary_ref",
        )
        _validate_safe_summary_text(
            self.runtime_availability_hint,
            field_name="runtime_availability_hint",
        )
        _validate_safe_mapping(
            self.trajectory_summary,
            field_name="trajectory_summary",
        )
        if not self.artifact_index:
            raise ValueError("runtime visible summary requires artifact_index.")
        for field_name in (
            "next_actions",
            "warnings",
        ):
            for item in getattr(self, field_name):
                _validate_safe_summary_text(item, field_name=field_name)
        for field_name in (
            "user_product_runtime_path_enabled",
            "default_local_state_dir_enabled",
            "auto_resume_answer_enabled",
            "workflow_replay_enabled",
            "llm_call_enabled",
            "task_runtime_implementation_enabled",
            "raw_runtime_object_included",
            "raw_event_payload_included",
            "artifact_body_included",
            "adk_eval_raw_data_included",
        ):
            if getattr(self, field_name):
                raise ValueError(f"{field_name} must be false.")
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionStoragePolicySchema(
    ContinuableEvidenceSessionBaseModel
):
    """Storage policy metadata without local session I/O."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal["continuable_evidence_session_storage_policy"] = (
        CONTINUABLE_EVIDENCE_SESSION_STORAGE_POLICY_PAYLOAD_TYPE
    )
    payload_version: Literal["continuable_evidence_session_storage_policy_v1"] = (
        CONTINUABLE_EVIDENCE_SESSION_STORAGE_POLICY_VERSION
    )
    storage_policy_ref: str = Field(..., min_length=1)
    continuable_evidence_session_ref: str = Field(..., min_length=1)
    save_policy: ContinuableEvidenceSessionSavePolicy = "explicit_user_opt_in"
    local_store_allowed: bool = True
    auto_save_default: bool = False
    requires_user_confirmation_on_save: bool = True
    requires_user_confirmation_on_resume: bool = True
    local_state_root_policy_ref: str = Field(..., min_length=1)
    retention_policy_ref: str = Field(..., min_length=1)
    delete_policy_ref: str = Field(..., min_length=1)
    export_policy_ref: str = Field(..., min_length=1)
    config_backed: bool = False
    runtime_backed: bool = False
    memory_enabled: bool = False
    raw_boundary_summary: ContinuableEvidenceSessionRawBoundarySummarySchema = Field(
        default_factory=ContinuableEvidenceSessionRawBoundarySummarySchema
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_storage_policy(
        self,
    ) -> "ContinuableEvidenceSessionStoragePolicySchema":
        _validate_ref(self.storage_policy_ref, field_name="storage_policy_ref")
        _validate_ref_prefix(
            self.continuable_evidence_session_ref,
            CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX,
            "continuable_evidence_session_ref",
        )
        for field_name in (
            "local_state_root_policy_ref",
            "retention_policy_ref",
            "delete_policy_ref",
            "export_policy_ref",
        ):
            _validate_ref(getattr(self, field_name), field_name=field_name)
        if self.auto_save_default:
            raise ValueError("auto_save_default must be false.")
        if self.requires_user_confirmation_on_save is not True:
            raise ValueError("save requires user confirmation.")
        if self.requires_user_confirmation_on_resume is not True:
            raise ValueError("resume requires user confirmation.")
        if self.config_backed:
            raise ValueError("storage policy is not config-backed in v1.")
        _validate_runtime_flags(self)
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionLocalStateRootPolicySchema(
    ContinuableEvidenceSessionBaseModel
):
    """Local state root policy that names strategy, not resolved paths."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal[
        "continuable_evidence_session_local_state_root_policy"
    ] = CONTINUABLE_EVIDENCE_SESSION_LOCAL_STATE_ROOT_POLICY_PAYLOAD_TYPE
    payload_version: Literal[
        "continuable_evidence_session_local_state_root_policy_v1"
    ] = CONTINUABLE_EVIDENCE_SESSION_LOCAL_STATE_ROOT_POLICY_VERSION
    local_state_root_policy_ref: str = Field(..., min_length=1)
    root_kind: ContinuableEvidenceSessionLocalStateRootKind = "platform_app_state"
    platform_strategy: str = Field(
        default=(
            "macos_application_support_or_xdg_state_home_or_windows_local_app_data"
        ),
        min_length=1,
    )
    env_override_candidate: str | None = "COGNITION_SESSION_STATE_DIR"
    reads_environment: bool = False
    resolves_user_home: bool = False
    uses_repo_outputs: bool = False
    packaged_resource: bool = False
    public_repo_synced: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_local_state_root_policy(
        self,
    ) -> "ContinuableEvidenceSessionLocalStateRootPolicySchema":
        _validate_ref(
            self.local_state_root_policy_ref,
            field_name="local_state_root_policy_ref",
        )
        if self.reads_environment:
            raise ValueError("policy contracts must not read environment variables.")
        if self.resolves_user_home:
            raise ValueError("policy contracts must not resolve user home paths.")
        if self.uses_repo_outputs:
            raise ValueError("local state root must not use repo outputs.")
        if self.packaged_resource:
            raise ValueError("local state root must not be a packaged resource.")
        if self.public_repo_synced:
            raise ValueError("local state root must not sync to public repo.")
        _validate_safe_summary_text(
            self.platform_strategy,
            field_name="platform_strategy",
        )
        _validate_safe_summary_text(
            self.env_override_candidate,
            field_name="env_override_candidate",
        )
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionRecordManifestSchema(
    ContinuableEvidenceSessionBaseModel
):
    """Logical record manifest contract before any local session I/O exists."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal["continuable_evidence_session_record_manifest"] = (
        CONTINUABLE_EVIDENCE_SESSION_RECORD_MANIFEST_PAYLOAD_TYPE
    )
    payload_version: Literal["continuable_evidence_session_record_manifest_v1"] = (
        CONTINUABLE_EVIDENCE_SESSION_RECORD_MANIFEST_VERSION
    )
    record_manifest_ref: str = Field(..., min_length=1)
    continuable_evidence_session_ref: str = Field(..., min_length=1)
    record_schema_version: str = "continuable_evidence_session_record_v1"
    record_status: ContinuableEvidenceSessionRecordStatus = "ready_for_store"
    logical_file_names: list[str] = Field(default_factory=list)
    storage_policy_ref: str = Field(..., min_length=1)
    local_state_root_policy_ref: str = Field(..., min_length=1)
    retention_policy_ref: str = Field(..., min_length=1)
    delete_policy_ref: str = Field(..., min_length=1)
    export_policy_ref: str = Field(..., min_length=1)
    created_at: str = Field(..., min_length=1)
    updated_at: str = Field(..., min_length=1)
    expires_at: str | None = None
    contains_raw_payload: bool = False
    io_performed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_record_manifest(
        self,
    ) -> "ContinuableEvidenceSessionRecordManifestSchema":
        _validate_ref(self.record_manifest_ref, field_name="record_manifest_ref")
        _validate_ref_prefix(
            self.continuable_evidence_session_ref,
            CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX,
            "continuable_evidence_session_ref",
        )
        for field_name in (
            "storage_policy_ref",
            "local_state_root_policy_ref",
            "retention_policy_ref",
            "delete_policy_ref",
            "export_policy_ref",
        ):
            _validate_ref(getattr(self, field_name), field_name=field_name)
        if not self.logical_file_names:
            raise ValueError("record manifest requires logical_file_names.")
        for logical_file_name in self.logical_file_names:
            _validate_logical_file_name(logical_file_name)
        if self.contains_raw_payload:
            raise ValueError("record manifest must not contain raw payload.")
        if self.io_performed:
            raise ValueError("record manifest contract must not claim local I/O.")
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionIndexEntrySchema(
    ContinuableEvidenceSessionBaseModel
):
    """Safe session index entry for future list/resume views."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal["continuable_evidence_session_index_entry"] = (
        CONTINUABLE_EVIDENCE_SESSION_INDEX_ENTRY_PAYLOAD_TYPE
    )
    payload_version: Literal["continuable_evidence_session_index_entry_v1"] = (
        CONTINUABLE_EVIDENCE_SESSION_INDEX_ENTRY_VERSION
    )
    session_id: str = Field(..., min_length=1)
    continuable_evidence_session_ref: str = Field(..., min_length=1)
    session_status: ContinuableEvidenceSessionStatus
    created_at: str = Field(..., min_length=1)
    updated_at: str = Field(..., min_length=1)
    expires_at: str | None = None
    source_scope_summary: str = Field(..., min_length=1, max_length=800)
    latest_resume_summary_preview: str = Field(..., min_length=1, max_length=800)
    turn_count: int = Field(default=0, ge=0)
    evidence_ref_count: int = Field(default=0, ge=0)
    digest_ref_count: int = Field(default=0, ge=0)
    requires_external_readonly_authorization: bool = True
    requires_model_authorization: bool = True
    resumable: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_index_entry(self) -> "ContinuableEvidenceSessionIndexEntrySchema":
        _validate_ref_prefix(
            self.continuable_evidence_session_ref,
            CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX,
            "continuable_evidence_session_ref",
        )
        if self.session_status == "resumable" and not self.resumable:
            raise ValueError("resumable index entries require resumable=true.")
        if self.session_status in {"blocked", "expired", "deleted", "unavailable"}:
            if self.resumable:
                raise ValueError(f"{self.session_status} entries cannot be resumable.")
        _validate_safe_summary_text(
            self.source_scope_summary,
            field_name="source_scope_summary",
        )
        _validate_safe_summary_text(
            self.latest_resume_summary_preview,
            field_name="latest_resume_summary_preview",
        )
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionDeletePolicySchema(
    ContinuableEvidenceSessionBaseModel
):
    """Delete policy contract for future local session records."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal["continuable_evidence_session_delete_policy"] = (
        CONTINUABLE_EVIDENCE_SESSION_DELETE_POLICY_PAYLOAD_TYPE
    )
    payload_version: Literal["continuable_evidence_session_delete_policy_v1"] = (
        CONTINUABLE_EVIDENCE_SESSION_DELETE_POLICY_VERSION
    )
    delete_policy_ref: str = Field(..., min_length=1)
    delete_allowed: bool = True
    requires_user_confirmation: bool = True
    removes_local_record: bool = True
    removes_from_resumable_index: bool = True
    deletion_receipt_allowed: bool = True
    deletion_receipt_contains_raw_payload: bool = False
    deleted_session_resumable: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_delete_policy(self) -> "ContinuableEvidenceSessionDeletePolicySchema":
        _validate_ref(self.delete_policy_ref, field_name="delete_policy_ref")
        if self.requires_user_confirmation is not True:
            raise ValueError("delete requires user confirmation.")
        if self.removes_local_record is not True:
            raise ValueError("delete must remove local record.")
        if self.removes_from_resumable_index is not True:
            raise ValueError("delete must remove from resumable index.")
        if self.deletion_receipt_contains_raw_payload:
            raise ValueError("deletion receipt must not contain raw payload.")
        if self.deleted_session_resumable:
            raise ValueError("deleted session must not be resumable.")
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionExpirationPolicySchema(
    ContinuableEvidenceSessionBaseModel
):
    """Expiration policy contract for future local session records."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal["continuable_evidence_session_expiration_policy"] = (
        CONTINUABLE_EVIDENCE_SESSION_EXPIRATION_POLICY_PAYLOAD_TYPE
    )
    payload_version: Literal["continuable_evidence_session_expiration_policy_v1"] = (
        CONTINUABLE_EVIDENCE_SESSION_EXPIRATION_POLICY_VERSION
    )
    retention_policy_ref: str = Field(..., min_length=1)
    default_retention_days: int = Field(default=30, ge=1)
    expired_session_resumable: bool = False
    expired_equals_deleted: bool = False
    cleanup_immediate: bool = False
    allows_reimport: bool = True
    allows_ref_reload: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_expiration_policy(
        self,
    ) -> "ContinuableEvidenceSessionExpirationPolicySchema":
        _validate_ref(self.retention_policy_ref, field_name="retention_policy_ref")
        if self.expired_session_resumable:
            raise ValueError("expired session must not be directly resumable.")
        if self.expired_equals_deleted:
            raise ValueError("expired must not equal deleted.")
        if self.cleanup_immediate:
            raise ValueError("cleanup execution is deferred in v1.")
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class ContinuableEvidenceSessionExportPolicySchema(
    ContinuableEvidenceSessionBaseModel
):
    """Export policy contract for refs-and-summaries packages."""

    product: Literal["continuable_evidence_session"] = (
        CONTINUABLE_EVIDENCE_SESSION_PRODUCT
    )
    payload_type: Literal["continuable_evidence_session_export_policy"] = (
        CONTINUABLE_EVIDENCE_SESSION_EXPORT_POLICY_PAYLOAD_TYPE
    )
    payload_version: Literal["continuable_evidence_session_export_policy_v1"] = (
        CONTINUABLE_EVIDENCE_SESSION_EXPORT_POLICY_VERSION
    )
    export_policy_ref: str = Field(..., min_length=1)
    export_allowed: bool = True
    export_package_kind: ContinuableEvidenceSessionExportPackageKind = (
        "refs_and_summaries"
    )
    export_package_is_evidence_archive: bool = False
    includes_raw_evidence: bool = False
    includes_raw_prompt: bool = False
    includes_raw_provider_response: bool = False
    includes_full_answer: bool = False
    includes_secret: bool = False
    includes_full_config_context: bool = False
    includes_adk_raw_object: bool = False
    warns_refs_may_not_resolve: bool = True
    import_requires_confirmation: bool = True
    import_requires_authorization: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_export_policy(self) -> "ContinuableEvidenceSessionExportPolicySchema":
        _validate_ref(self.export_policy_ref, field_name="export_policy_ref")
        if self.export_package_is_evidence_archive:
            raise ValueError("export package must not be an evidence archive.")
        for field_name in (
            "includes_raw_evidence",
            "includes_raw_prompt",
            "includes_raw_provider_response",
            "includes_full_answer",
            "includes_secret",
            "includes_full_config_context",
            "includes_adk_raw_object",
        ):
            if getattr(self, field_name):
                raise ValueError(f"{field_name} must be false.")
        if self.warns_refs_may_not_resolve is not True:
            raise ValueError("export must warn that refs may not resolve.")
        if self.import_requires_confirmation is not True:
            raise ValueError("imported session resume requires confirmation.")
        if self.import_requires_authorization is not True:
            raise ValueError("imported session resume requires authorization.")
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


def validate_continuable_evidence_session(
    session: dict[str, Any],
) -> ContinuableEvidenceSessionSchema:
    """Validate a plain dict as a continuable evidence session."""

    return ContinuableEvidenceSessionSchema.model_validate(session)


def validate_continuable_evidence_session_seed(
    seed: dict[str, Any],
) -> ContinuableEvidenceSessionSeedSchema:
    """Validate a plain dict as a continuable evidence session seed."""

    return ContinuableEvidenceSessionSeedSchema.model_validate(seed)


def validate_continuable_evidence_session_turn(
    turn: dict[str, Any],
) -> ContinuableEvidenceSessionTurnSchema:
    """Validate a plain dict as a continuable evidence session turn."""

    return ContinuableEvidenceSessionTurnSchema.model_validate(turn)


def validate_continuable_evidence_session_summary(
    summary: dict[str, Any],
) -> ContinuableEvidenceSessionSummarySchema:
    """Validate a plain dict as a continuable evidence session summary."""

    return ContinuableEvidenceSessionSummarySchema.model_validate(summary)


def validate_continuable_evidence_session_artifact_index(
    artifact_index: dict[str, Any],
) -> ContinuableEvidenceSessionArtifactIndexSchema:
    """Validate a plain dict as a continuable evidence session artifact index."""

    return ContinuableEvidenceSessionArtifactIndexSchema.model_validate(artifact_index)


def validate_continuable_evidence_session_resume_policy(
    resume_policy: dict[str, Any],
) -> ContinuableEvidenceSessionResumePolicySchema:
    """Validate a plain dict as a continuable evidence session resume policy."""

    return ContinuableEvidenceSessionResumePolicySchema.model_validate(resume_policy)


def validate_continuable_evidence_session_trajectory(
    trajectory: dict[str, Any],
) -> ContinuableEvidenceSessionTrajectorySchema:
    """Validate a plain dict as a continuable evidence session trajectory."""

    return ContinuableEvidenceSessionTrajectorySchema.model_validate(trajectory)


def validate_continuable_evidence_session_storage_policy(
    storage_policy: dict[str, Any],
) -> ContinuableEvidenceSessionStoragePolicySchema:
    """Validate a plain dict as a continuable evidence session storage policy."""

    return ContinuableEvidenceSessionStoragePolicySchema.model_validate(storage_policy)


def validate_continuable_evidence_session_local_state_root_policy(
    local_state_root_policy: dict[str, Any],
) -> ContinuableEvidenceSessionLocalStateRootPolicySchema:
    """Validate a plain dict as a continuable evidence session state root policy."""

    return ContinuableEvidenceSessionLocalStateRootPolicySchema.model_validate(
        local_state_root_policy
    )


def validate_continuable_evidence_session_record_manifest(
    record_manifest: dict[str, Any],
) -> ContinuableEvidenceSessionRecordManifestSchema:
    """Validate a plain dict as a continuable evidence session record manifest."""

    return ContinuableEvidenceSessionRecordManifestSchema.model_validate(
        record_manifest
    )


def validate_continuable_evidence_session_index_entry(
    index_entry: dict[str, Any],
) -> ContinuableEvidenceSessionIndexEntrySchema:
    """Validate a plain dict as a continuable evidence session index entry."""

    return ContinuableEvidenceSessionIndexEntrySchema.model_validate(index_entry)


def validate_continuable_evidence_session_delete_policy(
    delete_policy: dict[str, Any],
) -> ContinuableEvidenceSessionDeletePolicySchema:
    """Validate a plain dict as a continuable evidence session delete policy."""

    return ContinuableEvidenceSessionDeletePolicySchema.model_validate(delete_policy)


def validate_continuable_evidence_session_expiration_policy(
    expiration_policy: dict[str, Any],
) -> ContinuableEvidenceSessionExpirationPolicySchema:
    """Validate a plain dict as a continuable evidence session expiration policy."""

    return ContinuableEvidenceSessionExpirationPolicySchema.model_validate(
        expiration_policy
    )


def validate_continuable_evidence_session_export_policy(
    export_policy: dict[str, Any],
) -> ContinuableEvidenceSessionExportPolicySchema:
    """Validate a plain dict as a continuable evidence session export policy."""

    return ContinuableEvidenceSessionExportPolicySchema.model_validate(export_policy)


def validate_continuable_evidence_session_runtime_binding(
    runtime_binding: dict[str, Any],
) -> ContinuableEvidenceSessionRuntimeBindingSchema:
    """Validate a plain dict as a continuable session runtime binding."""

    return ContinuableEvidenceSessionRuntimeBindingSchema.model_validate(
        runtime_binding
    )


def validate_continuable_evidence_session_runtime_visible_summary(
    runtime_visible_summary: dict[str, Any],
) -> ContinuableEvidenceSessionRuntimeVisibleSummarySchema:
    """Validate a plain dict as a continuable session runtime visible summary."""

    return ContinuableEvidenceSessionRuntimeVisibleSummarySchema.model_validate(
        runtime_visible_summary
    )


def _validate_runtime_flags(model: BaseModel) -> None:
    for field_name in (
        "runtime_backed",
        "backed_by_adk_session",
        "backed_by_adk_event_stream",
        "backed_by_adk_artifact_service",
        "backed_by_adk_task_runtime",
        "backed_by_adk_workflow_runtime",
        "memory_enabled",
    ):
        if getattr(model, field_name, False):
            raise ValueError(f"{field_name} must be false.")


def _validate_ref_prefix(value: str, prefix: str, field_name: str) -> None:
    if not value.startswith(prefix):
        raise ValueError(f"{field_name} must start with {prefix!r}.")


def _validate_optional_ref_prefix(
    value: str | None,
    prefix: str,
    field_name: str,
) -> None:
    if value is None:
        return
    _validate_ref_prefix(value, prefix, field_name)


def _validate_optional_ref(value: str | None, *, field_name: str) -> None:
    if value is None:
        return
    _validate_ref(value, field_name=field_name)


def _validate_ref(value: str, *, field_name: str) -> None:
    if not any(value.startswith(prefix) for prefix in SAFE_REF_PREFIXES):
        raise ValueError(f"{field_name} has an unsupported product ref prefix.")


def _validate_logical_file_name(value: str) -> None:
    if not value or value.startswith("/") or ".." in value:
        raise ValueError("logical file names must be relative safe names.")
    _validate_safe_summary_text(value, field_name="logical_file_names")


def _validate_safe_summary_text(value: str | None, *, field_name: str) -> None:
    if value is None:
        return
    normalized = value.lower()
    for marker in (
        "api_key",
        "authorization:",
        "bearer ",
        "cookie:",
        "full_answer",
        "provider_response",
        "raw_prompt",
        "raw provider",
        "secret",
        "system_prompt",
        "token",
        "traceback",
    ):
        if marker in normalized:
            raise ValueError(f"{field_name} contains forbidden raw-boundary marker.")


def _validate_safe_mapping(value: dict[str, Any], *, field_name: str) -> None:
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError(f"{field_name} keys must be strings.")
        if key.lower() in FORBIDDEN_CONTINUABLE_EVIDENCE_SESSION_KEYS:
            raise ValueError(f"{field_name} contains forbidden key {key!r}.")
        if isinstance(item, dict):
            _validate_safe_mapping(item, field_name=field_name)
        elif isinstance(item, list):
            for nested in item:
                if isinstance(nested, dict):
                    _validate_safe_mapping(nested, field_name=field_name)
                elif not isinstance(nested, SAFE_METADATA_VALUE_TYPES):
                    raise ValueError(f"{field_name} contains unsafe list value.")
        elif not isinstance(item, SAFE_METADATA_VALUE_TYPES):
            raise ValueError(f"{field_name} contains unsafe value.")
        elif isinstance(item, str):
            _validate_safe_summary_text(item, field_name=field_name)


def _validate_safe_metadata(metadata: dict[str, Any], *, field_name: str) -> None:
    _validate_safe_mapping(metadata, field_name=field_name)


def _raise_if_forbidden_payload_found(payload: Any, *, path: str = "$") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key)
            normalized_key = key_text.lower()
            if normalized_key in FORBIDDEN_CONTINUABLE_EVIDENCE_SESSION_KEYS:
                raise ValueError(f"forbidden raw-boundary key at {path}.{key_text}")
            _raise_if_forbidden_payload_found(value, path=f"{path}.{key_text}")
        return
    if isinstance(payload, list):
        for index, item in enumerate(payload):
            _raise_if_forbidden_payload_found(item, path=f"{path}[{index}]")
        return
    if isinstance(payload, str):
        _validate_safe_summary_text(payload, field_name=path)


__all__ = [
    "CONTINUABLE_EVIDENCE_SESSION_ARTIFACT_INDEX_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_ARTIFACT_INDEX_REF_PREFIX",
    "CONTINUABLE_EVIDENCE_SESSION_ARTIFACT_INDEX_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_DELETE_POLICY_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_DELETE_POLICY_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_EXPIRATION_POLICY_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_EXPIRATION_POLICY_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_EXPORT_POLICY_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_EXPORT_POLICY_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_INDEX_ENTRY_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_INDEX_ENTRY_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_LOCAL_STATE_ROOT_POLICY_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_LOCAL_STATE_ROOT_POLICY_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_PRODUCT",
    "CONTINUABLE_EVIDENCE_SESSION_RECORD_MANIFEST_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_RECORD_MANIFEST_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX",
    "CONTINUABLE_EVIDENCE_SESSION_RESUME_POLICY_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_RESUME_POLICY_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_REF_PREFIX",
    "CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_RUNTIME_VISIBLE_SUMMARY_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_RUNTIME_VISIBLE_SUMMARY_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_SEED_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_SEED_REF_PREFIX",
    "CONTINUABLE_EVIDENCE_SESSION_SEED_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_STATUSES",
    "CONTINUABLE_EVIDENCE_SESSION_STORAGE_POLICY_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_STORAGE_POLICY_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_SUMMARY_KINDS",
    "CONTINUABLE_EVIDENCE_SESSION_SUMMARY_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_SUMMARY_REF_PREFIX",
    "CONTINUABLE_EVIDENCE_SESSION_SUMMARY_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_TRAJECTORY_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_TRAJECTORY_REF_PREFIX",
    "CONTINUABLE_EVIDENCE_SESSION_TRAJECTORY_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_TURN_KINDS",
    "CONTINUABLE_EVIDENCE_SESSION_TURN_PAYLOAD_TYPE",
    "CONTINUABLE_EVIDENCE_SESSION_TURN_REF_PREFIX",
    "CONTINUABLE_EVIDENCE_SESSION_TURN_STATUSES",
    "CONTINUABLE_EVIDENCE_SESSION_TURN_VERSION",
    "CONTINUABLE_EVIDENCE_SESSION_VERSION",
    "ContinuableEvidenceSessionArtifactIndexSchema",
    "ContinuableEvidenceSessionDeletePolicySchema",
    "ContinuableEvidenceSessionExpirationPolicySchema",
    "ContinuableEvidenceSessionExportPackageKind",
    "ContinuableEvidenceSessionExportPolicySchema",
    "ContinuableEvidenceSessionIndexEntrySchema",
    "ContinuableEvidenceSessionLocalStateRootKind",
    "ContinuableEvidenceSessionLocalStateRootPolicySchema",
    "ContinuableEvidenceSessionRawBoundarySummarySchema",
    "ContinuableEvidenceSessionRecordManifestSchema",
    "ContinuableEvidenceSessionRecordStatus",
    "ContinuableEvidenceSessionRefSummarySchema",
    "ContinuableEvidenceSessionResumePolicySchema",
    "ContinuableEvidenceSessionResumeStatus",
    "ContinuableEvidenceSessionRuntimeBindingSchema",
    "ContinuableEvidenceSessionRuntimeBindingScope",
    "ContinuableEvidenceSessionRuntimeBindingStatus",
    "ContinuableEvidenceSessionRuntimeEvaluationStatus",
    "ContinuableEvidenceSessionRuntimeVisibleSummarySchema",
    "ContinuableEvidenceSessionSavePolicy",
    "ContinuableEvidenceSessionSchema",
    "ContinuableEvidenceSessionSeedSchema",
    "ContinuableEvidenceSessionStatus",
    "ContinuableEvidenceSessionStoragePolicySchema",
    "ContinuableEvidenceSessionSummaryKind",
    "ContinuableEvidenceSessionSummarySchema",
    "ContinuableEvidenceSessionTrajectorySchema",
    "ContinuableEvidenceSessionTurnKind",
    "ContinuableEvidenceSessionTurnSchema",
    "ContinuableEvidenceSessionTurnStatus",
    "validate_continuable_evidence_session",
    "validate_continuable_evidence_session_artifact_index",
    "validate_continuable_evidence_session_delete_policy",
    "validate_continuable_evidence_session_expiration_policy",
    "validate_continuable_evidence_session_export_policy",
    "validate_continuable_evidence_session_index_entry",
    "validate_continuable_evidence_session_local_state_root_policy",
    "validate_continuable_evidence_session_record_manifest",
    "validate_continuable_evidence_session_resume_policy",
    "validate_continuable_evidence_session_runtime_binding",
    "validate_continuable_evidence_session_runtime_visible_summary",
    "validate_continuable_evidence_session_seed",
    "validate_continuable_evidence_session_storage_policy",
    "validate_continuable_evidence_session_summary",
    "validate_continuable_evidence_session_trajectory",
    "validate_continuable_evidence_session_turn",
]
