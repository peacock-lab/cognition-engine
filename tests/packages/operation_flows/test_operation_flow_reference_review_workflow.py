from __future__ import annotations

import hashlib
import json
from pathlib import Path

from contract_core.llm_invocation import (
    GovernedLlmInvocationService,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from cognition_operation_flows._workflows.reference_review import (
    OPERATION_FLOW_REFERENCE_REVIEW_TEMPLATE_VERSION,
    OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
    OperationFlowReferenceReviewWorkflowRequestCandidate,
    detect_operation_flow_reference_review_request,
    run_operation_flow_reference_review_workflow,
)
from cognition_operation_flows._core.control import OPERATION_FLOW_CONTROL_STAGES


class FakeReferenceReviewLlmService(GovernedLlmInvocationService):
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
                "source": "test_operation_flow_reference_review_workflow",
            },
        )


class FailingReferenceReviewLlmService(GovernedLlmInvocationService):
    def __init__(self) -> None:
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
            success=False,
            response_non_empty=False,
            failure_type="live_call_failure",
            error_message_sanitized="provider returned a controlled test failure",
            sanitized_response_length=0,
            sanitized_response_preview=None,
            metadata={"source": "test_operation_flow_reference_review_workflow"},
        )


def test_reference_review_detector_requires_reference_and_review_intent() -> None:
    assert detect_operation_flow_reference_review_request(
        "请审查这些资料，指出问题和建议",
        reference_paths=("docs/strategy/README.md",),
    )
    assert (
        detect_operation_flow_reference_review_request(
            "请审查这些资料，指出问题和建议",
            reference_paths=(),
        )
        is False
    )
    assert (
        detect_operation_flow_reference_review_request(
            "我要建一个鱼塘，帮我设计建设方案",
            reference_paths=("docs/fishpond.md",),
        )
        is False
    )


def test_no_live_reference_review_reads_reference_and_outputs_evidence(
    tmp_path: Path,
) -> None:
    reference = tmp_path / "review.md"
    reference.write_text(
        "通用 operation flow 阶段收口。\n"
        "Agent runtime 继续关闭。\n"
        "下一步建议进入真实验收。\n",
        encoding="utf-8",
    )

    result = run_operation_flow_reference_review_workflow(
        OperationFlowReferenceReviewWorkflowRequestCandidate(
            user_text="请审查这些资料，指出是否符合当前主线，并给出问题和建议",
            chat_session_id="cli-reference-review-test",
            turn_index=1,
            reference_paths=("review.md",),
            reference_repo_root=str(tmp_path),
        )
    )

    assert result.fail_safe is False
    assert result.no_live is True
    assert result.model_call_count == 0
    assert result.reference_context.status == "succeeded"
    assert result.reference_context.consumed_reference_count == 1
    assert result.reference_context.evidence_refs
    assert result.task_run_context is not None
    assert result.task_run_context.status == "succeeded"
    assert result.task_run_context.workflow_name == OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME
    assert result.task_run_context.stages == OPERATION_FLOW_CONTROL_STAGES
    assert "资料审查结果" in result.terminal_display_text
    assert "Agent runtime" in result.terminal_display_text
    assert "主要结论" in result.terminal_display_text
    assert "判断依据" in result.terminal_display_text
    assert "发现的问题" in result.terminal_display_text
    assert "风险边界" in result.terminal_display_text
    assert "建议动作" in result.terminal_display_text
    assert "evidence://reference-reader/" in result.terminal_display_text
    assert "no-live 路径" in result.terminal_display_text


