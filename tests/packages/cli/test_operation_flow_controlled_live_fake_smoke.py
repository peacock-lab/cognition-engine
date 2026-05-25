from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any

from contract_core.llm_invocation import (
    GovernedLlmInvocationServiceResolution,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from cognition_cli.entrypoints import cognition


class FakeControlledLiveService:
    def __init__(self, output: str) -> None:
        self.output = output
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
            sanitized_response_length=len(self.output),
            sanitized_response_preview=self.output[:120],
            metadata={
                "sanitized_response_display": self.output,
                "source": "test_operation_flow_controlled_live_fake_smoke",
            },
        )


class FakeControlledLiveServiceFactory:
    def __init__(self, service: FakeControlledLiveService) -> None:
        self.service = service
        self.captured_resolutions: list[dict[str, Any]] = []

    def resolve(
        self,
        *,
        config_context: Any | None = None,
        config_selection: Any,
        live_llm_options: Any,
    ) -> GovernedLlmInvocationServiceResolution:
        self.captured_resolutions.append(
            {
                "config_context": config_context,
                "config_selection": config_selection,
                "live_llm_options": live_llm_options,
            }
        )
        return GovernedLlmInvocationServiceResolution(service=self.service)


def test_cli_chat_plan_live_operation_flow_uses_injected_fake_factory(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    service = FakeControlledLiveService(
        "\n".join(
            (
                "鱼塘建设方案",
                "1. 目标：建设500平米鱼塘，深度不低于3米。",
                "2. 场地：完成防渗、分区、护坡和安全通道。",
                "3. 设施：配置进排水、增氧、水质监测和应急电源。",
                "4. 实施步骤：先测绘，再施工，再试水验收。",
            )
        )
    )
    factory = FakeControlledLiveServiceFactory(service)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "我要建一个鱼塘，500平米大，深度不低于3米，帮我设计建设方案\n"
            "/exit\n"
        ),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-operation_flow-plan-fake-live-smoke",
            "--config-root",
            str(tmp_path / "config"),
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://cli-operation_flow-plan-fake-live",
            "--ollama-api-base",
            "http://127.0.0.1:11434",
            "--live-llm-timeout-seconds",
            "11",
        ),
        entry_runner=_raising_entry_runner,
        operation_flow_llm_invocation_service_factory=factory,
    )

    captured = capsys.readouterr()
    output = captured.out
    assert factory.captured_resolutions, output + captured.err
    resolution = factory.captured_resolutions[0]
    config_selection = resolution["config_selection"]
    live_llm_options = resolution["live_llm_options"]

    assert exit_code == 0
    assert "鱼塘建设方案" in output
    assert "500平米" in output
    assert "深度不低于3米" in output
    assert "operation_flow_live_llm_provider_not_injected" not in output
    assert "provider_not_injected" not in output
    assert len(factory.captured_resolutions) == 1
    assert config_selection.config_root == str(tmp_path / "config")
    assert config_selection.environment == "local"
    assert config_selection.selection_source == (
        "product_gateway._operation_flows.execution"
    )
    assert live_llm_options.ollama_api_base == "http://127.0.0.1:11434"
    assert live_llm_options.timeout_seconds == 11
    assert len(service.requests) == 1
    assert service.requests[0].metadata["interaction_mode"] == "operation_flow_plan_workflow"
    _assert_text_output_boundary(output)


