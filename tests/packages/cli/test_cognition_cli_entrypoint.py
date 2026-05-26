from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

from google.adk.models.lite_llm import LiteLLMClient

from adk_adapter import (
    AdkGovernedLlmInvocationService,
    AdkRunConfigOptions,
    AdkRunnerServiceBundleOptions,
)
from composition.adk_workflow_runner_assembly import (
    AdkWorkflowRunnerAssemblyOptions,
    AdkWorkflowRunnerRuntimeAssembly,
    build_adk_workflow_runner_runtime,
)
from composition.runtime import RuntimeCompositionOptions
from config_assembly.runtime import assemble_runtime_config_payload
from contract_core.llm_invocation import (
    GovernedLlmInvocationServiceResolution,
    LlmInvocationFailureType,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from product_gateway.cli_surface import (
    build_cli_operation_flow_route_projection as build_cli_operation_flow_route_projection_real,
    build_cli_operation_flow_run_workspace_policy,
    create_cli_operation_flow_run_workspace,
    finalize_cli_operation_flow_run_workspace,
    write_cli_operation_flow_run_workspace_json,
    write_cli_operation_flow_run_workspace_text,
)
from product_application_assembly.evidence_summary_answer_ask_interaction import (
    EvidenceSummaryAnswerAskInteractionResult,
)
from schemas.product_gateway_response_summary import (
    validate_product_gateway_response_summary,
)
from product_runtime_assembly.cognition_run import (
    execute_cognition_run_with_default_runtime,
)
from runtime_container.controlled_adk_run_request_builder import (
    ControlledAdkRunRequestBuildInput,
    build_controlled_adk_run_request,
    build_controlled_adk_run_request_from_registry,
)
from runtime_container.controlled_adk_run_entry import (
    ControlledAdkRunRequest,
    evaluate_controlled_adk_run_final_preflight,
    evaluate_controlled_live_llm_preflight,
)
from cognition_cli.chat import channel as cognition_chat
from cognition_cli.chat import external_readonly_bridge as chat_external_readonly_bridge
from cognition_cli.chat import routing as cognition_chat_routing
from cognition_cli import application as cognition_application
from cognition_cli import constants as cognition_constants
from cognition_cli.entrypoints import cognition
from cognition_cli.run import gateway as cognition_run_gateway
from runtime_container.workflow_registry import (
    WorkflowRegistry,
    WorkflowRegistryAssemblyUnavailable,
    WorkflowRegistryBuildContext,
    WorkflowRegistryEntry,
    build_default_workflow_registry,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
ENTRYPOINT_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "entrypoints"
    / "cognition.py"
)
APPLICATION_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "application.py"
)
CHAT_CHANNEL_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "chat"
    / "channel.py"
)
CHAT_CONTROLS_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "chat"
    / "controls.py"
)
CHAT_EXTERNAL_READONLY_BRIDGE_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "chat"
    / "external_readonly_bridge.py"
)
CHAT_STATUS_PAYLOAD_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "chat"
    / "status_payload.py"
)
CHAT_STATUS_PRESENTER_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "chat"
    / "status_presenter.py"
)
CHAT_STATUS_ARTIFACTS_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "chat"
    / "status_artifacts.py"
)
CHAT_WORKFLOW_REQUESTS_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "chat"
    / "workflow_requests.py"
)
CHAT_REFERENCES_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "chat"
    / "references.py"
)
CHAT_ROUTING_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "chat"
    / "routing.py"
)
CHAT_OUTPUT_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "chat"
    / "output.py"
)
CHAT_TURNS_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "chat"
    / "turns.py"
)
CHAT_OPERATION_DISPATCH_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "chat"
    / "operation_dispatch.py"
)
CHAT_TASK_WORKFLOWS_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "chat"
    / "operation_flows.py"
)
RUN_COMMAND_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "run"
    / "command.py"
)
RUN_CONTROLS_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "run"
    / "controls.py"
)
RUN_INPUT_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "run"
    / "input.py"
)
RUN_GATEWAY_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "run"
    / "gateway.py"
)
RUN_OUTPUT_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "run"
    / "output.py"
)
RUNTIME_SERVICES_SOURCE = (
    REPO_ROOT
    / "packages"
    / "cli"
    / "src"
    / "cognition_cli"
    / "services"
    / "runtime.py"
)
RUNTIME_CONTAINER_PYPROJECT = REPO_ROOT / "packages" / "runtime_container" / "pyproject.toml"
CLI_PYPROJECT = REPO_ROOT / "packages" / "cli" / "pyproject.toml"
PRODUCT_RUNTIME_ASSEMBLY_PYPROJECT = (
    REPO_ROOT / "packages" / "product_runtime_assembly" / "pyproject.toml"
)


def test_cli_source_layout_has_no_root_channel_shims() -> None:
    cli_root = REPO_ROOT / "packages" / "cli" / "src" / "cognition_cli"
    old_root_files = [
        "chat_channel.py",
        "chat_controls.py",
        "chat_output.py",
        "chat_routing.py",
        "chat_status_artifacts.py",
        "chat_status_payload.py",
        "chat_status_presenter.py",
        "chat_operation_dispatch.py",
        "chat_operation_flows.py",
        "chat_turns.py",
        "chat_workflow_requests.py",
        "config_init.py",
        "run_command.py",
        "run_controls.py",
        "run_input.py",
        "run_output.py",
        "runtime_services.py",
    ]
    for old_file in old_root_files:
        assert not (cli_root / old_file).exists()

    expected_files = [
        "chat/channel.py",
        "chat/controls.py",
        "chat/external_readonly_bridge.py",
        "chat/output.py",
        "chat/routing.py",
        "chat/status_artifacts.py",
        "chat/status_payload.py",
        "chat/status_presenter.py",
        "chat/operation_dispatch.py",
        "chat/operation_flows.py",
        "chat/turns.py",
        "chat/workflow_requests.py",
        "config/init.py",
        "external_readonly/__init__.py",
        "external_readonly/fetch.py",
        "run/command.py",
        "run/controls.py",
        "run/gateway.py",
        "run/input.py",
        "run/output.py",
        "services/runtime.py",
    ]
    for expected_file in expected_files:
        assert (cli_root / expected_file).exists()


class NoLiveGovernedLlmInvocationService:
    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=request.route_facts,
            governance_precondition=request.governance_precondition,
            call_attempted=False,
            call_allowed=True,
            runtime_call_performed=False,
            success=False,
            response_non_empty=False,
            failure_type=LlmInvocationFailureType.LIVE_DISABLED,
            error_message_sanitized="live invocation remains disabled",
            metadata={"source": "test_cognition_cli_entrypoint"},
        )


class FakeLiveGovernedLlmInvocationService:
    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=request.route_facts,
            governance_precondition=request.governance_precondition,
            call_attempted=True,
            call_allowed=True,
            runtime_call_performed=True,
            success=True,
            response_non_empty=True,
            sanitized_response_length=len("controlled live output"),
            sanitized_response_preview="controlled live output",
            failure_type=None,
            metadata={"source": "test_cognition_cli_entrypoint_live"},
        )


class FakeExternalReadonlyAskLlmInvocationService:
    def __init__(self, answers: str | list[str]) -> None:
        self.answers = [answers] if isinstance(answers, str) else list(answers)
        self.requests: list[LlmInvocationRequest] = []

    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        answer = (
            self.answers[min(len(self.requests), len(self.answers) - 1)]
            if self.answers
            else ""
        )
        self.requests.append(request)
        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=request.route_facts,
            governance_precondition=request.governance_precondition,
            call_attempted=True,
            call_allowed=True,
            runtime_call_performed=True,
            success=True,
            response_non_empty=bool(answer),
            sanitized_response_length=len(answer),
            sanitized_response_preview=answer[:120],
            failure_type=None,
            metadata={"sanitized_response_display": answer},
        )


class FailingExternalReadonlyAskLlmInvocationService:
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
            failure_type=LlmInvocationFailureType.OUTPUT_SCHEMA_VALIDATION_FAILURE,
            error_message_sanitized="output schema validation failed",
            metadata={"source": "test_cognition_cli_entrypoint_failure"},
        )


class FakeExternalReadonlyAskLlmInvocationServiceFactory:
    def __init__(self, service: Any) -> None:
        self.service = service
        self.captured: dict[str, Any] = {}

    def resolve(self, **kwargs: Any) -> GovernedLlmInvocationServiceResolution:
        self.captured = dict(kwargs)
        return GovernedLlmInvocationServiceResolution(service=self.service)


class FakeAgentShellLiveClient(LiteLLMClient):
    async def acompletion(self, *, model: str, messages, tools, **kwargs):
        from litellm import ModelResponse

        return ModelResponse(
            model=model,
            choices=[
                {
                    "finish_reason": "stop",
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "controlled live output",
                    },
                }
            ],
        )


def test_bare_cognition_starts_default_local_live_chat_without_runtime(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("/status\n/exit\n"))

    exit_code = cognition.run_cli([], entry_runner=_raising_entry_runner)

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Cognition System / 认知系统" in captured.out
    assert "type /help, /status or /exit" in captured.out
    assert "live_llm_requested: true" in captured.out
    assert "ollama_requested: true" in captured.out
    assert "reference_path_count: 0" in captured.out
    assert "session: closed" in captured.out
    assert captured.err == ""


def test_startup_json_outputs_static_status(capsys: Any) -> None:
    exit_code = cognition.run_cli(["--json"], entry_runner=_raising_entry_runner)

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["product"] == "Cognition System / 认知系统"
    assert payload["session"] == "not-created"
    assert payload["available_commands"] == [
        "cognition",
        "cognition run",
        "cognition chat",
        "cognition external-readonly fetch",
        "cognition config init",
    ]


def test_bare_cognition_no_banner_suppresses_chat_banner(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("/exit\n"))

    exit_code = cognition.run_cli(["--no-banner"], entry_runner=_raising_entry_runner)

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == "session: closed\n"
    assert captured.err == ""


def test_run_help_does_not_call_runtime(capsys: Any) -> None:
    exit_code = cognition.run_cli(["run", "--help"], entry_runner=_raising_entry_runner)

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "--operator-approved" in captured.out
    assert "--input-text" in captured.out
    assert "--governance-summary-output-ref" in captured.out
    assert "--request-live-llm" in captured.out
    assert "--live-llm-approval-ref" in captured.out
    assert "controlled workflow" in captured.out
    assert "controlled no-live workflow" not in captured.out


def test_chat_help_does_not_call_runtime(capsys: Any) -> None:
    exit_code = cognition.run_cli(["chat", "--help"], entry_runner=_raising_entry_runner)

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "--chat-session-id" in captured.out
    assert "--max-turns" in captured.out
    assert "--history-limit" in captured.out
    assert "--request-live-llm" in captured.out
    assert "--reference-path" in captured.out
    assert "--enable-run-workspace" in captured.out
    assert "--audit-run-workspace-path" in captured.out
    assert "--audit-run-workspace-ref" in captured.out
    assert "multi-turn terminal chat" in captured.out