def test_controlled_live_reference_review_uses_one_model_call(
    tmp_path: Path,
) -> None:
    reference = tmp_path / "review.md"
    reference.write_text("当前主线是第二类真实 operation flow。\n", encoding="utf-8")
    service = FakeReferenceReviewLlmService(
        json.dumps(
            {
                "conclusion": "资料符合当前主线。",
                "evidence_basis": ["资料声明当前主线是第二类真实 operation flow。"],
                "issues": [],
                "risk_boundaries": ["Agent runtime 与 Skills runtime 未在本轮打开。"],
                "suggestions": ["进入最小实施。"],
            },
            ensure_ascii=False,
        )
    )

    result = run_operation_flow_reference_review_workflow(
        OperationFlowReferenceReviewWorkflowRequestCandidate(
            user_text="请审查这些资料，指出是否符合当前主线",
            chat_session_id="cli-reference-review-live-test",
            turn_index=1,
            live_model_allowed=True,
            llm_invocation_service=service,
            approval_ref="approval://reference-review-test",
            audit_ref="audit://reference-review-test",
            sanitized_evidence_ref="evidence://reference-review-test",
            reference_paths=("review.md",),
            reference_repo_root=str(tmp_path),
        )
    )

    assert result.fail_safe is False
    assert result.no_live is False
    assert result.model_call_count == 1
    assert len(service.requests) == 1
    assert service.requests[0].metadata["interaction_mode"] == (
        OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME
    )
    assert len(service.requests[0].prompt_preview_sanitized or "") <= 80
    assert service.requests[0].metadata["reference_context_status"] == "succeeded"
    assert service.requests[0].metadata["reference_review_context"][
        "reference_excerpts"
    ]
    assert service.requests[0].metadata["review_template_version"] == (
        OPERATION_FLOW_REFERENCE_REVIEW_TEMPLATE_VERSION
    )
    assert "资料符合当前主线" in result.terminal_display_text
    assert "判断依据" in result.terminal_display_text
    assert "风险边界" in result.terminal_display_text
    assert "进入最小实施" in result.terminal_display_text
    assert "review.md" in result.terminal_display_text
    assert '{"conclusion"' not in result.terminal_display_text


def test_controlled_live_reference_review_falls_back_to_local_summary_on_failure(
    tmp_path: Path,
) -> None:
    reference = tmp_path / "review.md"
    reference.write_text(
        "当前主线符合公共契约层抽取。\n"
        "下一步建议保留产品入口收口边界。\n",
        encoding="utf-8",
    )
    service = FailingReferenceReviewLlmService()

    result = run_operation_flow_reference_review_workflow(
        OperationFlowReferenceReviewWorkflowRequestCandidate(
            user_text="请总结这份资料的核心结论，并分类整理其中的英文专有名词。",
            chat_session_id="cli-reference-review-live-fallback-test",
            turn_index=1,
            live_model_allowed=True,
            llm_invocation_service=service,
            approval_ref="approval://reference-review-live-fallback-test",
            audit_ref="audit://reference-review-live-fallback-test",
            sanitized_evidence_ref="evidence://reference-review-live-fallback-test",
            reference_paths=("review.md",),
            reference_repo_root=str(tmp_path),
        )
    )

    assert result.fail_safe is False
    assert result.no_live is False
    assert result.model_call_count == 1
    assert len(service.requests) == 1
    assert result.draft is not None
    assert result.draft.source == "controlled_live_failed_local_fallback"
    assert result.task_run_context is not None
    assert result.task_run_context.status == "succeeded"
    assert "资料审查结果" in result.terminal_display_text
    assert "主要结论" in result.terminal_display_text
    assert "当前主线" in result.terminal_display_text
    assert "执行说明" in result.terminal_display_text
    assert "真实模型调用失败" in result.terminal_display_text
    assert "live_call_failure" in result.terminal_display_text
    assert "raw provider response" in result.terminal_display_text
    assert "evidence://reference-reader/" in result.terminal_display_text


