"""Channel-neutral request draft candidates for task workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from cognition_operation_flows._core.boundaries import (
    validate_task_workflow_metadata_boundary,
)
from cognition_operation_flows._core.control import MANAGED_GOVERNANCE_PARAMETERS
from cognition_operation_flows._requests.intent_detectors import (
    TWF_CONFIG_PROFILE_EXPLAIN_TASK_KIND,
    TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    TWF_REFERENCE_REVIEW_TASK_KIND,
    TWF_REFERENCE_REVIEW_WORKFLOW_NAME,
    TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_TASK_KIND,
    TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
)
from cognition_operation_flows._requests.registry import (
    TWF_PLAN_TASK_KIND,
    TWF_PLAN_WORKFLOW_NAME,
)


TWF_REQUEST_DRAFT_SCHEMA_VERSION = "v0.7.0-candidate"
TWF_REQUEST_DRAFT_FORBIDDEN_INPUT_KEYS = frozenset(
    {
        "argparse_namespace",
        "cli_args",
        "cognition_cli_args",
        "llm_invocation_service",
        "product_gateway_request",
        "runtime_container",
        "runtime_container_request",
        "runtime_request_candidate",
        "workflow_runner",
    }
)
_WORKFLOW_TASK_KINDS = {
    TWF_PLAN_WORKFLOW_NAME: TWF_PLAN_TASK_KIND,
    TWF_REFERENCE_REVIEW_WORKFLOW_NAME: TWF_REFERENCE_REVIEW_TASK_KIND,
    TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME: TWF_CONFIG_PROFILE_EXPLAIN_TASK_KIND,
    TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME: (
        TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_TASK_KIND
    ),
}


@dataclass(frozen=True)
class TwfChatTurnInputCandidate:
    """Sanitized channel input facts for one task workflow turn."""

    sanitized_user_text: str
    chat_session_id: str | None = None
    turn_index: int | None = None
    sanitized_history: tuple[Mapping[str, str], ...] = ()
    sanitized_previous_display_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.sanitized_user_text.strip():
            raise ValueError("sanitized_user_text must not be empty.")
        _validate_history(self.sanitized_history)
        validate_task_workflow_metadata_boundary(self.metadata)
        _validate_no_forbidden_runtime_objects(
            self.metadata,
            field_name="turn_input.metadata",
        )


@dataclass(frozen=True)
class TwfGovernanceRefsCandidate:
    """Governance references carried as refs, not raw governance payloads."""

    approval_ref: str | None = None
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    governance_summary_output_ref: str | None = None
    live_llm_approval_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_task_workflow_metadata_boundary(self.metadata)
        _validate_no_forbidden_runtime_objects(
            self.metadata,
            field_name="governance_refs.metadata",
        )


@dataclass(frozen=True)
class TwfReferenceWorkspaceControlsCandidate:
    """Reference, tool-profile and workspace controls for a request draft."""

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
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_string_tuple(self.reference_paths, "reference_paths")
        _validate_string_tuple(
            self.external_readonly_evidence_paths,
            "external_readonly_evidence_paths",
        )
        _validate_string_tuple(self.audit_focus, "audit_focus")
        if (
            self.run_workspace_max_write_bytes is not None
            and self.run_workspace_max_write_bytes <= 0
        ):
            raise ValueError("run_workspace_max_write_bytes must be positive.")
        validate_task_workflow_metadata_boundary(self.metadata)
        _validate_no_forbidden_runtime_objects(
            self.metadata,
            field_name="controls.metadata",
        )


@dataclass(frozen=True)
class TwfWorkflowRequestDraftCandidate:
    """Channel-neutral draft used before any runtime request adapter."""

    workflow_name: str
    task_kind: str
    turn_input: TwfChatTurnInputCandidate
    governance_refs: TwfGovernanceRefsCandidate = field(
        default_factory=TwfGovernanceRefsCandidate
    )
    controls: TwfReferenceWorkspaceControlsCandidate = field(
        default_factory=TwfReferenceWorkspaceControlsCandidate
    )
    route_summary: dict[str, Any] = field(default_factory=dict)
    entrypoint_explicit_args: dict[str, Any] = field(default_factory=dict)
    session_args: dict[str, Any] = field(default_factory=dict)
    user_passthrough_parameters: dict[str, Any] = field(default_factory=dict)
    operator_approved: bool = False
    request_live_llm: bool = False
    request_ollama: bool = False
    allow_live_llm: bool = False
    allow_ollama: bool = False
    live_llm_timeout_seconds: int | None = None
    live_model_allowed: bool = False
    schema_version: str = TWF_REQUEST_DRAFT_SCHEMA_VERSION
    candidate_only: bool = True
    channel_neutral: bool = True
    product_gateway_entry_required: bool = True
    runtime_adapter_required: bool = True
    runtime_request_candidate_enabled: bool = False
    workflow_execution_enabled: bool = False
    public_schema_enabled: bool = False
    llm_invocation_service_embedded: bool = False
    argparse_namespace_embedded: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        expected_task_kind = _WORKFLOW_TASK_KINDS.get(self.workflow_name)
        if expected_task_kind is None:
            raise ValueError(f"workflow_name unsupported: {self.workflow_name}")
        if self.task_kind != expected_task_kind:
            raise ValueError(
                f"task_kind must be {expected_task_kind} for {self.workflow_name}."
            )
        if self.schema_version != TWF_REQUEST_DRAFT_SCHEMA_VERSION:
            raise ValueError("schema_version must remain the candidate schema version.")
        if self.candidate_only is not True:
            raise ValueError("candidate_only must remain true.")
        if self.channel_neutral is not True:
            raise ValueError("channel_neutral must remain true.")
        if self.product_gateway_entry_required is not True:
            raise ValueError("product_gateway_entry_required must remain true.")
        if self.runtime_adapter_required is not True:
            raise ValueError("runtime_adapter_required must remain true.")
        if self.runtime_request_candidate_enabled:
            raise ValueError("runtime_request_candidate_enabled must remain false.")
        if self.workflow_execution_enabled:
            raise ValueError("workflow_execution_enabled must remain false.")
        if self.public_schema_enabled:
            raise ValueError("public_schema_enabled must remain false.")
        if self.llm_invocation_service_embedded:
            raise ValueError("llm_invocation_service_embedded must remain false.")
        if self.argparse_namespace_embedded:
            raise ValueError("argparse_namespace_embedded must remain false.")
        if (
            self.live_llm_timeout_seconds is not None
            and self.live_llm_timeout_seconds <= 0
        ):
            raise ValueError("live_llm_timeout_seconds must be positive.")
        _validate_mapping_boundary(
            self.route_summary,
            field_name="route_summary",
            allow_managed_parameters=True,
        )
        _validate_mapping_boundary(
            self.entrypoint_explicit_args,
            field_name="entrypoint_explicit_args",
            allow_managed_parameters=True,
        )
        _validate_mapping_boundary(
            self.session_args,
            field_name="session_args",
            allow_managed_parameters=False,
        )
        _validate_mapping_boundary(
            self.user_passthrough_parameters,
            field_name="user_passthrough_parameters",
            allow_managed_parameters=False,
        )
        validate_task_workflow_metadata_boundary(self.metadata)
        _validate_no_forbidden_runtime_objects(
            self.metadata,
            field_name="metadata",
        )


def build_twf_plan_request_draft(
    *,
    sanitized_user_text: str,
    chat_session_id: str | None = None,
    turn_index: int | None = None,
    sanitized_history: Sequence[Mapping[str, str]] = (),
    sanitized_previous_display_text: str | None = None,
    governance_refs: TwfGovernanceRefsCandidate | Mapping[str, Any] | None = None,
    controls: TwfReferenceWorkspaceControlsCandidate | Mapping[str, Any] | None = None,
    route_summary: Mapping[str, Any] | None = None,
    entrypoint_explicit_args: Mapping[str, Any] | None = None,
    session_args: Mapping[str, Any] | None = None,
    user_passthrough_parameters: Mapping[str, Any] | None = None,
    operator_approved: bool = False,
    request_live_llm: bool = False,
    request_ollama: bool = False,
    allow_live_llm: bool = False,
    allow_ollama: bool = False,
    live_llm_timeout_seconds: int | None = None,
    live_model_allowed: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> TwfWorkflowRequestDraftCandidate:
    """Build a channel-neutral plan workflow request draft."""

    return _build_twf_workflow_request_draft(
        workflow_name=TWF_PLAN_WORKFLOW_NAME,
        task_kind=TWF_PLAN_TASK_KIND,
        sanitized_user_text=sanitized_user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=sanitized_history,
        sanitized_previous_display_text=sanitized_previous_display_text,
        governance_refs=governance_refs,
        controls=controls,
        route_summary=route_summary,
        entrypoint_explicit_args=entrypoint_explicit_args,
        session_args=session_args,
        user_passthrough_parameters=user_passthrough_parameters,
        operator_approved=operator_approved,
        request_live_llm=request_live_llm,
        request_ollama=request_ollama,
        allow_live_llm=allow_live_llm,
        allow_ollama=allow_ollama,
        live_llm_timeout_seconds=live_llm_timeout_seconds,
        live_model_allowed=live_model_allowed,
        metadata=metadata,
    )


def build_twf_reference_review_request_draft(
    *,
    sanitized_user_text: str,
    chat_session_id: str | None = None,
    turn_index: int | None = None,
    sanitized_history: Sequence[Mapping[str, str]] = (),
    governance_refs: TwfGovernanceRefsCandidate | Mapping[str, Any] | None = None,
    controls: TwfReferenceWorkspaceControlsCandidate | Mapping[str, Any] | None = None,
    route_summary: Mapping[str, Any] | None = None,
    entrypoint_explicit_args: Mapping[str, Any] | None = None,
    session_args: Mapping[str, Any] | None = None,
    user_passthrough_parameters: Mapping[str, Any] | None = None,
    operator_approved: bool = False,
    request_live_llm: bool = False,
    request_ollama: bool = False,
    allow_live_llm: bool = False,
    allow_ollama: bool = False,
    live_llm_timeout_seconds: int | None = None,
    live_model_allowed: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> TwfWorkflowRequestDraftCandidate:
    """Build a channel-neutral reference review workflow request draft."""

    return _build_twf_workflow_request_draft(
        workflow_name=TWF_REFERENCE_REVIEW_WORKFLOW_NAME,
        task_kind=TWF_REFERENCE_REVIEW_TASK_KIND,
        sanitized_user_text=sanitized_user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=sanitized_history,
        governance_refs=governance_refs,
        controls=controls,
        route_summary=route_summary,
        entrypoint_explicit_args=entrypoint_explicit_args,
        session_args=session_args,
        user_passthrough_parameters=user_passthrough_parameters,
        operator_approved=operator_approved,
        request_live_llm=request_live_llm,
        request_ollama=request_ollama,
        allow_live_llm=allow_live_llm,
        allow_ollama=allow_ollama,
        live_llm_timeout_seconds=live_llm_timeout_seconds,
        live_model_allowed=live_model_allowed,
        metadata=metadata,
    )


def build_twf_config_profile_explain_request_draft(
    *,
    sanitized_user_text: str,
    chat_session_id: str | None = None,
    turn_index: int | None = None,
    sanitized_history: Sequence[Mapping[str, str]] = (),
    governance_refs: TwfGovernanceRefsCandidate | Mapping[str, Any] | None = None,
    controls: TwfReferenceWorkspaceControlsCandidate | Mapping[str, Any] | None = None,
    route_summary: Mapping[str, Any] | None = None,
    entrypoint_explicit_args: Mapping[str, Any] | None = None,
    session_args: Mapping[str, Any] | None = None,
    user_passthrough_parameters: Mapping[str, Any] | None = None,
    operator_approved: bool = False,
    request_live_llm: bool = False,
    request_ollama: bool = False,
    allow_live_llm: bool = False,
    allow_ollama: bool = False,
    live_llm_timeout_seconds: int | None = None,
    live_model_allowed: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> TwfWorkflowRequestDraftCandidate:
    """Build a channel-neutral config profile explain request draft."""

    return _build_twf_workflow_request_draft(
        workflow_name=TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
        task_kind=TWF_CONFIG_PROFILE_EXPLAIN_TASK_KIND,
        sanitized_user_text=sanitized_user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=sanitized_history,
        governance_refs=governance_refs,
        controls=controls,
        route_summary=route_summary,
        entrypoint_explicit_args=entrypoint_explicit_args,
        session_args=session_args,
        user_passthrough_parameters=user_passthrough_parameters,
        operator_approved=operator_approved,
        request_live_llm=request_live_llm,
        request_ollama=request_ollama,
        allow_live_llm=allow_live_llm,
        allow_ollama=allow_ollama,
        live_llm_timeout_seconds=live_llm_timeout_seconds,
        live_model_allowed=live_model_allowed,
        metadata=metadata,
    )


def build_twf_run_workspace_evidence_audit_request_draft(
    *,
    sanitized_user_text: str,
    chat_session_id: str | None = None,
    turn_index: int | None = None,
    sanitized_history: Sequence[Mapping[str, str]] = (),
    governance_refs: TwfGovernanceRefsCandidate | Mapping[str, Any] | None = None,
    controls: TwfReferenceWorkspaceControlsCandidate | Mapping[str, Any] | None = None,
    route_summary: Mapping[str, Any] | None = None,
    entrypoint_explicit_args: Mapping[str, Any] | None = None,
    session_args: Mapping[str, Any] | None = None,
    user_passthrough_parameters: Mapping[str, Any] | None = None,
    operator_approved: bool = False,
    request_live_llm: bool = False,
    request_ollama: bool = False,
    allow_live_llm: bool = False,
    allow_ollama: bool = False,
    live_llm_timeout_seconds: int | None = None,
    live_model_allowed: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> TwfWorkflowRequestDraftCandidate:
    """Build a channel-neutral run workspace evidence audit request draft."""

    return _build_twf_workflow_request_draft(
        workflow_name=TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
        task_kind=TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_TASK_KIND,
        sanitized_user_text=sanitized_user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=sanitized_history,
        governance_refs=governance_refs,
        controls=controls,
        route_summary=route_summary,
        entrypoint_explicit_args=entrypoint_explicit_args,
        session_args=session_args,
        user_passthrough_parameters=user_passthrough_parameters,
        operator_approved=operator_approved,
        request_live_llm=request_live_llm,
        request_ollama=request_ollama,
        allow_live_llm=allow_live_llm,
        allow_ollama=allow_ollama,
        live_llm_timeout_seconds=live_llm_timeout_seconds,
        live_model_allowed=live_model_allowed,
        metadata=metadata,
    )


def twf_workflow_request_draft_status_dict(
    draft: TwfWorkflowRequestDraftCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready low-sensitivity summary for a request draft."""

    return {
        "schema_version": draft.schema_version,
        "workflow_name": draft.workflow_name,
        "task_kind": draft.task_kind,
        "chat_session_id": draft.turn_input.chat_session_id,
        "turn_index": draft.turn_input.turn_index,
        "history_count": len(draft.turn_input.sanitized_history),
        "candidate_only": draft.candidate_only,
        "channel_neutral": draft.channel_neutral,
        "product_gateway_entry_required": draft.product_gateway_entry_required,
        "runtime_adapter_required": draft.runtime_adapter_required,
        "runtime_request_candidate_enabled": draft.runtime_request_candidate_enabled,
        "workflow_execution_enabled": draft.workflow_execution_enabled,
        "public_schema_enabled": draft.public_schema_enabled,
        "llm_invocation_service_embedded": draft.llm_invocation_service_embedded,
        "argparse_namespace_embedded": draft.argparse_namespace_embedded,
        "operator_approved": draft.operator_approved,
        "request_live_llm": draft.request_live_llm,
        "request_ollama": draft.request_ollama,
        "allow_live_llm": draft.allow_live_llm,
        "allow_ollama": draft.allow_ollama,
        "live_model_allowed": draft.live_model_allowed,
        "governance_refs": {
            "approval_ref_present": bool(draft.governance_refs.approval_ref),
            "audit_ref_present": bool(draft.governance_refs.audit_ref),
            "sanitized_evidence_ref_present": bool(
                draft.governance_refs.sanitized_evidence_ref
            ),
            "governance_summary_output_ref_present": bool(
                draft.governance_refs.governance_summary_output_ref
            ),
            "live_llm_approval_ref_present": bool(
                draft.governance_refs.live_llm_approval_ref
            ),
        },
        "controls": {
            "reference_path_count": len(draft.controls.reference_paths),
            "external_readonly_evidence_path_count": len(
                draft.controls.external_readonly_evidence_paths
            ),
            "reference_repo_root_present": bool(draft.controls.reference_repo_root),
            "external_readonly_evidence_repo_root_present": bool(
                draft.controls.external_readonly_evidence_repo_root
            ),
            "reference_profile_name_present": bool(
                draft.controls.reference_profile_name
            ),
            "tool_exposure_profile": draft.controls.tool_exposure_profile,
            "run_workspace_enabled": draft.controls.run_workspace_enabled,
            "run_workspace_root_present": bool(draft.controls.run_workspace_root),
            "audit_run_workspace_path_present": bool(
                draft.controls.audit_run_workspace_path
            ),
            "audit_run_workspace_ref_present": bool(
                draft.controls.audit_run_workspace_ref
            ),
            "audit_run_workspace_root_present": bool(
                draft.controls.audit_run_workspace_root
            ),
            "audit_focus_count": len(draft.controls.audit_focus),
        },
        "route_summary_present": bool(draft.route_summary),
        "entrypoint_explicit_arg_keys": sorted(draft.entrypoint_explicit_args),
        "session_arg_keys": sorted(draft.session_args),
        "user_passthrough_parameter_keys": sorted(
            draft.user_passthrough_parameters
        ),
    }


