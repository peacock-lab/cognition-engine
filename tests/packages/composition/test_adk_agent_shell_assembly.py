from __future__ import annotations

from pathlib import Path
import asyncio

from adk_adapter import (
    AdkAgentShellOptions,
    AdkRunnerServiceBundle,
    create_no_live_adk_llm_agent,
)
from google.adk.models.lite_llm import LiteLLMClient
from composition import (
    AdkAgentShellAssembly,
    AdkAgentShellAssemblyOptions,
    build_adk_agent_shell_assembly_from_runtime_config,
    build_adk_agent_shell_run_evidence,
    build_controlled_live_adk_agent_shell_profile_from_runtime_config,
    run_controlled_live_adk_agent_shell_smoke,
    run_no_live_adk_agent_shell_product_entry,
)
from composition.runtime import RuntimeCompositionOptions


def test_adk_agent_shell_assembly_builds_native_agent_service() -> None:
    service_bundle = AdkRunnerServiceBundle.in_memory(
        app_name="test_agent_shell_app",
        user_id="test-user",
    )
    assembly = AdkAgentShellAssembly(
        service_bundle=service_bundle,
        assembly_options=AdkAgentShellAssemblyOptions(
            app_name="test_agent_shell_app",
            user_id="test-user",
            agent_name="task_quality_shell",
            model="gemini-2.0-flash",
            instruction="Review governed task evidence.",
            metadata={"source": "composition-test"},
        ),
    )

    agent_service = assembly.build_agent_service()
    runner = agent_service.create_runner()
    metadata = assembly.metadata()

    assert runner.agent.name == "task_quality_shell"
    assert runner.artifact_service is service_bundle.adk_artifact_service
    assert runner.session_service is service_bundle.adk_session_service
    assert metadata["assembly"] == "composition.adk_agent_shell_assembly"
    assert metadata["agent_type"] == "LlmAgent"
    assert metadata["agent_name"] == "task_quality_shell"
    assert metadata["observability_candidate"] == (
        "observability_hub.adk_agent_shell_intake"
    )
    assert metadata["assembly_options"]["plugin_bundle_options"]["source"] == "empty"
    assert metadata["plugin_bundle"]["plugin_count"] == 0
    assert metadata["plugin_bundle"]["raw_plugin_object_included"] is False
    assert metadata["assembly_options"]["instruction_length"] == len(
        "Review governed task evidence."
    )
    assert "instruction" not in metadata["assembly_options"]


def test_adk_agent_shell_assembly_uses_runtime_config_run_config(
    tmp_path: Path,
) -> None:
    config_root = tmp_path / "config"
    (config_root / "base").mkdir(parents=True)
    (config_root / "env").mkdir()
    (config_root / "base" / "runtime.yaml").write_text(
        """
runtime:
  runtime_name: agent-shell-runtime
workflow_execution:
  workflow_name: agent-shell-workflow
node_execution: {}
resume_policy: {}
event_policy: {}
artifact_policy: {}
adapter_selection:
  default_runtime_adapter: adk
  adk_adapter_enabled: true
adk_run_config:
  max_llm_calls: 3
  streaming_mode: none
  custom_metadata:
    source: agent-shell-config
""",
        encoding="utf-8",
    )

    assembly = build_adk_agent_shell_assembly_from_runtime_config(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        assembly_options=AdkAgentShellAssemblyOptions(
            agent_name="configured_agent_shell",
            model="gemini-2.0-flash",
            instruction="Review configured evidence.",
        ),
    )

    assert assembly.assembly_options.run_config_options is not None
    assert assembly.assembly_options.run_config_options.max_llm_calls == 3
    assert assembly.assembly_options.run_config_options.streaming_mode == "none"
    assert assembly.assembly_options.run_config_options.custom_metadata == {
        "source": "agent-shell-config"
    }


