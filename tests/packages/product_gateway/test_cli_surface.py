from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import product_gateway.cli_surface as cli_surface_module
from contract_core.llm_invocation import (
    GovernedLlmInvocationServiceResolution,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from schemas.product_gateway_cli import (
    PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME,
    ProductGatewayCliTwfExecutionInputSchema,
    ProductGatewayCliTwfExecutionResultSchema,
    ProductGatewayCliTwfGovernanceRefsSchema,
    ProductGatewayCliTwfLatestPlanSnapshotSchema,
    ProductGatewayCliTwfReferenceWorkspaceControlsSchema,
    ProductGatewayCliTwfRequestDraftInputSchema,
    ProductGatewayCliTwfRunWorkspaceSnapshotSchema,
    ProductGatewayCliTwfRouteInputSchema,
)
from schemas.product_gateway_response_summary import (
    validate_product_gateway_response_summary,
)

from product_gateway.cli_surface import (
    build_cli_twf_latest_plan_status,
    build_cli_twf_run_workspace_policy,
    build_cli_twf_route_projection,
    create_cli_twf_run_workspace,
    execute_cli_twf_workflow,
    persist_cli_twf_status_summary,
    resolve_cli_twf_tool_exposure_profile,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCT_GATEWAY_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "product_gateway" / "src" / "product_gateway"
)


class FakeCliSurfaceLlmService:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.requests: list[LlmInvocationRequest] = []

    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        self.requests.append(request)
        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=request.route_facts,
            governance_precondition=request.governance_precondition,
            call_attempted=True,
            call_allowed=True,
            runtime_call_performed=True,
            success=True,
            response_non_empty=True,
            sanitized_response_length=len(self.output_text),
            sanitized_response_preview=self.output_text[:120],
            metadata={
                "sanitized_response_display": self.output_text,
                "source": "test_cli_surface",
            },
        )


class FakeCliSurfaceLlmServiceFactory:
    def __init__(self, service: FakeCliSurfaceLlmService) -> None:
        self.service = service
        self.captured: dict[str, Any] = {}

    def resolve(
        self,
        *,
        config_context=None,
        config_selection,
        live_llm_options,
    ) -> GovernedLlmInvocationServiceResolution:
        self.captured = {
            "config_context": config_context,
            "config_selection": config_selection,
            "live_llm_options": live_llm_options,
        }
        return GovernedLlmInvocationServiceResolution(service=self.service)


def test_cli_surface_builds_route_projection_from_contract_schema() -> None:
    projection = build_cli_twf_route_projection(
        ProductGatewayCliTwfRouteInputSchema(
            request_id="cli-surface-route/turn-001",
            sanitized_user_text="我要建一个鱼塘，帮我设计方案",
            chat_session_id="cli-surface-route",
            turn_index=1,
        )
    )

    assert projection.request_id == "cli-surface-route/turn-001"
    assert projection.entry_kind == "task_workflow_route"
    assert projection.matched is True
    assert projection.workflow_name == PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME


def test_cli_surface_executes_request_from_contract_input() -> None:
    projection = build_cli_twf_route_projection(
        ProductGatewayCliTwfRouteInputSchema(
            request_id="cli-surface-execute/turn-001",
            sanitized_user_text="我要建一个鱼塘，帮我设计方案",
            chat_session_id="cli-surface-execute",
            turn_index=1,
        )
    )
    result = execute_cli_twf_workflow(
        execution_input=ProductGatewayCliTwfExecutionInputSchema(
            request_id="cli-surface-execute/turn-001",
            route_projection=projection,
            request_draft_input=ProductGatewayCliTwfRequestDraftInputSchema(
                workflow_name=PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME,
                sanitized_user_text="我要建一个鱼塘，帮我设计方案",
                chat_session_id="cli-surface-execute",
                turn_index=1,
                governance_refs=ProductGatewayCliTwfGovernanceRefsSchema(
                    approval_ref="approval://cli-surface",
                    audit_ref="audit://cli-surface",
                ),
                controls=ProductGatewayCliTwfReferenceWorkspaceControlsSchema(),
            ),
        )
    )

    assert result.handled is True
    assert isinstance(result, ProductGatewayCliTwfExecutionResultSchema)
    assert result.product_response_summary["request_id"] == (
        "cli-surface-execute/turn-001"
    )
    assert result.product_response_summary["entry_kind"] == "task_workflow_execution"
    assert result.product_response_summary["payload_type"] == (
        "product_gateway_response_summary"
    )
    assert result.product_response_summary["payload_version"] == (
        "product_gateway_response_summary_v1"
    )
    assert result.product_response_summary["readonly"] is True
    assert result.product_response_summary["summary_only"] is True
    assert result.product_response_summary["refs_only"] is True
    assert result.product_response_summary["candidate_only"] is True
    assert result.product_response_summary["execution_enabled"] is False
    assert result.product_response_summary["llm_call_enabled"] is False
    assert result.product_response_summary["tool_execution_enabled"] is False
    assert result.product_response_summary["action_execution_enabled"] is False
    validate_product_gateway_response_summary(result.product_response_summary)
    assert result.latest_plan_snapshot is not None
    assert result.latest_plan_snapshot.metadata["workflow_name"] == (
        PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME
    )


