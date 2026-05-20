from __future__ import annotations

import asyncio
from typing import Any

from adk_adapter import (
    AdkAgentControlledLiveOptions,
    AdkAgentServiceAdapter,
    AdkAgentShellOptions,
    AdkRunnerServiceBundle,
    create_adk_llm_agent,
    create_controlled_live_adk_llm_agent,
    create_no_live_adk_llm_agent,
)
from google.adk.agents import ParallelAgent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.lite_llm import LiteLLMClient


def test_create_adk_llm_agent_builds_native_agent_shell() -> None:
    agent = create_adk_llm_agent(
        AdkAgentShellOptions(
            name="task_quality_shell",
            model="gemini-2.0-flash",
            instruction="Review governed task evidence.",
            description="Task quality shell",
            mode="single_turn",
            metadata={"source": "test"},
        )
    )

    assert type(agent).__name__ == "LlmAgent"
    assert agent.name == "task_quality_shell"
    assert agent.model == "gemini-2.0-flash"
    assert agent.instruction == "Review governed task evidence."
    assert agent.mode == "single_turn"


def test_agent_service_injects_runner_services_without_live_model_call() -> None:
    agent = create_adk_llm_agent(
        AdkAgentShellOptions(
            name="task_quality_shell",
            model="gemini-2.0-flash",
            instruction="Review governed task evidence.",
        )
    )
    service_bundle = AdkRunnerServiceBundle.in_memory(
        app_name="test_adk_agent_shell",
        user_id="test-user",
    )

    adapter = AdkAgentServiceAdapter(
        agent=agent,
        app_name="test_adk_agent_shell",
        user_id="test-user",
        service_bundle=service_bundle,
    )
    runner = adapter.create_runner()
    metadata = adapter.metadata()

    assert runner.agent is agent
    assert runner.app.name == "test_adk_agent_shell"
    assert runner.app.root_agent is agent
    assert runner.app.plugins == []
    assert runner.artifact_service is service_bundle.adk_artifact_service
    assert runner.session_service is service_bundle.adk_session_service
    assert metadata["adapter"] == "adk_adapter.agent_service"
    assert metadata["app_assembly_mode"] == "adk_app"
    assert metadata["runner_entry"] == "agent"
    assert metadata["agent_type"] == "LlmAgent"
    assert metadata["agent_name"] == "task_quality_shell"
    assert metadata["agent_model"] == "gemini-2.0-flash"
    assert metadata["app_root_type"] == "LlmAgent"
    assert metadata["plugin_bundle_type"] == "AdkPluginBundle"
    assert metadata["plugin_bundle_source"] == "empty"
    assert metadata["plugin_count"] == 0
    assert metadata["plugin_names"] == []
    assert metadata["plugin_types"] == []
    assert metadata["raw_app_object_included"] is False
    assert metadata["raw_plugin_object_included"] is False
    assert metadata["service_bundle"]["adapter"] == "adk_adapter.runner_service_bundle"


def test_agent_shell_options_metadata_does_not_expose_full_instruction() -> None:
    options = AdkAgentShellOptions(
        name="metadata_shell",
        model="gemini-2.0-flash",
        instruction="Sensitive internal instruction text.",
        metadata={"owner": "test"},
    )

    metadata = options.to_metadata()

    assert metadata["name"] == "metadata_shell"
    assert metadata["instruction_length"] == len(options.instruction)
    assert "instruction" not in metadata
    assert metadata["metadata_keys"] == ["owner"]


def test_create_controlled_live_adk_llm_agent_uses_adk_litellm_model() -> None:
    fake_client = _FakeAsyncLiteLlmClient("controlled live output")
    agent = create_controlled_live_adk_llm_agent(
        AdkAgentShellOptions(
            name="controlled_live_shell",
            model="unused-shell-model",
            instruction="Review governed task evidence.",
            mode="chat",
        ),
        live_options=AdkAgentControlledLiveOptions(
            model="ollama/gemma4-pro:latest",
            ollama_api_base="http://127.0.0.1:11434",
            timeout_seconds=9,
            temperature=0,
            max_tokens=11,
            llm_client=fake_client,
            metadata={"live_service_profile": "adk_litellm_ollama"},
        ),
    )

    assert type(agent).__name__ == "LlmAgent"
    assert type(agent.model).__name__ == "LiteLlm"
    assert agent.model.model == "ollama/gemma4-pro:latest"
    assert agent.model._additional_args["api_base"] == "http://127.0.0.1:11434"
    assert agent.model._additional_args["timeout"] == 9
    assert agent.model._additional_args["temperature"] == 0
    assert agent.model._additional_args["max_tokens"] == 11
    assert "messages" not in agent.model._additional_args
    assert "tools" not in agent.model._additional_args
    assert "stream" not in agent.model._additional_args


