from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contract_core.llm_invocation import (
    GovernedLlmInvocationService,
    LlmInvocationFailureType,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from cognition_operation_flows._core.control import TWF_CONTROL_STAGES
from cognition_operation_flows._workflows.plan import (
    TwfPlanDraftCandidate,
    TwfTerminalFormattedPlanCandidate,
    TwfPlanWorkflowRequestCandidate,
    detect_twf_plan_request,
    extract_twf_plan_requirements,
    format_twf_plan_for_terminal,
    review_twf_plan_quality,
    run_twf_plan_workflow,
)


class FakePlanLlmService(GovernedLlmInvocationService):
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
                "source": "test_twf_plan_workflow",
            },
        )


class FailingPlanLlmService(GovernedLlmInvocationService):
    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=request.route_facts,
            governance_precondition=request.governance_precondition,
            call_attempted=True,
            call_allowed=True,
            runtime_call_performed=True,
            success=False,
            response_non_empty=False,
            failure_type=LlmInvocationFailureType.LIVE_CALL_FAILURE,
            error_message_sanitized="provider failed",
            metadata={"source": "test_twf_plan_workflow"},
        )


def test_plan_input_triggers_workflow() -> None:
    assert detect_twf_plan_request(
        "我想建一个鱼塘，500平米大，深度不低于3米，帮我设计个建设方案"
    )


def test_casual_chat_does_not_trigger_workflow() -> None:
    assert detect_twf_plan_request("你好，今天心情有点闷") is False


def test_format_followup_triggers_when_previous_plan_exists() -> None:
    assert detect_twf_plan_request(
        "换行注意一下",
        previous_plan_text="鱼塘建设方案\n1. 场地规划",
    )


def test_continuation_followup_triggers_when_previous_plan_exists() -> None:
    assert detect_twf_plan_request(
        "所有的",
        previous_plan_text="养鸡场建设方案\n1. 场地规划",
    )
    assert detect_twf_plan_request(
        "能详细展开吗",
        previous_plan_text="鱼塘建设方案\n1. 场地规划",
    )
    assert detect_twf_plan_request(
        "发给我吧",
        previous_plan_text="鱼塘建设方案\n1. 场地规划",
    )


def test_requirement_extraction_preserves_fishpond_entities_and_constraints() -> None:
    facts = extract_twf_plan_requirements(
        TwfPlanWorkflowRequestCandidate(
            user_text="我想建一个鱼塘，500平米大，深度不低于3米，帮我设计个建设方案"
        )
    )

    assert "鱼塘" in facts.entities
    assert "500平米" in facts.scales
    assert "3米" in facts.scales
    assert "深度不低于3米" in facts.constraints


def test_requirement_extraction_does_not_promote_system_from_drainage_section() -> None:
    facts = extract_twf_plan_requirements(
        TwfPlanWorkflowRequestCandidate(
            user_text="能详细展开吗",
            previous_plan_text="鱼塘建设方案\n1. 进排水系统\n2. 水质管理",
        )
    )

    assert "鱼塘" in facts.entities
    assert "系统" not in facts.entities


def test_requirement_extraction_preserves_chicken_farm_entity_and_scale() -> None:
    facts = extract_twf_plan_requirements(
        TwfPlanWorkflowRequestCandidate(
            user_text="我要开个养鸡场，帮我设计个方案，规模500只鸡"
        )
    )

    assert "养鸡场" in facts.entities
    assert "500只鸡" in facts.scales


def test_terminal_display_preserves_line_breaks() -> None:
    facts = extract_twf_plan_requirements(
        TwfPlanWorkflowRequestCandidate(user_text="鱼塘500平米，设计建设方案")
    )
    formatted = format_twf_plan_for_terminal(
        TwfPlanDraftCandidate(
            draft_text="1. 场地整理\n2. 防渗处理\n3. 进排水设计",
            prompt_preview_sanitized="鱼塘方案",
        ),
        facts,
    )

    assert "鱼塘建设方案\n" in formatted.formatted_text
    assert "\n1. 场地整理\n2. 防渗处理\n3. 进排水设计" in formatted.formatted_text