def test_cli_surface_blocks_live_twf_without_injected_factory() -> None:
    projection = build_cli_twf_route_projection(
        ProductGatewayCliTwfRouteInputSchema(
            request_id="cli-surface-live/turn-001",
            sanitized_user_text="我要建一个鱼塘，帮我设计方案",
            chat_session_id="cli-surface-live",
            turn_index=1,
            live_model_requested=True,
        )
    )
    result = execute_cli_twf_workflow(
        execution_input=ProductGatewayCliTwfExecutionInputSchema(
            request_id="cli-surface-live/turn-001",
            route_projection=projection,
            request_draft_input=ProductGatewayCliTwfRequestDraftInputSchema(
                workflow_name=PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME,
                sanitized_user_text="我要建一个鱼塘，帮我设计方案",
                chat_session_id="cli-surface-live",
                turn_index=1,
                governance_refs=ProductGatewayCliTwfGovernanceRefsSchema(
                    approval_ref="approval://cli-surface-live",
                    audit_ref="audit://cli-surface-live",
                    live_llm_approval_ref="approval://cli-surface-live/llm",
                ),
                controls=ProductGatewayCliTwfReferenceWorkspaceControlsSchema(),
                operator_approved=True,
                request_live_llm=True,
                request_ollama=True,
                allow_live_llm=True,
                allow_ollama=True,
                live_llm_timeout_seconds=12,
                live_model_allowed=True,
            ),
            execution_options={
                "config_root": "config/twf",
                "environment": "local",
                "profile": "dev",
                "ollama_api_base": "http://127.0.0.1:11434",
            },
        ),
        config_context={"live_llm": "fake"},
    )

    assert result.product_response_summary["status"] == "blocked"
    assert result.blocking_reasons == ("twf_live_llm_provider_not_injected",)
    assert result.warnings == ("twf_live_llm_provider_required",)
    assert result.terminal_display_text is None


def test_cli_surface_uses_explicit_factory() -> None:
    service = FakeCliSurfaceLlmService("显式 factory 输出")
    factory = FakeCliSurfaceLlmServiceFactory(service)

    projection = build_cli_twf_route_projection(
        ProductGatewayCliTwfRouteInputSchema(
            request_id="cli-surface-explicit-live/turn-001",
            sanitized_user_text="我要建一个鱼塘，帮我设计方案",
            chat_session_id="cli-surface-explicit-live",
            turn_index=1,
            live_model_requested=True,
        )
    )
    result = execute_cli_twf_workflow(
        execution_input=ProductGatewayCliTwfExecutionInputSchema(
            request_id="cli-surface-explicit-live/turn-001",
            route_projection=projection,
            request_draft_input=ProductGatewayCliTwfRequestDraftInputSchema(
                workflow_name=PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME,
                sanitized_user_text="我要建一个鱼塘，帮我设计方案",
                governance_refs=ProductGatewayCliTwfGovernanceRefsSchema(
                    approval_ref="approval://cli-surface-explicit-live",
                    audit_ref="audit://cli-surface-explicit-live",
                    live_llm_approval_ref=(
                        "approval://cli-surface-explicit-live/llm"
                    ),
                ),
                operator_approved=True,
                request_live_llm=True,
                request_ollama=True,
                allow_live_llm=True,
                allow_ollama=True,
                live_model_allowed=True,
            ),
        ),
        llm_invocation_service_factory=factory,
    )

    assert result.product_response_summary["status"] == "success"
    assert len(service.requests) == 1


