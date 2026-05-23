"""Public CLI-facing product gateway schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PRODUCT_GATEWAY_CLI_SURFACE_PAYLOAD_VERSION = "product_gateway_cli_surface_v1"

PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME = "twf_plan_workflow"
PRODUCT_GATEWAY_CLI_TWF_REFERENCE_REVIEW_WORKFLOW_NAME = (
    "twf_reference_review_workflow"
)
PRODUCT_GATEWAY_CLI_TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME = (
    "twf_config_profile_explain_workflow"
)
PRODUCT_GATEWAY_CLI_TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME = (
    "twf_run_workspace_evidence_audit_workflow"
)
PRODUCT_GATEWAY_CLI_TWF_WORKFLOW_NAMES = frozenset(
    {
        PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME,
        PRODUCT_GATEWAY_CLI_TWF_REFERENCE_REVIEW_WORKFLOW_NAME,
        PRODUCT_GATEWAY_CLI_TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
        PRODUCT_GATEWAY_CLI_TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
    }
)

PRODUCT_GATEWAY_CLI_REFERENCE_READER_TOOL_NAME = "local_reference_reader"
PRODUCT_GATEWAY_CLI_REFERENCE_READER_FORBIDDEN_SEGMENTS = (
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
)
PRODUCT_GATEWAY_CLI_REFERENCE_READER_FORBIDDEN_PATH_MARKERS = (
    ".env",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials",
    "id_dsa",
    "id_ed25519",
    "id_rsa",
    "private_key",
    "secrets",
    "service_account",
)

ProductGatewayCliTaskWorkflowName = Literal[
    "twf_plan_workflow",
    "twf_reference_review_workflow",
    "twf_config_profile_explain_workflow",
    "twf_run_workspace_evidence_audit_workflow",
]

RAW_OR_SENSITIVE_PRODUCT_GATEWAY_CLI_KEYS = frozenset(
    {
        "api_key",
        "artifact_content",
        "completion",
        "content",
        "credential",
        "credentials",
        "full_response",
        "message",
        "messages",
        "payload",
        "prompt",
        "provider_payload",
        "provider_response",
        "raw",
        "raw_adk_object",
        "raw_api_payload",
        "raw_input",
        "raw_output",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_provider_response",
        "raw_response",
        "raw_tool_input",
        "raw_tool_output",
        "raw_user_message",
        "response",
        "response_text",
        "secret",
        "system_prompt",
        "text",
        "token",
        "tool_context",
        "tool_input",
        "tool_output",
        "user_message",
    }
)

PRODUCT_GATEWAY_CLI_SENSITIVE_KEY_EXCEPTIONS = frozenset(
    {
        "sanitized_previous_display_text",
        "sanitized_user_text",
    }
)

FORBIDDEN_PRODUCT_GATEWAY_CLI_OBJECT_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "runtime_container",
    "composition",
    "cognition_operation_flows",
    "litellm",
)


class ProductGatewayCliSurfaceBaseModel(BaseModel):
    """Base model for CLI-facing product gateway contract schemas."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_cli_surface_boundary(self) -> "ProductGatewayCliSurfaceBaseModel":
        violations = product_gateway_cli_surface_boundary_violations(
            self.model_dump(mode="python")
        )
        if violations:
            raise ValueError("; ".join(violations))
        return self


class ProductGatewayCliTwfGovernanceRefsSchema(ProductGatewayCliSurfaceBaseModel):
    """Governance refs accepted by CLI-facing task workflow requests."""

    approval_ref: str | None = None
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    governance_summary_output_ref: str | None = None
    live_llm_approval_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductGatewayCliTwfReferenceWorkspaceControlsSchema(
    ProductGatewayCliSurfaceBaseModel
):
    """Reference and workspace controls accepted from CLI task workflows."""

    reference_paths: tuple[str, ...] = ()
    reference_repo_root: str | None = None
    external_readonly_evidence_paths: tuple[str, ...] = ()
    external_readonly_evidence_repo_root: str | None = None
    reference_profile_name: str | None = None
    tool_exposure_profile: str | None = None
    run_workspace_root: str | None = None
    run_workspace_enabled: bool = False
    run_workspace_retention_policy: str | None = None
    run_workspace_cleanup_policy: str | None = None
    run_workspace_max_write_bytes: int | None = None
    audit_run_workspace_path: str | None = None
    audit_run_workspace_ref: str | None = None
    audit_run_workspace_root: str | None = None
    audit_focus: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_controls(self) -> "ProductGatewayCliTwfReferenceWorkspaceControlsSchema":
        if any(not item for item in self.reference_paths):
            raise ValueError("reference_paths must not contain empty values.")
        if any(not item for item in self.external_readonly_evidence_paths):
            raise ValueError(
                "external_readonly_evidence_paths must not contain empty values."
            )
        if (
            self.run_workspace_max_write_bytes is not None
            and self.run_workspace_max_write_bytes <= 0
        ):
            raise ValueError("run_workspace_max_write_bytes must be positive.")
        return self