def test_quality_review_identifies_missing_entity_scale_json_and_deflection() -> None:
    facts = extract_twf_plan_requirements(
        TwfPlanWorkflowRequestCandidate(user_text="鱼塘500平米，设计建设方案")
    )
    formatted = TwfTerminalFormattedPlanCandidate(
        formatted_text='鱼塘建设方案\n- 对象：鱼塘\n- 规模：500平米\n{"response":"请提供更多信息"}'
    )
    review = review_twf_plan_quality(formatted, facts)

    assert review.entity_coverage_ok is True
    assert review.scale_coverage_ok is True
    assert review.no_json_leak_ok is False
    assert review.no_deflection_ok is False
    assert review.passed is False


def test_quality_review_identifies_entity_and_scale_missing() -> None:
    facts = extract_twf_plan_requirements(
        TwfPlanWorkflowRequestCandidate(user_text="鱼塘500平米，设计建设方案")
    )
    formatted = format_twf_plan_for_terminal(
        TwfPlanDraftCandidate(
            draft_text="项目建设方案\n1. 先做现场整理\n2. 再安排施工",
            prompt_preview_sanitized="项目方案",
        ),
        facts,
    )
    formatted_without_facts = type(formatted)(
        formatted_text="项目建设方案\n1. 先做现场整理\n2. 再安排施工",
        source=formatted.source,
        stage_instructions=formatted.stage_instructions,
        output_policy=formatted.output_policy,
        metadata=formatted.metadata,
    )
    review = review_twf_plan_quality(formatted_without_facts, facts)

    assert review.entity_coverage_ok is False
    assert review.scale_coverage_ok is False
    assert "entity_coverage_ok" in review.failure_reasons
    assert "scale_coverage_ok" in review.failure_reasons


def test_no_live_workflow_does_not_fabricate_plan() -> None:
    result = run_twf_plan_workflow(
        TwfPlanWorkflowRequestCandidate(
            user_text="我要开个养鸡场，帮我设计个方案，规模500只鸡",
            live_model_allowed=False,
        )
    )

    assert result.no_live is True
    assert result.draft is None
    assert result.model_call_count == 0
    assert result.task_run_context is not None
    assert result.task_run_context.status == "no_live_boundary"
    assert result.task_run_context.stages == TWF_CONTROL_STAGES
    assert "未生成方案" in result.terminal_display_text
    assert "养鸡场" in result.terminal_display_text
    assert "500只鸡" in result.terminal_display_text


def test_controlled_live_workflow_uses_one_model_call_and_preserves_facts() -> None:
    service = FakePlanLlmService(
        "1. 场地规划\n2. 建设步骤\n3. 运维安排"
    )

    result = run_twf_plan_workflow(
        TwfPlanWorkflowRequestCandidate(
            user_text="我想建一个鱼塘，500平米大，深度不低于3米，帮我设计个建设方案",
            chat_session_id="cli-plan-test",
            turn_index=1,
            live_model_allowed=True,
            llm_invocation_service=service,
            approval_ref="approval://plan-test",
            audit_ref="audit://plan-test",
            sanitized_evidence_ref="evidence://plan-test",
        )
    )

    assert result.fail_safe is False
    assert result.model_call_count == 1
    assert result.task_run_context is not None
    assert result.task_run_context.status == "succeeded"
    assert result.task_run_context.preflight.allowed is True
    assert result.task_run_context.workspace.workspace_created is False
    assert result.task_run_context.stages == TWF_CONTROL_STAGES
    assert result.metadata["task_control"]["status"] == "succeeded"
    assert result.metadata["task_control"]["config_precedence"][0] == (
        "entrypoint_explicit_args"
    )
    assert len(service.requests) == 1
    assert service.requests[0].metadata["interaction_mode"] == "twf_plan_workflow"
    assert "防渗处理" in (service.requests[0].prompt_preview_sanitized or "")
    assert "进排水系统" in (service.requests[0].prompt_preview_sanitized or "")
    assert "鱼塘" in result.terminal_display_text
    assert "500平米" in result.terminal_display_text
    assert "深度不低于3米" in result.terminal_display_text
    assert "实施展开" in result.terminal_display_text
    assert "防渗处理" in result.terminal_display_text
    assert "进排水系统" in result.terminal_display_text
    assert "{" not in result.terminal_display_text