def test_adk_agent_shell_assembly_builds_run_evidence_without_live_call() -> None:
    agent = create_no_live_adk_llm_agent(
        AdkAgentShellOptions(
            name="no_live_composed_shell",
            model="adk-no-live/composed-shell",
            instruction="Review composed governed evidence.",
            mode="chat",
        ),
        response_text="Composed no-live review completed.",
    )
    assembly = AdkAgentShellAssembly(
        agent=agent,
        assembly_options=AdkAgentShellAssemblyOptions(
            app_name="composed_agent_shell",
            user_id="test-user",
            agent_name="no_live_composed_shell",
            model="adk-no-live/composed-shell",
            instruction="Review composed governed evidence.",
            mode="chat",
        ),
    )
    agent_service = assembly.build_agent_service()

    run_result = asyncio.run(
        agent_service.run_text_async(
            text="Review composed task evidence.",
            invocation_id="composed-agent-invocation-001",
        )
    )
    evidence_assembly = build_adk_agent_shell_run_evidence(
        agent_run_result=run_result,
        agent_shell_assembly=assembly,
    )

    evidence = evidence_assembly.agent_shell_evidence
    assert evidence.runtime_kind == "adk_agent_shell"
    assert evidence.agent_name == "no_live_composed_shell"
    assert evidence.status == "success"
    assert evidence.event_summary["event_count"] >= 2
    assert evidence.no_live_execution_observed is True
    assert evidence.session_summary["session_observed"] is True
    assert evidence.invocation_summary["requested_invocation_id"] == (
        "composed-agent-invocation-001"
    )
    assert evidence_assembly.assembly_metadata["assembly"] == (
        "composition.adk_agent_shell_assembly"
    )


def test_no_live_agent_shell_product_entry_builds_governance_audit(
    tmp_path: Path,
) -> None:
    config_root = tmp_path / "config"
    (config_root / "base").mkdir(parents=True)
    (config_root / "env").mkdir()
    (config_root / "base" / "runtime.yaml").write_text(
        """
runtime:
  runtime_name: agent-shell-product-runtime
workflow_execution:
  workflow_name: agent-shell-product-workflow
node_execution: {}
resume_policy: {}
event_policy: {}
artifact_policy: {}
adapter_selection:
  default_runtime_adapter: adk
  adk_adapter_enabled: true
adk_run_config:
  max_llm_calls: 2
  streaming_mode: none
  custom_metadata:
    source: agent-shell-product-config
""",
        encoding="utf-8",
    )

    product_run = run_no_live_adk_agent_shell_product_entry(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        input_text="Review product entry evidence.",
        invocation_id="agent-shell-inv-product-001",
        runtime_id="runtime-agent-shell-product-001",
    )

    audit = product_run.to_governance_audit()

    assert audit["agent_shell_evidence_ref"].startswith(
        "adk-agent-shell-evidence://adk-agent-shell-evidence-"
    )
    assert audit["agent_shell_run_ref"] == (
        "adk-agent-shell-run://agent-shell-inv-product-001"
    )
    assert audit["agent_name"] == "cognition_agent_shell"
    assert audit["agent_type"] == "LlmAgent"
    assert audit["app_name"] == "cognition_agent_shell_product_entry"
    assert audit["status"] == "success"
    assert audit["event_count"] >= 2
    assert audit["no_live_execution_observed"] is True
    assert audit["runtime_call_performed"] is True
    assert audit["failure_type"] is None
    assert audit["readonly_facts_embedded"] is False
    assert audit["does_not_store_prompt"] is True
    assert audit["does_not_store_raw_response"] is True
    assert audit["raw_adk_object_included"] is False
    assert audit["raw_adk_event_included"] is False
    assert audit["raw_adk_session_included"] is False


def test_controlled_live_agent_shell_profile_uses_runtime_live_options(
    tmp_path: Path,
) -> None:
    config_root = _write_agent_shell_runtime_config(tmp_path)

    profile = build_controlled_live_adk_agent_shell_profile_from_runtime_config(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        metadata={"smoke": "test"},
    )
    metadata = profile.to_metadata()

    assert profile.live_options.model == "ollama/gemma4-pro:latest"
    assert profile.live_options.ollama_api_base == "http://127.0.0.1:11434"
    assert profile.live_options.timeout_seconds == 7
    assert profile.live_options.temperature == 0
    assert profile.live_options.max_tokens == 12
    assert metadata["live_options"]["live_service_profile"] == "adk_litellm_ollama"
    assert metadata["live_options"]["live_options_source"] == (
        "config_contexts.runtime.RuntimeLiveLlmConfigView"
    )
    assert metadata["live_options"]["custom_client_injected"] is False
    assert "instruction" not in metadata


def test_controlled_live_agent_shell_profile_accepts_explicit_live_overrides(
    tmp_path: Path,
) -> None:
    config_root = _write_agent_shell_runtime_config(tmp_path)

    profile = build_controlled_live_adk_agent_shell_profile_from_runtime_config(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        model_name="ollama/override:latest",
        ollama_api_base="http://127.0.0.1:11555",
        timeout_seconds=11,
        temperature=0.2,
        max_tokens=21,
    )
    metadata = profile.to_metadata()

    assert profile.assembly_options.model == "ollama/override:latest"
    assert profile.live_options.model == "ollama/override:latest"
    assert profile.live_options.ollama_api_base == "http://127.0.0.1:11555"
    assert profile.live_options.timeout_seconds == 11
    assert profile.live_options.temperature == 0.2
    assert profile.live_options.max_tokens == 21
    assert metadata["live_options"]["model"] == "ollama/override:latest"
    assert metadata["metadata"]["config_model_name"] == "ollama/gemma4-pro:latest"
    assert metadata["metadata"]["live_options_override_applied"] is True