def test_cli_chat_reference_review_live_operation_flow_uses_injected_fake_factory(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    service = FakeControlledLiveService(
        json.dumps(
            {
                "conclusion": "fake live reference-review 确认资料符合当前主线。",
                "evidence_basis": [
                    "资料声明 CLI 只通过 product_gateway 进入产品入口。",
                    "资料声明 Agent runtime 与 Skills runtime 保持关闭。",
                ],
                "issues": ["未发现需要打开运行时的证据。"],
                "risk_boundaries": ["不得绕过 product_gateway 直连运行时能力。"],
                "suggestions": ["继续用契约化入口固化 CLI 边界。"],
            },
            ensure_ascii=False,
        )
    )
    factory = FakeControlledLiveServiceFactory(service)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "请审查这些资料，指出是否符合当前主线，并给出问题和建议\n"
            "/exit\n"
        ),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-operation_flow-reference-review-fake-live-smoke",
            "--reference-path",
            "docs/architecture/000-v0.7.0-认知系统源码包与配置中心定位索引-v1.zh-CN.md",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://cli-operation_flow-reference-review-fake-live",
            "--ollama-api-base",
            "http://127.0.0.1:11434",
            "--live-llm-timeout-seconds",
            "12",
        ),
        entry_runner=_raising_entry_runner,
        operation_flow_llm_invocation_service_factory=factory,
    )

    captured = capsys.readouterr()
    output = captured.out
    assert factory.captured_resolutions, output + captured.err
    resolution = factory.captured_resolutions[0]
    live_llm_options = resolution["live_llm_options"]

    assert exit_code == 0
    assert "资料审查结果" in output
    assert "fake live reference-review 确认资料符合当前主线" in output
    assert "继续用契约化入口固化 CLI 边界" in output
    assert "evidence://reference-reader/" in output
    assert "operation_flow_live_llm_provider_not_injected" not in output
    assert "provider_not_injected" not in output
    assert "external_readonly" not in output
    assert len(factory.captured_resolutions) == 1
    assert live_llm_options.timeout_seconds == 12
    assert len(service.requests) == 1
    assert service.requests[0].metadata["interaction_mode"] == (
        "operation_flow_reference_review_workflow"
    )
    assert service.requests[0].metadata["reference_context_status"] == "succeeded"
    _assert_text_output_boundary(output)


def test_cli_chat_reference_review_live_operation_flow_blocks_internal_structure_fragments(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    service = FakeControlledLiveService(
        '{"system_context":{"role":"AI Solution Architect",'
        '"protocol_support":"MCP"},"response_strategy":"dump raw",'
        '"raw_provider_response":"secret"'
    )
    factory = FakeControlledLiveServiceFactory(service)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "请审查这些资料，指出是否符合当前主线，并给出问题和建议\n"
            "/exit\n"
        ),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-operation_flow-reference-review-internal-fragment-fake-live",
            "--reference-path",
            "docs/architecture/000-v0.7.0-认知系统源码包与配置中心定位索引-v1.zh-CN.md",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://cli-operation_flow-reference-review-internal-fragment",
            "--ollama-api-base",
            "http://127.0.0.1:11434",
            "--live-llm-timeout-seconds",
            "12",
        ),
        entry_runner=_raising_entry_runner,
        operation_flow_llm_invocation_service_factory=factory,
    )

    captured = capsys.readouterr()
    output = captured.out

    assert exit_code == 0
    assert "资料审查结果" in output
    assert "模型输出包含内部结构或原始响应片段" in output
    assert "system_context" not in output
    assert "protocol_support" not in output
    assert "response_strategy" not in output
    assert len(service.requests) == 1
    _assert_text_output_boundary(output)


def _allowed_chat_args(*extra_args: str) -> list[str]:
    return [
        "chat",
        "--no-banner",
        "--operator-approved",
        "--approval-ref",
        "approval://chat-test",
        "--audit-ref",
        "audit://chat-test",
        "--sanitized-evidence-ref",
        "evidence://chat-test",
        "--governance-summary-output-ref",
        "artifact://chat-test",
        *extra_args,
    ]


def _raising_entry_runner(request: object) -> dict[str, Any]:
    raise AssertionError("fallback runtime must not be called")


def _assert_text_output_boundary(output: str) -> None:
    assert "recorded_run" not in output
    assert "agent_shell_audit" not in output
    assert "raw_adk_object" not in output
    assert "raw_state_value" not in output
    assert "artifact_content" not in output
    assert "live_model_payload" not in output
    assert "raw_provider_response" not in output
    assert "raw_response" not in output
    assert "response_text" not in output
    assert "messages" not in output