def test_no_live_reference_review_outputs_terminology_annotations_when_requested(
    tmp_path: Path,
) -> None:
    reference = tmp_path / "review.md"
    reference.write_text(
        "reference path 进入 local_reference_reader。\n"
        "MemoryApprovedProjectionCandidate 仍是 candidate-only 对象。\n"
        "Skills runtime 保持关闭，SkillToolset 不运行。\n",
        encoding="utf-8",
    )

    result = run_operation_flow_reference_review_workflow(
        OperationFlowReferenceReviewWorkflowRequestCandidate(
            user_text="请总结这份资料的核心结论，并分类整理其中的英文专有名词，给出中文语义注释。",
            chat_session_id="cli-reference-review-terms-test",
            turn_index=1,
            reference_paths=("review.md",),
            reference_repo_root=str(tmp_path),
        )
    )

    assert result.fail_safe is False
    assert result.no_live is True
    assert result.facts.terminology_output_requested is True
    assert result.draft is not None
    assert result.draft.metadata["terminology_output_requested"] is True
    assert result.draft.metadata["skills_readonly_hint"]["runtime_enabled"] is False
    assert OPERATION_FLOW_REFERENCE_REVIEW_TEMPLATE_VERSION == "reference_review_template_v2"
    assert "英文专有名词与中文语义注释" in result.terminal_display_text
    assert "reference path" in result.terminal_display_text
    assert "受控资料路径" in result.terminal_display_text
    assert "Memory approved projection candidate" in result.terminal_display_text
    assert "MemoryApprovedProjectionCandidate" in result.terminal_display_text
    assert "Skills runtime" in result.terminal_display_text
    assert "SkillToolset" in result.terminal_display_text
    assert "Skills capability projection 仅作为 reference-review" in (
        result.terminal_display_text
    )


def test_controlled_live_reference_review_displays_json_terminology_items(
    tmp_path: Path,
) -> None:
    reference = tmp_path / "review.md"
    reference.write_text("workflow read context 只做只读承接。\n", encoding="utf-8")
    service = FakeReferenceReviewLlmService(
        json.dumps(
            {
                "conclusion": "资料符合当前主线。",
                "evidence_basis": ["资料提到 workflow read context。"],
                "risk_boundaries": ["Skills runtime 不打开。"],
                "suggestions": ["继续保持只读承接。"],
                "terminology_items": [
                    {
                        "term": "workflow read context",
                        "readable": "workflow read context",
                        "category": "workflow 与操作控制",
                        "note": "workflow 读取上下文。",
                    }
                ],
            },
            ensure_ascii=False,
        )
    )

    result = run_operation_flow_reference_review_workflow(
        OperationFlowReferenceReviewWorkflowRequestCandidate(
            user_text="请分类整理英文专有名词，给出中文语义注释",
            chat_session_id="cli-reference-review-live-terms-test",
            turn_index=1,
            live_model_allowed=True,
            llm_invocation_service=service,
            approval_ref="approval://reference-review-live-terms-test",
            audit_ref="audit://reference-review-live-terms-test",
            sanitized_evidence_ref="evidence://reference-review-live-terms-test",
            reference_paths=("review.md",),
            reference_repo_root=str(tmp_path),
        )
    )

    assert result.fail_safe is False
    assert result.model_call_count == 1
    assert "英文专有名词与中文语义注释" in result.terminal_display_text
    assert "workflow read context" in result.terminal_display_text
    assert "workflow 读取上下文" in result.terminal_display_text
    assert service.requests[0].metadata["terminology_output_requested"] is True
    assert service.requests[0].metadata["skills_readonly_hint"][
        "runtime_enabled"
    ] is False
    assert service.requests[0].metadata["terminology_items"]


def test_controlled_live_plain_review_is_wrapped_with_quality_template(
    tmp_path: Path,
) -> None:
    reference = tmp_path / "review.md"
    reference.write_text("当前主线继续保持 Skills runtime 关闭。\n", encoding="utf-8")
    service = FakeReferenceReviewLlmService("资料整体符合当前主线。")

    result = run_operation_flow_reference_review_workflow(
        OperationFlowReferenceReviewWorkflowRequestCandidate(
            user_text="请审查这些资料，指出问题和建议",
            chat_session_id="cli-reference-review-template-test",
            turn_index=1,
            live_model_allowed=True,
            llm_invocation_service=service,
            approval_ref="approval://reference-review-template-test",
            audit_ref="audit://reference-review-template-test",
            sanitized_evidence_ref="evidence://reference-review-template-test",
            reference_paths=("review.md",),
            reference_repo_root=str(tmp_path),
        )
    )

    assert result.fail_safe is False
    assert "主要结论" in result.terminal_display_text
    assert "资料整体符合当前主线" in result.terminal_display_text
    assert "判断依据" in result.terminal_display_text
    assert "发现的问题" in result.terminal_display_text
    assert "风险边界" in result.terminal_display_text
    assert "建议动作" in result.terminal_display_text