def test_no_live_agent_service_run_async_emits_adk_events_without_live_call() -> None:
    agent = create_no_live_adk_llm_agent(
        AdkAgentShellOptions(
            name="no_live_task_quality_shell",
            model="adk-no-live/task-quality-shell",
            instruction="Review governed task evidence.",
            mode="chat",
        ),
        response_text="No-live review completed.",
    )
    adapter = AdkAgentServiceAdapter(
        agent=agent,
        app_name="test_no_live_agent_shell",
        user_id="test-user",
    )

    result = asyncio.run(
        adapter.run_text_async(
            text="Review this governed task.",
            invocation_id="agent-invocation-001",
        )
    )
    loaded_session = adapter.service_bundle.session_service.get_session_sync(
        session_id=result.session_id
    )

    assert result.requested_invocation_id == "agent-invocation-001"
    assert result.adk_invocation_id
    assert result.session_id
    assert result.agent_name == "no_live_task_quality_shell"
    assert result.metadata["no_live_execution_observed"] is True
    assert len(result.events) >= 2
    assert len(result.runtime_events) >= 2
    assert result.errors == []
    assert loaded_session.id == result.session_id
    assert len(loaded_session.events) >= 2
    assert any(
        event.payload["content"]
        and "No-live review completed." in str(event.payload["content"])
        for event in result.runtime_events
    )
    observability_input = result.to_observability_input()
    assert observability_input["event_count"] == len(result.runtime_events)
    assert observability_input["metadata"]["no_live_execution_observed"] is True


def test_no_live_multi_agent_root_preserves_event_author_branch_and_invocation_facts() -> None:
    """Use deprecated ParallelAgent only as an ADK compatibility sample."""

    parallel_root = ParallelAgent(
        name="par_root",
        sub_agents=[
            create_no_live_adk_llm_agent(
                AdkAgentShellOptions(
                    name="parallel_one",
                    model="adk-no-live/parallel-one",
                    instruction="Review one branch.",
                    mode="chat",
                ),
                response_text="Parallel one completed.",
            ),
            create_no_live_adk_llm_agent(
                AdkAgentShellOptions(
                    name="parallel_two",
                    model="adk-no-live/parallel-two",
                    instruction="Review another branch.",
                    mode="chat",
                ),
                response_text="Parallel two completed.",
            ),
        ],
    )
    adapter = AdkAgentServiceAdapter(
        agent=parallel_root,
        app_name="test_no_live_multi_agent_shell",
        user_id="test-user",
    )

    result = asyncio.run(
        adapter.run_text_async(
            text="Run the no-live multi-agent compatibility sample.",
            invocation_id="multi-agent-invocation-001",
        )
    )
    runtime_metadata = [event.metadata for event in result.runtime_events]

    assert result.requested_invocation_id == "multi-agent-invocation-001"
    assert result.agent_name == "par_root"
    assert result.agent_type == "ParallelAgent"
    assert result.metadata["no_live_execution_observed"] is True
    assert result.errors == []
    assert {"parallel_one", "parallel_two"}.issubset(
        {metadata.get("author") for metadata in runtime_metadata}
    )
    assert {"par_root.parallel_one", "par_root.parallel_two"}.issubset(
        {metadata.get("branch") for metadata in runtime_metadata}
    )
    assert {result.adk_invocation_id} == {
        metadata.get("adk_invocation_id")
        for metadata in runtime_metadata
        if metadata.get("adk_invocation_id")
    }
    assert any(
        event.payload["content"]
        and "Parallel one completed." in str(event.payload["content"])
        for event in result.runtime_events
    )
    assert any(
        event.payload["content"]
        and "Parallel two completed." in str(event.payload["content"])
        for event in result.runtime_events
    )


