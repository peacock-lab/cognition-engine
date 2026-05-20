from __future__ import annotations

import hashlib
import json
from pathlib import Path

from contract_core.llm_invocation import (
    GovernedLlmInvocationServiceResolution,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayStatus,
)
from product_gateway._task_workflows.execution import (
    InternalTwfExecutionContext,
    InternalTwfExecutionInput,
    execute_internal_twf_workflow,
)
from product_gateway._task_workflows.request import (
    InternalTwfGovernanceRefs,
    InternalTwfReferenceWorkspaceControls,
    build_internal_twf_plan_request_draft,
    build_internal_twf_reference_review_request_draft,
)
from product_gateway._task_workflows.route import (
    build_internal_twf_route_projection,
)
from product_gateway.response_summary_projection import (
    project_product_gateway_response_summary,
)


class FakeProductGatewayLlmService:
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
                "source": "test_product_gateway_twf_execution",
            },
        )


class FakeProductGatewayLlmServiceFactory:
    def __init__(self, service: FakeProductGatewayLlmService) -> None:
        self.service = service
        self.captured: dict[str, object] = {}

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
        return GovernedLlmInvocationServiceResolution(
            service=self.service,
            warnings=("factory_warning",),
            metadata={"source": "test_factory"},
        )


def test_product_gateway_executes_twf_plan_draft_through_product_entry() -> None:
    route_projection = build_internal_twf_route_projection(
        {
            "request_id": "twf-execution-plan",
            "sanitized_user_text": "我要建一个鱼塘，500平米大，帮我设计建设方案",
            "chat_session_id": "session-product-gateway-execution",
            "turn_index": 1,
        }
    )
    request_draft = build_internal_twf_plan_request_draft(
        sanitized_user_text="我要建一个鱼塘，500平米大，帮我设计建设方案",
        chat_session_id="session-product-gateway-execution",
        turn_index=1,
        route_summary=route_projection.model_dump(),
        governance_refs=InternalTwfGovernanceRefs(
            approval_ref="approval://twf-execution-plan",
            audit_ref="audit://twf-execution-plan",
            sanitized_evidence_ref="evidence://twf-execution-plan",
            governance_summary_output_ref="artifact://twf-execution-plan",
        ),
        operator_approved=True,
        live_model_allowed=False,
    )

    result = execute_internal_twf_workflow(
        InternalTwfExecutionInput(
            request_id="twf-execution-plan",
            route_projection=route_projection,
            request_draft=request_draft,
        )
    )

    assert result.handled is True
    assert result.product_request.entry_kind is (
        ProductGatewayEntryKind.TASK_WORKFLOW_EXECUTION
    )
    assert result.product_request.execution_mode is ProductGatewayExecutionMode.NO_LIVE
    assert result.product_request.input_payload["workflow_name"] == (
        "twf_plan_workflow"
    )
    assert result.product_request.input_payload["route_matched"] is True
    assert result.product_response.status is ProductGatewayStatus.SUCCESS
    assert result.product_response.metadata["source"] == (
        "product_gateway._task_workflows.execution"
    )
    assert result.product_response.metadata["no_live"] is True
    assert result.updates_latest_plan is True
    assert result.latest_plan_result is result.workflow_result
    assert "未生成方案" in (result.terminal_display_text or "")
    assert "鱼塘" in (result.terminal_display_text or "")


def test_product_gateway_skips_unmatched_twf_route_without_execution() -> None:
    route_projection = build_internal_twf_route_projection(
        {
            "request_id": "twf-execution-skip",
            "sanitized_user_text": "你好，今天先不做任务",
            "chat_session_id": "session-product-gateway-execution",
            "turn_index": 2,
        }
    )
    request_draft = build_internal_twf_plan_request_draft(
        sanitized_user_text="我要建一个鱼塘，500平米大，帮我设计建设方案",
        chat_session_id="session-product-gateway-execution",
        turn_index=2,
        route_summary=route_projection.model_dump(),
    )

    result = execute_internal_twf_workflow(
        InternalTwfExecutionInput(
            request_id="twf-execution-skip",
            route_projection=route_projection,
            request_draft=request_draft,
        )
    )

    assert route_projection.matched is False
    assert result.handled is False
    assert result.product_request.entry_kind is (
        ProductGatewayEntryKind.TASK_WORKFLOW_EXECUTION
    )
    assert result.product_request.input_payload["route_matched"] is False
    assert result.product_response.status is ProductGatewayStatus.SKIPPED
    assert result.product_response.warnings == ["task_workflow_route_not_matched"]
    assert result.workflow_result is None