def test_controlled_live_boundary_unsafe_json_suggestion_is_intercepted(
    tmp_path: Path,
) -> None:
    reference = tmp_path / "review.md"
    reference.write_text(
        "Agent runtime 未打开。\nSkills runtime 继续关闭。\n",
        encoding="utf-8",
    )
    service = FakeReferenceReviewLlmService(
        json.dumps(
            {
                "conclusion": "资料符合当前主线。",
                "risk_boundaries": [
                    "Agent runtime 与 Skills runtime 未打开，继续作为关闭边界。"
                ],
                "suggestions": [
                    "下一步开始集成 Agent runtime 和 Skills runtime 的功能。"
                ],
            },
            ensure_ascii=False,
        )
    )

    result = run_operation_flow_reference_review_workflow(
        OperationFlowReferenceReviewWorkflowRequestCandidate(
            user_text="请审查这些资料，指出风险边界和建议",
            chat_session_id="cli-reference-review-boundary-json-test",
            turn_index=1,
            live_model_allowed=True,
            llm_invocation_service=service,
            approval_ref="approval://reference-review-boundary-json-test",
            audit_ref="audit://reference-review-boundary-json-test",
            sanitized_evidence_ref="evidence://reference-review-boundary-json-test",
            reference_paths=("review.md",),
            reference_repo_root=str(tmp_path),
        )
    )

    assert result.fail_safe is False
    assert "开始集成 Agent runtime 和 Skills runtime" not in (
        result.terminal_display_text
    )
    assert "保持 Agent runtime / Skills runtime 关闭" in result.terminal_display_text
    assert "另开评议任务" in result.terminal_display_text


def test_controlled_live_boundary_unsafe_plain_suggestion_is_intercepted(
    tmp_path: Path,
) -> None:
    reference = tmp_path / "review.md"
    reference.write_text("Agent runtime 未打开。\n", encoding="utf-8")
    service = FakeReferenceReviewLlmService(
        "\n".join(
            (
                "主要结论",
                "- 符合",
                "风险边界",
                "1. Agent runtime 未打开。",
                "建议动作",
                "1. 下一步开始集成 Agent runtime。",
            )
        )
    )

    result = run_operation_flow_reference_review_workflow(
        OperationFlowReferenceReviewWorkflowRequestCandidate(
            user_text="请审查这些资料，指出风险边界和建议",
            chat_session_id="cli-reference-review-boundary-plain-test",
            turn_index=1,
            live_model_allowed=True,
            llm_invocation_service=service,
            approval_ref="approval://reference-review-boundary-plain-test",
            audit_ref="audit://reference-review-boundary-plain-test",
            sanitized_evidence_ref="evidence://reference-review-boundary-plain-test",
            reference_paths=("review.md",),
            reference_repo_root=str(tmp_path),
        )
    )

    assert result.fail_safe is False
    assert "下一步开始集成 Agent runtime" not in result.terminal_display_text
    assert "1. 保持 Agent runtime 关闭" in result.terminal_display_text
    assert "另开评议任务" in result.terminal_display_text


