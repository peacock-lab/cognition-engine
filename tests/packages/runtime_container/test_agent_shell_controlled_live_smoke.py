from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from google.adk.models.lite_llm import LiteLLMClient

from runtime_container.live_smoke.agent_shell_controlled_live import (
    build_agent_shell_controlled_live_smoke_result,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_CONTAINER_ROOT = REPO_ROOT / "packages" / "runtime_container"
CLI_PACKAGE_ROOT = REPO_ROOT / "packages" / "cli"
SMOKE_SOURCE = (
    RUNTIME_CONTAINER_ROOT
    / "src"
    / "runtime_container"
    / "live_smoke"
    / "agent_shell_controlled_live.py"
)


def test_agent_shell_controlled_live_smoke_is_skipped_without_gate(
    tmp_path: Path,
) -> None:
    config_root = _write_agent_shell_runtime_config(tmp_path)
    fake_client = _FakeAsyncLiteLlmClient("unused")

    result = build_agent_shell_controlled_live_smoke_result(
        env={"CE_CONFIG_ROOT": str(config_root)},
        live_client=fake_client,
    )

    assert result["status"] == "skipped"
    assert result["success"] is False
    assert result["failure_type"] == "live_disabled"
    assert result["live_enabled"] is False
    assert result["runtime_call_performed"] is False
    assert result["call_attempted"] is False
    assert fake_client.calls == []
    assert result["agent_shell_audit"]["controlled_live_smoke_enabled"] is False


def test_agent_shell_controlled_live_smoke_runs_fake_client_with_env_overrides(
    tmp_path: Path,
) -> None:
    config_root = _write_agent_shell_runtime_config(tmp_path)
    fake_client = _FakeAsyncLiteLlmClient("controlled live smoke completed")

    result = build_agent_shell_controlled_live_smoke_result(
        env={
            "CE_ENABLE_LIVE_LLM_SMOKE": "1",
            "CE_CONFIG_ROOT": str(config_root),
            "CE_ENVIRONMENT": "local",
            "CE_LIVE_LLM_MODEL": "ollama/gemma4-pro:latest",
            "OLLAMA_API_BASE": "http://127.0.0.1:11434",
            "CE_MODEL_TIMEOUT_SECONDS": "9",
            "CE_MODEL_TEMPERATURE": "0",
            "CE_MODEL_MAX_TOKENS": "16",
            "CE_AGENT_SHELL_SMOKE_INPUT": "very-private-task-input",
        },
        live_client=fake_client,
    )
    serialized = json.dumps(result, ensure_ascii=False)

    assert result["status"] == "success"
    assert result["success"] is True
    assert result["failure_type"] is None
    assert result["runtime_call_performed"] is True
    assert result["call_attempted"] is True
    assert result["config"]["model"] == "ollama/gemma4-pro:latest"
    assert result["config"]["ollama_api_base"] == "http://127.0.0.1:11434"
    assert result["config"]["timeout_seconds"] == 9
    assert result["config"]["temperature"] == 0
    assert result["config"]["max_tokens"] == 16
    assert result["agent_shell_audit"]["controlled_live_smoke_enabled"] is True
    assert fake_client.calls
    assert fake_client.calls[0]["model"] == "ollama/gemma4-pro:latest"
    assert fake_client.calls[0]["api_base"] == "http://127.0.0.1:11434"
    assert fake_client.calls[0]["timeout"] == 9
    assert fake_client.calls[0]["temperature"] == 0
    assert fake_client.calls[0]["max_tokens"] == 16
    assert "very-private-task-input" not in serialized
    assert "controlled live smoke completed" not in serialized
    assert result["does_not_store_prompt"] is True
    assert result["does_not_store_messages"] is True
    assert result["does_not_store_raw_response"] is True
    assert result["raw_provider_payload_included"] is False


def test_agent_shell_controlled_live_smoke_classifies_provider_unavailable(
    tmp_path: Path,
) -> None:
    config_root = _write_agent_shell_runtime_config(tmp_path)
    fake_client = _FailingAsyncLiteLlmClient(
        RuntimeError("provider unavailable: raw_response carried secret token")
    )

    result = build_agent_shell_controlled_live_smoke_result(
        env={
            "CE_ENABLE_LIVE_LLM_SMOKE": "1",
            "CE_CONFIG_ROOT": str(config_root),
            "CE_LIVE_LLM_MODEL": "ollama/gemma4-pro:latest",
            "OLLAMA_API_BASE": "http://127.0.0.1:11434",
        },
        live_client=fake_client,
    )
    error_text = " ".join(
        str(value or "")
        for value in (
            result["error_message_sanitized"],
            result["agent_shell_audit"]["error_message_sanitized"],
        )
    )

    assert result["status"] == "failure"
    assert result["success"] is False
    assert result["failure_type"] == "provider_unavailable"
    assert result["runtime_call_performed"] is True
    assert result["call_attempted"] is True
    assert "raw_response" not in error_text
    assert "secret" not in error_text
    assert "token" not in error_text


def test_agent_shell_controlled_live_smoke_module_keeps_runtime_boundary() -> None:
    source = SMOKE_SOURCE.read_text(encoding="utf-8")
    pyproject = tomllib.loads(
        (RUNTIME_CONTAINER_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    product_runtime_pyproject = tomllib.loads(
        (
            REPO_ROOT
            / "packages"
            / "product_runtime_assembly"
            / "pyproject.toml"
        ).read_text(encoding="utf-8")
    )

    assert re.search(r"^\s*(?:from|import)\s+adk_adapter\b", source, re.M) is None
    assert re.search(r"^\s*(?:from|import)\s+google\.adk\b", source, re.M) is None
    assert re.search(r"^\s*(?:from|import)\s+litellm\b", source, re.M) is None
    assert "raw_provider_payload_included" in source
    assert "scripts" not in pyproject["project"]
    assert product_runtime_pyproject["project"]["scripts"] == {
        "cognition": "product_runtime_assembly.entrypoints.cognition:main",
        "cognition-console": (
            "product_runtime_assembly.entrypoints.cognition_console:main"
        ),
    }


def _write_agent_shell_runtime_config(tmp_path: Path) -> Path:
    config_root = tmp_path / "config"
    (config_root / "base").mkdir(parents=True)
    (config_root / "env").mkdir()
    (config_root / "base" / "runtime.yaml").write_text(
        """
runtime:
  runtime_name: agent-shell-controlled-live-smoke-runtime
workflow_execution:
  workflow_name: agent-shell-controlled-live-smoke-workflow
node_execution: {}
resume_policy: {}
event_policy: {}
artifact_policy: {}
adapter_selection:
  default_runtime_adapter: adk
  adk_adapter_enabled: true
  litellm_adapter_enabled: true
adk_run_config:
  max_llm_calls: 2
  streaming_mode: none
  custom_metadata:
    source: agent-shell-controlled-live-smoke-config
live_llm:
  profile: adk_litellm_ollama
  model_name: ollama/config-default:latest
  ollama_api_base: http://127.0.0.1:11434
  timeout_seconds: 7
  temperature: 0
  max_tokens: 12
  enabled_by_default: false
  metadata:
    source: test-config
""",
        encoding="utf-8",
    )
    return config_root


class _FakeAsyncLiteLlmClient(LiteLLMClient):
    def __init__(self, content: str) -> None:
        self._content = content
        self.calls: list[dict[str, object]] = []

    async def acompletion(self, *, model: str, messages, tools, **kwargs):
        from litellm import ModelResponse

        self.calls.append(
            {
                "model": model,
                "message_count": len(messages),
                "tools": tools,
                **kwargs,
            }
        )
        return ModelResponse(
            model=model,
            choices=[
                {
                    "finish_reason": "stop",
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": self._content,
                    },
                }
            ],
        )


class _FailingAsyncLiteLlmClient(LiteLLMClient):
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def acompletion(self, *, model: str, messages, tools, **kwargs):
        raise self._exc