def test_config_init_writes_packaged_default_config(
    tmp_path: Path,
    capsys: Any,
) -> None:
    config_root = tmp_path / "config"

    exit_code = cognition.run_cli(
        ["config", "init", "--config-root", str(config_root)],
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Cognition System config initialized" in output
    assert "created: base/runtime.yaml" in output
    assert "created: templates/runtime.template.yaml" in output
    assert (config_root / "base" / "runtime.yaml").is_file()
    assert (config_root / "templates" / "runtime.template.yaml").is_file()

    payload = assemble_runtime_config_payload(config_root, environment="local")
    assert payload.payload["runtime"]["runtime_name"] == "default-runtime"


def test_config_init_json_skips_existing_files(
    tmp_path: Path,
    capsys: Any,
) -> None:
    config_root = tmp_path / "config"

    assert cognition.run_cli(
        ["config", "init", "--config-root", str(config_root)],
        entry_runner=_raising_entry_runner,
    ) == 0
    capsys.readouterr()

    exit_code = cognition.run_cli(
        ["config", "init", "--config-root", str(config_root), "--json"],
        entry_runner=_raising_entry_runner,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "cognition config init"
    assert payload["status"] == "succeeded"
    assert {item["status"] for item in payload["files"]} == {"skipped"}


def test_chat_exit_closes_without_runtime(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("/exit\n"))

    exit_code = cognition.run_cli(
        ["chat", "--no-banner"],
        entry_runner=_raising_entry_runner,
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "session: closed" in captured.out
    assert captured.err == ""


def test_chat_help_and_status_commands_do_not_call_runtime(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("/help\n/status\n/exit\n"))

    exit_code = cognition.run_cli(
        ["chat", "--no-banner", "--chat-session-id", "cli-chat-status-test"],
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "commands:" in output
    assert "/status" in output
    assert "/status --json" in output
    assert "session: cli-chat-status-test" in output
    assert "turn_count: 0" in output
    assert "history_limit: 6" in output
    assert "tool_profile: readonly_reference" in output
    assert "tool_exposure_status: resolved" in output
    assert "exposed_tools: local_reference_reader" in output
    assert "skills_status: candidate_only_frozen" in output
    assert "skills_runtime_integrated: false" in output
    assert "skill_toolset_runtime_enabled: false" in output
    assert (
        "skills_capability_projection_status: candidate_only_referenceable"
        in output
    )
    assert "skills_capability_projection_count: 4" in output
    assert "skills_workflow_slot_reference_count: 4" in output
    assert "skills_projection_runtime_enabled: false" in output
    assert "skills_projection_public_schema_enabled: false" in output
    assert "latest_plan_status: not_run" in output
    assert "status_summary_artifact_ref: none" in output


def test_chat_two_turns_reuse_controlled_run_with_distinct_refs(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    captured_args: list[dict[str, Any]] = []
    captured_payloads: list[dict[str, Any]] = []

    def request_builder(
        args: Any,
        input_payload: dict[str, Any],
    ) -> ControlledAdkRunRequest:
        captured_args.append(
            {
                "runtime_id": args.runtime_id,
                "approval_ref": args.approval_ref,
                "audit_ref": args.audit_ref,
                "sanitized_evidence_ref": args.sanitized_evidence_ref,
                "governance_summary_output_ref": (
                    args.governance_summary_output_ref
                ),
            }
        )
        captured_payloads.append(dict(input_payload))
        return _build_allowed_request(args, input_payload)

    monkeypatch.setattr(sys, "stdin", io.StringIO("第一轮\n第二轮\n/exit\n"))

    exit_code = cognition.run_cli(
        _allowed_chat_args("--chat-session-id", "cli-chat-test"),
        request_builder=request_builder,
        entry_runner=_fake_chat_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert [payload["input_summary"] for payload in captured_payloads] == [
        "第一轮",
        "第二轮",
    ]
    assert captured_payloads[0]["turn_history_summary"] == []
    assert captured_payloads[1]["turn_history_summary"] == [
        {
            "user": "第一轮",
            "assistant": cognition_constants.CHAT_NO_LIVE_ASSISTANT_MESSAGE,
        }
    ]
    assert captured_args[0]["runtime_id"] == "runtime-cli-chat-test-turn-001"
    assert captured_args[1]["runtime_id"] == "runtime-cli-chat-test-turn-002"
    assert captured_args[0]["approval_ref"] == (
        "approval://chat-test/cli-chat-test/turn-001"
    )
    assert captured_args[1]["audit_ref"] == (
        "audit://chat-test/cli-chat-test/turn-002"
    )
    assert captured_args[1]["sanitized_evidence_ref"] == (
        "evidence://chat-test/cli-chat-test/turn-002"
    )
    assert captured_args[1]["governance_summary_output_ref"] == (
        "artifact://chat-test/cli-chat-test/turn-002"
    )
    assert output.count(cognition_constants.CHAT_NO_LIVE_ASSISTANT_MESSAGE) == 2
    assert "turn: 1" in output
    assert "turn: 2" in output
    _assert_text_output_boundary(output)


def test_chat_local_reference_query_without_reference_path_does_not_call_runtime(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    reference_path = (
        REPO_ROOT
        / "tasks"
        / "b1"
        / "450-v0.7.0-公共契约层抽取前置盘点与发布基线收口判断结果包-v1.zh-CN.md"
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "帮我查下材料中是否有编号为300的任务包\n"
            f"帮我梳理 {reference_path}\n"
            "/exit\n"
        ),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args("--chat-session-id", "cli-reference-hint-test"),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert output.count("reference_path_not_configured") == 1
    assert output.count("live_llm_call_performed: false") == 2
    assert "当前版本不做目录扫描" in output
    assert "请回复“同意”继续读取并执行你的请求" in output
    assert "reference_path_confirmation_required" in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_reference_path_can_be_confirmed_and_read_in_session(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    reference_path = (
        REPO_ROOT
        / "tasks"
        / "b1"
        / "454-v0.7.0-CLI-cognition单词入口与local-live默认profile最小实施结果包-v1.zh-CN.md"
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            f"帮我整理摘要 {reference_path}\n"
            "同意\n"
            "/reference list\n"
            "/reference clear\n"
            "/reference list\n"
            "/exit\n"
        ),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args("--chat-session-id", "cli-reference-add-confirm-test"),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "reference_path_confirmation_required" in output
    assert "资料审查结果" in output
    assert "evidence://reference-reader/" in output
    assert "454-v0.7.0-CLI-cognition单词入口" in output
    assert "当前会话受控资料文件" in output
    assert "已清空当前会话的受控资料文件" in output
    assert "当前会话还没有加入受控资料文件" in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_project_metadata_file_can_be_confirmed_and_read(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    reference_path = REPO_ROOT / "pyproject.toml"
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            f"帮我读取 {reference_path}\n"
            "同意\n"
            "/exit\n"
        ),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args("--chat-session-id", "cli-reference-project-meta-test"),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "reference_path_confirmation_required" in output
    assert "资料审查结果" in output
    assert "pyproject.toml" in output
    assert "evidence://reference-reader/" in output
    assert "reference_outside_allowed_roots" not in output
    assert "外部只读 refs sidecar" not in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_external_readonly_evidence_path_can_be_confirmed_and_reviewed(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/cli-chat-example.json"
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            f"请审查 {evidence_path}\n"
            "同意\n"
            "/reference list\n"
            "/reference clear\n"
            "/reference list\n"
            "/exit\n"
        ),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-evidence-add-confirm-test",
            "--config-root",
            str(tmp_path / "config"),
        ),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "external_readonly_evidence_path_confirmation_required" in output
    assert "不会联网、不会上传" in output
    assert "外部只读证据摘要" in output
    assert "source_url: https://example.com/" in output
    assert "evidence://external-readonly/cli-fetch/cli-chat-example.json" in output
    assert _external_excerpt() in output
    assert "外部只读 refs sidecar" not in output
    assert "sidecar_stage" not in output
    assert "sidecar_permanent_bypass" not in output
    assert "external-readonly-evidence-observation://" not in output
    assert "当前会话外部只读 evidence-output" in output
    assert "已清空当前会话的受控资料文件和外部只读证据" in output
    assert "当前会话还没有加入受控资料文件或外部只读证据" in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_external_readonly_evidence_path_arg_routes_reference_review(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/cli-chat-arg.json"
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("请审查这份外部只读证据摘要，指出问题和建议\n/exit\n"),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-evidence-arg-test",
            "--config-root",
            str(tmp_path / "config"),
            "--external-readonly-evidence-path",
            evidence_path,
        ),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "资料审查结果" in output
    assert "外部只读证据摘要" in output
    assert "evidence://external-readonly/cli-fetch/cli-chat-arg.json" in output
    assert "外部只读 refs sidecar" not in output
    assert "sidecar_stage" not in output
    assert "external_readonly_refs_status" not in output
    assert "external-readonly-evidence-observation://" not in output
    assert "ProductGatewayResponse" not in output
    assert "reference_path_not_configured" not in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_external_readonly_evidence_path_arg_routes_ordinary_qa_to_ask_bridge(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/cli-chat-qa.json"
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("这份资料主要说明了什么？\n2\nyes\n/exit\n"),
    )
    service = FakeExternalReadonlyAskLlmInvocationService(
        "这个页面说明 Example Domain 用于文档示例，证据见 "
        "evidence://external-readonly/cli-fetch/cli-chat-qa.json。"
    )
    factory = FakeExternalReadonlyAskLlmInvocationServiceFactory(service)

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-evidence-qa-bridge-test",
            "--config-root",
            str(tmp_path / "config"),
            "--external-readonly-evidence-path",
            evidence_path,
        ),
        entry_runner=_raising_entry_runner,
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(service.requests) == 1
    assert "请选择模型：1) deepseek  2) gemma4" in output
    assert "允许本次受控大模型回答？ 输入 yes/no" in output
    assert "external_readonly_ask: true" in output
    assert "readonly_refs_status: ready" in output
    assert "llm_runtime_call_performed: true" in output
    assert "追问仅在当前进程内围绕同一受治理证据继续" in output
    assert "Example Domain 用于文档示例" in output
    assert "external_readonly_evidence_qa_requires_ask_entry" not in output
    assert "operation_flow_reference_review_workflow" not in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_external_readonly_evidence_path_arg_ask_bridge_follow_up_reuses_state(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/cli-chat-follow-up.json"
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "这份资料主要说明了什么？\n"
            "2\n"
            "yes\n"
            "它适合用于什么场景？\n"
            "/exit\n"
        ),
    )
    service = FakeExternalReadonlyAskLlmInvocationService(
        [
            "这个页面说明 Example Domain 用于文档示例，证据见 "
            "evidence://external-readonly/cli-fetch/cli-chat-follow-up.json。",
            "它适合用于文档示例和教程场景，不应用于实际运营。"
            "证据见 evidence://external-readonly/cli-fetch/cli-chat-follow-up.json。",
        ]
    )
    factory = FakeExternalReadonlyAskLlmInvocationServiceFactory(service)

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-evidence-qa-follow-up-test",
            "--config-root",
            str(tmp_path / "config"),
            "--external-readonly-evidence-path",
            evidence_path,
        ),
        entry_runner=_raising_entry_runner,
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(service.requests) == 2
    assert service.requests[1].metadata["evidence_summary_answer_context"][
        "user_question"
    ] == "它适合用于什么场景？"
    assert "external_readonly_ask: true" in output
    assert "follow_up_turn_index: 1" in output
    assert "follow_up_scope: temporary_only; durable_session=false;" in output
    assert "不启用长期 Memory 或持久会话" in output
    assert "它适合用于文档示例和教程场景" in output
    assert "operation_flow_reference_review_workflow" not in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_external_readonly_ask_bridge_answer_transformation_uses_last_answer(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/cli-chat-transform.json"
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "这份资料主要说明了什么？\n"
            "2\n"
            "yes\n"
            "将摘要翻译成英文\n"
            "/exit\n"
        ),
    )
    first_answer = (
        "这个页面说明 Example Domain 用于文档示例，不应在实际运营中使用。"
    )
    service = FakeExternalReadonlyAskLlmInvocationService(
        [
            first_answer,
            "This summary says Example Domain is for documentation examples "
            "and should not be used in operations.",
        ]
    )
    factory = FakeExternalReadonlyAskLlmInvocationServiceFactory(service)

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-evidence-answer-transform-test",
            "--config-root",
            str(tmp_path / "config"),
            "--external-readonly-evidence-path",
            evidence_path,
        ),
        entry_runner=_raising_entry_runner,
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(service.requests) == 2
    transform_request = service.requests[1]
    assert transform_request.metadata["answer_scoped_transformation"] is True
    transform_context = transform_request.metadata["evidence_summary_answer_context"]
    assert transform_context["user_question"] == "将摘要翻译成英文"
    assert transform_context["summary_facts"] == [first_answer]
    assert "answer_scoped_transformation: true" in output
    assert "answer_scope: answer_scoped; temporary_only;" in output
    assert "This summary says Example Domain" in output
    assert "follow_up_turn_index: 1" not in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_external_readonly_ask_bridge_formats_previous_answer(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/cli-chat-format.json"
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "这份资料主要说明了什么？\n"
            "2\n"
            "yes\n"
            "你给我的答案，可否做个排版优化吗\n"
            "/exit\n"
        ),
    )
    first_answer = (
        "这个页面说明 Example Domain 用于文档示例，不应在实际运营中使用。"
    )
    service = FakeExternalReadonlyAskLlmInvocationService(
        [first_answer, "unused model formatting answer"]
    )
    factory = FakeExternalReadonlyAskLlmInvocationServiceFactory(service)

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-evidence-answer-format-test",
            "--config-root",
            str(tmp_path / "config"),
            "--external-readonly-evidence-path",
            evidence_path,
        ),
        entry_runner=_raising_entry_runner,
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(service.requests) == 1
    assert "answer_scoped_transformation: true" in output
    assert "## 排版优化" in output
    assert "follow_up_turn_index: 1" not in output
    _assert_text_output_boundary(output)


def test_chat_external_readonly_ask_bridge_three_point_summary_uses_last_answer(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/cli-chat-three-point.json"
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "这份资料主要说明了什么？\n"
            "2\n"
            "yes\n"
            "请基于以上答案内容做个三点式摘要\n"
            "/exit\n"
        ),
    )
    first_answer = (
        "Cognition System 可以读取外部只读资料并回答问题。"
        "它会要求用户明确授权抓取资料和调用模型。"
        "它不会把当前追问冒充为长期记忆。"
    )
    service = FakeExternalReadonlyAskLlmInvocationService(
        [first_answer, "unused follow-up answer"]
    )
    factory = FakeExternalReadonlyAskLlmInvocationServiceFactory(service)

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-evidence-answer-three-point-test",
            "--config-root",
            str(tmp_path / "config"),
            "--external-readonly-evidence-path",
            evidence_path,
        ),
        entry_runner=_raising_entry_runner,
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(service.requests) == 1
    assert "answer_scoped_transformation: true" in output
    assert "answer_run_ref: unavailable" in output
    assert "answer_run_unavailable_reason: answer_scoped_transformation" in output
    assert "follow_up_turn_index: 1" not in output
    assert "1. Cognition System 可以读取外部只读资料并回答问题" in output
    assert "2. 它会要求用户明确授权抓取资料和调用模型" in output
    assert "3. 它不会把当前追问冒充为长期记忆" in output
    _assert_text_output_boundary(output)