def test_reference_review_displays_external_readonly_evidence_without_prompt_injection(
    tmp_path: Path,
) -> None:
    reference = tmp_path / "review.md"
    reference.write_text("当前主线继续保持 reference-review 只读承接。\n", encoding="utf-8")
    evidence_path = "outputs/external-readonly/cli-fetch/reference-review-example.json"
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    service = FakeReferenceReviewLlmService(
        json.dumps(
            {
                "conclusion": "资料符合当前主线。",
                "evidence_basis": ["本轮模型输入仍只包含本地 reference excerpt。"],
                "risk_boundaries": ["external-readonly evidence 仅 prepared_only。"],
                "suggestions": ["下一步再显式接入 reference-review 正文。"],
            },
            ensure_ascii=False,
        )
    )

    result = run_operation_flow_reference_review_workflow(
        OperationFlowReferenceReviewWorkflowRequestCandidate(
            user_text="请审查这些资料，指出问题和建议",
            chat_session_id="cli-reference-review-external-evidence-test",
            turn_index=1,
            live_model_allowed=True,
            llm_invocation_service=service,
            approval_ref="approval://reference-review-external-evidence-test",
            audit_ref="audit://reference-review-external-evidence-test",
            sanitized_evidence_ref=(
                "evidence://reference-review-external-evidence-test"
            ),
            reference_paths=("review.md",),
            reference_repo_root=str(tmp_path),
            external_readonly_evidence_paths=(evidence_path,),
            external_readonly_evidence_repo_root=str(tmp_path),
        )
    )

    external_context = result.reference_context.metadata[
        "external_readonly_evidence_context"
    ]
    request_metadata = service.requests[0].metadata
    model_context = request_metadata["reference_review_context"]

    assert result.fail_safe is False
    assert result.model_call_count == 1
    assert external_context["status"] == "ready"
    assert external_context["metadata"]["integration_mode"] == "prepared_only"
    assert external_context["metadata"]["prompt_injection_enabled"] is False
    assert external_context["summaries"][0]["sanitized_excerpt_preview"] == _excerpt()
    assert request_metadata["external_readonly_evidence_prepared"] is True
    assert request_metadata["external_readonly_evidence_prompt_injection_enabled"] is False
    assert "external_readonly_evidence_context" not in model_context
    assert _excerpt() not in json.dumps(model_context, ensure_ascii=False)
    assert "外部只读证据摘要" in result.terminal_display_text
    assert "source_url: https://example.com/" in result.terminal_display_text
    assert "evidence://external-readonly/cli-fetch/reference-review-example.json" in (
        result.terminal_display_text
    )
    assert _hash(_excerpt()) in result.terminal_display_text
    assert _excerpt() in result.terminal_display_text
    assert "reference-review 本轮未联网" in result.terminal_display_text
    assert "未上传" in result.terminal_display_text


def test_no_live_reference_review_displays_external_readonly_evidence_summary(
    tmp_path: Path,
) -> None:
    reference = tmp_path / "review.md"
    reference.write_text("当前主线继续保持 reference-review 只读承接。\n", encoding="utf-8")
    evidence_path = "outputs/external-readonly/cli-fetch/no-live-example.json"
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )

    result = run_operation_flow_reference_review_workflow(
        OperationFlowReferenceReviewWorkflowRequestCandidate(
            user_text="请审查这些资料，指出问题和建议",
            chat_session_id="cli-reference-review-no-live-external-evidence-test",
            turn_index=1,
            reference_paths=("review.md",),
            reference_repo_root=str(tmp_path),
            external_readonly_evidence_paths=(evidence_path,),
            external_readonly_evidence_repo_root=str(tmp_path),
        )
    )

    assert result.fail_safe is False
    assert result.no_live is True
    assert result.model_call_count == 0
    assert "外部只读证据摘要" in result.terminal_display_text
    assert "source_url: https://example.com/" in result.terminal_display_text
    assert "evidence://external-readonly/cli-fetch/no-live-example.json" in (
        result.terminal_display_text
    )
    assert _excerpt() in result.terminal_display_text
    assert "raw response / raw HTML / response headers" in (
        result.terminal_display_text
    )
    assert "no-live 路径" in result.terminal_display_text


def test_no_live_reference_review_can_use_external_readonly_evidence_without_local_reference(
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/external-only.json"
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )

    result = run_operation_flow_reference_review_workflow(
        OperationFlowReferenceReviewWorkflowRequestCandidate(
            user_text="请审查这份外部只读证据摘要，指出问题和建议",
            chat_session_id="cli-reference-review-external-only-test",
            turn_index=1,
            external_readonly_evidence_paths=(evidence_path,),
            external_readonly_evidence_repo_root=str(tmp_path),
        )
    )

    assert result.fail_safe is False
    assert result.no_live is True
    assert result.reference_context.status == "succeeded"
    assert result.reference_context.metadata["reference_reader_requested"] is False
    assert result.reference_context.consumed_reference_count == 0
    assert "外部只读证据摘要" in result.terminal_display_text
    assert "source_url: https://example.com/" in result.terminal_display_text
    assert "未生成本地资料证据引用" in result.terminal_display_text