def test_controlled_live_agent_shell_smoke_is_disabled_by_default(
    tmp_path: Path,
) -> None:
    config_root = _write_agent_shell_runtime_config(tmp_path)
    fake_client = _FakeAsyncLiteLlmClient("unused")

    result = run_controlled_live_adk_agent_shell_smoke(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        input_text="Review product entry evidence.",
        invocation_id="agent-shell-live-disabled-001",
        runtime_id="runtime-agent-shell-live-disabled-001",
        live_client=fake_client,
    )
    audit = result.to_governance_audit()

    assert result.success is False
    assert result.failure_type == "live_disabled"
    assert result.runtime_call_performed is False
    assert fake_client.calls == []
    assert audit["controlled_live"] is True
    assert audit["controlled_live_smoke_enabled"] is False
    assert audit["failure_type"] == "live_disabled"
    assert audit["does_not_store_prompt"] is True
    assert audit["does_not_store_raw_response"] is True


def test_controlled_live_agent_shell_smoke_runs_fake_provider_success(
    tmp_path: Path,
) -> None:
    config_root = _write_agent_shell_runtime_config(tmp_path)
    fake_client = _FakeAsyncLiteLlmClient("Controlled live shell completed.")

    result = run_controlled_live_adk_agent_shell_smoke(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        input_text="Review product entry evidence.",
        invocation_id="agent-shell-live-success-001",
        runtime_id="runtime-agent-shell-live-success-001",
        live_enabled=True,
        live_client=fake_client,
    )
    audit = result.to_governance_audit()

    assert result.success is True
    assert result.failure_type is None
    assert result.runtime_call_performed is True
    assert fake_client.calls
    assert fake_client.calls[0]["model"] == "ollama/gemma4-pro:latest"
    assert fake_client.calls[0]["api_base"] == "http://127.0.0.1:11434"
    assert fake_client.calls[0]["timeout"] == 7
    assert fake_client.calls[0]["max_tokens"] == 12
    assert audit["controlled_live_smoke_enabled"] is True
    assert audit["runtime_call_performed"] is True
    assert audit["failure_type"] is None
    assert audit["live_profile"]["live_service_profile"] == "adk_litellm_ollama"
    assert audit["raw_adk_object_included"] is False
    assert audit["raw_adk_event_included"] is False
    assert audit["raw_adk_session_included"] is False


def test_controlled_live_agent_shell_smoke_classifies_provider_unavailable(
    tmp_path: Path,
) -> None:
    config_root = _write_agent_shell_runtime_config(tmp_path)
    fake_client = _FailingAsyncLiteLlmClient(
        RuntimeError("provider unavailable: raw_response carried secret token")
    )

    result = run_controlled_live_adk_agent_shell_smoke(
        options=RuntimeCompositionOptions(config_root=config_root, environment="local"),
        input_text="Review product entry evidence.",
        invocation_id="agent-shell-live-provider-failure-001",
        runtime_id="runtime-agent-shell-live-provider-failure-001",
        live_enabled=True,
        live_client=fake_client,
    )
    audit = result.to_governance_audit()

    assert result.success is False
    assert result.failure_type == "provider_unavailable"
    assert result.runtime_call_performed is True
    assert result.call_attempted is True
    assert "raw_response" not in (result.error_message_sanitized or "")
    assert "secret" not in (result.error_message_sanitized or "")
    assert "token" not in (result.error_message_sanitized or "")
    assert audit["failure_type"] == "provider_unavailable"
    assert audit["controlled_live_smoke_enabled"] is True


def _write_agent_shell_runtime_config(tmp_path: Path) -> Path:
    config_root = tmp_path / "config"
    (config_root / "base").mkdir(parents=True)
    (config_root / "env").mkdir()
    (config_root / "base" / "runtime.yaml").write_text(
        """
runtime:
  runtime_name: agent-shell-controlled-live-runtime
workflow_execution:
  workflow_name: agent-shell-controlled-live-workflow
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
    source: agent-shell-controlled-live-config
live_llm:
  profile: adk_litellm_ollama
  model_name: ollama/gemma4-pro:latest
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
