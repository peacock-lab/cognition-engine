"""Runtime-facing configuration contexts for Cognition Engine."""

from __future__ import annotations

from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from schemas.evidence_summary_answer import (
    SUMMARY_FACT_ITEM_MAX_CHARS,
    SUMMARY_FACT_MAX_CHARS,
    SUMMARY_FACT_MAX_ITEMS,
)

from config_contexts.governance import GovernanceConfigContext


SENSITIVE_CONFIG_METADATA_KEYS = frozenset(
    {
        "approval",
        "approval_ref",
        "api_key",
        "authorization",
        "command",
        "credential",
        "credentials",
        "password",
        "raw",
        "raw_payload",
        "raw_tool_input",
        "raw_tool_output",
        "secret",
        "token",
        "tool_confirmation_approval_ref",
    }
)


class ExecutionMode(str, Enum):
    """Runtime execution mode."""

    LOCAL = "local"
    REMOTE = "remote"
    HYBRID = "hybrid"
    TEST = "test"


class RuntimeConfigBaseModel(BaseModel):
    """Base model for runtime configuration views."""

    model_config = ConfigDict(extra="forbid")


class RuntimeConfigSelectionContext(RuntimeConfigBaseModel):
    """Runtime configuration source and profile selection context."""

    config_root: str | None = None
    environment: str = Field(default="local", min_length=1)
    profile: str | None = None
    selection_source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_selection_context(self) -> "RuntimeConfigSelectionContext":
        forbidden_paths = _sensitive_metadata_paths(self.metadata)
        if forbidden_paths:
            raise ValueError(
                "Runtime config selection metadata must not include "
                "sensitive fields: "
                + ", ".join(forbidden_paths)
            )
        return self


class RuntimeLiveLlmInvocationOptionsContext(RuntimeConfigBaseModel):
    """Runtime live LLM invocation override and selection context."""

    ollama_api_base: str | None = None
    timeout_seconds: int | None = Field(default=None, gt=0)
    max_tokens: int | None = Field(default=None, gt=0)
    response_preview_limit: int | None = Field(default=None, gt=0)
    provider_profile_ref: str | None = Field(default=None, min_length=1)
    model_profile_ref: str | None = Field(default=None, min_length=1)
    output_governance_profile_ref: str | None = Field(default=None, min_length=1)
    network_gate_open: bool = False
    operator_approved: bool = False
    approval_ref: str | None = Field(default=None, min_length=1)
    audit_ref: str | None = Field(default=None, min_length=1)
    selection_source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_invocation_options(self) -> "RuntimeLiveLlmInvocationOptionsContext":
        forbidden_paths = _sensitive_metadata_paths(self.metadata)
        if forbidden_paths:
            raise ValueError(
                "Runtime live LLM invocation options metadata must not "
                "include sensitive fields: "
                + ", ".join(forbidden_paths)
            )
        return self


class RuntimeConfigView(RuntimeConfigBaseModel):
    """Runtime execution configuration view."""

    runtime_name: str
    execution_mode: ExecutionMode = ExecutionMode.LOCAL
    default_workflow_name: str | None = None
    enable_event_capture: bool = True
    enable_state_delta_capture: bool = True
    enable_artifact_delta_capture: bool = True
    default_adapter: str = "local"
    timeout_seconds: int = Field(default=300, gt=0)
    retry_policy_ref: str | None = None


class WorkflowExecutionConfigView(RuntimeConfigBaseModel):
    """Workflow execution policy configuration view."""

    workflow_name: str
    graph_mode: bool = True
    allow_dynamic_nodes: bool = True
    allow_collaborative_agents: bool = False
    max_node_count: int = Field(default=100, gt=0)
    max_execution_depth: int = Field(default=20, gt=0)
    timeout_seconds: int = Field(default=300, gt=0)


class NodeExecutionConfigView(RuntimeConfigBaseModel):
    """Node execution policy configuration view."""

    node_execution_mode: str = "isolated"
    enable_node_isolation: bool = True
    timeout_seconds: int = Field(default=120, gt=0)
    max_retries: int = Field(default=0, ge=0)
    allow_parallel_execution: bool = False


class ResumePolicyConfigView(RuntimeConfigBaseModel):
    """Resume and HITL policy configuration view."""

    enable_resume: bool = True
    enable_hitl: bool = False
    resume_storage_policy: str = "local"
    resume_token_ttl_seconds: int = Field(default=3600, gt=0)
    require_human_confirmation: bool = False

    @model_validator(mode="after")
    def validate_hitl_requires_resume(self) -> "ResumePolicyConfigView":
        """HITL requires resume support."""
        if self.enable_hitl and not self.enable_resume:
            raise ValueError("enable_hitl requires enable_resume")
        return self


class EventPolicyConfigView(RuntimeConfigBaseModel):
    """Event capture and output policy configuration view."""

    enable_event_stream: bool = True
    capture_node_events: bool = True
    capture_state_deltas: bool = True
    capture_artifact_deltas: bool = True
    event_sink_name: str = "local"