def _build_twf_workflow_request_draft(
    *,
    workflow_name: str,
    task_kind: str,
    sanitized_user_text: str,
    chat_session_id: str | None,
    turn_index: int | None,
    sanitized_history: Sequence[Mapping[str, str]],
    sanitized_previous_display_text: str | None = None,
    governance_refs: TwfGovernanceRefsCandidate | Mapping[str, Any] | None = None,
    controls: TwfReferenceWorkspaceControlsCandidate | Mapping[str, Any] | None = None,
    route_summary: Mapping[str, Any] | None = None,
    entrypoint_explicit_args: Mapping[str, Any] | None = None,
    session_args: Mapping[str, Any] | None = None,
    user_passthrough_parameters: Mapping[str, Any] | None = None,
    operator_approved: bool = False,
    request_live_llm: bool = False,
    request_ollama: bool = False,
    allow_live_llm: bool = False,
    allow_ollama: bool = False,
    live_llm_timeout_seconds: int | None = None,
    live_model_allowed: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> TwfWorkflowRequestDraftCandidate:
    turn_input = TwfChatTurnInputCandidate(
        sanitized_user_text=sanitized_user_text,
        chat_session_id=chat_session_id,
        turn_index=turn_index,
        sanitized_history=tuple(dict(item) for item in sanitized_history),
        sanitized_previous_display_text=sanitized_previous_display_text,
        metadata={
            "source": "cognition_operation_flows._requests.drafts",
            "input_stage": "channel_sanitized",
        },
    )
    return TwfWorkflowRequestDraftCandidate(
        workflow_name=workflow_name,
        task_kind=task_kind,
        turn_input=turn_input,
        governance_refs=_coerce_governance_refs(governance_refs),
        controls=_coerce_controls(controls),
        route_summary=dict(route_summary or {}),
        entrypoint_explicit_args=dict(entrypoint_explicit_args or {}),
        session_args=dict(session_args or {}),
        user_passthrough_parameters=dict(user_passthrough_parameters or {}),
        operator_approved=operator_approved,
        request_live_llm=request_live_llm,
        request_ollama=request_ollama,
        allow_live_llm=allow_live_llm,
        allow_ollama=allow_ollama,
        live_llm_timeout_seconds=live_llm_timeout_seconds,
        live_model_allowed=live_model_allowed,
        metadata={
            "source": "cognition_operation_flows._requests.drafts",
            "request_draft_candidate": True,
            "runtime_adapter_required": True,
            **dict(metadata or {}),
        },
    )


def _coerce_governance_refs(
    governance_refs: TwfGovernanceRefsCandidate | Mapping[str, Any] | None,
) -> TwfGovernanceRefsCandidate:
    if isinstance(governance_refs, TwfGovernanceRefsCandidate):
        return governance_refs
    return TwfGovernanceRefsCandidate(**dict(governance_refs or {}))


def _coerce_controls(
    controls: TwfReferenceWorkspaceControlsCandidate | Mapping[str, Any] | None,
) -> TwfReferenceWorkspaceControlsCandidate:
    if isinstance(controls, TwfReferenceWorkspaceControlsCandidate):
        return controls
    payload = dict(controls or {})
    for tuple_key in (
        "reference_paths",
        "external_readonly_evidence_paths",
        "audit_focus",
    ):
        if tuple_key in payload:
            payload[tuple_key] = tuple(str(item) for item in payload[tuple_key])
    return TwfReferenceWorkspaceControlsCandidate(**payload)


def _validate_history(history: Sequence[Mapping[str, str]]) -> None:
    for item in history:
        if not isinstance(item, Mapping):
            raise ValueError("sanitized_history items must be mappings.")
        for key, value in item.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("sanitized_history keys and values must be strings.")


def _validate_string_tuple(value: Sequence[str], field_name: str) -> None:
    if any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} items must be strings.")