class ProductGatewayCliTwfRouteInputSchema(ProductGatewayCliSurfaceBaseModel):
    """CLI-facing task workflow route input."""

    request_id: str = Field(..., min_length=1)
    sanitized_user_text: str = Field(..., min_length=1)
    chat_session_id: str | None = None
    turn_index: int | None = None
    sanitized_history: tuple[dict[str, str], ...] = ()
    sanitized_previous_display_text: str | None = None
    live_model_requested: bool = False
    reference_paths: tuple[str, ...] = ()
    external_readonly_evidence_paths: tuple[str, ...] = ()
    run_workspace_requested: bool = False
    audit_run_workspace_requested: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_route_input(self) -> "ProductGatewayCliTwfRouteInputSchema":
        if any(not item for item in self.reference_paths):
            raise ValueError("reference_paths must not contain empty values.")
        if any(not item for item in self.external_readonly_evidence_paths):
            raise ValueError(
                "external_readonly_evidence_paths must not contain empty values."
            )
        return self


class ProductGatewayCliTwfRouteProjectionSchema(ProductGatewayCliSurfaceBaseModel):
    """CLI-facing task workflow route projection."""

    request_id: str = Field(..., min_length=1)
    entry_kind: str = Field(..., min_length=1)
    execution_mode: str = Field(..., min_length=1)
    matched: bool
    workflow_name: ProductGatewayCliTaskWorkflowName | None = None
    workflow_version: str | None = None
    task_kind: str | None = None
    route_reason: str = Field(..., min_length=1)
    confidence: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    turn_index: int | None = None
    requires_live_model: bool = False
    requires_tools: tuple[str, ...] = ()
    requires_workspace: bool = False
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    registry_version: str = Field(..., min_length=1)
    registry_workflow_count: int = 0
    registry_workflow_names: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductGatewayCliTwfRequestDraftInputSchema(ProductGatewayCliSurfaceBaseModel):
    """CLI-facing task workflow draft input before product_gateway execution."""

    workflow_name: ProductGatewayCliTaskWorkflowName
    sanitized_user_text: str = Field(..., min_length=1)
    chat_session_id: str | None = None
    turn_index: int | None = None
    sanitized_history: tuple[dict[str, str], ...] = ()
    sanitized_previous_display_text: str | None = None
    governance_refs: ProductGatewayCliTwfGovernanceRefsSchema | None = None
    controls: ProductGatewayCliTwfReferenceWorkspaceControlsSchema | None = None
    route_summary: dict[str, Any] | None = None
    entrypoint_explicit_args: dict[str, Any] | None = None
    session_args: dict[str, Any] | None = None
    user_passthrough_parameters: dict[str, Any] | None = None
    operator_approved: bool = False
    request_live_llm: bool = False
    request_ollama: bool = False
    allow_live_llm: bool = False
    allow_ollama: bool = False
    live_llm_timeout_seconds: int | None = None
    live_model_allowed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_request_draft(self) -> "ProductGatewayCliTwfRequestDraftInputSchema":
        if self.live_llm_timeout_seconds is not None and self.live_llm_timeout_seconds <= 0:
            raise ValueError("live_llm_timeout_seconds must be positive.")
        if self.live_model_allowed and self.governance_refs is None:
            raise ValueError("live_model_allowed requires governance_refs.")
        return self