def test_chat_external_readonly_ask_bridge_tolerates_ta_typo_follow_up(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/cli-chat-ta-follow-up.json"
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "这份资料主要说明了什么？\n"
            "2\n"
            "yes\n"
            "他适用于什么场景\n"
            "/exit\n"
        ),
    )
    service = FakeExternalReadonlyAskLlmInvocationService(
        [
            "这个页面说明 Example Domain 用于文档示例，证据见 "
            "evidence://external-readonly/cli-fetch/cli-chat-ta-follow-up.json。",
            "它适用于文档示例和教程场景，不应用于实际运营。",
        ]
    )
    factory = FakeExternalReadonlyAskLlmInvocationServiceFactory(service)

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-evidence-ta-follow-up-test",
            "--config-root",
            str(tmp_path / "config"),
            "--external-readonly-evidence-path",
            evidence_path,
        ),
        entry_runner=_raising_entry_runner,
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(service.requests) == 2
    assert service.requests[1].metadata["evidence_summary_answer_context"][
        "user_question"
    ] == "他适用于什么场景"
    assert "follow_up_turn_index: 1" in output
    assert "它适用于文档示例和教程场景" in output
    assert "no-live 模式已完成受控运行" not in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_session_operation_summary_is_local_and_no_model(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/cli-chat-session-summary.json"
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "请基于这份公开资料说明 Example Domain 主要说明了什么。\n"
            "2\n"
            "yes\n"
            "将摘要翻译成英文\n"
            "它适合哪些用户？\n"
            "对我 以上操作做个总结\n"
            "/exit\n"
        ),
    )
    service = FakeExternalReadonlyAskLlmInvocationService(
        [
            "这个页面说明 Example Domain 用于文档示例。",
            "This material describes Example Domain for documentation examples.",
            "它适用于文档示例和教程场景，不应用于实际运营。",
        ]
    )
    factory = FakeExternalReadonlyAskLlmInvocationServiceFactory(service)

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-evidence-session-summary-test",
            "--config-root",
            str(tmp_path / "config"),
            "--external-readonly-evidence-path",
            evidence_path,
        ),
        entry_runner=_raising_entry_runner,
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(service.requests) == 3
    assert "chat_session_operation_summary: true" in output
    assert "以上操作小结" in output
    assert (
        "提出资料问题：请基于这份公开资料说明 Example Domain 主要说明了什么。"
        in output
    )
    assert "完成首轮 external-readonly 问答并形成资料答案" in output
    assert "对上一轮答案做变换：将摘要翻译成英文" in output
    assert "围绕同一受治理证据追问：它适合哪些用户？" in output
    assert "summary_scope: current_process_only; durable_session=false;" in output
    assert "no-live 模式已完成受控运行" not in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_session_experience_suggestions_are_local_and_no_model(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    evidence_path = (
        "outputs/external-readonly/cli-fetch/"
        "cli-chat-session-experience-suggestions.json"
    )
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "这份资料主要说明了什么？\n"
            "2\n"
            "yes\n"
            "将摘要翻译成英文\n"
            "他适用于什么场景\n"
            "对我以上操作做个总结\n"
            "基于以上操作，结合用户体验，你觉得我还有哪些方面值得体验下\n"
            "/exit\n"
        ),
    )
    service = FakeExternalReadonlyAskLlmInvocationService(
        [
            "这个页面说明 Example Domain 用于文档示例。",
            "This material describes Example Domain for documentation examples.",
            "它适用于文档示例和教程场景，不应用于实际运营。",
        ]
    )
    factory = FakeExternalReadonlyAskLlmInvocationServiceFactory(service)

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-evidence-session-experience-suggestions-test",
            "--config-root",
            str(tmp_path / "config"),
            "--external-readonly-evidence-path",
            evidence_path,
        ),
        entry_runner=_raising_entry_runner,
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(service.requests) == 3
    assert "chat_session_operation_summary: true" in output
    assert "chat_session_experience_suggestions: true" in output
    assert "基于当前进程内已完成的操作，建议继续体验" in output
    assert "答案态变换链路" in output
    assert "证据态追问" in output
    assert "拒绝授权路径" in output
    assert "suggestion_scope: current_process_only; durable_session=false;" in output
    assert "no-live 模式已完成受控运行" not in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_session_summary_and_suggestions_mark_failed_external_flow(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    evidence_path = (
        "outputs/external-readonly/cli-fetch/"
        "cli-chat-session-failed-external-flow.json"
    )
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "这份资料主要说明了什么？\n"
            "2\n"
            "yes\n"
            "将该摘要翻译成英文\n"
            "它适合用于什么场景？\n"
            "对我以上操作做个总结\n"
            "基于以上操作，结合用户体验，你觉得我还有哪些方面值得体验下\n"
            "/exit\n"
        ),
    )
    service = FailingExternalReadonlyAskLlmInvocationService()
    factory = FakeExternalReadonlyAskLlmInvocationServiceFactory(service)

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-evidence-session-failed-flow-test",
            "--config-root",
            str(tmp_path / "config"),
            "--external-readonly-evidence-path",
            evidence_path,
        ),
        entry_runner=_raising_entry_runner,
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(service.requests) == 1
    assert "chat_answer_transformation_snapshot_missing" in output
    assert "首轮 external-readonly 问答被治理或传输条件拦截，未形成资料答案" in output
    assert "尝试答案变换但未形成结果：将该摘要翻译成英文" in output
    assert "尝试证据态追问但没有可追问证据：它适合用于什么场景？" in output
    assert "先复验首轮资料问答成功路径" in output
    assert "先完成一次成功资料问答，再体验答案态变换" in output
    assert "先让首轮资料问答形成可追问证据" in output
    assert "继续比较 Gemma4 本地路径下的证据追问" not in output
    assert "no-live 模式已完成受控运行" not in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_url_bridge_summary_and_suggestions_mark_initial_fetch_failure(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "https://example.com\n"
            "这份资料主要说明了什么？\n"
            "2\n"
            "y\n"
            "y\n"
            "将该摘要翻译成英文\n"
            "它适合用于什么场景？\n"
            "对我以上操作做个总结\n"
            "基于以上操作，结合用户体验，你觉得我还有哪些方面值得体验下\n"
            "/exit\n"
        ),
    )

    def fake_blocked_ask_output(
        *_: Any,
        **__: Any,
    ) -> EvidenceSummaryAnswerAskInteractionResult:
        return EvidenceSummaryAnswerAskInteractionResult(
            exit_code=3,
            output={
                "status": "blocked",
                "failure_explanation": "本次请求被治理条件拦截，未形成可返回答案。",
                "readonly_refs_status": "blocked",
                "llm_call_attempted": False,
                "llm_runtime_call_performed": False,
                "blocking_reasons": [
                    "transport_error",
                    "http_status_not_success",
                ],
                "warnings": ["content_type_missing"],
                "safe_observability_summary": {
                    "reason": "transport_error",
                    "user_explanation": (
                        "本轮未能成功读取外部资料，可能是网络、远端服务或 URL "
                        "临时不可用导致。请稍后重试，或确认 URL 可访问。"
                    ),
                },
            },
        )

    monkeypatch.setattr(
        cognition_application,
        "run_external_readonly_ask_initial_channel",
        fake_blocked_ask_output,
    )
    service = FakeExternalReadonlyAskLlmInvocationService(
        "这个回答不应被调用。"
    )
    factory = FakeExternalReadonlyAskLlmInvocationServiceFactory(service)

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-url-initial-fetch-failure-test",
            "--config-root",
            str(tmp_path / "config"),
        ),
        entry_runner=_raising_entry_runner,
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(service.requests) == 0
    assert "transport_error" in output
    assert "http_status_not_success" in output
    assert "observability_reason: transport_error" in output
    assert "observability_explanation: 本轮未能成功读取外部资料" in output
    assert "当前没有可变换的上一轮答案" in output
    assert "上一轮 external-readonly 问答未形成可追问证据" in output
    assert "输入外部只读抓取 / 受控大模型回答等授权确认" in output
    assert "完成外部只读抓取 / 受控大模型回答等授权确认" not in output
    assert "首轮 external-readonly 问答被治理或传输条件拦截，未形成资料答案" in output
    assert "尝试答案变换但未形成结果：将该摘要翻译成英文" in output
    assert "尝试证据态追问但没有可追问证据：它适合用于什么场景？" in output
    assert "先复验首轮资料问答成功路径" in output
    assert "先完成一次成功资料问答，再体验答案态变换" in output
    assert "先让首轮资料问答形成可追问证据" in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_session_experience_guide_preempts_external_follow_up(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    evidence_path = (
        "outputs/external-readonly/cli-fetch/"
        "cli-chat-session-experience-guide.json"
    )
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "这份资料主要说明了什么？\n"
            "2\n"
            "yes\n"
            "将摘要翻译成英文\n"
            "他适用于什么场景\n"
            "基于以上操作，结合用户体验，你觉得我还有哪些方面值得体验下\n"
            "很好，请你帮我整理成体验指引，我该如何操作来在我们当前的交互中来体验\n"
            "将上面的回答改写成适合初中生理解的版本\n"
            "我是说你给我的建议，我如何具体体验，是命令行还是自然语言？\n"
            "/exit\n"
        ),
    )
    service = FakeExternalReadonlyAskLlmInvocationService(
        [
            "这个页面说明 Example Domain 用于文档示例。",
            "This material describes Example Domain for documentation examples.",
            "它适用于文档示例和教程场景，不应用于实际运营。",
        ]
    )
    factory = FakeExternalReadonlyAskLlmInvocationServiceFactory(service)

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-evidence-session-experience-guide-test",
            "--config-root",
            str(tmp_path / "config"),
            "--external-readonly-evidence-path",
            evidence_path,
        ),
        entry_runner=_raising_entry_runner,
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(service.requests) == 3
    assert "chat_session_experience_suggestions: true" in output
    assert output.count("chat_session_experience_guide: true") == 2
    assert "当前已经在 `uv run cognition chat` 交互里" in output
    assert "继续体验主要直接输入自然语言" in output
    assert "需要新开一轮命令行的边界测试" in output
    assert "你现在已经在聊天模式里了" in output
    assert "想继续试，大多数时候直接输入一句自然语言就行" in output
    assert "llm_call_attempted: false" in output
    assert "guide_scope: current_process_only; durable_session=false;" in output
    assert "follow_up_turn_index: 2" not in output
    assert "no-live 模式已完成受控运行" not in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_answer_transformation_without_snapshot_is_explained(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("将该摘要翻译成英文\n/exit\n"),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args("--chat-session-id", "cli-answer-transform-missing-test"),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "当前没有可变换的上一轮答案" in output
    assert "chat_answer_transformation_snapshot_missing" in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_external_readonly_evidence_path_arg_ask_bridge_long_summary_preflight(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    evidence_path = "outputs/external-readonly/cli-fetch/cli-chat-preflight.json"
    evidence_file = tmp_path / evidence_path
    evidence_file.parent.mkdir(parents=True)
    evidence_file.write_text(
        json.dumps(_external_readonly_archive(evidence_path), ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "这份资料主要说明了什么？\n"
            "2\n"
            "yes\n"
            "请将首页内容改写成1200字的中文摘要\n"
            "/exit\n"
        ),
    )
    service = FakeExternalReadonlyAskLlmInvocationService(
        "这个页面说明 Example Domain 用于文档示例，证据见 "
        "evidence://external-readonly/cli-fetch/cli-chat-preflight.json。"
    )
    factory = FakeExternalReadonlyAskLlmInvocationServiceFactory(service)

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-evidence-qa-preflight-test",
            "--config-root",
            str(tmp_path / "config"),
            "--external-readonly-evidence-path",
            evidence_path,
        ),
        entry_runner=_raising_entry_runner,
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(service.requests) == 1
    assert "当前受治理证据内容很短" in output
    assert "无法在不添加未证实信息的情况下" in output
    assert "llm_call_attempted: false" in output
    assert "llm_runtime_call_performed: false" in output
    assert "external_readonly_ask: true" in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_source_url_starts_external_readonly_ask_bridge_without_fetching(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("URL/evidence: https://example.com\n/exit\n"),
    )
    service = FakeExternalReadonlyAskLlmInvocationService(
        "这个页面说明 Example Domain 用于文档示例。"
    )
    factory = FakeExternalReadonlyAskLlmInvocationServiceFactory(service)

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-readonly-url-bridge-test",
            "--config-root",
            str(tmp_path / "config"),
        ),
        entry_runner=_raising_entry_runner,
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(service.requests) == 0
    assert "已收到外部只读 URL" in output
    assert "external_readonly_ask: true" in output
    assert "chat_external_readonly_bridge_pending" in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_source_url_ask_bridge_passes_fetch_confirmation_to_ask(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "https://example.com\n"
            "这份资料主要说明了什么？\n"
            "2\n"
            "y\n"
            "y\n"
            "它适合用于什么场景？\n"
            "/exit\n"
        ),
    )
    captured_args: dict[str, Any] = {}

    def fake_build_ask_output(
        args: Any,
        **_: Any,
    ) -> EvidenceSummaryAnswerAskInteractionResult:
        captured_args["confirm_external_readonly_fetch"] = (
            args.confirm_external_readonly_fetch
        )
        return EvidenceSummaryAnswerAskInteractionResult(
            exit_code=0,
            output={
                "status": "success",
                "answer": "这个页面说明 Example Domain 用于文档示例。",
                "readonly_refs_status": "ready",
                "llm_call_attempted": True,
                "llm_runtime_call_performed": True,
            },
        )

    monkeypatch.setattr(
        cognition_application,
        "run_external_readonly_ask_initial_channel",
        fake_build_ask_output,
    )
    service = FakeExternalReadonlyAskLlmInvocationService(
        "这个页面说明 Example Domain 用于文档示例。"
    )
    factory = FakeExternalReadonlyAskLlmInvocationServiceFactory(service)

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-external-readonly-url-confirm-test",
            "--config-root",
            str(tmp_path / "config"),
        ),
        entry_runner=_raising_entry_runner,
        external_readonly_ask_llm_invocation_service_factory=factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert captured_args["confirm_external_readonly_fetch"] == "同意外部只读抓取"
    assert "external_readonly_natural_language_confirmation_required" not in output
    assert "这个页面说明 Example Domain 用于文档示例" in output
    assert "上一轮 external-readonly 问答未形成可追问证据" in output
    assert "no-live 模式已完成受控运行" not in output
    _assert_text_output_boundary(output)