def test_reference_review_blocks_invalid_external_readonly_evidence_path(
    tmp_path: Path,
) -> None:
    reference = tmp_path / "review.md"
    reference.write_text("当前主线继续保持只读审查。\n", encoding="utf-8")
    service = FakeReferenceReviewLlmService("不应被调用")

    result = run_operation_flow_reference_review_workflow(
        OperationFlowReferenceReviewWorkflowRequestCandidate(
            user_text="请审查这些资料，指出问题和建议",
            live_model_allowed=True,
            llm_invocation_service=service,
            approval_ref="approval://reference-review-bad-external-evidence",
            audit_ref="audit://reference-review-bad-external-evidence",
            sanitized_evidence_ref="evidence://reference-review-bad-external-evidence",
            reference_paths=("review.md",),
            reference_repo_root=str(tmp_path),
            external_readonly_evidence_paths=(
                "outputs/external-readonly/../leak.json",
            ),
            external_readonly_evidence_repo_root=str(tmp_path),
        )
    )

    assert result.fail_safe is True
    assert result.model_call_count == 0
    assert service.requests == []
    assert result.reference_context.status == "blocked"
    assert any(
        reason.startswith("external_readonly_evidence_blocked:")
        for reason in result.reference_context.blocking_reasons
    )


def test_reference_review_persists_run_workspace_layers(tmp_path: Path) -> None:
    reference = tmp_path / "review.md"
    reference.write_text("Skills runtime 继续关闭。\n下一步进入真实 workflow。\n", encoding="utf-8")
    workspace_root = tmp_path / "cli-runs"

    result = run_operation_flow_reference_review_workflow(
        OperationFlowReferenceReviewWorkflowRequestCandidate(
            user_text="请审查这些资料，指出问题和建议",
            chat_session_id="cli-reference-review-workspace-test",
            turn_index=2,
            reference_paths=("review.md",),
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
    result_payload = json.loads(
        (workspace_path / "results" / "workflow_result.json").read_text(
            encoding="utf-8"
        )
    )
    manifest = json.loads(
        Path(result.run_workspace.manifest_path).read_text(encoding="utf-8")
    )
    assert reference_context["tool_loading_gate"]["status"] == "passed"
    assert result_payload["workflow"] == OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME
    assert result_payload["reference_context_status"] == "succeeded"
    assert result_payload["review_template_version"] == (
        OPERATION_FLOW_REFERENCE_REVIEW_TEMPLATE_VERSION
    )
    assert manifest["status"] == "succeeded"
    assert manifest["metadata"]["review_template_version"] == (
        OPERATION_FLOW_REFERENCE_REVIEW_TEMPLATE_VERSION
    )
    assert result.run_workspace.artifact_refs
    assert result.run_workspace.evidence_refs
    assert result.run_workspace.result_refs


def test_reference_review_blocks_bad_reference_before_model_call(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / "outside-reference-review.md"
    outside.write_text("outside", encoding="utf-8")
    service = FakeReferenceReviewLlmService("不应被调用")

    result = run_operation_flow_reference_review_workflow(
        OperationFlowReferenceReviewWorkflowRequestCandidate(
            user_text="请审查这些资料，指出问题",
            live_model_allowed=True,
            llm_invocation_service=service,
            reference_paths=(str(outside),),
            reference_repo_root=str(tmp_path),
        )
    )

    assert result.fail_safe is True
    assert result.model_call_count == 0
    assert service.requests == []
    assert result.reference_context.status == "blocked"
    assert "reference_read_blocked:reference_outside_allowed_roots" in (
        result.reference_context.blocking_reasons
    )
    assert result.task_run_context is not None
    assert result.task_run_context.status == "blocked"
    assert "reference reader 已阻止" in result.terminal_display_text


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