class ArtifactPolicyConfigView(RuntimeConfigBaseModel):
    """Artifact capture and publishing policy configuration view."""

    enable_artifact_capture: bool = True
    artifact_sink_name: str = "local"
    artifact_name_prefix: str = "ce-runtime"
    artifact_version_policy: str = "timestamp"


class AdapterSelectionConfigView(RuntimeConfigBaseModel):
    """Runtime adapter selection configuration view."""

    default_runtime_adapter: str = "local"
    adk_adapter_enabled: bool = False
    litellm_adapter_enabled: bool = False
    hermes_adapter_enabled: bool = False
    openclaw_adapter_enabled: bool = False
    fallback_adapter: str | None = "local"


class AdkRunConfigView(RuntimeConfigBaseModel):
    """Runtime-facing ADK RunConfig configuration view."""

    speech_config: dict[str, Any] | None = None
    max_llm_calls: int | None = Field(default=None, gt=0)
    response_modalities: tuple[str, ...] | None = None
    avatar_config: dict[str, Any] | None = None
    support_cfc: bool | None = None
    streaming_mode: Literal["none", "sse", "bidi"] | None = None
    output_audio_transcription: dict[str, Any] | None = None
    input_audio_transcription: dict[str, Any] | None = None
    realtime_input_config: dict[str, Any] | None = None
    enable_affective_dialog: bool | None = None
    proactivity: dict[str, Any] | None = None
    session_resumption: dict[str, Any] | None = None
    context_window_compression: dict[str, Any] | None = None
    save_live_blob: bool | None = None
    tool_thread_pool_config: dict[str, Any] | None = None
    save_live_audio: bool | None = None
    get_session_num_recent_events: int | None = Field(default=None, ge=0)
    get_session_after_timestamp: float | None = None
    custom_metadata: dict[str, Any] = Field(default_factory=dict)


class SessionPolicyConfigView(RuntimeConfigBaseModel):
    """Session facts and state-summary policy configuration view."""

    enable_session_facts: bool = True
    capture_session_state_keys: bool = True
    max_state_key_count: int = Field(default=50, gt=0)
    state_key_sanitization: str = "keys_only"
    session_service_source: str = "in_memory"


class RuntimeProductizationGateConfigView(RuntimeConfigBaseModel):
    """Runtime-facing productization gate configuration view."""

    gate_id: str = "runtime-productization-gate"
    request_adk_run: bool = False
    request_live_llm: bool = False
    request_ollama: bool = False
    allow_adk_run: bool = False
    allow_live_llm: bool = False
    allow_ollama: bool = False
    explicit_operator_approval: bool = False
    sanitized_evidence_ref: str | None = None
    governance_summary_output_ref: str | None = None
    audit_ref: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeLlmProviderProfileConfigView(RuntimeConfigBaseModel):
    """Provider-level live LLM route profile consumed by runtime assembly."""

    provider: str = Field(default="litellm", min_length=1)
    backend_provider: str = Field(default="ollama", min_length=1)
    route_kind: str = Field(default="adk_litellm", min_length=1)
    api_base: str | None = Field(default="http://127.0.0.1:11434", min_length=1)
    api_base_env_var: str | None = Field(default=None, min_length=1)
    secret_ref: str | None = Field(default=None, min_length=1)
    network_access: Literal["local_only", "external_gated"] = "local_only"
    requires_network_gate: bool = False
    requires_operator_approval: bool = False
    requires_audit_ref: bool = False
    enabled_by_default: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_provider_profile(self) -> "RuntimeLlmProviderProfileConfigView":
        """Keep provider profile facts safe and non-executing."""

        if self.api_base_env_var and not _safe_env_var_name(self.api_base_env_var):
            raise ValueError("api_base_env_var must be a safe environment variable name.")
        if self.network_access == "external_gated":
            if not self.requires_network_gate:
                raise ValueError("external_gated provider profiles require network gate.")
            if not self.requires_operator_approval:
                raise ValueError(
                    "external_gated provider profiles require operator approval."
                )
            if not self.requires_audit_ref:
                raise ValueError("external_gated provider profiles require audit ref.")
        forbidden_paths = _sensitive_metadata_paths(self.metadata)
        if forbidden_paths:
            raise ValueError(
                "Provider profile metadata must not include sensitive fields: "
                + ", ".join(forbidden_paths)
            )
        return self


