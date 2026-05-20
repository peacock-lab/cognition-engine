"""CLI-facing product gateway aggregation surface."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from schemas.product_gateway_cli import (
    PRODUCT_GATEWAY_CLI_TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME,
    PRODUCT_GATEWAY_CLI_TWF_REFERENCE_REVIEW_WORKFLOW_NAME,
    PRODUCT_GATEWAY_CLI_TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
    ProductGatewayCliReferenceReaderPolicySchema,
    ProductGatewayCliToolExposureResolutionSchema,
    ProductGatewayCliTwfExecutionInputSchema,
    ProductGatewayCliTwfExecutionResultSchema,
    ProductGatewayCliTwfLatestPlanSnapshotSchema,
    ProductGatewayCliTwfRequestDraftInputSchema,
    ProductGatewayCliTwfRunWorkspaceSnapshotSchema,
    ProductGatewayCliTwfRouteInputSchema,
    ProductGatewayCliTwfRouteProjectionSchema,
    ProductGatewayCliTwfStatusSummaryPersistenceSchema,
)

from product_gateway._task_workflows.controls import (
    build_internal_twf_skill_capability_projection_status,
    build_internal_twf_tools_status,
    resolve_internal_twf_tool_exposure_profile,
)
from product_gateway._task_workflows.execution import (
    InternalTwfExecutionContext,
    InternalTwfExecutionInput,
    execute_internal_twf_workflow,
)
from product_gateway._task_workflows.request import (
    build_internal_twf_config_profile_explain_request_draft,
    build_internal_twf_plan_request_draft,
    build_internal_twf_reference_review_request_draft,
    build_internal_twf_run_workspace_evidence_audit_request_draft,
)
from product_gateway._task_workflows.route import (
    build_internal_twf_route_projection,
)
from product_gateway._task_workflows.workspace import (
    build_internal_twf_run_workspace_policy,
    create_internal_twf_run_workspace,
    finalize_internal_twf_run_workspace,
    restore_internal_twf_run_workspace_snapshot,
    write_internal_twf_run_workspace_json,
    write_internal_twf_run_workspace_text,
)
from product_gateway.response_summary_projection import (
    project_product_gateway_response_summary,
)


def build_cli_twf_route_projection(
    route_input: ProductGatewayCliTwfRouteInputSchema | Mapping[str, Any],
) -> Any:
    """Build a task workflow route projection through one CLI-facing entry."""

    normalized = _route_input(route_input)
    projection = build_internal_twf_route_projection(
        normalized.model_dump(mode="python")
    )
    return ProductGatewayCliTwfRouteProjectionSchema.model_validate(
        projection.model_dump(mode="python")
    )


def _build_cli_twf_request_draft(
    draft_input: ProductGatewayCliTwfRequestDraftInputSchema | Mapping[str, Any],
) -> Any:
    """Build a task workflow request draft behind the product gateway surface."""

    normalized = _draft_input(draft_input)
    common = {
        "sanitized_user_text": normalized.sanitized_user_text,
        "chat_session_id": normalized.chat_session_id,
        "turn_index": normalized.turn_index,
        "sanitized_history": tuple(normalized.sanitized_history),
        "governance_refs": _model_dump_or_none(normalized.governance_refs),
        "controls": _model_dump_or_none(normalized.controls),
        "route_summary": normalized.route_summary,
        "user_passthrough_parameters": normalized.user_passthrough_parameters,
        "operator_approved": normalized.operator_approved,
        "request_live_llm": normalized.request_live_llm,
        "request_ollama": normalized.request_ollama,
        "allow_live_llm": normalized.allow_live_llm,
        "allow_ollama": normalized.allow_ollama,
        "live_llm_timeout_seconds": normalized.live_llm_timeout_seconds,
        "live_model_allowed": normalized.live_model_allowed,
        "metadata": dict(normalized.metadata),
    }
    if normalized.workflow_name == PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME:
        return build_internal_twf_plan_request_draft(
            sanitized_previous_display_text=normalized.sanitized_previous_display_text,
            **common,
        )
    if (
        normalized.workflow_name
        == PRODUCT_GATEWAY_CLI_TWF_REFERENCE_REVIEW_WORKFLOW_NAME
    ):
        return build_internal_twf_reference_review_request_draft(**common)
    if (
        normalized.workflow_name
        == PRODUCT_GATEWAY_CLI_TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME
    ):
        return build_internal_twf_config_profile_explain_request_draft(
            entrypoint_explicit_args=normalized.entrypoint_explicit_args,
            session_args=normalized.session_args,
            **common,
        )
    if (
        normalized.workflow_name
        == PRODUCT_GATEWAY_CLI_TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME
    ):
        return build_internal_twf_run_workspace_evidence_audit_request_draft(
            **common
        )
    raise ValueError(f"unsupported CLI task workflow: {normalized.workflow_name}")


def execute_cli_twf_workflow(
    *,
    execution_input: ProductGatewayCliTwfExecutionInputSchema,
    config_context: Any | None = None,
    llm_invocation_service_factory: Any | None = None,
) -> ProductGatewayCliTwfExecutionResultSchema:
    """Execute a task workflow through the CLI-facing product gateway surface."""

    options = execution_input.execution_options
    request_draft = _build_cli_twf_request_draft(execution_input.request_draft_input)
    result = execute_internal_twf_workflow(
        InternalTwfExecutionInput(
            request_id=execution_input.request_id,
            route_projection=execution_input.route_projection,
            request_draft=request_draft,
            execution_context=InternalTwfExecutionContext(
                llm_invocation_service_factory=llm_invocation_service_factory,
                config_context=config_context,
                config_root=options.config_root,
                environment=options.environment,
                profile=options.profile,
                ollama_api_base=options.ollama_api_base,
                reference_profile_config=options.reference_profile_config,
                reference_session_args=dict(options.reference_session_args),
                reference_entrypoint_explicit_args=dict(
                    options.reference_entrypoint_explicit_args
                ),
            ),
        )
    )
    return _execution_result_schema(result)


def build_cli_twf_latest_plan_status(
    latest_plan_snapshot: ProductGatewayCliTwfLatestPlanSnapshotSchema
    | Mapping[str, Any]
    | None,
) -> dict[str, Any]:
    """Build the status payload fragment for the latest plan snapshot."""

    snapshot = _latest_plan_snapshot_or_none(latest_plan_snapshot)
    if snapshot is None:
        return _latest_plan_not_run_status()
    workspace = snapshot.workspace
    route_projection = snapshot.product_gateway_route_projection or {
        **_route_projection_not_run_status(),
        "status": "not_available",
    }
    return {
        "status": snapshot.status,
        "reference_context_status": snapshot.reference_context_status,
        "reference_evidence_ref_count": snapshot.reference_evidence_ref_count,
        "workspace_created": bool(
            workspace is not None and workspace.workspace_created
        ),
        "workspace_ref": workspace.workspace_ref if workspace is not None else None,
        "workspace_artifact_ref_count": (
            len(workspace.artifact_refs) if workspace is not None else 0
        ),
        "workspace_result_ref_count": (
            len(workspace.result_refs) if workspace is not None else 0
        ),
        "product_gateway_route_projection": dict(route_projection),
    }


def persist_cli_twf_status_summary(
    *,
    latest_plan_snapshot: ProductGatewayCliTwfLatestPlanSnapshotSchema
    | Mapping[str, Any]
    | None,
    status_summary_payload: Mapping[str, Any],
) -> ProductGatewayCliTwfStatusSummaryPersistenceSchema:
    """Persist a status summary artifact from a CLI-facing latest-plan snapshot."""

    snapshot = _latest_plan_snapshot_or_none(latest_plan_snapshot)
    if snapshot is None or snapshot.workspace is None:
        return ProductGatewayCliTwfStatusSummaryPersistenceSchema(
            latest_plan_snapshot=snapshot,
            status="skipped",
            warnings=("latest_plan_snapshot_unavailable",),
        )
    workspace_snapshot = snapshot.workspace
    if not workspace_snapshot.workspace_created or workspace_snapshot.cleanup_performed:
        return ProductGatewayCliTwfStatusSummaryPersistenceSchema(
            latest_plan_snapshot=snapshot,
            status="skipped",
            warnings=("run_workspace_unavailable",),
        )

    max_write_bytes = int(
        workspace_snapshot.max_write_bytes
        or workspace_snapshot.metadata.get("max_write_bytes")
        or 65536
    )
    workspace = restore_internal_twf_run_workspace_snapshot(
        workspace_snapshot.model_dump(mode="python")
    )
    workspace, write_result = write_internal_twf_run_workspace_json(
        workspace,
        relative_path="artifacts/status_summary.json",
        payload=status_summary_payload,
        kind="artifact",
        max_write_bytes=max_write_bytes,
    )
    if write_result.status != "succeeded":
        return ProductGatewayCliTwfStatusSummaryPersistenceSchema(
            latest_plan_snapshot=snapshot,
            status=write_result.status,
            blocking_reasons=tuple(write_result.blocking_reasons),
            warnings=tuple(write_result.warnings),
        )

    updated_snapshot = _replace_latest_plan_workspace(snapshot, workspace)
    payload_with_ref = dict(status_summary_payload)
    payload_with_ref["latest_plan"] = build_cli_twf_latest_plan_status(
        updated_snapshot
    )
    payload_with_ref["status_summary_artifact_ref"] = write_result.ref
    workspace, write_result = write_internal_twf_run_workspace_json(
        workspace,
        relative_path="artifacts/status_summary.json",
        payload=payload_with_ref,
        kind="artifact",
        max_write_bytes=max_write_bytes,
    )
    if write_result.status != "succeeded":
        return ProductGatewayCliTwfStatusSummaryPersistenceSchema(
            latest_plan_snapshot=updated_snapshot,
            status=write_result.status,
            blocking_reasons=tuple(write_result.blocking_reasons),
            warnings=tuple(write_result.warnings),
        )

    workspace = finalize_internal_twf_run_workspace(
        workspace,
        status=updated_snapshot.status,
        metadata={"status_summary_artifact_ref": write_result.ref},
    )
    updated_snapshot = _replace_latest_plan_workspace(updated_snapshot, workspace)
    return ProductGatewayCliTwfStatusSummaryPersistenceSchema(
        latest_plan_snapshot=updated_snapshot,
        status_summary_artifact_ref=write_result.ref,
        status="succeeded",
    )


def resolve_cli_twf_tool_exposure_profile(
    *,
    profile_name: str,
    profile_config: Mapping[str, Any] | None = None,
    repo_root: str | None = None,
    entrypoint_explicit_args: Mapping[str, Any] | None = None,
) -> ProductGatewayCliToolExposureResolutionSchema:
    """Resolve tool exposure as a CLI-facing contract schema."""

    resolution = resolve_internal_twf_tool_exposure_profile(
        profile_name=profile_name,
        profile_config=profile_config,
        repo_root=repo_root,
        entrypoint_explicit_args=entrypoint_explicit_args,
    )
    policy = resolution.reference_reader_policy
    return ProductGatewayCliToolExposureResolutionSchema(
        status=resolution.status,
        exposed_tool_names=tuple(resolution.exposed_tool_names),
        blocked_tool_names=tuple(resolution.blocked_tool_names),
        blocking_reasons=tuple(resolution.blocking_reasons),
        warnings=tuple(resolution.warnings),
        reference_reader_policy=(
            ProductGatewayCliReferenceReaderPolicySchema(
                allowed_roots=tuple(policy.allowed_roots),
                allowed_files=tuple(policy.allowed_files),
                allowed_suffixes=tuple(policy.allowed_suffixes),
                max_bytes=policy.max_bytes,
                max_chars=policy.max_chars,
                max_excerpt_lines=policy.max_excerpt_lines,
                metadata=dict(policy.metadata),
            )
            if policy is not None
            else None
        ),
        metadata=dict(resolution.metadata),
    )


def build_cli_twf_tools_status(
    *,
    profile_name: str,
    profile_config: Mapping[str, Any] | None,
    repo_root: str,
    entrypoint_explicit_args: Mapping[str, Any],
    operator_approved: bool,
    approval_ref: str | None,
) -> dict[str, Any]:
    """Build CLI-facing task workflow tools status."""

    return build_internal_twf_tools_status(
        profile_name=profile_name,
        profile_config=profile_config,
        repo_root=repo_root,
        entrypoint_explicit_args=entrypoint_explicit_args,
        operator_approved=operator_approved,
        approval_ref=approval_ref,
    )


def build_cli_twf_skill_capability_projection_status() -> dict[str, Any]:
    """Build CLI-facing Skills capability projection status."""

    return build_internal_twf_skill_capability_projection_status()


def build_cli_twf_run_workspace_policy(
    *,
    workspace_root: Any,
    retention_policy: str,
    cleanup_policy: str,
    max_write_bytes: int,
) -> Any:
    """Build a run-workspace policy through the product gateway surface."""

    return build_internal_twf_run_workspace_policy(
        workspace_root=workspace_root,
        retention_policy=retention_policy,
        cleanup_policy=cleanup_policy,
        max_write_bytes=max_write_bytes,
    )


def create_cli_twf_run_workspace(
    *,
    policy: Any,
    workflow_name: str,
    run_id: str,
) -> Any:
    """Create a run workspace through the product gateway surface."""

    return create_internal_twf_run_workspace(
        policy=policy,
        workflow_name=workflow_name,
        run_id=run_id,
    )


def write_cli_twf_run_workspace_json(
    workspace: Any,
    *,
    relative_path: str,
    payload: Mapping[str, Any],
    kind: str,
    max_write_bytes: int,
) -> tuple[Any, Any]:
    """Write a run-workspace JSON artifact through the product gateway surface."""

    return write_internal_twf_run_workspace_json(
        workspace,
        relative_path=relative_path,
        payload=payload,
        kind=kind,
        max_write_bytes=max_write_bytes,
    )


def write_cli_twf_run_workspace_text(
    workspace: Any,
    *,
    relative_path: str,
    text: str,
    kind: str,
    max_write_bytes: int | None = None,
) -> tuple[Any, Any]:
    """Write a run-workspace text artifact through the product gateway surface."""

    return write_internal_twf_run_workspace_text(
        workspace,
        relative_path=relative_path,
        text=text,
        kind=kind,
        max_write_bytes=max_write_bytes,
    )


def finalize_cli_twf_run_workspace(
    workspace: Any,
    *,
    status: str,
    metadata: Mapping[str, Any] | None = None,
) -> Any:
    """Finalize a run workspace through the product gateway surface."""

    return finalize_internal_twf_run_workspace(
        workspace,
        status=status,
        metadata=metadata,
    )


def _execution_result_schema(result: Any) -> ProductGatewayCliTwfExecutionResultSchema:
    product_response = result.product_response
    latest_plan_snapshot = _latest_plan_snapshot(result)
    return ProductGatewayCliTwfExecutionResultSchema(
        handled=bool(result.handled),
        terminal_display_text=result.terminal_display_text,
        latest_plan_display_text=result.latest_plan_display_text,
        latest_plan_snapshot=latest_plan_snapshot,
        product_response_summary=project_product_gateway_response_summary(
            product_response
        ),
        blocking_reasons=tuple(product_response.blocking_reasons),
        warnings=tuple(product_response.warnings),
        metadata={
            "source": "product_gateway.cli_surface",
            "updates_latest_plan": bool(result.updates_latest_plan),
        },
    )


def _latest_plan_snapshot(
    result: Any,
) -> ProductGatewayCliTwfLatestPlanSnapshotSchema | None:
    workflow_result = getattr(result, "latest_plan_snapshot", None)
    workflow_result = workflow_result or getattr(result, "latest_plan_result", None)
    if workflow_result is None:
        return None

    reference_context = getattr(workflow_result, "reference_context", None)
    request = getattr(workflow_result, "request", None)
    request_metadata = getattr(request, "metadata", {})
    if not isinstance(request_metadata, Mapping):
        request_metadata = {}
    return ProductGatewayCliTwfLatestPlanSnapshotSchema(
        status=_plan_result_status(workflow_result),
        reference_context_status=(
            reference_context.status if reference_context is not None else "not_run"
        ),
        reference_evidence_ref_count=(
            len(reference_context.evidence_refs)
            if reference_context is not None
            else 0
        ),
        workspace=_workspace_snapshot(
            getattr(workflow_result, "run_workspace", None)
        ),
        product_gateway_route_projection=_route_projection_summary_from_workflow_result(
            workflow_result
        ),
        no_live=bool(getattr(workflow_result, "no_live", False)),
        fail_safe=bool(getattr(workflow_result, "fail_safe", False)),
        quality_review_present=getattr(workflow_result, "quality_review", None)
        is not None,
        model_call_count=int(getattr(workflow_result, "model_call_count", 0) or 0),
        metadata={
            "source": "product_gateway.cli_surface",
            "workflow_name": request_metadata.get("builder_target"),
        },
    )


def _workspace_snapshot(
    workspace: Any | None,
) -> ProductGatewayCliTwfRunWorkspaceSnapshotSchema | None:
    if workspace is None:
        return None
    metadata = dict(getattr(workspace, "metadata", {}) or {})
    return ProductGatewayCliTwfRunWorkspaceSnapshotSchema(
        workspace_ref=getattr(workspace, "workspace_ref", None),
        workspace_path=getattr(workspace, "workspace_path", None),
        workflow_name=getattr(workspace, "workflow_name", None),
        run_id=getattr(workspace, "run_id", None),
        workspace_created=bool(getattr(workspace, "workspace_created", False)),
        retention_policy=getattr(workspace, "retention_policy", None),
        cleanup_policy=getattr(workspace, "cleanup_policy", None),
        cleanup_performed=bool(getattr(workspace, "cleanup_performed", False)),
        manifest_path=getattr(workspace, "manifest_path", None),
        subdirs=tuple(getattr(workspace, "subdirs", ()) or ()),
        artifact_refs=tuple(getattr(workspace, "artifact_refs", ()) or ()),
        evidence_refs=tuple(getattr(workspace, "evidence_refs", ()) or ()),
        result_refs=tuple(getattr(workspace, "result_refs", ()) or ()),
        blocking_reasons=tuple(getattr(workspace, "blocking_reasons", ()) or ()),
        warnings=tuple(getattr(workspace, "warnings", ()) or ()),
        max_write_bytes=(
            int(metadata["max_write_bytes"])
            if metadata.get("max_write_bytes") is not None
            else None
        ),
        metadata=metadata,
    )


def _replace_latest_plan_workspace(
    snapshot: ProductGatewayCliTwfLatestPlanSnapshotSchema,
    workspace: Any,
) -> ProductGatewayCliTwfLatestPlanSnapshotSchema:
    return snapshot.model_copy(update={"workspace": _workspace_snapshot(workspace)})


def _latest_plan_snapshot_or_none(
    value: ProductGatewayCliTwfLatestPlanSnapshotSchema | Mapping[str, Any] | None,
) -> ProductGatewayCliTwfLatestPlanSnapshotSchema | None:
    if value is None:
        return None
    if isinstance(value, ProductGatewayCliTwfLatestPlanSnapshotSchema):
        return value
    return ProductGatewayCliTwfLatestPlanSnapshotSchema.model_validate(dict(value))


def _plan_result_status(plan_result: Any) -> str:
    if bool(getattr(plan_result, "fail_safe", False)):
        return (
            "failed"
            if not bool(getattr(plan_result, "no_live", False))
            else "blocked"
        )
    if bool(getattr(plan_result, "no_live", False)):
        return "no_live_boundary"
    return (
        "succeeded"
        if getattr(plan_result, "quality_review", None)
        else "triggered"
    )


def _route_projection_summary_from_workflow_result(
    workflow_result: Any,
) -> dict[str, Any]:
    request = getattr(workflow_result, "request", None)
    metadata = getattr(request, "metadata", None)
    if isinstance(metadata, Mapping):
        projection = metadata.get("product_gateway_route_projection")
        if isinstance(projection, Mapping):
            return dict(projection)
    return {
        **_route_projection_not_run_status(),
        "status": "not_available",
    }


def _latest_plan_not_run_status() -> dict[str, Any]:
    return {
        "status": "not_run",
        "reference_context_status": "not_run",
        "reference_evidence_ref_count": 0,
        "workspace_created": False,
        "workspace_ref": None,
        "workspace_artifact_ref_count": 0,
        "workspace_result_ref_count": 0,
        "product_gateway_route_projection": _route_projection_not_run_status(),
    }


def _route_projection_not_run_status() -> dict[str, Any]:
    return {
        "status": "not_run",
        "entry_kind": None,
        "execution_mode": None,
        "source": None,
        "workflow_name": None,
        "workflow_version": None,
        "task_kind": None,
        "route_reason": None,
        "confidence": "none",
        "requires_live_model": False,
        "requires_workspace": False,
        "requires_tools": [],
        "registry_workflow_count": 0,
        "route_only": False,
        "workflow_execution_enabled": False,
    }
def _value(value: Any) -> Any:
    return getattr(value, "value", value)


def _route_input(
    value: ProductGatewayCliTwfRouteInputSchema | Mapping[str, Any],
) -> ProductGatewayCliTwfRouteInputSchema:
    if isinstance(value, ProductGatewayCliTwfRouteInputSchema):
        return value
    return ProductGatewayCliTwfRouteInputSchema.model_validate(dict(value))


def _draft_input(
    value: ProductGatewayCliTwfRequestDraftInputSchema | Mapping[str, Any],
) -> ProductGatewayCliTwfRequestDraftInputSchema:
    if isinstance(value, ProductGatewayCliTwfRequestDraftInputSchema):
        return value
    return ProductGatewayCliTwfRequestDraftInputSchema.model_validate(dict(value))


def _model_dump_or_none(value: Any | None) -> dict[str, Any] | None:
    if value is None:
        return None
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return dict(model_dump(mode="python"))
    return dict(value)


__all__ = [
    "build_cli_twf_run_workspace_policy",
    "build_cli_twf_latest_plan_status",
    "build_cli_twf_route_projection",
    "build_cli_twf_skill_capability_projection_status",
    "build_cli_twf_tools_status",
    "create_cli_twf_run_workspace",
    "execute_cli_twf_workflow",
    "finalize_cli_twf_run_workspace",
    "persist_cli_twf_status_summary",
    "resolve_cli_twf_tool_exposure_profile",
    "write_cli_twf_run_workspace_json",
    "write_cli_twf_run_workspace_text",
]