class ProductGatewayCliTwfExecutionOptionsSchema(ProductGatewayCliSurfaceBaseModel):
    """CLI-facing execution options for product gateway task workflows."""

    config_root: str | None = None
    environment: str = Field(default="local", min_length=1)
    profile: str | None = None
    ollama_api_base: str | None = None
    reference_profile_config: dict[str, Any] | None = None
    reference_session_args: dict[str, Any] = Field(default_factory=dict)
    reference_entrypoint_explicit_args: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductGatewayCliTwfExecutionInputSchema(ProductGatewayCliSurfaceBaseModel):
    """CLI-facing task workflow execution input."""

    request_id: str = Field(..., min_length=1)
    route_projection: ProductGatewayCliTwfRouteProjectionSchema
    request_draft_input: ProductGatewayCliTwfRequestDraftInputSchema
    execution_options: ProductGatewayCliTwfExecutionOptionsSchema = Field(
        default_factory=ProductGatewayCliTwfExecutionOptionsSchema
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_execution_input(self) -> "ProductGatewayCliTwfExecutionInputSchema":
        if self.route_projection.request_id != self.request_id:
            raise ValueError("route_projection request_id must match request_id.")
        if (
            self.route_projection.workflow_name
            and self.route_projection.workflow_name
            != self.request_draft_input.workflow_name
        ):
            raise ValueError(
                "route projection and request draft input workflow mismatch."
            )
        return self


class ProductGatewayCliTwfRunWorkspaceSnapshotSchema(ProductGatewayCliSurfaceBaseModel):
    """CLI-facing snapshot of a task workflow run workspace."""

    workspace_ref: str | None = None
    workspace_path: str | None = None
    workflow_name: str | None = None
    run_id: str | None = None
    workspace_created: bool = False
    retention_policy: str | None = None
    cleanup_policy: str | None = None
    cleanup_performed: bool = False
    manifest_path: str | None = None
    subdirs: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    result_refs: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    max_write_bytes: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_workspace_snapshot(
        self,
    ) -> "ProductGatewayCliTwfRunWorkspaceSnapshotSchema":
        if self.max_write_bytes is not None and self.max_write_bytes <= 0:
            raise ValueError("max_write_bytes must be positive.")
        if any(not item for item in self.artifact_refs):
            raise ValueError("artifact_refs must not contain empty values.")
        if any(not item for item in self.evidence_refs):
            raise ValueError("evidence_refs must not contain empty values.")
        if any(not item for item in self.result_refs):
            raise ValueError("result_refs must not contain empty values.")
        return self


class ProductGatewayCliTwfLatestPlanSnapshotSchema(ProductGatewayCliSurfaceBaseModel):
    """CLI-facing latest plan status snapshot."""

    status: str = Field(..., min_length=1)
    reference_context_status: str = Field(default="not_run", min_length=1)
    reference_evidence_ref_count: int = Field(default=0, ge=0)
    workspace: ProductGatewayCliTwfRunWorkspaceSnapshotSchema | None = None
    product_gateway_route_projection: dict[str, Any] = Field(default_factory=dict)
    no_live: bool = False
    fail_safe: bool = False
    quality_review_present: bool = False
    model_call_count: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductGatewayCliTwfExecutionResultSchema(ProductGatewayCliSurfaceBaseModel):
    """CLI-facing task workflow execution result."""

    handled: bool
    terminal_display_text: str | None = None
    latest_plan_display_text: str | None = None
    latest_plan_snapshot: ProductGatewayCliTwfLatestPlanSnapshotSchema | None = None
    product_response_summary: dict[str, Any] = Field(default_factory=dict)
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductGatewayCliTwfStatusSummaryPersistenceSchema(
    ProductGatewayCliSurfaceBaseModel
):
    """Result of persisting a CLI status summary artifact."""

    latest_plan_snapshot: ProductGatewayCliTwfLatestPlanSnapshotSchema | None = None
    status_summary_artifact_ref: str | None = None
    status: str = Field(default="skipped", min_length=1)
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductGatewayCliReferenceReaderPolicySchema(ProductGatewayCliSurfaceBaseModel):
    """Sanitized reference-reader policy exposed to CLI controls."""

    allowed_roots: tuple[str, ...]
    allowed_files: tuple[str, ...] = ()
    allowed_suffixes: tuple[str, ...] = ()
    max_bytes: int = Field(default=32768, gt=0)
    max_chars: int = Field(default=6000, gt=0)
    max_excerpt_lines: int = Field(default=80, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductGatewayCliToolExposureResolutionSchema(ProductGatewayCliSurfaceBaseModel):
    """Sanitized tool exposure resolution consumed by CLI."""

    status: str = Field(..., min_length=1)
    exposed_tool_names: tuple[str, ...]
    blocked_tool_names: tuple[str, ...]
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    reference_reader_policy: ProductGatewayCliReferenceReaderPolicySchema | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def validate_product_gateway_cli_surface_contract(
    value: dict[str, Any],
) -> dict[str, Any]:
    """Validate a mapping through the generic CLI surface boundary guard."""

    violations = product_gateway_cli_surface_boundary_violations(value)
    if violations:
        raise ValueError("; ".join(violations))
    return value


def product_gateway_cli_surface_boundary_violations(
    value: Any,
    path: str = "$",
) -> list[str]:
    """Return public-boundary violations for CLI-facing product gateway shapes."""

    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}"
            if _is_forbidden_cli_key(str(key)):
                violations.append(f"raw or sensitive field is forbidden at {key_path}")
            if key == "object_module" and isinstance(item, str) and _is_runtime_module(
                item
            ):
                violations.append(f"runtime object module is forbidden at {key_path}")
            violations.extend(product_gateway_cli_surface_boundary_violations(item, key_path))
        return violations
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            violations.extend(
                product_gateway_cli_surface_boundary_violations(item, f"{path}[{index}]")
            )
        return violations
    if _is_runtime_object(value):
        violations.append(f"runtime object is forbidden at {path}")
    return violations


def _is_forbidden_cli_key(key: str) -> bool:
    lowered = key.lower()
    if lowered in PRODUCT_GATEWAY_CLI_SENSITIVE_KEY_EXCEPTIONS:
        return False
    return lowered in RAW_OR_SENSITIVE_PRODUCT_GATEWAY_CLI_KEYS


def _is_runtime_object(value: Any) -> bool:
    module_name = getattr(type(value), "__module__", "")
    return _is_runtime_module(module_name)


def _is_runtime_module(module_name: str) -> bool:
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for prefix in FORBIDDEN_PRODUCT_GATEWAY_CLI_OBJECT_MODULE_PREFIXES
    )


