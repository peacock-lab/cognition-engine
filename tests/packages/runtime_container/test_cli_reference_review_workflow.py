from __future__ import annotations

import json
from pathlib import Path

from contract_core.llm_invocation import (
    GovernedLlmInvocationService,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from runtime_container.cli_reference_review_workflow import (
    CLI_REFERENCE_REVIEW_TEMPLATE_VERSION,
    CLI_REFERENCE_REVIEW_WORKFLOW_NAME,
    CliReferenceReviewWorkflowRequestCandidate,
    detect_cli_reference_review_request,
    run_cli_reference_review_workflow,
)
from runtime_container.cli_task_control import CLI_TASK_CONTROL_STAGES


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
                "source": "test_cli_reference_review_workflow",
            },
        )


def test_reference_review_detector_requires_reference_and_review_intent() -> None:
    assert detect_cli_reference_review_request(
        "请审查这些资料，指出问题和建议",
        reference_paths=("docs/strategy/README.md",),
    )
    assert (
        detect_cli_reference_review_request(
            "请审查这些资料，指出问题和建议",
            reference_paths=(),
        )
        is False
    )
    assert (
        detect_cli_reference_review_request(
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
        "CLI task workflow 阶段收口。\n"
        "Agent runtime 继续关闭。\n"
        "下一步建议进入真实验收。\n",
        encoding="utf-8",
    )

    result = run_cli_reference_review_workflow(
        CliReferenceReviewWorkflowRequestCandidate(
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
    assert result.task_run_context.workflow_name == CLI_REFERENCE_REVIEW_WORKFLOW_NAME
    assert result.task_run_context.stages == CLI_TASK_CONTROL_STAGES
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
    reference.write_text("当前主线是第二类真实 CLI task workflow。\n", encoding="utf-8")
    service = FakeReferenceReviewLlmService(
        json.dumps(
            {
                "conclusion": "资料符合当前主线。",
                "evidence_basis": ["资料声明当前主线是第二类真实 CLI task workflow。"],
                "issues": [],
                "risk_boundaries": ["Agent runtime 与 Skills runtime 未在本轮打开。"],
                "suggestions": ["进入最小实施。"],
            },
            ensure_ascii=False,
        )
    )

    result = run_cli_reference_review_workflow(
        CliReferenceReviewWorkflowRequestCandidate(
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
        CLI_REFERENCE_REVIEW_WORKFLOW_NAME
    )
    assert len(service.requests[0].prompt_preview_sanitized or "") <= 80
    assert service.requests[0].metadata["reference_context_status"] == "succeeded"
    assert service.requests[0].metadata["reference_review_context"][
        "reference_excerpts"
    ]
    assert service.requests[0].metadata["review_template_version"] == (
        CLI_REFERENCE_REVIEW_TEMPLATE_VERSION
    )
    assert "资料符合当前主线" in result.terminal_display_text
    assert "判断依据" in result.terminal_display_text
    assert "风险边界" in result.terminal_display_text
    assert "进入最小实施" in result.terminal_display_text
    assert "review.md" in result.terminal_display_text
    assert '{"conclusion"' not in result.terminal_display_text


def test_controlled_live_plain_review_is_wrapped_with_quality_template(
    tmp_path: Path,
) -> None:
    reference = tmp_path / "review.md"
    reference.write_text("当前主线继续保持 Skills runtime 关闭。\n", encoding="utf-8")
    service = FakeReferenceReviewLlmService("资料整体符合当前主线。")

    result = run_cli_reference_review_workflow(
        CliReferenceReviewWorkflowRequestCandidate(
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

    result = run_cli_reference_review_workflow(
        CliReferenceReviewWorkflowRequestCandidate(
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

    result = run_cli_reference_review_workflow(
        CliReferenceReviewWorkflowRequestCandidate(
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


def test_reference_review_persists_run_workspace_layers(tmp_path: Path) -> None:
    reference = tmp_path / "review.md"
    reference.write_text("Skills runtime 继续关闭。\n下一步进入真实 workflow。\n", encoding="utf-8")
    workspace_root = tmp_path / "cli-runs"

    result = run_cli_reference_review_workflow(
        CliReferenceReviewWorkflowRequestCandidate(
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
    assert result_payload["workflow"] == CLI_REFERENCE_REVIEW_WORKFLOW_NAME
    assert result_payload["reference_context_status"] == "succeeded"
    assert result_payload["review_template_version"] == (
        CLI_REFERENCE_REVIEW_TEMPLATE_VERSION
    )
    assert manifest["status"] == "succeeded"
    assert manifest["metadata"]["review_template_version"] == (
        CLI_REFERENCE_REVIEW_TEMPLATE_VERSION
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

    result = run_cli_reference_review_workflow(
        CliReferenceReviewWorkflowRequestCandidate(
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