def _validate_mapping_boundary(
    value: Mapping[str, Any],
    *,
    field_name: str,
    allow_managed_parameters: bool,
) -> None:
    forbidden_keys = tuple(
        key
        for key in value
        if str(key).lower() in TWF_REQUEST_DRAFT_FORBIDDEN_INPUT_KEYS
    )
    if forbidden_keys:
        joined = ", ".join(sorted(str(key) for key in forbidden_keys))
        raise ValueError(f"{field_name} contains forbidden runtime keys: {joined}.")
    if not allow_managed_parameters:
        managed_conflicts = tuple(
            key for key in value if str(key) in MANAGED_GOVERNANCE_PARAMETERS
        )
        if managed_conflicts:
            joined = ", ".join(sorted(str(key) for key in managed_conflicts))
            raise ValueError(f"{field_name} contains managed governance keys: {joined}.")
    validate_task_workflow_metadata_boundary(value, field_name=field_name)
    _validate_no_forbidden_runtime_objects(value, field_name=field_name)


def _validate_no_forbidden_runtime_objects(
    value: Any,
    *,
    field_name: str,
) -> None:
    for path, item in _walk(value):
        if isinstance(item, Mapping):
            object_module = item.get("object_module")
            if isinstance(object_module, str) and object_module.startswith(
                (
                    "argparse",
                    "cognition_cli",
                    "product_gateway",
                    "runtime_container",
                )
            ):
                raise ValueError(
                    f"{field_name} contains forbidden object module at {path}."
                )
            continue
        if item is None or isinstance(item, (str, int, float, bool, list, tuple, dict)):
            continue
        if type(item).__module__.startswith(
            ("argparse", "cognition_cli", "product_gateway", "runtime_container")
        ):
            raise ValueError(
                f"{field_name} contains forbidden runtime object at {path}."
            )


def _walk(value: Any, path: str = "$") -> tuple[tuple[str, Any], ...]:
    items: list[tuple[str, Any]] = [(path, value)]
    if isinstance(value, Mapping):
        for key, item in value.items():
            items.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_walk(item, f"{path}[{index}]"))
    return tuple(items)