__all__ = [
    "FORBIDDEN_PRODUCT_GATEWAY_CLI_OBJECT_MODULE_PREFIXES",
    "PRODUCT_GATEWAY_CLI_REFERENCE_READER_FORBIDDEN_PATH_MARKERS",
    "PRODUCT_GATEWAY_CLI_REFERENCE_READER_FORBIDDEN_SEGMENTS",
    "PRODUCT_GATEWAY_CLI_REFERENCE_READER_TOOL_NAME",
    "PRODUCT_GATEWAY_CLI_SENSITIVE_KEY_EXCEPTIONS",
    "PRODUCT_GATEWAY_CLI_SURFACE_PAYLOAD_VERSION",
    "PRODUCT_GATEWAY_CLI_TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME",
    "PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME",
    "PRODUCT_GATEWAY_CLI_TWF_REFERENCE_REVIEW_WORKFLOW_NAME",
    "PRODUCT_GATEWAY_CLI_TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME",
    "PRODUCT_GATEWAY_CLI_TWF_WORKFLOW_NAMES",
    "ProductGatewayCliReferenceReaderPolicySchema",
    "ProductGatewayCliSurfaceBaseModel",
    "ProductGatewayCliTaskWorkflowName",
    "ProductGatewayCliToolExposureResolutionSchema",
    "ProductGatewayCliTwfExecutionInputSchema",
    "ProductGatewayCliTwfExecutionOptionsSchema",
    "ProductGatewayCliTwfExecutionResultSchema",
    "ProductGatewayCliTwfGovernanceRefsSchema",
    "ProductGatewayCliTwfLatestPlanSnapshotSchema",
    "ProductGatewayCliTwfReferenceWorkspaceControlsSchema",
    "ProductGatewayCliTwfRequestDraftInputSchema",
    "ProductGatewayCliTwfRunWorkspaceSnapshotSchema",
    "ProductGatewayCliTwfRouteInputSchema",
    "ProductGatewayCliTwfRouteProjectionSchema",
    "ProductGatewayCliTwfStatusSummaryPersistenceSchema",
    "RAW_OR_SENSITIVE_PRODUCT_GATEWAY_CLI_KEYS",
    "product_gateway_cli_surface_boundary_violations",
    "validate_product_gateway_cli_surface_contract",
]