def test_no_live_transfer_to_agent_handoff_preserves_transfer_action_fact() -> None:
    from google.adk.agents import Agent

    handoff_target = create_no_live_adk_llm_agent(
        AdkAgentShellOptions(
            name="handoff_target",
            model="adk-no-live/handoff-target",
            instruction="Complete the transferred request.",
            mode="chat",
        ),
        response_text="Handoff target completed.",
    )
    handoff_root = Agent(
        name="handoff_root",
        model=_TransferToAgentNoLiveLlm(model="adk-no-live-transfer/handoff-root"),
        instruction="Transfer this request to handoff_target.",
        sub_agents=[handoff_target],
    )
    adapter = AdkAgentServiceAdapter(
        agent=handoff_root,
        app_name="test_no_live_handoff_agent_shell",
        user_id="test-user",
    )

    result = asyncio.run(
        adapter.run_text_async(
            text="Route this request.",
            invocation_id="handoff-invocation-001",
        )
    )
    runtime_metadata = [event.metadata for event in result.runtime_events]
    runtime_contents = [
        event.payload["content"]
        for event in result.runtime_events
        if event.payload.get("content")
    ]

    assert result.requested_invocation_id == "handoff-invocation-001"
    assert result.agent_name == "handoff_root"
    assert result.errors == []
    assert result.metadata["no_live_execution_observed"] is True
    assert any(
        metadata.get("adk_transfer_to_agent") == "handoff_target"
        for metadata in runtime_metadata
    )
    assert all(
        "adk_transfer_to_agent" not in metadata
        for metadata in runtime_metadata
        if metadata.get("adk_transfer_to_agent") != "handoff_target"
    )
    assert "handoff_target" in {
        metadata.get("author")
        for metadata in runtime_metadata
        if metadata.get("author")
    }
    assert any(
        "function_call" in str(content) and "transfer_to_agent" in str(content)
        for content in runtime_contents
    )
    assert any(
        "function_response" in str(content) and "transfer_to_agent" in str(content)
        for content in runtime_contents
    )
    assert any(
        event.payload["content"]
        and "Handoff target completed." in str(event.payload["content"])
        for event in result.runtime_events
    )


def test_controlled_live_agent_service_run_async_uses_injected_adk_litellm_client() -> None:
    fake_client = _FakeAsyncLiteLlmClient("Controlled live Agent shell completed.")
    agent = create_controlled_live_adk_llm_agent(
        AdkAgentShellOptions(
            name="controlled_live_task_quality_shell",
            model="unused-shell-model",
            instruction="Review governed task evidence.",
            mode="chat",
        ),
        live_options=AdkAgentControlledLiveOptions(
            model="ollama/gemma4-pro:latest",
            ollama_api_base="http://127.0.0.1:11434",
            timeout_seconds=9,
            temperature=0,
            max_tokens=11,
            llm_client=fake_client,
        ),
    )
    adapter = AdkAgentServiceAdapter(
        agent=agent,
        app_name="test_controlled_live_agent_shell",
        user_id="test-user",
    )

    result = asyncio.run(
        adapter.run_text_async(
            text="Review this governed task.",
            invocation_id="agent-invocation-controlled-live-001",
        )
    )

    assert result.requested_invocation_id == "agent-invocation-controlled-live-001"
    assert result.adk_invocation_id
    assert result.agent_name == "controlled_live_task_quality_shell"
    assert result.metadata["no_live_execution_observed"] is False
    assert result.errors == []
    assert fake_client.calls
    assert fake_client.calls[0]["model"] == "ollama/gemma4-pro:latest"
    assert fake_client.calls[0]["api_base"] == "http://127.0.0.1:11434"
    assert fake_client.calls[0]["timeout"] == 9
    assert fake_client.calls[0]["temperature"] == 0
    assert fake_client.calls[0]["max_tokens"] == 11


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


class _TransferToAgentNoLiveLlm(BaseLlm):
    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"adk-no-live-transfer/.+"]

    async def generate_content_async(self, llm_request: Any, stream: bool = False):
        from google.adk.models.llm_response import LlmResponse
        from google.genai import types

        yield LlmResponse(
            model_version=self.model,
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_function_call(
                        name="transfer_to_agent",
                        args={"agent_name": "handoff_target"},
                    )
                ],
            ),
            partial=False,
            turn_complete=True,
            custom_metadata={
                "no_live_execution": True,
                "source": "test._TransferToAgentNoLiveLlm",
            },
        )