class RuntimeLlmModelProfileConfigView(RuntimeConfigBaseModel):
    """Model-level live LLM profile consumed by runtime assembly."""

    provider_profile_ref: str = Field(default="local_ollama", min_length=1)
    model_name: str = Field(default="ollama/gemma4-pro:latest", min_length=1)
    model_role: str = Field(default="local_debug_baseline", min_length=1)
    timeout_seconds: int = Field(default=45, gt=0)
    temperature: float = Field(default=0, ge=0)
    max_tokens: int = Field(default=64, gt=0)
    context_window: int | None = Field(default=None, gt=0)
    num_ctx: int | None = Field(default=None, gt=0)
    resource_tier: Literal[
        "local_debug",
        "standard",
        "high_memory",
        "external_managed",
    ] = "local_debug"
    enabled_by_default: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_model_profile(self) -> "RuntimeLlmModelProfileConfigView":
        """Keep model profile limits coherent and non-sensitive."""

        declared_windows = [
            value
            for value in (self.context_window, self.num_ctx)
            if value is not None
        ]
        if declared_windows and self.max_tokens > min(declared_windows):
            raise ValueError("max_tokens must not exceed declared context window.")
        forbidden_paths = _sensitive_metadata_paths(self.metadata)
        if forbidden_paths:
            raise ValueError(
                "Model profile metadata must not include sensitive fields: "
                + ", ".join(forbidden_paths)
            )
        return self


class RuntimeLlmOutputGovernanceProfileConfigView(RuntimeConfigBaseModel):
    """Output governance profile for controlled live LLM answer generation."""

    mode: Literal[
        "direct_controlled_live",
        "adk_output_schema",
        "adk_no_output_schema",
    ] = "direct_controlled_live"
    adk_native: bool = False
    uses_output_schema: bool = False
    uses_output_key: bool = False
    uses_after_model_callback: bool = False
    uses_answer_quality_guard: Literal[True] = True
    max_repair_attempts: int = Field(default=0, ge=0)
    enabled_by_default: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_output_governance_profile(
        self,
    ) -> "RuntimeLlmOutputGovernanceProfileConfigView":
        """Keep output governance mode flags internally coherent."""

        if self.mode == "direct_controlled_live":
            if self.adk_native:
                raise ValueError("direct_controlled_live must not be ADK-native.")
            if self.uses_output_schema or self.uses_output_key:
                raise ValueError(
                    "direct_controlled_live must not use output_schema or output_key."
                )
            if self.uses_after_model_callback:
                raise ValueError(
                    "direct_controlled_live must not use after_model_callback."
                )
        if self.mode == "adk_output_schema":
            if not self.adk_native:
                raise ValueError("adk_output_schema requires adk_native.")
            if not self.uses_output_schema or not self.uses_output_key:
                raise ValueError(
                    "adk_output_schema requires output_schema and output_key."
                )
            if not self.uses_after_model_callback:
                raise ValueError("adk_output_schema requires after_model_callback.")
        if self.mode == "adk_no_output_schema":
            if not self.adk_native:
                raise ValueError("adk_no_output_schema requires adk_native.")
            if self.uses_output_schema or self.uses_output_key:
                raise ValueError(
                    "adk_no_output_schema must not use output_schema or output_key."
                )
            if not self.uses_after_model_callback:
                raise ValueError("adk_no_output_schema requires after_model_callback.")
        forbidden_paths = _sensitive_metadata_paths(self.metadata)
        if forbidden_paths:
            raise ValueError(
                "Output governance profile metadata must not include sensitive fields: "
                + ", ".join(forbidden_paths)
            )
        return self


class RuntimeLlmModelAliasConfigView(RuntimeConfigBaseModel):
    """User-facing live LLM model alias backed by explicit profile refs."""

    provider_profile_ref: str = Field(min_length=1)
    model_profile_ref: str = Field(min_length=1)
    output_governance_profile_ref: str = Field(min_length=1)
    model_name: str | None = Field(default=None, min_length=1)
    enabled_by_default: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_model_alias(self) -> "RuntimeLlmModelAliasConfigView":
        """Keep user-facing aliases non-sensitive and profile-backed."""

        forbidden_paths = _sensitive_metadata_paths(self.metadata)
        if forbidden_paths:
            raise ValueError(
                "Model alias metadata must not include sensitive fields: "
                + ", ".join(forbidden_paths)
            )
        return self