def test_product_gateway_blocks_live_twf_when_provider_not_injected() -> None:
    route_projection = build_internal_twf_route_projection(
        {
            "request_id": "twf-execution-live-blocked",
            "sanitized_user_text": "我要建一个鱼塘，500平米大，帮我设计建设方案",
            "chat_session_id": "session-product-gateway-execution",
            "turn_index": 3,
        }
    )
    request_draft = _live_plan_request_draft(
        route_projection=route_projection,
        request_id="twf-execution-live-blocked",
    )

    result = execute_internal_twf_workflow(
        InternalTwfExecutionInput(
            request_id="twf-execution-live-blocked",
            route_projection=route_projection,
            request_draft=request_draft,
        )
    )

    assert result.handled is True
    assert result.product_request.execution_mode is (
        ProductGatewayExecutionMode.CONTROLLED_LIVE
    )
    assert result.product_response.status is ProductGatewayStatus.BLOCKED
    assert result.product_response.blocking_reasons == [
        "twf_live_llm_provider_not_injected"
    ]
    assert result.product_response.warnings == [
        "twf_live_llm_provider_required"
    ]
    assert result.product_response.metadata["provider_resolution_blocked"] is True
    assert result.workflow_result is None


def test_product_gateway_executes_live_twf_with_injected_service() -> None:
    service = FakeProductGatewayLlmService(
        "1. 场地规划\n2. 建设步骤\n3. 运维安排"
    )
    route_projection = build_internal_twf_route_projection(
        {
            "request_id": "twf-execution-live-service",
            "sanitized_user_text": "我要建一个鱼塘，500平米大，帮我设计建设方案",
            "chat_session_id": "session-product-gateway-execution",
            "turn_index": 4,
        }
    )
    request_draft = _live_plan_request_draft(
        route_projection=route_projection,
        request_id="twf-execution-live-service",
    )

    result = execute_internal_twf_workflow(
        InternalTwfExecutionInput(
            request_id="twf-execution-live-service",
            route_projection=route_projection,
            request_draft=request_draft,
            execution_context=InternalTwfExecutionContext(
                llm_invocation_service=service
            ),
        )
    )

    assert result.product_response.status is ProductGatewayStatus.SUCCESS
    assert result.product_response.metadata["model_call_count"] == 1
    assert len(service.requests) == 1
    assert "鱼塘" in (result.terminal_display_text or "")


def test_product_gateway_executes_live_twf_with_injected_factory() -> None:
    service = FakeProductGatewayLlmService(
        "1. 场地规划\n2. 建设步骤\n3. 运维安排"
    )
    factory = FakeProductGatewayLlmServiceFactory(service)
    config_context = object()
    route_projection = build_internal_twf_route_projection(
        {
            "request_id": "twf-execution-live-factory",
            "sanitized_user_text": "我要建一个鱼塘，500平米大，帮我设计建设方案",
            "chat_session_id": "session-product-gateway-execution",
            "turn_index": 5,
        }
    )
    request_draft = _live_plan_request_draft(
        route_projection=route_projection,
        request_id="twf-execution-live-factory",
        timeout_seconds=12,
    )

    result = execute_internal_twf_workflow(
        InternalTwfExecutionInput(
            request_id="twf-execution-live-factory",
            route_projection=route_projection,
            request_draft=request_draft,
            execution_context=InternalTwfExecutionContext(
                llm_invocation_service_factory=factory,
                config_context=config_context,
                config_root="config/twf",
                environment="local",
                profile="dev",
                ollama_api_base="http://127.0.0.1:11434",
            ),
        )
    )

    config_selection = factory.captured["config_selection"]
    live_llm_options = factory.captured["live_llm_options"]
    assert result.product_response.status is ProductGatewayStatus.SUCCESS
    assert "factory_warning" in result.product_response.warnings
    assert factory.captured["config_context"] is config_context
    assert config_selection.config_root == "config/twf"
    assert config_selection.environment == "local"
    assert config_selection.profile == "dev"
    assert live_llm_options.ollama_api_base == "http://127.0.0.1:11434"
    assert live_llm_options.timeout_seconds == 12
    assert live_llm_options.metadata["request_id"] == (
        "twf-execution-live-factory"
    )
    assert len(service.requests) == 1