def test_plan_workflow_consumes_reference_reader_context(tmp_path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    reference = docs_dir / "fishpond.md"
    reference.write_text(
        "鱼塘参考资料\n防渗膜接缝需要单独验收。\n",
        encoding="utf-8",
    )
    service = FakePlanLlmService("1. 场地规划\n2. 防渗处理\n3. 运维安排")

    result = run_twf_plan_workflow(
        TwfPlanWorkflowRequestCandidate(
            user_text="鱼塘500平米，设计建设方案",
            chat_session_id="cli-plan-reference-test",
            turn_index=1,
            live_model_allowed=True,
            llm_invocation_service=service,
            reference_paths=("docs/fishpond.md",),
            reference_repo_root=str(tmp_path),
        )
    )

    assert result.fail_safe is False
    assert result.reference_context is not None
    assert result.reference_context.status == "succeeded"
    assert result.reference_context.consumed_reference_count == 1
    assert result.reference_context.metadata["tool_loading_gate"]["status"] == (
        "passed"
    )
    assert result.reference_context.metadata["tool_loading_gate"][
        "allowed_tool_names"
    ] == ["local_reference_reader"]
    assert "fishpond.md" in result.reference_context.reference_excerpts[0]
    assert "防渗膜接缝" in result.reference_context.reference_excerpts[0]
    assert result.reference_context.evidence_refs
    assert result.task_run_context is not None
    assert result.reference_context.evidence_refs[0] in (
        result.task_run_context.workspace.evidence_refs
    )
    assert "参考资料" in result.terminal_display_text
    assert "fishpond.md" in result.terminal_display_text
    assert service.requests[0].metadata["reference_context_status"] == "succeeded"
    assert service.requests[0].metadata["reference_context_evidence_ref_count"] == 1


def test_plan_workflow_persists_run_workspace_layers(tmp_path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    reference = docs_dir / "fishpond.md"
    reference.write_text("鱼塘资料\n防渗处理要复核。\n", encoding="utf-8")
    workspace_root = tmp_path / "run-workspaces"
    service = FakePlanLlmService("1. 场地规划\n2. 防渗处理\n3. 运维安排")

    result = run_twf_plan_workflow(
        TwfPlanWorkflowRequestCandidate(
            user_text="鱼塘500平米，设计建设方案",
            chat_session_id="cli-plan-workspace-test",
            turn_index=2,
            live_model_allowed=True,
            llm_invocation_service=service,
            reference_paths=("docs/fishpond.md",),
            reference_repo_root=str(tmp_path),
            run_workspace_root=str(workspace_root),
            run_workspace_enabled=True,
        )
    )

    assert result.fail_safe is False
    assert result.run_workspace is not None
    assert result.run_workspace.workspace_created is True
    assert result.task_run_context is not None
    assert result.task_run_context.workspace.workspace_created is True
    assert result.task_run_context.workspace.workspace_ref == (
        result.run_workspace.workspace_ref
    )
    workspace_path = Path(result.run_workspace.workspace_path)
    assert (workspace_path / "references" / "reference-001.txt").is_file()
    assert (workspace_path / "evidence" / "reference_context.json").is_file()
    assert (workspace_path / "artifacts" / "terminal_display.txt").is_file()
    assert (workspace_path / "results" / "workflow_result.json").is_file()
    reference_context = json.loads(
        (workspace_path / "evidence" / "reference_context.json").read_text(
            encoding="utf-8"
        )
    )
    assert reference_context["tool_loading_gate"]["status"] == "passed"
    assert reference_context["tool_loading_gate"]["allowed_tool_names"] == [
        "local_reference_reader"
    ]
    manifest = json.loads(
        Path(result.run_workspace.manifest_path).read_text(encoding="utf-8")
    )
    assert manifest["status"] == "succeeded"
    assert result.run_workspace.artifact_refs
    assert result.run_workspace.evidence_refs
    assert result.run_workspace.result_refs
    assert result.run_workspace.result_refs[0] in (
        result.task_run_context.workspace.artifact_refs
    )


def test_plan_workflow_blocks_reference_reader_before_model_call(tmp_path) -> None:
    outside = tmp_path.parent / "outside-plan-reference.md"
    outside.write_text("outside", encoding="utf-8")
    service = FakePlanLlmService("不应被调用")

    result = run_twf_plan_workflow(
        TwfPlanWorkflowRequestCandidate(
            user_text="鱼塘500平米，设计建设方案",
            live_model_allowed=True,
            llm_invocation_service=service,
            reference_paths=(str(outside),),
            reference_repo_root=str(tmp_path),
        )
    )

    assert result.fail_safe is True
    assert result.model_call_count == 0
    assert service.requests == []
    assert result.reference_context is not None
    assert result.reference_context.status == "blocked"
    assert "reference_read_blocked:reference_outside_allowed_roots" in (
        result.reference_context.blocking_reasons
    )
    assert result.task_run_context is not None
    assert result.task_run_context.status == "blocked"
    assert "reference reader 已阻止" in result.terminal_display_text


def test_plan_workflow_blocks_user_passthrough_governance_override() -> None:
    service = FakePlanLlmService("不应被调用")

    result = run_twf_plan_workflow(
        TwfPlanWorkflowRequestCandidate(
            user_text="鱼塘500平米，设计建设方案",
            live_model_allowed=True,
            llm_invocation_service=service,
            user_passthrough_parameters={
                "approval_ref": "approval://user-override",
            },
        )
    )

    assert result.fail_safe is True
    assert result.model_call_count == 0
    assert service.requests == []
    assert result.task_run_context is not None
    assert result.task_run_context.preflight.allowed is False
    assert "user_passthrough_overrides_approval_ref" in (
        result.task_run_context.preflight.blocking_reasons
    )
    assert "未调用模型" in result.terminal_display_text


def test_format_existing_plan_reuses_previous_plan_without_model_call() -> None:
    service = FakePlanLlmService("不应被调用")
    previous_plan = (
        "鱼塘建设方案\n\n"
        "需求事实\n"
        "- 对象：鱼塘\n"
        "- 规模：500平米、3米\n"
        "- 约束：深度不低于3米\n\n"
        "1. 场地规划\n2. 防渗处理"
    )

    result = run_twf_plan_workflow(
        TwfPlanWorkflowRequestCandidate(
            user_text="换行注意一下",
            previous_plan_text=previous_plan,
            live_model_allowed=True,
            llm_invocation_service=service,
        )
    )

    assert result.model_call_count == 0
    assert service.requests == []
    assert result.terminal_display_text.count("需求事实") == 1
    assert "鱼塘" in result.terminal_display_text
    assert "500平米" in result.terminal_display_text


def test_expand_existing_plan_outputs_structured_plan_not_plain_chat() -> None:
    service = FakePlanLlmService("description")
    previous_plan = (
        "鱼塘建设方案\n\n"
        "需求事实\n"
        "- 对象：鱼塘\n"
        "- 规模：500平米、3米\n"
        "- 约束：深度不低于3米\n\n"
        "专项章节\n1. 防渗处理\n2. 进排水系统"
    )

    result = run_twf_plan_workflow(
        TwfPlanWorkflowRequestCandidate(
            user_text="能详细展开吗",
            previous_plan_text=previous_plan,
            live_model_allowed=True,
            llm_invocation_service=service,
        )
    )

    assert result.fail_safe is False
    assert result.model_call_count == 1
    assert "description" not in result.terminal_display_text
    assert "实施展开" in result.terminal_display_text
    assert "防渗处理" in result.terminal_display_text
    assert "进排水系统" in result.terminal_display_text
    assert "深度不低于3米" in result.terminal_display_text


def test_controlled_live_failure_fails_safe_without_raw_response() -> None:
    result = run_twf_plan_workflow(
        TwfPlanWorkflowRequestCandidate(
            user_text="鱼塘500平米，设计建设方案",
            live_model_allowed=True,
            llm_invocation_service=FailingPlanLlmService(),
        )
    )

    assert result.fail_safe is True
    assert "受控失败边界" in result.terminal_display_text
    assert "raw provider response" in result.terminal_display_text
    assert "鱼塘" in result.terminal_display_text
    assert "专项章节" in result.terminal_display_text
    assert "provider failed" not in result.terminal_display_text