def test_chat_reference_path_outside_allowed_roots_is_explained(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("帮我整理摘要 /private/tmp/outside-reference.md\n/exit\n"),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args("--chat-session-id", "cli-reference-add-blocked-test"),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "这个文件路径暂时不能读取" in output
    assert "reference_outside_allowed_roots" in output
    assert "reference_path_blocked" in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_directory_path_does_not_reuse_previous_reference(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    reference_path = (
        REPO_ROOT
        / "tasks"
        / "b1"
        / "454-v0.7.0-CLI-cognition单词入口与local-live默认profile最小实施结果包-v1.zh-CN.md"
    )
    directory_path = REPO_ROOT / "tasks" / "b1"
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            f"帮我整理摘要 {reference_path}\n"
            "同意\n"
            f"帮我看看 {directory_path}\n"
            "/exit\n"
        ),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args("--chat-session-id", "cli-reference-directory-block-test"),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert output.count("资料审查结果") == 1
    assert "reference_directory_not_supported" in output
    assert "当前版本不做目录扫描或文件发现" in output
    assert "reference_path_blocked" in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_sensitive_local_path_without_supported_suffix_is_blocked(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("帮我读取 /Users/peacock/.ssh/id_rsa\n/exit\n"),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args("--chat-session-id", "cli-reference-sensitive-block-test"),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "这个文件路径暂时不能读取" in output
    assert "reference_forbidden_path_marker" in output
    assert "reference_suffix_not_allowed" in output
    assert "该路径命中敏感路径边界" in output
    assert "reference_path_blocked" in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


class _InterruptingStdin:
    def isatty(self) -> bool:
        return True

    def readline(self) -> str:
        raise KeyboardInterrupt


def test_chat_keyboard_interrupt_exits_without_traceback(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    monkeypatch.setattr(sys, "stdin", _InterruptingStdin())

    exit_code = cognition.run_cli(
        _allowed_chat_args("--chat-session-id", "cli-keyboard-interrupt-test"),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "session: interrupted" in output
    assert "Traceback" not in output
    _assert_text_output_boundary(output)


def test_chat_plan_request_enters_workflow_without_controlled_run(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("我要开个养鸡场，帮我设计个方案，规模500只鸡\n/exit\n"),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args("--chat-session-id", "cli-plan-no-live-test"),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "plan workflow 已识别方案类请求" in output
    assert "未生成方案" in output
    assert "养鸡场" in output
    assert "500只鸡" in output
    assert "controlled live output" not in output
    _assert_text_output_boundary(output)


def test_chat_plan_request_routes_through_product_gateway_operation_flow_projection(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    captured_inputs: list[dict[str, Any]] = []

    def capturing_projection(route_input: Any) -> Any:
        captured_inputs.append(dict(route_input))
        return build_cli_operation_flow_route_projection_real(route_input)

    monkeypatch.setattr(
        cognition_chat_routing,
        "_build_product_gateway_operation_flow_route_projection",
        capturing_projection,
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("我要建一个鱼塘，500平米大，深度不低于3米，帮我设计个建设方案\n/exit\n"),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args("--chat-session-id", "cli-plan-router-test"),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(captured_inputs) == 1
    assert captured_inputs[0]["request_id"] == "cli-plan-router-test/turn-001"
    assert captured_inputs[0]["chat_session_id"] == "cli-plan-router-test"
    assert captured_inputs[0]["turn_index"] == 1
    assert captured_inputs[0]["sanitized_previous_display_text"] is None
    assert captured_inputs[0]["reference_paths"] == ()
    assert "plan workflow 已识别方案类请求" in output
    assert "未生成方案" in output
    _assert_text_output_boundary(output)


def test_chat_status_after_plan_shows_workspace_and_evidence_summary(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "cli-runs"
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "我要建一个鱼塘，500平米大，深度不低于3米，帮我设计个建设方案\n"
            "/status\n"
            "/exit\n"
        ),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-plan-status-summary-test",
            "--reference-path",
            "docs/strategy/README.md",
            "--enable-run-workspace",
            "--run-workspace-root",
            str(workspace_root),
        ),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "tool_profile: readonly_reference" in output
    assert "tool_exposure_status: resolved" in output
    assert "exposed_tools: local_reference_reader" in output
    assert "reference_reader_status: enabled" in output
    assert "run_workspace_enabled: true" in output
    assert f"run_workspace_root: {workspace_root}" in output
    assert "skills_status: candidate_only_frozen" in output
    assert "skills_runtime_integrated: false" in output
    assert (
        "skills_capability_projection_status: candidate_only_referenceable"
        in output
    )
    assert "skills_capability_projection_count: 4" in output
    assert "skills_active_slot_reference_count: 4" in output
    assert "skills_projection_runtime_enabled: false" in output
    assert "skills_projection_public_schema_enabled: false" in output
    assert "latest_plan_status: no_live_boundary" in output
    assert "latest_product_gateway_route_status: matched" in output
    assert (
        "latest_product_gateway_route_source: product_gateway._operation_flows.route"
        in output
    )
    assert (
        "latest_product_gateway_route_workflow_name: operation_flow_plan_workflow" in output
    )
    assert "latest_product_gateway_route_execution_enabled: false" in output
    assert "latest_reference_context_status: succeeded" in output
    assert "latest_reference_evidence_ref_count: 1" in output
    assert "latest_workspace_created: true" in output
    assert "latest_workspace_artifact_ref_count: 2" in output
    assert "latest_workspace_result_ref_count: 1" in output
    assert "status_summary_artifact_ref: artifact://run-workspace/" in output
    _assert_text_output_boundary(output)


def test_chat_status_json_after_plan_writes_status_summary_artifact(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "cli-runs"
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "我要建一个鱼塘，500平米大，深度不低于3米，帮我设计个建设方案\n"
            "/status --json\n"
            "/exit\n"
        ),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-plan-status-json-summary-test",
            "--reference-path",
            "docs/strategy/README.md",
            "--enable-run-workspace",
            "--run-workspace-root",
            str(workspace_root),
        ),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out
    json_line = next(line for line in output.splitlines() if line.startswith("{"))
    payload = json.loads(json_line)
    workspace_paths = sorted(
        path for path in workspace_root.glob("*/*") if path.is_dir()
    )
    workspace_path = workspace_paths[0]
    status_summary = json.loads(
        (workspace_path / "artifacts" / "status_summary.json").read_text(
            encoding="utf-8"
        )
    )
    manifest = json.loads(
        (workspace_path / "manifest.json").read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert payload["command"] == "cognition chat /status"
    assert payload["chat_session_id"] == "cli-plan-status-json-summary-test"
    assert payload["tools"]["status"] == "resolved"
    assert payload["tools"]["exposed_tool_names"] == ["local_reference_reader"]
    assert payload["tools"]["loading_validation_status"] == "passed"
    assert payload["tools"]["risk_gate_status"] == "passed"
    assert payload["tools"]["loading_allowed_tool_names"] == [
        "local_reference_reader"
    ]
    assert payload["tools"]["tool_loading_validations"][0]["risk_level"] == "low"
    assert payload["skills"]["status"] == "candidate_only_frozen"
    assert payload["skills"]["runtime_integrated"] is False
    skill_projection = payload["skills"]["capability_projection"]
    assert skill_projection["status"] == "candidate_only_referenceable"
    assert skill_projection["projection_count"] == 4
    assert skill_projection["workflow_slot_reference_count"] == 4
    assert skill_projection["active_slot_reference_count"] == 4
    assert skill_projection["reference_modes"] == ["projection_summary_only"]
    assert skill_projection["runtime_enabled"] is False
    assert skill_projection["skill_file_loading_enabled"] is False
    assert skill_projection["resources_loading_enabled"] is False
    assert skill_projection["scripts_execution_enabled"] is False
    assert skill_projection["tool_exposure_enabled"] is False
    assert skill_projection["agent_runtime_enabled"] is False
    assert skill_projection["prompt_context_enabled"] is False
    assert skill_projection["public_schema_enabled"] is False
    assert skill_projection["metadata"]["does_not_load_skill_file"] is True
    assert skill_projection["metadata"]["does_not_execute_scripts"] is True
    assert payload["latest_plan"]["status"] == "no_live_boundary"
    route_projection = payload["latest_plan"]["product_gateway_route_projection"]
    assert route_projection["status"] == "matched"
    assert route_projection["source"] == "product_gateway._operation_flows.route"
    assert route_projection["workflow_name"] == "operation_flow_plan_workflow"
    assert route_projection["entry_kind"] == "operation_flow_route"
    assert route_projection["execution_mode"] == "preflight_only"
    assert route_projection["route_only"] is True
    assert route_projection["workflow_execution_enabled"] is False
    assert route_projection["registry_workflow_count"] == 4
    assert payload["latest_plan"]["reference_context_status"] == "succeeded"
    assert payload["latest_plan"]["workspace_created"] is True
    assert payload["latest_plan"]["workspace_artifact_ref_count"] == 2
    assert payload["status_summary_artifact_ref"].endswith(
        "/artifacts/status_summary.json"
    )
    assert status_summary["status_summary_artifact_ref"] == (
        payload["status_summary_artifact_ref"]
    )
    assert status_summary["latest_plan"]["workspace_artifact_ref_count"] == 2
    assert status_summary["skills"]["capability_projection"] == skill_projection
    assert payload["status_summary_artifact_ref"] in manifest["artifact_refs"]
    assert manifest["metadata"]["status_summary_artifact_ref"] == (
        payload["status_summary_artifact_ref"]
    )
    _assert_text_output_boundary(output)


def test_chat_plan_manual_reference_requires_governance_boundary(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("我要建一个鱼塘，帮我设计个建设方案\n/exit\n"),
    )

    exit_code = cognition.run_cli(
        [
            "chat",
            "--no-banner",
            "--reference-path",
            "docs/strategy/README.md",
        ],
        entry_runner=_raising_entry_runner,
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "manual reference/workspace controls require" in captured.err
    assert "--operator-approved" in captured.err
    assert "--approval-ref" in captured.err
    assert captured.out == ""


def test_chat_plan_manual_reference_and_workspace_args_create_evidence_layers(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "cli-runs"
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("我要建一个鱼塘，500平米大，深度不低于3米，帮我设计个建设方案\n/exit\n"),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-plan-manual-reference-workspace-test",
            "--reference-path",
            "docs/strategy/README.md",
            "--enable-run-workspace",
            "--run-workspace-root",
            str(workspace_root),
            "--run-workspace-retention-policy",
            "keep",
            "--run-workspace-cleanup-policy",
            "manual",
            "--run-workspace-max-write-bytes",
            "65536",
        ),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "plan workflow 已识别方案类请求" in output

    workspace_paths = sorted(
        path for path in workspace_root.glob("*/*") if path.is_dir()
    )
    assert len(workspace_paths) == 1
    workspace_path = workspace_paths[0]
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
        (workspace_path / "manifest.json").read_text(encoding="utf-8")
    )

    assert reference_context["status"] == "succeeded"
    assert reference_context["requested_references"] == ["docs/strategy/README.md"]
    assert reference_context["consumed_reference_count"] == 1
    assert reference_context["evidence_refs"]
    assert result_payload["reference_context_status"] == "succeeded"
    assert manifest["status"] == "no_live_boundary"
    assert manifest["metadata"]["max_write_bytes"] == 65536
    _assert_text_output_boundary(output)


def test_chat_reference_review_routes_to_second_operation_flow(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "cli-runs"
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
            "cli-reference-review-chat-test",
            "--reference-path",
            "tasks/b1/358-v0.7.0-CLI第二类真实task-workflow场景选择与端到端设计判断结果包-v1.zh-CN.md",
            "--enable-run-workspace",
            "--run-workspace-root",
            str(workspace_root),
        ),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "资料审查结果" in output
    assert "审查范围" in output
    assert "evidence://reference-reader/" in output
    assert "plan workflow 已识别方案类请求" not in output

    workspace_paths = sorted(
        path for path in workspace_root.glob("*/*") if path.is_dir()
    )
    assert len(workspace_paths) == 1
    workspace_path = workspace_paths[0]
    result_payload = json.loads(
        (workspace_path / "results" / "workflow_result.json").read_text(
            encoding="utf-8"
        )
    )
    reference_context = json.loads(
        (workspace_path / "evidence" / "reference_context.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_payload["workflow"] == "operation_flow_reference_review_workflow"
    assert result_payload["status"] == "succeeded"
    assert result_payload["reference_context_status"] == "succeeded"
    assert reference_context["tool_loading_gate"]["status"] == "passed"
    _assert_text_output_boundary(output)


def test_chat_config_profile_explain_routes_to_third_operation_flow(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "cli-runs"
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            "请解释当前配置为什么这样生效，尤其是 tool exposure 和 run workspace 的覆盖关系\n"
            "/exit\n"
        ),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-config-profile-explain-chat-test",
            "--enable-run-workspace",
            "--run-workspace-root",
            str(workspace_root),
        ),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "配置解释结果" in output
    assert "覆盖关系" in output
    assert "tool exposure profile" in output
    assert "reference-reader" in output
    assert "run workspace" in output
    assert "资料审查结果" not in output
    assert "plan workflow 已识别方案类请求" not in output

    workspace_paths = sorted(
        path for path in workspace_root.glob("*/*") if path.is_dir()
    )
    assert len(workspace_paths) == 1
    workspace_path = workspace_paths[0]
    result_payload = json.loads(
        (workspace_path / "results" / "workflow_result.json").read_text(
            encoding="utf-8"
        )
    )
    explain_context = json.loads(
        (workspace_path / "evidence" / "config_explain_context.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_payload["workflow"] == "operation_flow_config_profile_explain_workflow"
    assert result_payload["status"] == "succeeded"
    assert result_payload["model_call_count"] == 0
    assert explain_context["does_not_read_raw_config_directly"] is True
    assert explain_context["does_not_execute_tools"] is True
    assert explain_context["does_not_call_model"] is True
    assert explain_context["run_workspace_summary"]["source"] == "entrypoint_explicit_args"
    _assert_text_output_boundary(output)


def test_chat_run_workspace_evidence_audit_routes_to_fourth_operation_flow(
    monkeypatch: Any,
    capsys: Any,
    tmp_path: Path,
) -> None:
    audited_workspace = _create_audit_source_workspace(tmp_path / "audited")
    output_root = tmp_path / "audit-output"
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("请审计 run workspace，检查证据完整吗\n/exit\n"),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-run-workspace-audit-chat-test",
            "--audit-run-workspace-path",
            str(audited_workspace),
            "--enable-run-workspace",
            "--run-workspace-root",
            str(output_root),
        ),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "运行工作区证据审计结果" in output
    assert "结构完整性" in output
    assert "引用一致性" in output
    assert "边界检查" in output
    assert "配置解释结果" not in output
    assert "plan workflow 已识别方案类请求" not in output

    workspace_paths = sorted(
        path for path in output_root.glob("*/*") if path.is_dir()
    )
    assert len(workspace_paths) == 1
    workspace_path = workspace_paths[0]
    result_payload = json.loads(
        (workspace_path / "results" / "workflow_result.json").read_text(
            encoding="utf-8"
        )
    )
    audit_context = json.loads(
        (workspace_path / "evidence" / "workspace_audit_context.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_payload["workflow"] == "operation_flow_run_workspace_evidence_audit_workflow"
    assert result_payload["audit_result"] == "passed"
    assert result_payload["model_call_count"] == 0
    assert audit_context["does_not_modify_audited_workspace"] is True
    assert audit_context["does_not_execute_tools"] is True
    assert audit_context["does_not_call_model"] is True
    _assert_text_output_boundary(output)


def test_chat_plan_format_followup_reuses_previous_plan_boundary(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("我想建一个鱼塘，500平米大，深度不低于3米，帮我设计个建设方案\n换行注意一下\n/exit\n"),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args("--chat-session-id", "cli-plan-format-no-live-test"),
        entry_runner=_raising_entry_runner,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert output.count("plan workflow 已识别方案类请求") == 2
    assert "鱼塘" in output
    assert "500平米" in output
    assert "深度不低于3米" in output
    assert "boundary facts:\n- request_kind: format_existing_plan" in output
    _assert_text_output_boundary(output)


def test_chat_controlled_live_args_are_passed_and_sanitized_preview_is_visible(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    captured_requests: list[ControlledAdkRunRequest] = []

    def capturing_entry_runner(request: ControlledAdkRunRequest) -> dict[str, Any]:
        captured_requests.append(request)
        return _fake_chat_entry_result(live=True)

    monkeypatch.setattr(sys, "stdin", io.StringIO("请用一句话回复\n/exit\n"))

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-chat-live-test",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://chat-live-llm-test",
            "--ollama-api-base",
            "http://127.0.0.1:11434",
            "--live-llm-timeout-seconds",
            "11",
        ),
        entry_runner=capturing_entry_runner,
        run_gateway_executor=execute_cognition_run_with_default_runtime,
    )

    output = capsys.readouterr().out
    request = captured_requests[0]
    service = request.llm_invocation_service

    assert exit_code == 0
    assert request.runtime_input.input_payload["input_summary"] == "请用一句话回复"
    assert request.operator_approval.live_llm_approval_ref == (
        "approval://chat-live-llm-test/cli-chat-live-test/turn-001"
    )
    assert isinstance(service, AdkGovernedLlmInvocationService)
    assert service._options.live_enabled is True
    assert service._options.ollama_api_base == "http://127.0.0.1:11434"
    assert service._options.timeout_seconds == 11
    assert service._options.max_tokens == cognition_constants.CHAT_LIVE_LLM_MAX_TOKENS
    assert service._options.metadata["cli_chat_controlled_live"] is True
    assert service._options.metadata["response_preview_limit"] == (
        cognition_constants.CHAT_RESPONSE_PREVIEW_LIMIT
    )
    assert "assistant: controlled live output" in output
    assert "live_llm_call_performed: true" in output
    assert "ollama_call_performed: true" in output
    _assert_text_output_boundary(output)


def test_chat_default_fallback_routes_through_product_gateway(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    captured_gateway_inputs: list[dict[str, Any]] = []

    class FakeRuntimeSummary:
        def to_runtime_mapping(self) -> dict[str, Any]:
            return {
                "runtime_id": "runtime-cli-chat-gateway-test-turn-001",
                "invocation_id": "inv-runtime-cli-chat-gateway-test-turn-001",
                "workflow_id": "workflow-controlled-adk-run",
                "execution_mode": "cognition_internal_cli_controlled_run",
                "adk_run_allowed": True,
                "adk_run_performed": True,
                "execution_performed": True,
                "blocking_reasons": [],
                "warnings": [],
                "final_preflight": {"allowed": True},
                "live_llm_call_performed": True,
                "ollama_call_performed": True,
                "llm_invocation_call_allowed": True,
                "llm_invocation_call_attempted": True,
                "llm_invocation_runtime_call_performed": True,
                "sanitized_response_display": "gateway live display",
                "governance_summary_output_ref": "artifact://chat-gateway",
                "sanitized_evidence_ref": "evidence://chat-gateway",
                "audit_ref": "audit://chat-gateway",
            }

    class FakeGatewayResult:
        runtime_summary = FakeRuntimeSummary()
        product_response_summary = _fake_cognition_run_product_response_summary(
            request_id="request-chat-gateway"
        )

    def fake_execute_gateway(
        gateway_input: dict[str, Any],
        **_: Any,
    ) -> FakeGatewayResult:
        captured_gateway_inputs.append(dict(gateway_input))
        return FakeGatewayResult()

    monkeypatch.setattr(
        cognition_run_gateway,
        "execute_cognition_run_gateway_request",
        fake_execute_gateway,
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("你好\n/exit\n"))

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-chat-gateway-test",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://chat-gateway-live",
        )
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert len(captured_gateway_inputs) == 1
    assert captured_gateway_inputs[0]["request_id"] == (
        "inv-runtime-cli-chat-gateway-test-turn-001"
    )
    assert captured_gateway_inputs[0]["input_payload"]["input_summary"] == "你好"
    assert captured_gateway_inputs[0]["input_payload"]["chat_session_id"] == (
        "cli-chat-gateway-test"
    )
    assert captured_gateway_inputs[0]["input_payload"]["turn_index"] == 1
    assert captured_gateway_inputs[0]["live_llm_approval_ref"] == (
        "approval://chat-gateway-live/cli-chat-gateway-test/turn-001"
    )
    assert "assistant: gateway live display" in output
    assert "live_llm_call_performed: true" in output
    _assert_text_output_boundary(output)


def test_chat_live_history_carries_user_and_assistant_summaries(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    captured_payloads: list[dict[str, Any]] = []

    def request_builder(
        args: Any,
        input_payload: dict[str, Any],
    ) -> ControlledAdkRunRequest:
        captured_payloads.append(dict(input_payload))
        return _build_allowed_live_request(args, input_payload)

    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("推荐一部解闷电影\n能详细解释下这个电影吗\n/exit\n"),
    )

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-chat-context-test",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://chat-context-live",
        ),
        request_builder=request_builder,
        entry_runner=lambda request: _fake_chat_entry_result(
            live=True,
            request=request,
        ),
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert captured_payloads[0]["turn_history_summary"] == []
    assert captured_payloads[1]["turn_history_summary"] == [
        {
            "user": "推荐一部解闷电影",
            "assistant": "controlled live output",
        }
    ]
    assert "turn: 2" in output
    _assert_text_output_boundary(output)


def test_chat_history_limit_zero_carries_no_history(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    captured_payloads: list[dict[str, Any]] = []

    def request_builder(
        args: Any,
        input_payload: dict[str, Any],
    ) -> ControlledAdkRunRequest:
        captured_payloads.append(dict(input_payload))
        return _build_allowed_live_request(args, input_payload)

    monkeypatch.setattr(sys, "stdin", io.StringIO("第一轮\n第二轮\n/exit\n"))

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-chat-history-zero-test",
            "--history-limit",
            "0",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://chat-history-zero-live",
        ),
        request_builder=request_builder,
        entry_runner=lambda request: _fake_chat_entry_result(
            live=True,
            request=request,
        ),
    )

    assert exit_code == 0
    assert captured_payloads[0]["turn_history_summary"] == []
    assert captured_payloads[1]["turn_history_summary"] == []
    _assert_text_output_boundary(capsys.readouterr().out)


def test_chat_history_limit_keeps_recent_turns_only(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    captured_payloads: list[dict[str, Any]] = []

    def request_builder(
        args: Any,
        input_payload: dict[str, Any],
    ) -> ControlledAdkRunRequest:
        captured_payloads.append(dict(input_payload))
        return _build_allowed_live_request(args, input_payload)

    monkeypatch.setattr(sys, "stdin", io.StringIO("第一轮\n第二轮\n第三轮\n/exit\n"))

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-chat-history-limit-test",
            "--history-limit",
            "1",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://chat-history-limit-live",
        ),
        request_builder=request_builder,
        entry_runner=lambda request: _fake_chat_entry_result(live=True),
    )

    assert exit_code == 0
    assert captured_payloads[2]["turn_history_summary"] == [
        {"user": "第二轮", "assistant": "controlled live output"}
    ]
    _assert_text_output_boundary(capsys.readouterr().out)


def test_chat_decodes_json_response_preview_for_terminal_display(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    def json_preview_entry_runner(request: ControlledAdkRunRequest) -> dict[str, Any]:
        return _fake_chat_entry_result(live=True, preview='{"response":"你好，可以聊聊。"}')

    monkeypatch.setattr(sys, "stdin", io.StringIO("心情不好，能聊聊吗\n/exit\n"))

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-chat-json-preview-test",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://chat-json-preview-live",
        ),
        entry_runner=json_preview_entry_runner,
        run_gateway_executor=execute_cognition_run_with_default_runtime,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "assistant: 你好，可以聊聊。" in output
    assert '{"response"' not in output
    _assert_text_output_boundary(output)


def test_chat_prefers_sanitized_response_display_when_available(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    display_text = "这是一段更完整的脱敏终端展示文本，可以超过短 preview。"

    def display_entry_runner(request: ControlledAdkRunRequest) -> dict[str, Any]:
        return _fake_chat_entry_result(
            live=True,
            preview="这是一段更完整的脱敏",
            display=display_text,
        )

    monkeypatch.setattr(sys, "stdin", io.StringIO("请详细解释这部电影\n/exit\n"))

    exit_code = cognition.run_cli(
        _allowed_chat_args(
            "--chat-session-id",
            "cli-chat-display-test",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://chat-display-live",
        ),
        entry_runner=display_entry_runner,
        run_gateway_executor=execute_cognition_run_with_default_runtime,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert f"assistant: {display_text}" in output
    _assert_text_output_boundary(output)


def test_run_invalid_input_json_returns_usage_error(capsys: Any) -> None:
    exit_code = cognition.run_cli(
        ["run", "--input-json", "{not-json"],
        entry_runner=_raising_entry_runner,
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "cognition run error" in captured.err


def test_run_blank_input_text_returns_usage_error(capsys: Any) -> None:
    exit_code = cognition.run_cli(
        ["run", "--input-text", "   "],
        entry_runner=_raising_entry_runner,
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--input-text must not be blank" in captured.err


def test_run_input_text_is_mutually_exclusive_with_input_json(capsys: Any) -> None:
    exit_code = cognition.run_cli(
        ["run", "--input-text", "hello", "--input-json", "{}"],
        entry_runner=_raising_entry_runner,
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert "not allowed with argument" in captured.err


def test_run_missing_approval_and_refs_blocks_without_runtime(capsys: Any) -> None:
    exit_code = cognition.run_cli(
        ["run", "--json"],
        entry_runner=_raising_entry_runner,
    )

    output = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert output["status"] == "blocked"
    assert output["adk_run_performed"] is False
    assert output["execution_performed"] is False
    assert "operator_approval_not_true" in output["blocking_reasons"]
    assert "sanitized_evidence_ref_missing" in output["blocking_reasons"]


def test_run_preflight_only_does_not_call_runtime(capsys: Any) -> None:
    exit_code = cognition.run_cli(
        [
            "run",
            "--json",
            "--preflight-only",
            "--operator-approved",
            "--approval-ref",
            "approval://cli-test",
            "--audit-ref",
            "audit://cli-test",
            "--sanitized-evidence-ref",
            "evidence://cli-test",
            "--governance-summary-output-ref",
            "artifact://cli-summary",
        ],
        entry_runner=_raising_entry_runner,
    )

    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["status"] == "preflight_allowed"
    assert output["adk_run_allowed"] is True
    assert output["adk_run_performed"] is False
    assert output["execution_performed"] is False
    assert "preflight_only_runtime_not_executed" in output["warnings"]


def test_run_input_text_maps_to_sanitized_input_summary(capsys: Any) -> None:
    captured_payloads: list[dict[str, Any]] = []

    def request_builder(
        args: Any,
        input_payload: dict[str, Any],
    ) -> ControlledAdkRunRequest:
        captured_payloads.append(dict(input_payload))
        return _build_allowed_request(args, input_payload)

    exit_code = cognition.run_cli(
        [
            "run",
            "--json",
            "--operator-approved",
            "--approval-ref",
            "approval://cli-input-text-test",
            "--audit-ref",
            "audit://cli-input-text-test",
            "--sanitized-evidence-ref",
            "evidence://cli-input-text-test",
            "--governance-summary-output-ref",
            "artifact://cli-input-text-test",
            "--input-text",
            "请做一次 no-live 终端体验验证",
        ],
        request_builder=request_builder,
        entry_runner=_fake_chat_entry_runner,
    )

    output = json.loads(capsys.readouterr().out)
    serialized = json.dumps(output, ensure_ascii=False, sort_keys=True)

    assert exit_code == 0
    assert captured_payloads == [
        {"input_summary": "请做一次 no-live 终端体验验证"}
    ]
    assert output["status"] == "succeeded"
    assert output["live_llm_call_performed"] is False
    assert output["ollama_call_performed"] is False
    assert "raw_prompt" not in serialized
    assert "raw_provider_response" not in serialized
    assert "raw_response" not in serialized
    assert "messages" not in serialized


def test_run_allowed_default_registry_uses_production_no_live_provider(
    capsys: Any,
) -> None:
    exit_code = cognition.run_cli(
        [
            "run",
            "--json",
            "--operator-approved",
            "--approval-ref",
            "approval://cli-provider-test",
            "--audit-ref",
            "audit://cli-provider-test",
            "--sanitized-evidence-ref",
            "evidence://cli-provider-test",
            "--governance-summary-output-ref",
            "artifact://cli-provider-test",
            "--input-json",
            '{"message":"hello"}',
        ],
        run_gateway_executor=execute_cognition_run_with_default_runtime,
    )

    output = json.loads(capsys.readouterr().out)
    serialized = json.dumps(output, ensure_ascii=False, sort_keys=True)

    assert exit_code == 0
    assert output["status"] == "succeeded"
    assert output["adk_run_allowed"] is True
    assert output["adk_run_performed"] is True
    assert output["execution_performed"] is True
    assert output["live_llm_call_performed"] is False
    assert output["ollama_call_performed"] is False
    assert output["llm_invocation_call_allowed"] is True
    assert output["llm_invocation_call_attempted"] is False
    assert output["llm_invocation_runtime_call_performed"] is False
    assert output["llm_invocation_failure_type"] == "live_disabled"
    assert output["controlled_live_llm_preflight"]["allowed"] is False
    assert (
        output["controlled_live_llm_preflight"]["live_llm_call_performed"] is False
    )
    assert "live_llm_allowed_not_true" in output[
        "controlled_live_llm_preflight"
    ]["blocking_reasons"]
    assert output["llm_invocation_result_ref"].startswith(
        "llm-invocation-result://llm-invocation-"
    )
    assert output["llm_invocation_observation_ref"].startswith(
        "llm-call-observation://llm-invocation-"
    )
    assert output["llm_invocation_summary_ref"].startswith(
        "agent-llm-invocation-summary://llm-invocation-"
    )
    assert output["governance_summary_payload_ref"] == "artifact://cli-provider-test"
    assert "recorded_run" not in output
    assert "llm_invocation_audit" not in output
    assert "agent_shell_audit" not in output
    assert "llm_invocation_readonly_facts" not in output
    assert "live_profile" not in serialized
    assert "llm_call_observation_candidate" not in output
    assert "agent_llm_invocation_summary_candidate" not in output
    assert "raw_adk_object" not in serialized
    assert "raw_state_value" not in serialized
    assert "artifact_content" not in serialized
    assert "live_model_payload" not in serialized


def test_run_default_path_routes_through_product_gateway(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    captured_gateway_inputs: list[dict[str, Any]] = []

    class FakeRuntimeSummary:
        def to_runtime_mapping(self) -> dict[str, Any]:
            return {
                "runtime_id": "runtime-gateway-default-test",
                "invocation_id": "inv-gateway-default-test",
                "workflow_id": "workflow-controlled-adk-run",
                "execution_mode": "cognition_internal_cli_controlled_run",
                "adk_run_allowed": True,
                "adk_run_performed": True,
                "execution_performed": True,
                "blocking_reasons": [],
                "warnings": [],
                "final_preflight": {"allowed": True},
                "live_llm_call_performed": False,
                "ollama_call_performed": False,
                "llm_invocation_call_allowed": True,
                "llm_invocation_call_attempted": False,
                "llm_invocation_runtime_call_performed": False,
                "llm_invocation_failure_type": "live_disabled",
                "governance_summary_output_ref": "artifact://gateway-default",
                "sanitized_evidence_ref": "evidence://gateway-default",
                "audit_ref": "audit://gateway-default",
            }

    class FakeGatewayResult:
        runtime_summary = FakeRuntimeSummary()
        product_response_summary = _fake_cognition_run_product_response_summary(
            request_id="request-gateway-default"
        )

    def fake_execute_gateway(
        gateway_input: dict[str, Any],
        **_: Any,
    ) -> FakeGatewayResult:
        captured_gateway_inputs.append(dict(gateway_input))
        return FakeGatewayResult()

    monkeypatch.setattr(
        cognition_run_gateway,
        "execute_cognition_run_gateway_request",
        fake_execute_gateway,
    )

    exit_code = cognition.run_cli(
        [
            "run",
            "--json",
            "--runtime-id",
            "runtime-gateway-default-test",
            "--operator-approved",
            "--approval-ref",
            "approval://gateway-default",
            "--audit-ref",
            "audit://gateway-default",
            "--sanitized-evidence-ref",
            "evidence://gateway-default",
            "--governance-summary-output-ref",
            "artifact://gateway-default",
            "--input-json",
            '{"message":"hello"}',
        ],
    )

    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert len(captured_gateway_inputs) == 1
    assert captured_gateway_inputs[0]["input_payload"] == {
        "input_summary": "hello"
    }
    assert "message" not in captured_gateway_inputs[0]["input_payload"]
    assert output["status"] == "succeeded"
    assert output["governance_summary_payload_ref"] == "artifact://gateway-default"
    _assert_cognition_run_product_response_summary(output)


def test_run_allowed_default_registry_stdout_is_parseable_json() -> None:
    result = _run_cognition_subprocess(
        [
            "run",
            "--json",
            "--operator-approved",
            "--approval-ref",
            "approval://cli-json-contract-test",
            "--audit-ref",
            "audit://cli-json-contract-test",
            "--sanitized-evidence-ref",
            "evidence://cli-json-contract-test",
            "--governance-summary-output-ref",
            "artifact://cli-json-contract-test",
            "--input-json",
            '{"message":"hello"}',
        ]
    )

    output = json.loads(result.stdout)

    assert result.returncode == 0
    assert result.stdout.lstrip().startswith("{")
    assert "AuthlibDeprecationWarning" not in result.stderr
    assert "[EXPERIMENTAL] feature FeatureName." not in result.stderr
    assert set(output).issubset(cognition_constants.ALLOWED_TOP_LEVEL_FIELDS)
    assert output["status"] == "succeeded"
    assert output["execution_performed"] is True
    assert output["live_llm_call_performed"] is False
    assert output["ollama_call_performed"] is False
    assert output["llm_invocation_runtime_call_performed"] is False
    assert output["llm_invocation_failure_type"] == "live_disabled"
    assert output["controlled_live_llm_preflight"]["allowed"] is False
    summary = _assert_cognition_run_product_response_summary(output)
    assert summary["governance_summary_ref"] == "artifact://cli-json-contract-test"
    assert [ref["ref"] for ref in summary["evidence_refs"]] == [
        "evidence://cli-json-contract-test"
    ]
    assert [ref["ref"] for ref in summary["audit_refs"]] == [
        "audit://cli-json-contract-test"
    ]
    assert "Warning" not in result.stdout
    _assert_output_boundary(output)


def test_run_allowed_default_registry_output_file_matches_stdout_json(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "cognition-run-output.json"
    result = _run_cognition_subprocess(
        [
            "run",
            "--json",
            "--operator-approved",
            "--approval-ref",
            "approval://cli-output-contract-test",
            "--audit-ref",
            "audit://cli-output-contract-test",
            "--sanitized-evidence-ref",
            "evidence://cli-output-contract-test",
            "--governance-summary-output-ref",
            "artifact://cli-output-contract-test",
            "--input-json",
            '{"message":"hello"}',
            "--output",
            str(output_path),
        ]
    )

    stdout_payload = json.loads(result.stdout)
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert stdout_payload == file_payload
    assert stdout_payload["output_ref"] == str(output_path)
    assert stdout_payload["status"] == "succeeded"
    _assert_cognition_run_product_response_summary(stdout_payload)
    _assert_output_boundary(stdout_payload)


def test_run_allowed_default_registry_text_output_declares_no_live_boundaries(
    capsys: Any,
) -> None:
    exit_code = cognition.run_cli(
        [
            "run",
            "--operator-approved",
            "--approval-ref",
            "approval://cli-text-contract-test",
            "--audit-ref",
            "audit://cli-text-contract-test",
            "--sanitized-evidence-ref",
            "evidence://cli-text-contract-test",
            "--governance-summary-output-ref",
            "artifact://cli-text-contract-test",
            "--input-json",
            '{"message":"hello"}',
        ],
        run_gateway_executor=execute_cognition_run_with_default_runtime,
    )

    text = capsys.readouterr().out

    assert exit_code == 0
    assert "status: succeeded" in text
    assert "live_llm_call_performed: false" in text
    assert "ollama_call_performed: false" in text
    assert "llm_invocation_call_allowed: true" in text
    assert "llm_invocation_call_attempted: false" in text
    assert "llm_invocation_runtime_call_performed: false" in text
    assert "llm_invocation_failure_type: live_disabled" in text
    assert "controlled_live_llm_preflight_allowed: false" in text
    assert "product_response_summary" not in text
    _assert_text_output_boundary(text)


def test_run_allowed_no_live_calls_productized_entry(capsys: Any) -> None:
    exit_code = cognition.run_cli(
        [
            "run",
            "--json",
            "--runtime-id",
            "runtime-cli-test-169",
            "--workflow-id",
            "workflow-cli-test-169",
            "--workflow-name",
            "controlled-adk-run",
            "--input-json",
            '{"case_id":"169"}',
            "--operator-approved",
            "--approval-ref",
            "approval://cli-test-169",
            "--audit-ref",
            "audit://cli-test-169",
            "--sanitized-evidence-ref",
            "evidence://cli-test-169",
            "--governance-summary-output-ref",
            "artifact://cli-summary-169",
        ],
        request_builder=_build_allowed_request,
        entry_runner=_fake_chat_entry_runner,
    )

    output = json.loads(capsys.readouterr().out)
    serialized = json.dumps(output, ensure_ascii=False, sort_keys=True)

    assert exit_code == 0
    assert output["status"] == "succeeded"
    assert output["adk_run_allowed"] is True
    assert output["adk_run_performed"] is True
    assert output["execution_performed"] is True
    assert output["live_llm_call_performed"] is False
    assert output["ollama_call_performed"] is False
    assert output["llm_invocation_call_allowed"] is True
    assert output["llm_invocation_failure_type"] == "live_disabled"
    assert output["controlled_live_llm_preflight"]["allowed"] is False
    assert output["governance_summary_payload_ref"] == "artifact://cli-summary-169"
    assert "recorded_run" not in output
    assert "llm_invocation_audit" not in output
    assert "agent_shell_audit" not in output
    assert "llm_invocation_readonly_facts" not in output
    assert "live_profile" not in serialized
    assert "llm_call_observation_candidate" not in output
    assert "agent_llm_invocation_summary_candidate" not in output
    assert "raw_adk_object" not in serialized
    assert "artifact_content" not in serialized
    assert "live_model_payload" not in serialized


def test_run_allowed_controlled_live_keeps_cli_output_sanitized(capsys: Any) -> None:
    exit_code = cognition.run_cli(
        [
            "run",
            "--json",
            "--runtime-id",
            "runtime-cli-live-test-182",
            "--workflow-id",
            "workflow-cli-live-test-182",
            "--workflow-name",
            "controlled-adk-run",
            "--input-json",
            '{"case_id":"182"}',
            "--operator-approved",
            "--approval-ref",
            "approval://cli-live-test-182",
            "--audit-ref",
            "audit://cli-live-test-182",
            "--sanitized-evidence-ref",
            "evidence://cli-live-test-182",
            "--governance-summary-output-ref",
            "artifact://cli-live-summary-182",
        ],
        request_builder=_build_allowed_live_request,
        entry_runner=lambda request: _fake_chat_entry_result(live=True),
    )

    output = json.loads(capsys.readouterr().out)
    serialized = json.dumps(output, ensure_ascii=False, sort_keys=True)

    assert exit_code == 0
    assert set(output).issubset(cognition_constants.ALLOWED_TOP_LEVEL_FIELDS)
    assert output["status"] == "succeeded"
    assert output["execution_performed"] is True
    assert output["live_llm_call_performed"] is True
    assert output["ollama_call_performed"] is True
    assert output["llm_invocation_call_allowed"] is True
    assert output["llm_invocation_call_attempted"] is True
    assert output["llm_invocation_runtime_call_performed"] is True
    assert output["llm_invocation_failure_type"] is None
    assert output["controlled_live_llm_preflight"]["allowed"] is True
    assert "product_response_summary" not in output
    assert "llm_invocation_audit" not in output
    assert "agent_shell_audit" not in output
    assert "llm_invocation_readonly_facts" not in output
    assert "live_profile" not in serialized
    assert "controlled live output" not in serialized
    assert "raw_response" not in serialized
    assert "response_text" not in serialized
    assert "prompt" not in serialized
    assert "messages" not in serialized
    _assert_output_boundary(output)


def test_run_partial_controlled_live_args_block_before_runtime(capsys: Any) -> None:
    exit_code = cognition.run_cli(
        [
            "run",
            "--json",
            "--input-json",
            '{"case_id":"184-partial-live"}',
            "--operator-approved",
            "--approval-ref",
            "approval://cli-partial-live-test-184",
            "--audit-ref",
            "audit://cli-partial-live-test-184",
            "--sanitized-evidence-ref",
            "evidence://cli-partial-live-test-184",
            "--governance-summary-output-ref",
            "artifact://cli-partial-live-summary-184",
            "--request-live-llm",
        ],
        entry_runner=_raising_entry_runner,
    )

    output = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert output["status"] == "blocked"
    assert output["adk_run_performed"] is False
    assert output["execution_performed"] is False
    assert "controlled_live_request_ollama_missing" in output["blocking_reasons"]
    assert "controlled_live_allow_live_llm_missing" in output["blocking_reasons"]
    assert "controlled_live_allow_ollama_missing" in output["blocking_reasons"]
    assert "controlled_live_llm_approval_ref_missing" in output["blocking_reasons"]


def test_run_full_controlled_live_args_assemble_live_service_without_calling_it(
    capsys: Any,
) -> None:
    captured_requests: list[ControlledAdkRunRequest] = []

    def capturing_entry_runner(request: ControlledAdkRunRequest) -> dict[str, Any]:
        captured_requests.append(request)
        return {
            "adk_run_allowed": True,
            "adk_run_performed": True,
            "execution_performed": True,
            "blocking_reasons": [],
            "warnings": [],
            "final_preflight": {"allowed": True, "execution_scope": "test-184"},
            "controlled_live_llm_preflight": {"allowed": True},
            "live_llm_call_performed": False,
            "ollama_call_performed": False,
        }

    exit_code = cognition.run_cli(
        [
            "run",
            "--json",
            "--input-text",
            "controlled live local model smoke input",
            "--operator-approved",
            "--approval-ref",
            "approval://cli-live-test-184",
            "--audit-ref",
            "audit://cli-live-test-184",
            "--sanitized-evidence-ref",
            "evidence://cli-live-test-184",
            "--governance-summary-output-ref",
            "artifact://cli-live-summary-184",
            "--request-live-llm",
            "--request-ollama",
            "--allow-live-llm",
            "--allow-ollama",
            "--live-llm-approval-ref",
            "approval://cli-live-llm-test-184",
            "--ollama-api-base",
            "http://127.0.0.1:11434",
            "--live-llm-timeout-seconds",
            "11",
        ],
        entry_runner=capturing_entry_runner,
        run_gateway_executor=execute_cognition_run_with_default_runtime,
    )

    output = json.loads(capsys.readouterr().out)
    request = captured_requests[0]
    service = request.llm_invocation_service

    assert exit_code == 0
    assert output["status"] == "succeeded"
    assert request.runtime_input.input_payload == {
        "input_summary": "controlled live local model smoke input"
    }
    assert request.productization_gate.request_live_llm is True
    assert request.productization_gate.request_ollama is True
    assert request.productization_gate.allow_live_llm is True
    assert request.productization_gate.allow_ollama is True
    assert request.operator_approval.live_llm_approval_ref == (
        "approval://cli-live-llm-test-184"
    )
    assert request.operator_approval.does_not_trigger_live_llm is False
    assert isinstance(service, AdkGovernedLlmInvocationService)
    assert service._options.live_enabled is True
    assert service._options.ollama_api_base == "http://127.0.0.1:11434"
    assert service._options.timeout_seconds == 11
    assert service._options.temperature == 0
    assert service._options.max_tokens == 64
    assert service._options.metadata["cli_controlled_live"] is True
    assert service._options.metadata["live_options_source"] == (
        "config_contexts.runtime.RuntimeLiveLlmConfigView"
    )
    assert service._options.metadata["configured_model_name"] == (
        "ollama/gemma4-pro:latest"
    )
    assert service._options.metadata["cli_ollama_api_base_override"] is True
    assert service._options.metadata["cli_timeout_seconds_override"] is True


def test_production_request_builder_maps_cli_fields_to_controlled_request() -> None:
    request = build_controlled_adk_run_request(
        ControlledAdkRunRequestBuildInput(
            config_root=Path(".") / "config",
            environment="local",
            profile="dev",
            runtime_id="runtime-builder-test",
            invocation_id="inv-runtime-builder-test",
            workflow_id="workflow-builder-test",
            workflow_name="controlled-adk-run",
            input_payload={"message": "hello"},
            operator_approved=True,
            approval_ref="approval://builder-test",
            audit_ref="audit://builder-test",
            sanitized_evidence_ref="evidence://builder-test",
            governance_summary_output_ref="artifact://builder-summary",
            runtime_assembly=object(),
            evidence_id="evidence-builder-test",
            llm_invocation_service=NoLiveGovernedLlmInvocationService(),
        )
    )

    assert request.runtime_input.runtime_id == "runtime-builder-test"
    assert request.runtime_input.workflow_ref.workflow_id == "workflow-builder-test"
    assert request.runtime_input.workflow_ref.name == "controlled-adk-run"
    assert request.runtime_input.input_payload == {"message": "hello"}
    assert request.productization_gate.request_adk_run is True
    assert request.productization_gate.allow_adk_run is True
    assert request.productization_gate.allow_live_llm is False
    assert request.productization_gate.allow_ollama is False
    assert request.productization_gate.sanitized_evidence_ref == "evidence://builder-test"
    assert request.operator_approval.approved is True
    assert request.operator_approval.approval_ref == "approval://builder-test"
    assert request.operator_approval.audit_ref == "audit://builder-test"
    assert request.operator_approval.allow_live_llm is False
    assert request.operator_approval.allow_ollama is False
    assert request.operator_approval.live_llm_approval_ref is None
    assert request.operator_approval.does_not_trigger_live_llm is True
    assert request.evidence_id == "evidence-builder-test"
    assert request.llm_invocation_service is not None


def test_request_builder_carries_explicit_live_request_without_running_live() -> None:
    request = build_controlled_adk_run_request(
        ControlledAdkRunRequestBuildInput(
            config_root=Path(".") / "config",
            environment="local",
            profile="dev",
            runtime_id="runtime-builder-live-test",
            invocation_id="inv-runtime-builder-live-test",
            workflow_id="workflow-builder-live-test",
            workflow_name="controlled-adk-run",
            input_payload={"message": "hello"},
            operator_approved=True,
            approval_ref="approval://builder-live-test",
            audit_ref="audit://builder-live-test",
            request_live_llm=True,
            request_ollama=True,
            allow_live_llm=True,
            allow_ollama=True,
            live_llm_approval_ref="approval://builder-live-llm",
            sanitized_evidence_ref="evidence://builder-live-test",
            governance_summary_output_ref="artifact://builder-live-summary",
            runtime_assembly=object(),
            evidence_id="evidence-builder-live-test",
            llm_invocation_service=NoLiveGovernedLlmInvocationService(),
        )
    )

    assert request.productization_gate.request_live_llm is True
    assert request.productization_gate.request_ollama is True
    assert request.productization_gate.allow_live_llm is True
    assert request.productization_gate.allow_ollama is True
    assert request.operator_approval.allow_live_llm is True
    assert request.operator_approval.allow_ollama is True
    assert request.operator_approval.live_llm_approval_ref == (
        "approval://builder-live-llm"
    )
    assert request.operator_approval.does_not_trigger_live_llm is False
    assert (
        request.operator_approval.metadata["explicit_controlled_live_requested"] is True
    )

    live_preflight = evaluate_controlled_live_llm_preflight(
        productization_gate=request.productization_gate,
        operator_approval=request.operator_approval,
    )
    final_preflight = evaluate_controlled_adk_run_final_preflight(
        productization_gate=request.productization_gate,
        operator_approval=request.operator_approval,
    )

    assert live_preflight["allowed"] is True
    assert live_preflight["runtime_call_performed"] is False
    assert live_preflight["live_llm_call_performed"] is False
    assert final_preflight["allowed"] is False
    assert "operator_approval_live_llm_boundary_not_true" in final_preflight[
        "blocking_reasons"
    ]
    assert "live_llm_allowed_not_false" in final_preflight["blocking_reasons"]
    assert "ollama_allowed_not_false" in final_preflight["blocking_reasons"]


def test_production_request_builder_keeps_partial_live_request_no_live_safe() -> None:
    request = build_controlled_adk_run_request(
        ControlledAdkRunRequestBuildInput(
            config_root=Path(".") / "config",
            environment="local",
            profile="dev",
            runtime_id="runtime-builder-partial-live-test",
            invocation_id="inv-runtime-builder-partial-live-test",
            workflow_id="workflow-builder-partial-live-test",
            workflow_name="controlled-adk-run",
            input_payload={"message": "hello"},
            operator_approved=True,
            approval_ref="approval://builder-partial-live-test",
            audit_ref="audit://builder-partial-live-test",
            request_live_llm=True,
            request_ollama=True,
            allow_live_llm=True,
            allow_ollama=True,
            live_llm_approval_ref=None,
            sanitized_evidence_ref="evidence://builder-partial-live-test",
            governance_summary_output_ref="artifact://builder-partial-live-summary",
            runtime_assembly=object(),
        )
    )

    assert request.operator_approval.does_not_trigger_live_llm is True
    assert (
        request.operator_approval.metadata["explicit_controlled_live_requested"] is False
    )

    live_preflight = evaluate_controlled_live_llm_preflight(
        productization_gate=request.productization_gate,
        operator_approval=request.operator_approval,
    )

    assert live_preflight["allowed"] is False
    assert "operator_approval_live_llm_boundary_still_true" in live_preflight[
        "blocking_reasons"
    ]
    assert "operator_approval_live_llm_ref_missing" in live_preflight[
        "blocking_reasons"
    ]


def test_workflow_registry_resolves_default_without_executing_runtime() -> None:
    registry = build_default_workflow_registry()
    entry = registry.resolve(workflow_name="controlled-adk-run")

    assert entry.workflow_id == "workflow-controlled-adk-run"
    assert entry.workflow_name == "controlled-adk-run"
    assert entry.no_live_default is True
    assert entry.runtime_assembly_provider is None

    context = WorkflowRegistryBuildContext(
        config_root=Path(".") / "config",
        environment="local",
        profile=None,
        runtime_id="runtime-registry-test",
        workflow_id=entry.workflow_id,
        workflow_name=entry.workflow_name,
        input_payload={"message": "hello"},
    )
    try:
        registry.build_runtime_assembly(entry, context)
    except WorkflowRegistryAssemblyUnavailable as exc:
        assert "no runtime assembly provider" in str(exc)
    else:  # pragma: no cover - defensive assertion.
        raise AssertionError("default registry must not construct runtime assembly")


def test_workflow_registry_default_can_receive_runtime_assembly_provider() -> None:
    registry = build_default_workflow_registry(
        runtime_assembly_provider=_test_runtime_assembly_provider
    )
    entry = registry.resolve(workflow_name="controlled-adk-run")

    assert entry.runtime_assembly_provider is _test_runtime_assembly_provider
    assert entry.metadata["provider_boundary"] == (
        "composition_no_live_runtime_assembly_provider"
    )


def test_cli_entrypoint_keeps_product_boundary() -> None:
    entrypoint_source = ENTRYPOINT_SOURCE.read_text(encoding="utf-8")
    application_source = APPLICATION_SOURCE.read_text(encoding="utf-8")
    chat_source = CHAT_CHANNEL_SOURCE.read_text(encoding="utf-8")
    chat_controls_source = CHAT_CONTROLS_SOURCE.read_text(encoding="utf-8")
    chat_external_readonly_bridge_source = (
        CHAT_EXTERNAL_READONLY_BRIDGE_SOURCE.read_text(encoding="utf-8")
    )
    chat_status_payload_source = CHAT_STATUS_PAYLOAD_SOURCE.read_text(
        encoding="utf-8"
    )
    chat_status_presenter_source = CHAT_STATUS_PRESENTER_SOURCE.read_text(
        encoding="utf-8"
    )
    chat_status_artifacts_source = CHAT_STATUS_ARTIFACTS_SOURCE.read_text(
        encoding="utf-8"
    )
    chat_workflow_requests_source = CHAT_WORKFLOW_REQUESTS_SOURCE.read_text(
        encoding="utf-8"
    )
    chat_references_source = CHAT_REFERENCES_SOURCE.read_text(encoding="utf-8")
    chat_routing_source = CHAT_ROUTING_SOURCE.read_text(encoding="utf-8")
    chat_output_source = CHAT_OUTPUT_SOURCE.read_text(encoding="utf-8")
    chat_turns_source = CHAT_TURNS_SOURCE.read_text(encoding="utf-8")
    chat_operation_dispatch_source = CHAT_OPERATION_DISPATCH_SOURCE.read_text(encoding="utf-8")
    chat_operation_flows_source = CHAT_TASK_WORKFLOWS_SOURCE.read_text(
        encoding="utf-8"
    )
    run_command_source = RUN_COMMAND_SOURCE.read_text(encoding="utf-8")
    run_controls_source = RUN_CONTROLS_SOURCE.read_text(encoding="utf-8")
    run_input_source = RUN_INPUT_SOURCE.read_text(encoding="utf-8")
    run_output_source = RUN_OUTPUT_SOURCE.read_text(encoding="utf-8")
    source = "\n".join(
        [
            application_source,
            chat_source,
            chat_controls_source,
            chat_external_readonly_bridge_source,
            chat_status_payload_source,
            chat_status_presenter_source,
            chat_status_artifacts_source,
            chat_workflow_requests_source,
            chat_references_source,
            chat_routing_source,
            chat_output_source,
            chat_turns_source,
            chat_operation_dispatch_source,
            chat_operation_flows_source,
            run_command_source,
            run_controls_source,
            RUN_GATEWAY_SOURCE.read_text(encoding="utf-8"),
            run_input_source,
            run_output_source,
            RUNTIME_SERVICES_SOURCE.read_text(encoding="utf-8"),
        ]
    )

    assert "runtime_container" not in entrypoint_source
    assert "product_gateway" not in entrypoint_source
    assert "cognition_operation_flows" not in entrypoint_source
    assert "from cognition_cli.application import" in entrypoint_source
    assert "runtime_container" not in application_source
    assert "product_gateway" not in application_source
    assert "cognition_operation_flows" not in application_source

    assert "google.adk" not in source
    assert "scripts." not in source
    assert "dev_controlled_run_executor" not in source
    assert "dev_governance_summary_no_live_productization" not in source
    assert not re.search(r"^\s*(?:from|import)\s+cognition_agent\b", source, re.M)
    assert not re.search(r"^\s*(?:from|import)\s+observability_hub\b", source, re.M)
    assert not re.search(r"^\s*(?:from|import)\s+adk_adapter\b", source, re.M)
    assert "console_scripts" not in source
    assert "[project.scripts]" not in source
    assert "runtime_container.cli_operation_flow_registry" not in source
    assert "runtime_container" not in source
    assert "composition" not in source
    assert "product_gateway." + "operation_flow_" not in source
    assert not re.search(
        r"^\s*from\s+runtime_container\.operation_flow_run_workspace\s+import\b",
        source,
        re.M,
    )
    assert not re.search(
        r"^from\s+product_gateway\.operation_flow_route\s+import\b",
        source,
        re.M,
    )
    assert "product_gateway._operation_flows.route" not in chat_source
    assert "product_gateway._operation_flows.route" not in chat_routing_source
    assert "ProductGatewayCliOperationFlowRouteInputSchema" in chat_routing_source
    operation_flow_private_requests_registry = (
        "cognition_operation_flows." + "_requests.registry"
    )
    operation_flow_private_workflows_plan = "cognition_operation_flows." + "_workflows.plan"
    operation_flow_private_requests_drafts = (
        "cognition_operation_flows." + "_requests.drafts"
    )
    operation_flow_private_requests_builder = (
        "cognition_operation_flows." + "_requests.builder"
    )
    operation_flow_private_core_run_workspace = (
        "cognition_operation_flows." + "_core.run_workspace"
    )

    assert operation_flow_private_requests_registry not in chat_source
    assert "cognition_operation_flows" not in source
    assert operation_flow_private_workflows_plan not in chat_source
    assert "run_operation_flow_plan_workflow" not in chat_source
    assert "run_operation_flow_reference_review_workflow" not in chat_source
    assert "run_operation_flow_config_profile_explain_workflow" not in chat_source
    assert "run_operation_flow_run_workspace_evidence_audit_workflow" not in chat_source
    assert "cognition_operation_flows" not in chat_operation_dispatch_source
    assert "run_operation_flow_plan_workflow" not in chat_operation_dispatch_source
    assert "run_operation_flow_reference_review_workflow" not in chat_operation_dispatch_source
    assert (
        "run_operation_flow_config_profile_explain_workflow" not in chat_operation_dispatch_source
    )
    assert (
        "run_operation_flow_run_workspace_evidence_audit_workflow"
        not in chat_operation_dispatch_source
    )
    assert "run_operation_flow_plan_workflow" not in chat_operation_flows_source
    assert "run_operation_flow_reference_review_workflow" not in chat_operation_flows_source
    assert "run_operation_flow_config_profile_explain_workflow" not in chat_operation_flows_source
    assert (
        "run_operation_flow_run_workspace_evidence_audit_workflow"
        not in chat_operation_flows_source
    )
    assert "execute_cli_operation_flow_workflow" in chat_operation_flows_source
    assert "InternalOperationFlowExecutionInput" not in chat_operation_flows_source
    assert "InternalOperationFlowExecutionResult" not in chat_operation_flows_source
    assert "ProductGatewayCliOperationFlowExecutionInputSchema" in chat_operation_flows_source
    assert "latest_plan_result" not in source
    assert "latest_plan_snapshot" in chat_source
    assert "latest_plan_snapshot" in chat_operation_flows_source
    assert "build_cli_operation_flow_latest_plan_status" in chat_status_payload_source
    assert "persist_cli_operation_flow_status_summary" in chat_status_artifacts_source
    assert "latest_plan_snapshot.reference_context" not in chat_status_payload_source
    assert "latest_plan_snapshot.run_workspace" not in chat_status_payload_source
    assert "latest_plan_snapshot.request" not in chat_status_payload_source
    assert operation_flow_private_requests_drafts not in chat_source
    assert operation_flow_private_requests_builder not in chat_source
    assert (
        "product_gateway._operation_flows.request"
        not in chat_workflow_requests_source
    )
    assert "build_cli_operation_flow_request_draft" not in chat_workflow_requests_source
    assert "request_draft: Any" not in chat_operation_flows_source
    assert "request_draft_input=" in chat_operation_flows_source
    assert operation_flow_private_requests_builder not in chat_workflow_requests_source
    assert operation_flow_private_requests_drafts not in source
    assert "product_gateway._operation_flows.workspace" not in chat_status_artifacts_source
    assert operation_flow_private_core_run_workspace not in source
    assert "product_gateway._operation_flows.controls" not in chat_references_source
    assert "def _chat_status_text" not in chat_source
    assert "def _chat_control_status" not in chat_source
    assert "def _persist_chat_status_summary" not in chat_source
    assert "def _chat_plan_workflow_request" not in chat_source
    assert "def _chat_reference_review_workflow_request" not in chat_source
    assert "def _chat_config_profile_explain_workflow_request" not in chat_source
    assert "def _chat_run_workspace_evidence_audit_workflow_request" not in chat_source
    assert "def _chat_product_gateway_operation_flow_route_projection" not in chat_source
    assert (
        "def _chat_operation_flow_route_from_product_gateway_projection" not in chat_source
    )
    assert "def _chat_banner" not in chat_source
    assert "def _chat_help_text" not in chat_source
    assert "def _chat_turn_text_output" not in chat_source
    assert "def _assistant_text_from_chat_turn" not in chat_source
    assert "def _chat_turn_args" not in chat_source
    assert "def _chat_input_payload" not in chat_source
    assert "def _chat_history_entry" not in chat_source
    assert "def _run_chat_turn" not in chat_source
    assert "def _dispatch_chat_input_turn" not in chat_source
    assert "def _chat_status_text" in chat_status_presenter_source
    assert "def _chat_status_payload" in chat_status_payload_source
    assert "def _chat_control_status" in chat_status_payload_source
    assert "def _persist_chat_status_summary" in chat_status_artifacts_source
    assert "def _chat_plan_control_kwargs" in chat_controls_source
    assert "def _chat_plan_workflow_request" in chat_workflow_requests_source
    assert "def _chat_reference_review_workflow_request" in chat_workflow_requests_source
    assert (
        "def _chat_config_profile_explain_workflow_request"
        in chat_workflow_requests_source
    )
    assert (
        "def _chat_run_workspace_evidence_audit_workflow_request"
        in chat_workflow_requests_source
    )
    assert "def _chat_product_gateway_operation_flow_route_projection" in chat_routing_source
    assert (
        "def _chat_operation_flow_route_from_product_gateway_projection"
        in chat_routing_source
    )
    assert "def _chat_banner" in chat_output_source
    assert "def _chat_help_text" in chat_output_source
    assert "def _chat_turn_text_output" in chat_output_source
    assert "def _assistant_text_from_chat_turn" in chat_output_source
    assert "def _chat_turn_args" in chat_turns_source
    assert "def _chat_input_payload" in chat_turns_source
    assert "def _chat_history_entry" in chat_turns_source
    assert "def _run_chat_turn" in chat_turns_source
    assert "_run_via_product_gateway" in chat_turns_source
    assert "def _dispatch_chat_input_turn" in chat_operation_dispatch_source
    assert "def _dispatch_chat_operation_flow_turn" in chat_operation_flows_source
    assert "def _run_command" in run_command_source
    assert "execute_cognition_run_gateway_request" not in run_command_source
    assert "execute_cognition_run_gateway_request" in RUN_GATEWAY_SOURCE.read_text(
        encoding="utf-8"
    )
    assert "product_gateway.response_summary_projection" not in (
        RUN_GATEWAY_SOURCE.read_text(encoding="utf-8")
    )
    assert "def _load_input_payload" not in run_command_source
    assert "def _cli_blocking_reasons" not in run_command_source
    assert "def _emit_run_output" not in run_command_source
    assert "def _load_input_payload" in run_input_source
    assert "def _cli_blocking_reasons" in run_controls_source
    assert "def _emit_run_output" in run_output_source
    assert "OperationFlowPlanWorkflowRequestCandidate(" not in chat_source
    assert "OperationFlowReferenceReviewWorkflowRequestCandidate(" not in chat_source
    assert "OperationFlowConfigProfileExplainWorkflowRequestCandidate(" not in chat_source
    assert "OperationFlowRunWorkspaceEvidenceAuditWorkflowRequestCandidate(" not in chat_source


def test_cognition_command_is_registered_on_product_runtime_assembly() -> None:
    root_pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    runtime_container_pyproject = tomllib.loads(
        RUNTIME_CONTAINER_PYPROJECT.read_text(encoding="utf-8")
    )
    cli_pyproject = tomllib.loads(CLI_PYPROJECT.read_text(encoding="utf-8"))
    product_runtime_pyproject = tomllib.loads(
        PRODUCT_RUNTIME_ASSEMBLY_PYPROJECT.read_text(encoding="utf-8")
    )

    assert "scripts" not in root_pyproject["project"]
    assert "scripts" not in runtime_container_pyproject["project"]
    assert "scripts" not in cli_pyproject["project"]
    assert product_runtime_pyproject["project"]["scripts"] == {
        "cognition": "product_runtime_assembly.entrypoints.cognition:main",
        "cognition-console": (
            "product_runtime_assembly.entrypoints.cognition_console:main"
        ),
    }
    assert "cognition-system-product-gateway==0.8.3" in cli_pyproject[
        "project"
    ]["dependencies"]
    assert "cognition-system-product-application-assembly==0.8.3" in cli_pyproject[
        "project"
    ]["dependencies"]
    assert "cognition-system-contract-core==0.8.3" in cli_pyproject[
        "project"
    ]["dependencies"]
    assert "cognition-system-config-assembly==0.8.3" in cli_pyproject[
        "project"
    ]["dependencies"]
    assert "cognition-system-config-contexts==0.8.3" in cli_pyproject[
        "project"
    ]["dependencies"]
    assert "cognition-system-runtime-container==0.8.3" not in cli_pyproject[
        "project"
    ]["dependencies"]
    assert "cognition-system-operation-flows==0.8.3" not in cli_pyproject[
        "project"
    ]["dependencies"]
    assert "cognition-system-cli==0.8.3" in product_runtime_pyproject[
        "project"
    ]["dependencies"]
    assert "cognition-system-product-console==0.8.3" in product_runtime_pyproject[
        "project"
    ]["dependencies"]
    assert "cognition-system-product-application-assembly==0.8.3" not in (
        product_runtime_pyproject["project"]["dependencies"]
    )


def _raising_entry_runner(request: ControlledAdkRunRequest) -> dict[str, Any]:
    raise AssertionError("runtime must not be called")


def _run_cognition_subprocess(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "product_runtime_assembly.entrypoints.cognition",
            *args,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _create_audit_source_workspace(workspace_root: Path) -> Path:
    policy = build_cli_operation_flow_run_workspace_policy(
        workspace_root=workspace_root,
        retention_policy="keep",
        cleanup_policy="manual",
        max_write_bytes=65536,
    )
    workspace = create_cli_operation_flow_run_workspace(
        policy=policy,
        workflow_name="operation_flow_config_profile_explain_workflow",
        run_id="cli-config-profile-explain-workflow-entrypoint-audit-turn-001",
    )
    workspace, _ = write_cli_operation_flow_run_workspace_json(
        workspace,
        relative_path="evidence/config_explain_context.json",
        payload={
            "status": "succeeded",
            "does_not_read_raw_config_directly": True,
            "does_not_execute_tools": True,
            "does_not_call_model": True,
            "run_workspace_summary": {"source": "entrypoint_explicit_args"},
        },
        kind="evidence",
        max_write_bytes=65536,
    )
    workspace, _ = write_cli_operation_flow_run_workspace_text(
        workspace,
        relative_path="artifacts/terminal_display.txt",
        text="配置解释结果\n边界：不读取原始配置，不调用模型。\n",
        kind="artifact",
        max_write_bytes=65536,
    )
    workspace, _ = write_cli_operation_flow_run_workspace_json(
        workspace,
        relative_path="results/workflow_result.json",
        payload={
            "workflow": "operation_flow_config_profile_explain_workflow",
            "status": "succeeded",
            "model_call_count": 0,
            "no_live": True,
        },
        kind="result",
        max_write_bytes=65536,
    )
    workspace = finalize_cli_operation_flow_run_workspace(
        workspace,
        status="succeeded",
        metadata={"workflow": "operation_flow_config_profile_explain_workflow"},
    )
    return Path(workspace.workspace_path)


def _assert_output_boundary(output: dict[str, Any]) -> None:
    serialized = json.dumps(output, ensure_ascii=False, sort_keys=True)

    assert "recorded_run" not in output
    assert "agent_shell_audit" not in output
    assert "raw_adk_object" not in serialized
    assert "raw_state_value" not in serialized
    assert "artifact_content" not in serialized
    assert "live_model_payload" not in serialized


def _assert_cognition_run_product_response_summary(
    output: dict[str, Any],
) -> dict[str, Any]:
    summary = output["product_response_summary"]
    validated = validate_product_gateway_response_summary(summary)
    serialized = json.dumps(summary, ensure_ascii=False, sort_keys=True)

    assert validated.model_dump(mode="python") == summary
    assert summary["payload_type"] == "product_gateway_response_summary"
    assert summary["payload_version"] == "product_gateway_response_summary_v1"
    assert summary["entry_kind"] == "cognition_run"
    assert summary["status"] == "success"
    assert summary["product_gateway_response_ref"] is None
    assert summary["readonly"] is True
    assert summary["summary_only"] is True
    assert summary["refs_only"] is True
    assert summary["candidate_only"] is True
    assert summary["execution_enabled"] is False
    assert summary["runtime_permission_granted"] is False
    assert summary["llm_call_enabled"] is False
    assert summary["tool_execution_enabled"] is False
    assert summary["action_execution_enabled"] is False
    assert summary["gateway_enabled"] is False
    assert "raw_prompt" not in serialized
    assert "raw_response" not in serialized
    assert "raw_provider_response" not in serialized
    assert "raw_tool_input" not in serialized
    assert "raw_tool_output" not in serialized
    assert "config_context" not in serialized
    return summary


def _fake_cognition_run_product_response_summary(
    *,
    request_id: str,
) -> dict[str, Any]:
    return validate_product_gateway_response_summary(
        {
            "request_id": request_id,
            "entry_kind": "cognition_run",
            "status": "success",
            "exit_code": 0,
            "product_gateway_response_ref": None,
            "readonly": True,
            "summary_only": True,
            "refs_only": True,
            "candidate_only": True,
            "execution_enabled": False,
            "runtime_permission_granted": False,
            "llm_call_enabled": False,
            "tool_execution_enabled": False,
            "action_execution_enabled": False,
            "gateway_enabled": False,
            "metadata": {
                "source": "test_cognition_cli_entrypoint",
                "product_gateway_response_source": "product_gateway.cognition_run",
            },
        }
    ).model_dump(mode="python")


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


def _external_readonly_archive(evidence_path: str) -> dict[str, object]:
    evidence_ref = (
        "evidence://external-readonly/"
        f"{Path(evidence_path).relative_to('outputs/external-readonly')}"
    )
    return {
        "allow_runtime_fetch": True,
        "allowed_for_model_context": True,
        "blocking_reasons": [],
        "command": "cognition external-readonly fetch",
        "evidence_output_path": evidence_path,
        "evidence_ref": evidence_ref,
        "evidence_written": True,
        "external_network_call_performed": True,
        "governed_summary_facts": _external_governed_summary_facts(
            evidence_path,
            evidence_ref=evidence_ref,
        ),
        "raw_html_included": False,
        "raw_response_included": False,
        "response_headers_included": False,
        "runtime": {
            "allowed_for_model_context": True,
            "blocking_reasons": [],
            "content_hash": _sha256(_external_excerpt()),
            "external_network_call_performed": True,
            "runtime_fetch_performed": True,
            "sanitized_excerpt_preview": _external_excerpt(),
            "source_urls": ["https://example.com/"],
            "status": "completed",
            "total_excerpt_chars": len(_external_excerpt()),
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


def _external_governed_summary_facts(
    evidence_path: str,
    *,
    evidence_ref: str,
) -> dict[str, object]:
    fact = _external_excerpt()
    content_hash = _sha256(fact)
    return {
        "payload_type": "external_readonly_governed_summary_facts",
        "payload_version": "external_readonly_governed_summary_facts_v1",
        "status": "ready",
        "evidence_ref": evidence_ref,
        "evidence_output_path": evidence_path,
        "source_url_host": "example.com",
        "source_url_scheme": "https",
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "evidence_written": True,
        "content_hash": content_hash,
        "facts": [
            {
                "fact_ref": "external-readonly-governed-summary-fact://cli-chat-1",
                "fact_text": fact,
                "fact_index": 1,
                "evidence_ref": evidence_ref,
                "source_url_host": "example.com",
                "content_hash": content_hash,
                "metadata": {"citation_index": 1},
            }
        ],
        "fact_count": 1,
        "total_fact_chars": len(fact),
        "blocking_reasons": [],
        "warnings": [],
        "generation_policy_ref": (
            "policy://external-readonly/governed-summary-facts/minimal-v1"
        ),
        "metadata": {"source_package": "external_readonly"},
    }


def _external_excerpt() -> str:
    return "Example Domain sanitized excerpt from CLI chat evidence."


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fake_chat_entry_runner(request: ControlledAdkRunRequest) -> dict[str, Any]:
    return _fake_chat_entry_result(live=False, request=request)


def _fake_chat_entry_result(
    *,
    live: bool,
    preview: str = "controlled live output",
    display: str | None = None,
    request: ControlledAdkRunRequest | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "adk_run_allowed": True,
        "adk_run_performed": True,
        "execution_performed": True,
        "blocking_reasons": [],
        "warnings": [],
        "final_preflight": {"allowed": True, "execution_scope": "test-chat"},
        "controlled_live_llm_preflight": {"allowed": live},
        "live_llm_call_performed": live,
        "ollama_call_performed": live,
        "llm_invocation_call_allowed": True,
        "llm_invocation_call_attempted": live,
        "llm_invocation_runtime_call_performed": live,
        "llm_invocation_failure_type": None if live else "live_disabled",
    }
    if request is not None:
        gate = request.productization_gate
        result["governance_summary_payload_ref"] = (
            gate.governance_summary_output_ref
        )
        result["governance_summary_output_ref"] = gate.governance_summary_output_ref
        result["sanitized_evidence_ref"] = gate.sanitized_evidence_ref
        result["audit_ref"] = gate.audit_ref
    if live:
        result["llm_invocation_readonly_facts"] = {"result": {}}
        result["llm_invocation_readonly_facts"]["result"][
            "sanitized_response_preview"
        ] = preview
        if display is not None:
            result["llm_invocation_readonly_facts"]["result"][
                "sanitized_response_display"
            ] = display
    return result


def _build_allowed_request(
    args: Any,
    input_payload: dict[str, Any],
) -> ControlledAdkRunRequest:
    registry = WorkflowRegistry(
        entries=[
            WorkflowRegistryEntry(
                workflow_id=args.workflow_id,
                workflow_name=args.workflow_name,
                description="test controlled no-live workflow",
                runtime_assembly_provider=_test_runtime_assembly_provider,
            )
        ]
    )
    return build_controlled_adk_run_request_from_registry(
        build_input=ControlledAdkRunRequestBuildInput(
            config_root=Path(".") / "config",
            environment="local",
            profile=None,
            runtime_id=args.runtime_id,
            invocation_id=args.invocation_id,
            workflow_id=args.workflow_id,
            workflow_name=args.workflow_name,
            input_payload=dict(input_payload),
            operator_approved=args.operator_approved,
            approval_ref=args.approval_ref,
            audit_ref=args.audit_ref,
            sanitized_evidence_ref=args.sanitized_evidence_ref,
            governance_summary_output_ref=args.governance_summary_output_ref,
            evidence_id=f"cognition-cli-{args.runtime_id}",
            llm_invocation_service=NoLiveGovernedLlmInvocationService(),
        ),
        workflow_registry=registry,
    )


def _build_allowed_live_request(
    args: Any,
    input_payload: dict[str, Any],
) -> ControlledAdkRunRequest:
    registry = WorkflowRegistry(
        entries=[
            WorkflowRegistryEntry(
                workflow_id=args.workflow_id,
                workflow_name=args.workflow_name,
                description="test controlled-live workflow",
                runtime_assembly_provider=_test_runtime_assembly_provider,
            )
        ]
    )
    return build_controlled_adk_run_request_from_registry(
        build_input=ControlledAdkRunRequestBuildInput(
            config_root=Path(".") / "config",
            environment="local",
            profile=None,
            runtime_id=args.runtime_id,
            invocation_id=args.invocation_id,
            workflow_id=args.workflow_id,
            workflow_name=args.workflow_name,
            input_payload=dict(input_payload),
            operator_approved=args.operator_approved,
            approval_ref=args.approval_ref,
            audit_ref=args.audit_ref,
            request_live_llm=True,
            request_ollama=True,
            allow_live_llm=True,
            allow_ollama=True,
            live_llm_approval_ref="approval://cli-live-llm-test-182",
            sanitized_evidence_ref=args.sanitized_evidence_ref,
            governance_summary_output_ref=args.governance_summary_output_ref,
            evidence_id=f"cognition-cli-{args.runtime_id}",
            llm_invocation_service=FakeLiveGovernedLlmInvocationService(),
            agent_shell_live_client=FakeAgentShellLiveClient(),
        ),
        workflow_registry=registry,
    )


def _test_runtime_assembly_provider(
    context: WorkflowRegistryBuildContext,
) -> AdkWorkflowRunnerRuntimeAssembly:
    return _runtime_assembly(workflow_name=context.workflow_name)


def _runtime_assembly(*, workflow_name: str) -> AdkWorkflowRunnerRuntimeAssembly:
    from google.adk.agents.context import Context
    from google.adk.events import Event
    from google.adk.events.event import NodeInfo
    from google.adk.workflow import START, BaseNode, Workflow
    from google.genai import types

    class ControlledRunNode(BaseNode):
        async def _run_impl(self, *, ctx: Context, node_input: Any):
            version = await ctx.save_artifact(
                "cognition-cli-controlled-run-output.txt",
                types.Part(text="cognition cli sanitized artifact body"),
                custom_metadata={"source": "test_cognition_cli_entrypoint"},
            )
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                node_info=NodeInfo(path=ctx.node_path),
                output={
                    "artifact_version": version,
                    "run_config_source": ctx.run_config.custom_metadata["source"],
                },
            )

    workflow = Workflow(
        name=workflow_name.replace("-", "_"),
        edges=[(START, ControlledRunNode(name="controlled_run_node"))],
    )
    assembly_options = AdkWorkflowRunnerAssemblyOptions(
        app_name="cognition_cli_test",
        user_id="cognition-cli-test-user",
        workflow_name=workflow_name,
        service_bundle_options=AdkRunnerServiceBundleOptions(source="in_memory"),
        run_config_options=AdkRunConfigOptions(
            max_llm_calls=1,
            custom_metadata={"source": "cognition_cli.entrypoints.cognition"},
            streaming_mode="none",
        ),
        metadata={"entry": "cognition_cli.entrypoints.cognition"},
    )
    return build_adk_workflow_runner_runtime(
        options=RuntimeCompositionOptions(
            config_root=Path(".") / "config",
            environment="local",
        ),
        workflow=workflow,
        assembly_options=assembly_options,
    )
