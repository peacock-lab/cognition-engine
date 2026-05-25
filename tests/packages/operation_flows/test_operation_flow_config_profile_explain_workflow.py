from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from cognition_operation_flows._workflows.config_profile_explain import (
    OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    OperationFlowConfigProfileExplainWorkflowRequestCandidate,
    detect_operation_flow_config_profile_explain_request,
    run_operation_flow_config_profile_explain_workflow,
)
from cognition_operation_flows._core.control import OPERATION_FLOW_CONTROL_STAGES


class FakeToolExposure:
    default_profile = "readonly_reference"

    def to_profile_config(self) -> dict[str, object]:
        return {
            "profiles": {
                "readonly_reference": {
                    "source_ref": "default://runtime-config/tool-exposure",
                    "toolsets": [
                        {
                            "toolset_name": "local_reference_tools",
                            "toolset_kind": "toolset",
                            "source_ref": "local-reference-reader://workspace",
                            "allowlist_tool_names": ["local_reference_reader"],
                            "tool_filter": ["local_reference_reader"],
                            "readonly_only": True,
                            "max_risk_level": "low",
                            "reference_reader": {
                                "allowed_roots": ["tasks", "docs"],
                                "allowed_suffixes": [".md", ".txt"],
                                "max_bytes": 32768,
                                "max_chars": 6000,
                            },
                        }
                    ],
                }
            }
        }


class FakeRunWorkspace:
    enabled_by_default = False

    def to_policy_kwargs(self) -> dict[str, object]:
        return {
            "workspace_root": ".cognition-runs",
            "retention_policy": "keep",
            "cleanup_policy": "manual",
            "max_write_bytes": 65536,
        }


def test_config_profile_explain_detector_matches_config_intent() -> None:
    assert detect_operation_flow_config_profile_explain_request(
        "请解释当前配置为什么这样生效，尤其是 tool exposure 的覆盖关系"
    )
    assert detect_operation_flow_config_profile_explain_request(
        "run workspace 为什么没有启用"
    )
    assert (
        detect_operation_flow_config_profile_explain_request("请修改配置文件，打开 live LLM")
        is False
    )
    assert (
        detect_operation_flow_config_profile_explain_request("请打开 Agent runtime")
        is False
    )


def test_no_live_config_profile_explain_outputs_sanitized_config_context() -> None:
    result = run_operation_flow_config_profile_explain_workflow(
        OperationFlowConfigProfileExplainWorkflowRequestCandidate(
            user_text="请解释当前配置为什么这样生效，尤其是 tool exposure 和 live LLM",
            chat_session_id="cli-config-explain-test",
            turn_index=1,
            config_context=_fake_config_context(),
            config_root="config",
            environment="local",
            approval_ref="approval://config-explain-test",
            audit_ref="audit://config-explain-test",
            sanitized_evidence_ref="evidence://config-explain-test",
        )
    )

    assert result.fail_safe is False
    assert result.no_live is True
    assert result.model_call_count == 0
    assert result.explain_context.status == "succeeded"
    assert result.explain_context.config_context_available is True
    assert result.task_run_context is not None
    assert result.task_run_context.status == "succeeded"
    assert result.task_run_context.workflow_name == (
        OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME
    )
    assert result.task_run_context.stages == OPERATION_FLOW_CONTROL_STAGES
    assert "配置解释结果" in result.terminal_display_text
    assert "覆盖关系" in result.terminal_display_text
    assert "tool exposure profile: readonly_reference" in result.terminal_display_text
    assert "reference-reader: enabled" in result.terminal_display_text
    assert "不执行工具" in result.terminal_display_text
    assert "approval://config-explain-test" not in result.terminal_display_text
    assert "audit://config-explain-test" not in result.terminal_display_text
    assert "raw config" not in result.terminal_display_text


def test_config_profile_explain_run_workspace_writes_evidence(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "cli-runs"

    result = run_operation_flow_config_profile_explain_workflow(
        OperationFlowConfigProfileExplainWorkflowRequestCandidate(
            user_text="请解释 run workspace 为什么启用，以及配置来源",
            chat_session_id="cli-config-explain-workspace-test",
            turn_index=1,
            config_context=_fake_config_context(),
            config_root="config",
            environment="local",
            entrypoint_explicit_args={
                "enable_run_workspace": True,
                "run_workspace_root": str(workspace_root),
            },
            run_workspace_root=str(workspace_root),
            run_workspace_enabled=True,
            run_workspace_retention_policy="keep",
            run_workspace_cleanup_policy="manual",
            run_workspace_max_write_bytes=65536,
        )
    )

    assert result.run_workspace is not None
    workspace_path = Path(result.run_workspace.workspace_path)
    context_payload = json.loads(
        (workspace_path / "evidence" / "config_explain_context.json").read_text(
            encoding="utf-8"
        )
    )
    result_payload = json.loads(
        (workspace_path / "results" / "workflow_result.json").read_text(
            encoding="utf-8"
        )
    )
    terminal_display = (
        workspace_path / "artifacts" / "terminal_display.txt"
    ).read_text(encoding="utf-8")

    assert context_payload["status"] == "succeeded"
    assert context_payload["redaction_applied"] is True
    assert context_payload["does_not_read_raw_config_directly"] is True
    assert context_payload["does_not_execute_tools"] is True
    assert context_payload["does_not_call_model"] is True
    assert context_payload["run_workspace_summary"]["source"] == "entrypoint_explicit_args"
    assert result_payload["workflow"] == OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME
    assert result_payload["status"] == "succeeded"
    assert result_payload["model_call_count"] == 0
    assert "配置解释结果" in terminal_display


def _fake_config_context() -> SimpleNamespace:
    return SimpleNamespace(
        tool_exposure=FakeToolExposure(),
        run_workspace=FakeRunWorkspace(),
        live_llm=SimpleNamespace(
            profile="adk_litellm_ollama",
            model_name="ollama/gemma4-pro:latest",
            ollama_api_base="http://127.0.0.1:11434",
            timeout_seconds=45,
        ),
    )