class RuntimeLiveLlmConfigView(RuntimeConfigBaseModel):
    """Runtime-facing controlled-live LLM invocation configuration view."""

    profile: str = "adk_litellm_ollama"
    model_name: str = "ollama/gemma4-pro:latest"
    ollama_api_base: str = "http://127.0.0.1:11434"
    timeout_seconds: int = Field(default=45, gt=0)
    temperature: float = Field(default=0, ge=0)
    max_tokens: int = Field(default=64, gt=0)
    enabled_by_default: bool = False
    default_provider_profile_ref: str = "local_ollama"
    provider_profiles: dict[str, RuntimeLlmProviderProfileConfigView] = Field(
        default_factory=lambda: {
            "local_ollama": RuntimeLlmProviderProfileConfigView(),
            "deepseek_gated": RuntimeLlmProviderProfileConfigView(
                backend_provider="deepseek",
                route_kind="adk_litellm_openai_compatible",
                api_base="https://api.deepseek.com",
                api_base_env_var="DEEPSEEK_API_BASE",
                secret_ref="secret-ref://env/DEEPSEEK_API_KEY",
                network_access="external_gated",
                requires_network_gate=True,
                requires_operator_approval=True,
                requires_audit_ref=True,
                enabled_by_default=False,
                metadata={
                    "candidate_only": True,
                    "product_optional_provider": True,
                },
            ),
        }
    )
    default_model_profile_ref: str = "gemma4_pro_local"
    model_profiles: dict[str, RuntimeLlmModelProfileConfigView] = Field(
        default_factory=lambda: {
            "gemma4_pro_local": RuntimeLlmModelProfileConfigView(max_tokens=256),
            "deepseek_v4_flash_external": RuntimeLlmModelProfileConfigView(
                provider_profile_ref="deepseek_gated",
                model_name="deepseek/deepseek-v4-flash",
                model_role="external_low_hardware_candidate",
                timeout_seconds=180,
                max_tokens=256,
                resource_tier="external_managed",
                enabled_by_default=False,
                metadata={
                    "candidate_only": True,
                    "model_family": "deepseek_v4",
                    "model_release": "v4",
                    "thinking_mode": "disabled",
                },
            ),
            "deepseek_v4_pro_external": RuntimeLlmModelProfileConfigView(
                provider_profile_ref="deepseek_gated",
                model_name="deepseek/deepseek-v4-pro",
                model_role="external_high_quality_candidate",
                timeout_seconds=180,
                max_tokens=256,
                resource_tier="external_managed",
                enabled_by_default=False,
                metadata={
                    "candidate_only": True,
                    "model_family": "deepseek_v4",
                    "model_release": "v4",
                    "thinking_mode": "disabled",
                },
            ),
        }
    )
    default_output_governance_profile_ref: str = "direct_controlled_live"
    output_governance_profiles: dict[
        str,
        RuntimeLlmOutputGovernanceProfileConfigView,
    ] = Field(
        default_factory=lambda: {
            "direct_controlled_live": RuntimeLlmOutputGovernanceProfileConfigView(),
            "adk_output_schema_gemma4_baseline": (
                RuntimeLlmOutputGovernanceProfileConfigView(
                    mode="adk_output_schema",
                    adk_native=True,
                    uses_output_schema=True,
                    uses_output_key=True,
                    uses_after_model_callback=True,
                    max_repair_attempts=1,
                    enabled_by_default=False,
                    metadata={
                        "profile_gated": True,
                        "local_gemma4_baseline": True,
                    },
                )
            ),
            "adk_no_output_schema_candidate": (
                RuntimeLlmOutputGovernanceProfileConfigView(
                    mode="adk_no_output_schema",
                    adk_native=True,
                    uses_after_model_callback=True,
                    max_repair_attempts=1,
                    enabled_by_default=False,
                    metadata={"candidate_only": True},
                )
            ),
        }
    )
    model_aliases: dict[str, RuntimeLlmModelAliasConfigView] = Field(
        default_factory=lambda: {
            "gemma4": RuntimeLlmModelAliasConfigView(
                provider_profile_ref="local_ollama",
                model_profile_ref="gemma4_pro_local",
                output_governance_profile_ref="adk_output_schema_gemma4_baseline",
                model_name="ollama/gemma4-pro:latest",
                enabled_by_default=False,
                metadata={
                    "user_facing": True,
                    "adk_native_output_governance": True,
                },
            ),
            "deepseek": RuntimeLlmModelAliasConfigView(
                provider_profile_ref="deepseek_gated",
                model_profile_ref="deepseek_v4_flash_external",
                output_governance_profile_ref="adk_no_output_schema_candidate",
                model_name="deepseek/deepseek-v4-flash",
                enabled_by_default=False,
                metadata={
                    "user_facing": True,
                    "product_optional_provider": True,
                    "thinking_mode": "disabled",
                },
            ),
        }
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_live_llm_config(self) -> "RuntimeLiveLlmConfigView":
        """Validate live LLM profile refs while preserving legacy fields."""

        if not _profile_keys_are_safe(self.provider_profiles):
            raise ValueError("provider profile names must be non-empty.")
        if not _profile_keys_are_safe(self.model_profiles):
            raise ValueError("model profile names must be non-empty.")
        if not _profile_keys_are_safe(self.output_governance_profiles):
            raise ValueError("output governance profile names must be non-empty.")
        if not _profile_keys_are_safe(self.model_aliases):
            raise ValueError("model alias names must be non-empty.")
        if self.default_provider_profile_ref not in self.provider_profiles:
            raise ValueError("default_provider_profile_ref must exist in provider_profiles.")
        if self.default_model_profile_ref not in self.model_profiles:
            raise ValueError("default_model_profile_ref must exist in model_profiles.")
        if (
            self.default_output_governance_profile_ref
            not in self.output_governance_profiles
        ):
            raise ValueError(
                "default_output_governance_profile_ref must exist in "
                "output_governance_profiles."
            )
        for name, profile in self.model_profiles.items():
            if profile.provider_profile_ref not in self.provider_profiles:
                raise ValueError(
                    f"model profile {name} references unknown provider profile."
                )
        for name, alias in self.model_aliases.items():
            if alias.provider_profile_ref not in self.provider_profiles:
                raise ValueError(
                    f"model alias {name} references unknown provider profile."
                )
            if alias.model_profile_ref not in self.model_profiles:
                raise ValueError(
                    f"model alias {name} references unknown model profile."
                )
            if (
                alias.output_governance_profile_ref
                not in self.output_governance_profiles
            ):
                raise ValueError(
                    f"model alias {name} references unknown output governance profile."
                )
            model_profile = self.model_profiles[alias.model_profile_ref]
            if alias.provider_profile_ref != model_profile.provider_profile_ref:
                raise ValueError(
                    f"model alias {name} provider ref must match model profile."
                )
            if alias.model_name and alias.model_name != model_profile.model_name:
                raise ValueError(
                    f"model alias {name} model name must match model profile."
                )
        forbidden_paths = _sensitive_metadata_paths(self.metadata)
        if forbidden_paths:
            raise ValueError(
                "Runtime live LLM metadata must not include sensitive fields: "
                + ", ".join(forbidden_paths)
            )
        return self


class EvidenceSummaryAnswerPolicyConfigView(RuntimeConfigBaseModel):
    """Runtime-facing evidence summary answer policy configuration view."""

    enabled_by_default: Literal[False] = False
    profile: Literal["smoke_only", "controlled_live_answer_generation"] = "smoke_only"
    exposure_enabled: bool = True
    allow_model_context: bool = True
    allow_governed_summary_facts: Literal[True] = True
    allow_answer_generation_success: bool = False
    requires_live_llm_gate: Literal[True] = True
    answer_generation_service_ref: str | None = Field(default=None, min_length=1)
    llm_provider_factory_ref: str | None = Field(default=None, min_length=1)
    answer_policy_ref: str | None = Field(
        default=(
            "policy://product-application-assembly/evidence-summary-answer/"
            "answer/minimal-v1"
        ),
        min_length=1,
    )
    citation_policy_ref: str | None = Field(
        default=(
            "policy://product-application-assembly/evidence-summary-answer/"
            "citation/minimal-v1"
        ),
        min_length=1,
    )
    allow_raw_boundary: Literal[False] = False
    allow_sanitized_excerpt_preview: Literal[False] = False
    allow_observability_candidate_body: Literal[False] = False
    citation_required: Literal[True] = True
    allow_citation_exception: Literal[False] = False
    insufficient_evidence_required: Literal[True] = True
    max_summary_facts: int = Field(
        default=SUMMARY_FACT_MAX_ITEMS,
        gt=0,
        le=SUMMARY_FACT_MAX_ITEMS,
    )
    max_summary_fact_chars: int = Field(
        default=SUMMARY_FACT_ITEM_MAX_CHARS,
        gt=0,
        le=SUMMARY_FACT_ITEM_MAX_CHARS,
    )
    max_total_summary_fact_chars: int = Field(
        default=SUMMARY_FACT_MAX_CHARS,
        gt=0,
        le=SUMMARY_FACT_MAX_CHARS,
    )
    model_context_budget: int = Field(
        default=SUMMARY_FACT_MAX_CHARS,
        gt=0,
        le=SUMMARY_FACT_MAX_CHARS,
    )
    answer_preview_limit: int = Field(
        default=1000,
        gt=0,
        le=SUMMARY_FACT_MAX_CHARS,
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_evidence_summary_answer_policy(
        self,
    ) -> "EvidenceSummaryAnswerPolicyConfigView":
        """Keep evidence summary answer config as policy, not execution setup."""

        if self.allow_model_context and not self.exposure_enabled:
            raise ValueError("allow_model_context requires exposure_enabled.")
        if self.profile == "smoke_only" and self.allow_answer_generation_success:
            raise ValueError(
                "smoke_only profile cannot allow answer generation success."
            )
        if self.allow_answer_generation_success:
            if self.profile != "controlled_live_answer_generation":
                raise ValueError(
                    "allow_answer_generation_success requires "
                    "controlled_live_answer_generation profile."
                )
            if not self.answer_generation_service_ref:
                raise ValueError(
                    "allow_answer_generation_success requires "
                    "answer_generation_service_ref."
                )
            if not self.llm_provider_factory_ref:
                raise ValueError(
                    "allow_answer_generation_success requires "
                    "llm_provider_factory_ref."
                )
            if not self.answer_policy_ref:
                raise ValueError(
                    "allow_answer_generation_success requires answer_policy_ref."
                )
            if not self.citation_policy_ref:
                raise ValueError(
                    "allow_answer_generation_success requires citation_policy_ref."
                )
        if self.max_total_summary_fact_chars < self.max_summary_fact_chars:
            raise ValueError(
                "max_total_summary_fact_chars must cover max_summary_fact_chars."
            )
        if self.model_context_budget < self.max_total_summary_fact_chars:
            raise ValueError(
                "model_context_budget must cover max_total_summary_fact_chars."
            )
        forbidden_paths = _sensitive_metadata_paths(self.metadata)
        if forbidden_paths:
            raise ValueError(
                "Evidence summary answer metadata must not include sensitive fields: "
                + ", ".join(forbidden_paths)
            )
        return self


class ToolConfirmationConfigView(RuntimeConfigBaseModel):
    """Runtime-facing ADK FunctionTool confirmation configuration view."""

    default_require_confirmation: bool = True
    default_mode: Literal["operator_required"] = "operator_required"
    controlled_live_external_tool_smoke_enabled: bool = False
    auto_confirmation_allowed: bool = False
    low_risk_tool_allowlist: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_tool_confirmation_config(self) -> "ToolConfirmationConfigView":
        """Keep first-cut Tool confirmation config candidate safe."""

        if self.auto_confirmation_allowed:
            raise ValueError("auto_confirmation_allowed must remain false.")
        for tool_id in self.low_risk_tool_allowlist:
            if not tool_id.strip():
                raise ValueError("low_risk_tool_allowlist entries must be non-empty.")
        forbidden_paths = _sensitive_metadata_paths(self.metadata)
        if forbidden_paths:
            raise ValueError(
                "Tool confirmation metadata must not include sensitive or "
                "runtime approval fields: "
                + ", ".join(forbidden_paths)
            )
        return self


class ReferenceReaderPolicyConfigView(RuntimeConfigBaseModel):
    """Runtime-facing local reference reader policy configuration view."""

    enabled: bool = True
    allowed_roots: tuple[str, ...] = ("tasks", "docs")
    allowed_files: tuple[str, ...] = ("pyproject.toml",)
    allowed_suffixes: tuple[str, ...] = (
        ".md",
        ".txt",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
    )
    max_bytes: int = Field(default=32768, gt=0)
    max_chars: int = Field(default=6000, gt=0)
    max_excerpt_lines: int = Field(default=80, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_reference_reader_policy(self) -> "ReferenceReaderPolicyConfigView":
        """Keep configured local reference reads inside safe relative roots."""

        if not self.allowed_roots:
            raise ValueError("reference reader allowed_roots must be non-empty.")
        for root in self.allowed_roots:
            if _unsafe_config_relative_path(root):
                raise ValueError("reference reader allowed_roots must be safe relative paths.")
        for file in self.allowed_files:
            if _unsafe_config_relative_path(file) or file.endswith(("/", "\\")):
                raise ValueError("reference reader allowed_files must be safe relative files.")
        for suffix in self.allowed_suffixes:
            if not suffix.startswith(".") or "/" in suffix or "\\" in suffix:
                raise ValueError("reference reader allowed_suffixes must be file suffixes.")
        forbidden_paths = _sensitive_metadata_paths(self.metadata)
        if forbidden_paths:
            raise ValueError(
                "Reference reader metadata must not include sensitive fields: "
                + ", ".join(forbidden_paths)
            )
        return self

    def to_mapping(self) -> dict[str, Any]:
        """Return the runtime_container reference_reader mapping shape."""

        return {
            "allowed_roots": list(self.allowed_roots),
            "allowed_files": list(self.allowed_files),
            "allowed_suffixes": list(self.allowed_suffixes),
            "max_bytes": self.max_bytes,
            "max_chars": self.max_chars,
            "max_excerpt_lines": self.max_excerpt_lines,
        }


class ToolsetExposurePolicyConfigView(RuntimeConfigBaseModel):
    """Runtime-facing policy for one exposed CLI toolset."""

    toolset_name: str
    toolset_kind: str = "toolset"
    source_ref: str | None = None
    allowlist_tool_names: tuple[str, ...]
    tool_filter: tuple[str, ...] = Field(default_factory=tuple)
    readonly_only: bool = True
    max_risk_level: Literal["none", "low", "medium", "high"] = "low"
    dynamic_toolset: bool = True
    discovery_credential_ref: str | None = None
    execution_credential_ref: str | None = None
    reference_reader: ReferenceReaderPolicyConfigView | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_toolset_exposure_policy(self) -> "ToolsetExposurePolicyConfigView":
        """Keep configured CLI tool exposure as an explicit readonly allowlist."""

        if not self.toolset_name.strip():
            raise ValueError("toolset_name must be non-empty.")
        if not self.toolset_kind.strip():
            raise ValueError("toolset_kind must be non-empty.")
        if self.dynamic_toolset and not self.source_ref:
            raise ValueError("dynamic toolsets must declare source_ref.")
        if not self.allowlist_tool_names:
            raise ValueError("allowlist_tool_names must be non-empty.")
        for tool_name in self.allowlist_tool_names:
            if not tool_name.strip():
                raise ValueError("allowlist_tool_names entries must be non-empty.")
        for tool_name in self.tool_filter:
            if tool_name not in self.allowlist_tool_names:
                raise ValueError("tool_filter must be a subset of allowlist_tool_names.")
        if not self.readonly_only:
            raise ValueError("toolset exposure must remain readonly_only.")
        forbidden_paths = _sensitive_metadata_paths(self.metadata)
        if forbidden_paths:
            raise ValueError(
                "Toolset exposure metadata must not include sensitive fields: "
                + ", ".join(forbidden_paths)
            )
        return self

    def to_mapping(self) -> dict[str, Any]:
        """Return the runtime_container toolset mapping shape."""

        mapping: dict[str, Any] = {
            "toolset_name": self.toolset_name,
            "toolset_kind": self.toolset_kind,
            "source_ref": self.source_ref,
            "allowlist_tool_names": list(self.allowlist_tool_names),
            "tool_filter": list(self.tool_filter or self.allowlist_tool_names),
            "readonly_only": self.readonly_only,
            "max_risk_level": self.max_risk_level,
            "dynamic_toolset": self.dynamic_toolset,
            "discovery_credential_ref": self.discovery_credential_ref,
            "execution_credential_ref": self.execution_credential_ref,
        }
        if self.reference_reader is not None and self.reference_reader.enabled:
            mapping["reference_reader"] = self.reference_reader.to_mapping()
        return mapping


class ToolExposureProfileConfigView(RuntimeConfigBaseModel):
    """Runtime-facing profile mapping for CLI tool exposure."""

    source_ref: str | None = None
    toolsets: tuple[ToolsetExposurePolicyConfigView, ...]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_tool_exposure_profile(self) -> "ToolExposureProfileConfigView":
        """Require at least one toolset and no sensitive metadata."""

        if not self.toolsets:
            raise ValueError("tool exposure profile toolsets must be non-empty.")
        forbidden_paths = _sensitive_metadata_paths(self.metadata)
        if forbidden_paths:
            raise ValueError(
                "Tool exposure profile metadata must not include sensitive fields: "
                + ", ".join(forbidden_paths)
            )
        return self

    def to_mapping(self) -> dict[str, Any]:
        """Return one runtime_container profile mapping."""

        return {
            "source_ref": self.source_ref,
            "toolsets": [toolset.to_mapping() for toolset in self.toolsets],
        }


class ToolExposureConfigView(RuntimeConfigBaseModel):
    """Runtime-facing CLI tool exposure profile configuration view."""

    default_profile: str = "readonly_reference"
    profiles: dict[str, ToolExposureProfileConfigView] = Field(
        default_factory=lambda: {
            "readonly_reference": ToolExposureProfileConfigView(
                source_ref="default://runtime-config/tool-exposure/readonly-reference",
                toolsets=(
                    ToolsetExposurePolicyConfigView(
                        toolset_name="local_reference_tools",
                        toolset_kind="toolset",
                        source_ref="local-reference-reader://workspace",
                        allowlist_tool_names=("local_reference_reader",),
                        tool_filter=("local_reference_reader",),
                        readonly_only=True,
                        max_risk_level="low",
                        dynamic_toolset=True,
                        discovery_credential_ref="credential://not-required",
                        execution_credential_ref="credential://not-required",
                        reference_reader=ReferenceReaderPolicyConfigView(),
                    ),
                ),
            )
        }
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_tool_exposure_config(self) -> "ToolExposureConfigView":
        """Require a declared default profile and safe metadata."""

        if not self.default_profile.strip():
            raise ValueError("default_profile must be non-empty.")
        if self.default_profile not in self.profiles:
            raise ValueError("default_profile must exist in profiles.")
        for name in self.profiles:
            if not name.strip():
                raise ValueError("tool exposure profile names must be non-empty.")
        forbidden_paths = _sensitive_metadata_paths(self.metadata)
        if forbidden_paths:
            raise ValueError(
                "Tool exposure metadata must not include sensitive fields: "
                + ", ".join(forbidden_paths)
            )
        return self

    def to_profile_config(self) -> dict[str, Any]:
        """Return the runtime_container profile_config mapping shape."""

        return {
            "profiles": {
                name: profile.to_mapping()
                for name, profile in self.profiles.items()
            }
        }


class RunWorkspacePolicyConfigView(RuntimeConfigBaseModel):
    """Runtime-facing CLI run workspace policy configuration view."""

    enabled_by_default: bool = False
    workspace_root: str = ".cognition-runs"
    retention_policy: Literal["keep", "ephemeral", "delete_on_success"] = "keep"
    cleanup_policy: Literal["manual", "delete_on_success", "delete_always"] = "manual"
    max_write_bytes: int = Field(default=65536, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_run_workspace_policy(self) -> "RunWorkspacePolicyConfigView":
        """Keep configured run workspace roots safe and relative by default."""

        if _unsafe_config_relative_path(self.workspace_root):
            raise ValueError("run workspace root must be a safe relative path.")
        forbidden_paths = _sensitive_metadata_paths(self.metadata)
        if forbidden_paths:
            raise ValueError(
                "Run workspace metadata must not include sensitive fields: "
                + ", ".join(forbidden_paths)
            )
        return self

    def to_policy_kwargs(self) -> dict[str, Any]:
        """Return the runtime_container run workspace policy kwargs."""

        return {
            "workspace_root": self.workspace_root,
            "retention_policy": self.retention_policy,
            "cleanup_policy": self.cleanup_policy,
            "max_write_bytes": self.max_write_bytes,
        }


class RuntimeConfigContextBundle(RuntimeConfigBaseModel):
    """Runtime-facing configuration context bundle."""

    runtime: RuntimeConfigView
    workflow_execution: WorkflowExecutionConfigView
    node_execution: NodeExecutionConfigView
    resume_policy: ResumePolicyConfigView
    event_policy: EventPolicyConfigView
    artifact_policy: ArtifactPolicyConfigView
    session_policy: SessionPolicyConfigView = Field(default_factory=SessionPolicyConfigView)
    adapter_selection: AdapterSelectionConfigView
    adk_run_config: AdkRunConfigView = Field(default_factory=AdkRunConfigView)
    productization_gate: RuntimeProductizationGateConfigView = Field(
        default_factory=RuntimeProductizationGateConfigView
    )
    live_llm: RuntimeLiveLlmConfigView = Field(
        default_factory=RuntimeLiveLlmConfigView
    )
    tool_confirmation: ToolConfirmationConfigView = Field(
        default_factory=ToolConfirmationConfigView
    )
    tool_exposure: ToolExposureConfigView = Field(default_factory=ToolExposureConfigView)
    run_workspace: RunWorkspacePolicyConfigView = Field(
        default_factory=RunWorkspacePolicyConfigView
    )
    evidence_summary_answer: EvidenceSummaryAnswerPolicyConfigView = Field(
        default_factory=EvidenceSummaryAnswerPolicyConfigView
    )
    governance: GovernanceConfigContext = Field(default_factory=GovernanceConfigContext)


def _sensitive_metadata_paths(value: Any, path: str = "metadata") -> list[str]:
    if isinstance(value, dict):
        violations: list[str] = []
        for key, item in value.items():
            key_text = str(key)
            item_path = f"{path}.{key_text}"
            if _is_sensitive_config_metadata_key(key_text):
                violations.append(item_path)
            violations.extend(_sensitive_metadata_paths(item, item_path))
        return violations
    if isinstance(value, (list, tuple)):
        violations = []
        for index, item in enumerate(value):
            violations.extend(_sensitive_metadata_paths(item, f"{path}[{index}]"))
        return violations
    if isinstance(value, str) and _is_sensitive_config_metadata_value(value):
        return [path]
    return []


def _is_sensitive_config_metadata_key(key: str) -> bool:
    lowered = key.lower()
    if lowered in SENSITIVE_CONFIG_METADATA_KEYS:
        return True
    return (
        lowered.endswith("_token")
        or lowered.endswith("_secret")
        or lowered.endswith("_credential")
        or lowered.endswith("_approval_ref")
    )


def _is_sensitive_config_metadata_value(value: str) -> bool:
    lowered = value.strip().lower()
    return (
        lowered.startswith("sk-")
        or lowered.startswith("bearer ")
        or "api_key=" in lowered
        or "authorization:" in lowered
        or "password=" in lowered
        or "secret=" in lowered
        or "token=" in lowered
        or "-----begin private key-----" in lowered
    )


def _safe_env_var_name(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    first = text[0]
    if not (first.isalpha() or first == "_"):
        return False
    if not all(char.isupper() or char.isdigit() or char == "_" for char in text):
        return False
    forbidden_fragments = (
        "API_KEY",
        "AUTHORIZATION",
        "CREDENTIAL",
        "PASSWORD",
        "SECRET",
        "TOKEN",
    )
    return not any(fragment in text for fragment in forbidden_fragments)


def _profile_keys_are_safe(value: dict[str, Any]) -> bool:
    return all(
        isinstance(key, str)
        and bool(key.strip())
        and not _is_sensitive_config_metadata_key(key)
        for key in value
    )


def _unsafe_config_relative_path(value: str) -> bool:
    text = value.strip()
    if not text:
        return True
    if text.startswith(("/", "~")) or "\\" in text:
        return True
    parts = PurePosixPath(text).parts
    if ".." in parts:
        return True
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            ".env",
            "api_key",
            "credential",
            "password",
            "private_key",
            "secret",
            "service_account",
            "token",
        )
    )
