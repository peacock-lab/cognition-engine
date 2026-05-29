"""Product-level contracts for cognition agent carrier boundaries."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


COGNITION_AGENT_CARRIER_PRODUCT = "cognition_agent"
COGNITION_AGENT_CARRIER_PAYLOAD_TYPE = "cognition_agent_carrier"
COGNITION_AGENT_CARRIER_VERSION = "cognition_agent_carrier_v1"
COGNITION_AGENT_RESUME_REQUEST_PAYLOAD_TYPE = "cognition_agent_resume_request"
COGNITION_AGENT_RESUME_REQUEST_VERSION = "cognition_agent_resume_request_v1"
COGNITION_AGENT_RESPONSE_PROJECTION_PAYLOAD_TYPE = (
    "cognition_agent_response_projection"
)
COGNITION_AGENT_RESPONSE_PROJECTION_VERSION = (
    "cognition_agent_response_projection_v1"
)
COGNITION_AGENT_MATERIAL_CONSUMPTION_PAYLOAD_TYPE = (
    "cognition_agent_material_consumption"
)
COGNITION_AGENT_MATERIAL_CONSUMPTION_VERSION = (
    "cognition_agent_material_consumption_v1"
)

COGNITION_AGENT_CARRIER_REF_PREFIX = "cognition-agent-carrier://"
COGNITION_AGENT_RESUME_REQUEST_REF_PREFIX = "cognition-agent-resume-request://"
COGNITION_AGENT_RESPONSE_REF_PREFIX = "cognition-agent-response://"
COGNITION_AGENT_MATERIAL_CONSUMPTION_REF_PREFIX = (
    "cognition-agent-material-consumption://"
)

COGNITION_AGENT_CARRIER_STATUSES = frozenset(
    {"candidate_only", "contract_ready", "blocked", "unavailable"}
)
COGNITION_AGENT_CARRIER_SCOPES = frozenset({"continuable_evidence_session"})
COGNITION_AGENT_RESUME_AUTHORIZATION_STATES = frozenset(
    {
        "requires_confirmation",
        "authorized",
        "blocked",
        "expired",
        "deleted",
        "unavailable",
    }
)

CognitionAgentCarrierStatus = Literal[
    "candidate_only",
    "contract_ready",
    "blocked",
    "unavailable",
]
CognitionAgentCarrierScope = Literal["continuable_evidence_session"]
CognitionAgentResumeAuthorizationState = Literal[
    "requires_confirmation",
    "authorized",
    "blocked",
    "expired",
    "deleted",
    "unavailable",
]

SAFE_REF_PREFIXES = (
    COGNITION_AGENT_CARRIER_REF_PREFIX,
    COGNITION_AGENT_RESUME_REQUEST_REF_PREFIX,
    COGNITION_AGENT_RESPONSE_REF_PREFIX,
    COGNITION_AGENT_MATERIAL_CONSUMPTION_REF_PREFIX,
    "continuable-evidence-session://",
    "continuable-evidence-session-runtime-binding://",
    "evidence://external-readonly/",
    "governed-evidence-digest://",
    "evidence-summary-answer-context://",
    "evidence-summary-answer-run://",
    "evidence-summary-answer-artifact://",
    "evidence-summary-answer-trace-inspect://",
    "evidence-summary-answer-observability-summary://",
    "evaluation://",
)

FORBIDDEN_COGNITION_AGENT_CARRIER_KEYS = frozenset(
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
        "full_answer",
        "full_prompt",
        "full_response",
        "google_adk_object",
        "headers",
        "html",
        "message",
        "messages",
        "password",
        "prompt",
        "provider_implementation",
        "provider_payload",
        "provider_response",
        "raw",
        "raw_adk_agent",
        "raw_adk_artifact",
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
        "secret",
        "system_prompt",
        "token",
        "traceback",
        "user_question",
    }
)
SAFE_METADATA_VALUE_TYPES = (str, int, float, bool, type(None))


class CognitionAgentCarrierBaseModel(BaseModel):
    """Base model for cognition agent carrier contracts."""

    model_config = ConfigDict(extra="forbid")


class CognitionAgentCarrierSchema(CognitionAgentCarrierBaseModel):
    """Product-level cognition agent carrier reference."""

    product: Literal["cognition_agent"] = COGNITION_AGENT_CARRIER_PRODUCT
    payload_type: Literal["cognition_agent_carrier"] = (
        COGNITION_AGENT_CARRIER_PAYLOAD_TYPE
    )
    payload_version: Literal["cognition_agent_carrier_v1"] = (
        COGNITION_AGENT_CARRIER_VERSION
    )
    agent_carrier_id: str = Field(..., min_length=1)
    agent_carrier_ref: str = Field(..., min_length=1)
    agent_carrier_status: CognitionAgentCarrierStatus = "candidate_only"
    agent_carrier_scope: CognitionAgentCarrierScope = "continuable_evidence_session"
    product_intent_summary: str = Field(..., min_length=1, max_length=1200)
    continuable_evidence_session_ref: str | None = None
    evidence_material_refs: list[str] = Field(default_factory=list)
    runtime_binding_refs: list[str] = Field(default_factory=list)
    response_projection_refs: list[str] = Field(default_factory=list)
    candidate_only: bool = True
    readonly: bool = True
    execution_enabled: bool = False
    agent_runtime_enabled: bool = False
    adk_raw_object_included: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_carrier(self) -> "CognitionAgentCarrierSchema":
        _validate_ref_prefix(
            self.agent_carrier_ref,
            COGNITION_AGENT_CARRIER_REF_PREFIX,
            "agent_carrier_ref",
        )
        _validate_optional_ref_prefix(
            self.continuable_evidence_session_ref,
            "continuable-evidence-session://",
            "continuable_evidence_session_ref",
        )
        for field_name in (
            "evidence_material_refs",
            "runtime_binding_refs",
            "response_projection_refs",
        ):
            _validate_ref_list(getattr(self, field_name), field_name=field_name)
        _validate_candidate_boundary(self)
        _validate_safe_summary_text(
            self.product_intent_summary,
            field_name="product_intent_summary",
        )
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class CognitionAgentResumeRequestSchema(CognitionAgentCarrierBaseModel):
    """Product-level request to prepare a user-authorized resume."""

    product: Literal["cognition_agent"] = COGNITION_AGENT_CARRIER_PRODUCT
    payload_type: Literal["cognition_agent_resume_request"] = (
        COGNITION_AGENT_RESUME_REQUEST_PAYLOAD_TYPE
    )
    payload_version: Literal["cognition_agent_resume_request_v1"] = (
        COGNITION_AGENT_RESUME_REQUEST_VERSION
    )
    agent_resume_request_id: str = Field(..., min_length=1)
    agent_resume_request_ref: str = Field(..., min_length=1)
    agent_carrier_ref: str = Field(..., min_length=1)
    continuable_evidence_session_ref: str = Field(..., min_length=1)
    resume_authorization_state: CognitionAgentResumeAuthorizationState = (
        "requires_confirmation"
    )
    evidence_material_refs: list[str] = Field(default_factory=list)
    runtime_binding_refs: list[str] = Field(default_factory=list)
    requested_user_action: str = Field(..., min_length=1, max_length=240)
    blocking_reasons: list[str] = Field(default_factory=list)
    requires_user_confirmation: bool = True
    requires_external_readonly_authorization: bool = True
    auto_resume_answer_enabled: bool = False
    model_call_requested: bool = False
    user_product_runtime_path_enabled: bool = False
    workflow_replay_enabled: bool = False
    task_runtime_implementation_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_resume_request(self) -> "CognitionAgentResumeRequestSchema":
        _validate_ref_prefix(
            self.agent_resume_request_ref,
            COGNITION_AGENT_RESUME_REQUEST_REF_PREFIX,
            "agent_resume_request_ref",
        )
        _validate_ref_prefix(
            self.agent_carrier_ref,
            COGNITION_AGENT_CARRIER_REF_PREFIX,
            "agent_carrier_ref",
        )
        _validate_ref_prefix(
            self.continuable_evidence_session_ref,
            "continuable-evidence-session://",
            "continuable_evidence_session_ref",
        )
        _validate_ref_list(self.evidence_material_refs, field_name="evidence_material_refs")
        _validate_ref_list(self.runtime_binding_refs, field_name="runtime_binding_refs")
        if self.requires_user_confirmation is not True:
            raise ValueError("resume request must require user confirmation.")
        if self.requires_external_readonly_authorization is not True:
            raise ValueError("resume request must require material authorization.")
        if self.resume_authorization_state in {
            "blocked",
            "expired",
            "deleted",
            "unavailable",
        } and not self.blocking_reasons:
            raise ValueError(
                f"{self.resume_authorization_state} requests require blocking_reasons."
            )
        _validate_false_flags(
            self,
            (
                "auto_resume_answer_enabled",
                "model_call_requested",
                "user_product_runtime_path_enabled",
                "workflow_replay_enabled",
                "task_runtime_implementation_enabled",
            ),
        )
        _validate_safe_summary_text(
            self.requested_user_action,
            field_name="requested_user_action",
        )
        for reason in self.blocking_reasons:
            _validate_safe_summary_text(reason, field_name="blocking_reasons")
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class CognitionAgentResponseProjectionSchema(CognitionAgentCarrierBaseModel):
    """Safe response projection candidate for future product gateway output."""

    product: Literal["cognition_agent"] = COGNITION_AGENT_CARRIER_PRODUCT
    payload_type: Literal["cognition_agent_response_projection"] = (
        COGNITION_AGENT_RESPONSE_PROJECTION_PAYLOAD_TYPE
    )
    payload_version: Literal["cognition_agent_response_projection_v1"] = (
        COGNITION_AGENT_RESPONSE_PROJECTION_VERSION
    )
    agent_response_id: str = Field(..., min_length=1)
    agent_response_ref: str = Field(..., min_length=1)
    agent_carrier_ref: str = Field(..., min_length=1)
    agent_resume_request_ref: str | None = None
    answer_run_ref: str | None = None
    answer_artifact_ref: str | None = None
    trace_inspect_ref: str | None = None
    observability_summary_ref: str | None = None
    evaluation_summary_ref: str | None = None
    recovery_hints: list[str] = Field(default_factory=list)
    boundary_hints: list[str] = Field(default_factory=list)
    raw_provider_response_included: bool = False
    full_answer_persistence_claim: bool = False
    llm_call_performed: bool = False
    product_gateway_user_visible: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_response_projection(
        self,
    ) -> "CognitionAgentResponseProjectionSchema":
        _validate_ref_prefix(
            self.agent_response_ref,
            COGNITION_AGENT_RESPONSE_REF_PREFIX,
            "agent_response_ref",
        )
        _validate_ref_prefix(
            self.agent_carrier_ref,
            COGNITION_AGENT_CARRIER_REF_PREFIX,
            "agent_carrier_ref",
        )
        _validate_optional_ref_prefix(
            self.agent_resume_request_ref,
            COGNITION_AGENT_RESUME_REQUEST_REF_PREFIX,
            "agent_resume_request_ref",
        )
        for field_name in (
            "answer_run_ref",
            "answer_artifact_ref",
            "trace_inspect_ref",
            "observability_summary_ref",
            "evaluation_summary_ref",
        ):
            _validate_optional_ref(getattr(self, field_name), field_name=field_name)
        _validate_false_flags(
            self,
            (
                "raw_provider_response_included",
                "full_answer_persistence_claim",
                "llm_call_performed",
                "product_gateway_user_visible",
            ),
        )
        for field_name in ("recovery_hints", "boundary_hints"):
            for hint in getattr(self, field_name):
                _validate_safe_summary_text(hint, field_name=field_name)
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


class CognitionAgentMaterialConsumptionSchema(CognitionAgentCarrierBaseModel):
    """Refs-only material consumption contract for external-readonly facts."""

    product: Literal["cognition_agent"] = COGNITION_AGENT_CARRIER_PRODUCT
    payload_type: Literal["cognition_agent_material_consumption"] = (
        COGNITION_AGENT_MATERIAL_CONSUMPTION_PAYLOAD_TYPE
    )
    payload_version: Literal["cognition_agent_material_consumption_v1"] = (
        COGNITION_AGENT_MATERIAL_CONSUMPTION_VERSION
    )
    material_consumption_id: str = Field(..., min_length=1)
    material_consumption_ref: str = Field(..., min_length=1)
    agent_carrier_ref: str = Field(..., min_length=1)
    source_layer: Literal["external_readonly"] = "external_readonly"
    evidence_refs: list[str] = Field(default_factory=list)
    digest_refs: list[str] = Field(default_factory=list)
    answer_context_refs: list[str] = Field(default_factory=list)
    answer_run_refs: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    trace_inspect_refs: list[str] = Field(default_factory=list)
    observability_summary_refs: list[str] = Field(default_factory=list)
    refs_only: bool = True
    implementation_object_included: bool = False
    provider_implementation_included: bool = False
    raw_evidence_included: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_material_consumption(
        self,
    ) -> "CognitionAgentMaterialConsumptionSchema":
        _validate_ref_prefix(
            self.material_consumption_ref,
            COGNITION_AGENT_MATERIAL_CONSUMPTION_REF_PREFIX,
            "material_consumption_ref",
        )
        _validate_ref_prefix(
            self.agent_carrier_ref,
            COGNITION_AGENT_CARRIER_REF_PREFIX,
            "agent_carrier_ref",
        )
        for field_name in (
            "evidence_refs",
            "digest_refs",
            "answer_context_refs",
            "answer_run_refs",
            "artifact_refs",
            "trace_inspect_refs",
            "observability_summary_refs",
        ):
            _validate_ref_list(getattr(self, field_name), field_name=field_name)
        if not self.evidence_refs:
            raise ValueError("material consumption requires evidence_refs.")
        if not self.digest_refs:
            raise ValueError("material consumption requires digest_refs.")
        if self.refs_only is not True:
            raise ValueError("material consumption must remain refs-only.")
        _validate_false_flags(
            self,
            (
                "implementation_object_included",
                "provider_implementation_included",
                "raw_evidence_included",
            ),
        )
        _validate_safe_metadata(self.metadata, field_name="metadata")
        _raise_if_forbidden_payload_found(self.model_dump(mode="python"))
        return self


def validate_cognition_agent_carrier(
    carrier: dict[str, Any],
) -> CognitionAgentCarrierSchema:
    """Validate a plain dict as a cognition agent carrier contract."""

    return CognitionAgentCarrierSchema.model_validate(carrier)


def validate_cognition_agent_resume_request(
    resume_request: dict[str, Any],
) -> CognitionAgentResumeRequestSchema:
    """Validate a plain dict as a cognition agent resume request."""

    return CognitionAgentResumeRequestSchema.model_validate(resume_request)


def validate_cognition_agent_response_projection(
    response_projection: dict[str, Any],
) -> CognitionAgentResponseProjectionSchema:
    """Validate a plain dict as a cognition agent response projection."""

    return CognitionAgentResponseProjectionSchema.model_validate(response_projection)


def validate_cognition_agent_material_consumption(
    material_consumption: dict[str, Any],
) -> CognitionAgentMaterialConsumptionSchema:
    """Validate a plain dict as a cognition agent material consumption contract."""

    return CognitionAgentMaterialConsumptionSchema.model_validate(material_consumption)


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


def _validate_ref(value: str, *, field_name: str) -> None:
    if not any(value.startswith(prefix) for prefix in SAFE_REF_PREFIXES):
        raise ValueError(f"{field_name} has an unsupported product ref prefix.")


def _validate_optional_ref(value: str | None, *, field_name: str) -> None:
    if value is None:
        return
    _validate_ref(value, field_name=field_name)


def _validate_ref_list(values: list[str], *, field_name: str) -> None:
    for value in values:
        _validate_ref(value, field_name=field_name)


def _validate_candidate_boundary(model: BaseModel) -> None:
    if getattr(model, "candidate_only", True) is not True:
        raise ValueError("candidate_only must be true.")
    if getattr(model, "readonly", True) is not True:
        raise ValueError("readonly must be true.")
    _validate_false_flags(
        model,
        (
            "execution_enabled",
            "agent_runtime_enabled",
            "adk_raw_object_included",
        ),
    )


def _validate_false_flags(model: BaseModel, field_names: tuple[str, ...]) -> None:
    for field_name in field_names:
        if getattr(model, field_name, False):
            raise ValueError(f"{field_name} must be false.")


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
        "google.adk",
        "provider_response",
        "raw prompt",
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
        if key.lower() in FORBIDDEN_COGNITION_AGENT_CARRIER_KEYS:
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
            if normalized_key in FORBIDDEN_COGNITION_AGENT_CARRIER_KEYS:
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
    "COGNITION_AGENT_CARRIER_PAYLOAD_TYPE",
    "COGNITION_AGENT_CARRIER_PRODUCT",
    "COGNITION_AGENT_CARRIER_REF_PREFIX",
    "COGNITION_AGENT_CARRIER_SCOPES",
    "COGNITION_AGENT_CARRIER_STATUSES",
    "COGNITION_AGENT_CARRIER_VERSION",
    "COGNITION_AGENT_MATERIAL_CONSUMPTION_PAYLOAD_TYPE",
    "COGNITION_AGENT_MATERIAL_CONSUMPTION_REF_PREFIX",
    "COGNITION_AGENT_MATERIAL_CONSUMPTION_VERSION",
    "COGNITION_AGENT_RESPONSE_PROJECTION_PAYLOAD_TYPE",
    "COGNITION_AGENT_RESPONSE_PROJECTION_VERSION",
    "COGNITION_AGENT_RESPONSE_REF_PREFIX",
    "COGNITION_AGENT_RESUME_AUTHORIZATION_STATES",
    "COGNITION_AGENT_RESUME_REQUEST_PAYLOAD_TYPE",
    "COGNITION_AGENT_RESUME_REQUEST_REF_PREFIX",
    "COGNITION_AGENT_RESUME_REQUEST_VERSION",
    "CognitionAgentCarrierSchema",
    "CognitionAgentCarrierScope",
    "CognitionAgentCarrierStatus",
    "CognitionAgentMaterialConsumptionSchema",
    "CognitionAgentResponseProjectionSchema",
    "CognitionAgentResumeAuthorizationState",
    "CognitionAgentResumeRequestSchema",
    "validate_cognition_agent_carrier",
    "validate_cognition_agent_material_consumption",
    "validate_cognition_agent_response_projection",
    "validate_cognition_agent_resume_request",
]