def test_product_gateway_twf_execution_consumes_external_readonly_refs(
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/product-gateway.json"
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    external_ref = (
        "evidence://external-readonly/cli-fetch/product-gateway.json"
    )
    route_projection = build_internal_twf_route_projection(
        {
            "request_id": "twf-execution-external-readonly-refs",
            "sanitized_user_text": "请审查这份外部只读证据摘要，指出问题和建议",
            "chat_session_id": "session-product-gateway-external-readonly",
            "turn_index": 6,
            "external_readonly_evidence_paths": (evidence_path,),
        }
    )
    request_draft = build_internal_twf_reference_review_request_draft(
        sanitized_user_text="请审查这份外部只读证据摘要，指出问题和建议",
        chat_session_id="session-product-gateway-external-readonly",
        turn_index=6,
        route_summary=route_projection.model_dump(),
        governance_refs=InternalTwfGovernanceRefs(
            approval_ref="approval://twf-execution-external-readonly-refs",
            audit_ref="audit://twf-execution-external-readonly-refs",
            sanitized_evidence_ref=(
                "evidence://twf-execution-external-readonly-refs"
            ),
            governance_summary_output_ref=(
                "artifact://twf-execution-external-readonly-refs"
            ),
        ),
        controls=InternalTwfReferenceWorkspaceControls(
            external_readonly_evidence_paths=(evidence_path,),
            external_readonly_evidence_repo_root=str(tmp_path),
        ),
        operator_approved=True,
        live_model_allowed=False,
    )

    result = execute_internal_twf_workflow(
        InternalTwfExecutionInput(
            request_id="twf-execution-external-readonly-refs",
            route_projection=route_projection,
            request_draft=request_draft,
        )
    )

    assert result.handled is True
    assert result.product_response.entry_kind is (
        ProductGatewayEntryKind.TASK_WORKFLOW_EXECUTION
    )
    assert result.product_response.status is ProductGatewayStatus.SUCCESS
    assert any(
        ref.ref == external_ref
        and ref.kind == "external_readonly_evidence"
        and ref.purpose == "external_readonly_readonly_public_refs"
        for ref in result.product_response.output_refs.evidence_refs
    )
    assert all(
        not (ref.ref == external_ref and ref.kind == "evidence")
        for ref in result.product_response.output_refs.evidence_refs
    )
    assert result.product_response.output_refs.additional_refs == []
    metadata = result.product_response.metadata
    assert metadata["external_readonly_refs_consumed"] is True
    assert metadata["external_readonly_refs_response_status"] == "success"
    assert metadata["external_readonly_refs_status"] == "ready"
    assert metadata["external_readonly_refs_evidence_ref_count"] == 1
    assert metadata["external_readonly_refs_additional_ref_count"] == 0

    serialized_metadata = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
    assert "external_readonly_evidence_context" not in serialized_metadata
    assert "summaries" not in serialized_metadata
    assert "sanitized_excerpt_preview" not in serialized_metadata

    summary = project_product_gateway_response_summary(result.product_response)
    assert summary["additional_refs"] == []
    assert any(
        ref["ref"] == external_ref
        and ref["kind"] == "external_readonly_evidence"
        for ref in summary["evidence_refs"]
    )


def _live_plan_request_draft(
    *,
    route_projection,
    request_id: str,
    timeout_seconds: int = 11,
):
    return build_internal_twf_plan_request_draft(
        sanitized_user_text="我要建一个鱼塘，500平米大，帮我设计建设方案",
        chat_session_id="session-product-gateway-execution",
        turn_index=1,
        route_summary=route_projection.model_dump(),
        governance_refs=InternalTwfGovernanceRefs(
            approval_ref=f"approval://{request_id}",
            audit_ref=f"audit://{request_id}",
            sanitized_evidence_ref=f"evidence://{request_id}",
            governance_summary_output_ref=f"artifact://{request_id}",
            live_llm_approval_ref=f"approval://{request_id}/live-llm",
        ),
        operator_approved=True,
        request_live_llm=True,
        request_ollama=True,
        allow_live_llm=True,
        allow_ollama=True,
        live_llm_timeout_seconds=timeout_seconds,
        live_model_allowed=True,
    )


def _external_readonly_archive(evidence_path: str) -> dict[str, object]:
    return {
        "allow_runtime_fetch": True,
        "allowed_for_model_context": True,
        "blocking_reasons": [],
        "command": "cognition external-readonly fetch",
        "evidence_output_path": evidence_path,
        "evidence_ref": (
            "evidence://external-readonly/"
            f"{Path(evidence_path).relative_to('outputs/external-readonly')}"
        ),
        "evidence_written": True,
        "external_network_call_performed": True,
        "raw_html_included": False,
        "raw_response_included": False,
        "response_headers_included": False,
        "runtime": {
            "allowed_for_model_context": True,
            "blocking_reasons": [],
            "content_hash": _hash(_excerpt()),
            "external_network_call_performed": True,
            "runtime_fetch_performed": True,
            "sanitized_excerpt_preview": _excerpt(),
            "source_urls": ["https://example.com/"],
            "status": "completed",
            "total_excerpt_chars": len(_excerpt()),
            "transport_called": True,
            "warnings": [],
        },
        "runtime_fetch_performed": True,
        "source_url": "https://example.com/",
        "status": "success",
        "success": True,
        "transport_called": True,
        "uploads_content": False,
        "writes_files": False,
    }


def _excerpt() -> str:
    return "Example Domain sanitized excerpt prepared only."


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