def test_cli_surface_builds_latest_plan_status_from_snapshot() -> None:
    status = build_cli_twf_latest_plan_status(
        ProductGatewayCliTwfLatestPlanSnapshotSchema(
            status="succeeded",
            reference_context_status="completed",
            reference_evidence_ref_count=2,
            workspace=ProductGatewayCliTwfRunWorkspaceSnapshotSchema(
                workspace_ref="workspace://latest-plan",
                workspace_created=True,
                artifact_refs=("artifact://terminal",),
                result_refs=("result://workflow",),
            ),
            product_gateway_route_projection={
                "status": "matched",
                "workflow_name": PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME,
            },
        )
    )

    assert status["status"] == "succeeded"
    assert status["workspace_created"] is True
    assert status["workspace_artifact_ref_count"] == 1
    assert status["workspace_result_ref_count"] == 1
    assert status["product_gateway_route_projection"]["status"] == "matched"


def test_cli_surface_persists_status_summary_from_snapshot(tmp_path: Path) -> None:
    policy = build_cli_twf_run_workspace_policy(
        workspace_root=tmp_path,
        retention_policy="keep",
        cleanup_policy="manual",
        max_write_bytes=65536,
    )
    workspace = create_cli_twf_run_workspace(
        policy=policy,
        workflow_name=PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME,
        run_id="cli-surface-status-summary",
    )
    snapshot = ProductGatewayCliTwfLatestPlanSnapshotSchema(
        status="succeeded",
        workspace=ProductGatewayCliTwfRunWorkspaceSnapshotSchema(
            workspace_ref=workspace.workspace_ref,
            workspace_path=workspace.workspace_path,
            workflow_name=workspace.workflow_name,
            run_id=workspace.run_id,
            workspace_created=workspace.workspace_created,
            retention_policy=workspace.retention_policy,
            cleanup_policy=workspace.cleanup_policy,
            manifest_path=workspace.manifest_path,
            subdirs=workspace.subdirs,
            metadata=workspace.metadata,
        ),
    )

    persistence = persist_cli_twf_status_summary(
        latest_plan_snapshot=snapshot,
        status_summary_payload={
            "product": "Cognition System / 认知系统",
            "command": "cognition chat /status",
        },
    )

    assert persistence.status == "succeeded"
    assert persistence.status_summary_artifact_ref is not None
    assert persistence.latest_plan_snapshot is not None
    assert persistence.latest_plan_snapshot.workspace is not None
    assert persistence.status_summary_artifact_ref in (
        persistence.latest_plan_snapshot.workspace.artifact_refs
    )


def test_cli_surface_does_not_export_request_draft_builder() -> None:
    import product_gateway

    assert product_gateway.__all__ == ()
    assert "cli_surface" not in product_gateway.__all__
    assert "build_cli_twf_request_draft" not in cli_surface_module.__all__
    assert not hasattr(cli_surface_module, "build_cli_twf_request_draft")


def test_cli_surface_keeps_private_request_draft_inside_surface() -> None:
    draft = ProductGatewayCliTwfRequestDraftInputSchema(
        workflow_name=PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME,
        sanitized_user_text="我要建一个鱼塘，帮我设计方案",
        chat_session_id="cli-surface-draft",
        turn_index=1,
        governance_refs=ProductGatewayCliTwfGovernanceRefsSchema(
            approval_ref="approval://cli-surface",
            audit_ref="audit://cli-surface",
        ),
        controls=ProductGatewayCliTwfReferenceWorkspaceControlsSchema(),
    )

    assert draft.workflow_name == PRODUCT_GATEWAY_CLI_TWF_PLAN_WORKFLOW_NAME
    assert draft.chat_session_id == "cli-surface-draft"


def test_cli_surface_resolves_tool_exposure_to_contract_schema() -> None:
    resolution = resolve_cli_twf_tool_exposure_profile(
        profile_name="readonly_reference",
        repo_root=str(REPO_ROOT),
    )

    assert resolution.status in {"resolved", "blocked"}
    assert isinstance(resolution.exposed_tool_names, tuple)


def test_cli_surface_source_has_no_runtime_or_composition_imports() -> None:
    source = (PRODUCT_GATEWAY_SOURCE_ROOT / "cli_surface.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:runtime_container|composition|adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None
    assert "contract_core" not in source
