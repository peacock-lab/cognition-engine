from pathlib import Path

import pytest

from config_assembly.runtime import RuntimeConfigPayload, assemble_runtime_config_payload
from config_contexts.runtime import ExecutionMode
from pydantic import ValidationError
from config_contexts.runtime_builder import (
    RuntimeConfigContextBuildError,
    build_runtime_config_contexts,
)


def test_build_runtime_config_contexts_from_project_payload() -> None:
    payload = assemble_runtime_config_payload(Path("config"), environment="local")

    bundle = build_runtime_config_contexts(payload)

    assert bundle.runtime.runtime_name == "local-runtime"
    assert bundle.runtime.execution_mode == ExecutionMode.LOCAL
    assert bundle.runtime.timeout_seconds == 180
    assert bundle.workflow_execution.graph_mode is True
    assert bundle.node_execution.max_retries == 1
    assert bundle.event_policy.event_sink_name == "local"
    assert bundle.artifact_policy.artifact_name_prefix == "ce-runtime-local"
    assert bundle.adapter_selection.default_runtime_adapter == "local"
    assert bundle.adk_run_config.max_llm_calls == 1
    assert bundle.adk_run_config.streaming_mode == "none"
    assert bundle.adk_run_config.custom_metadata["source"] == "config/env/local.yaml"
    assert bundle.live_llm.profile == "adk_litellm_ollama"
    assert bundle.live_llm.model_name == "ollama/gemma4-pro:latest"
    assert bundle.live_llm.ollama_api_base == "http://127.0.0.1:11434"
    assert bundle.live_llm.timeout_seconds == 45
    assert bundle.live_llm.temperature == 0
    assert bundle.live_llm.max_tokens == 64
    assert bundle.live_llm.enabled_by_default is False
    assert bundle.live_llm.metadata["source"] == "config/env/local.yaml"
    assert bundle.tool_confirmation.default_require_confirmation is True
    assert bundle.tool_confirmation.default_mode == "operator_required"
    assert bundle.tool_confirmation.auto_confirmation_allowed is False
    assert (
        bundle.tool_confirmation.controlled_live_external_tool_smoke_enabled
        is False
    )
    assert bundle.tool_confirmation.low_risk_tool_allowlist == (
        "deterministic_external_echo",
    )
    assert (
        bundle.tool_confirmation.metadata["adk_feature_status"]
        == "experimental"
    )
    assert bundle.tool_exposure.default_profile == "readonly_reference"
    profile_config = bundle.tool_exposure.to_profile_config()
    assert "readonly_reference" in profile_config["profiles"]
    assert profile_config["profiles"]["readonly_reference"]["toolsets"][0][
        "toolset_name"
    ] == "local_reference_tools"
    assert bundle.run_workspace.enabled_by_default is False
    assert bundle.run_workspace.to_policy_kwargs() == {
        "workspace_root": ".cognition-runs",
        "retention_policy": "keep",
        "cleanup_policy": "manual",
        "max_write_bytes": 65536,
    }
    assert bundle.productization_gate.gate_id == (
        "gate-ce-156-no-live-productization"
    )
    assert bundle.productization_gate.request_adk_run is False
    assert bundle.governance.governance_profile == "no-live-productization"
    assert bundle.governance.policy_refs == ("policy:no-live-productization-config",)


def test_build_runtime_config_contexts_rejects_missing_section() -> None:
    payload = RuntimeConfigPayload(
        source_root="config",
        environment="test",
        base_file="config/base/runtime.yaml",
        payload={
            "runtime": {"runtime_name": "test-runtime"},
        },
    )

    with pytest.raises(RuntimeConfigContextBuildError):
        build_runtime_config_contexts(payload)


def test_build_runtime_config_contexts_rejects_non_mapping_section() -> None:
    payload = RuntimeConfigPayload(
        source_root="config",
        environment="test",
        base_file="config/base/runtime.yaml",
        payload={
            "runtime": {"runtime_name": "test-runtime"},
            "workflow_execution": [],
            "node_execution": {},
            "resume_policy": {},
            "event_policy": {},
            "artifact_policy": {},
            "adapter_selection": {},
            "adk_run_config": [],
        },
    )

    with pytest.raises(RuntimeConfigContextBuildError):
        build_runtime_config_contexts(payload)


def test_build_runtime_config_contexts_rejects_non_mapping_adk_run_config() -> None:
    payload = RuntimeConfigPayload(
        source_root="config",
        environment="test",
        base_file="config/base/runtime.yaml",
        payload={
            "runtime": {"runtime_name": "test-runtime"},
            "workflow_execution": {"workflow_name": "test-workflow"},
            "node_execution": {},
            "resume_policy": {},
            "event_policy": {},
            "artifact_policy": {},
            "adapter_selection": {},
            "adk_run_config": [],
        },
    )

    with pytest.raises(RuntimeConfigContextBuildError):
        build_runtime_config_contexts(payload)


def test_build_runtime_config_contexts_rejects_non_mapping_live_llm() -> None:
    payload = RuntimeConfigPayload(
        source_root="config",
        environment="test",
        base_file="config/base/runtime.yaml",
        payload={
            "runtime": {"runtime_name": "test-runtime"},
            "workflow_execution": {"workflow_name": "test-workflow"},
            "node_execution": {},
            "resume_policy": {},
            "event_policy": {},
            "artifact_policy": {},
            "adapter_selection": {},
            "live_llm": [],
        },
    )

    with pytest.raises(RuntimeConfigContextBuildError):
        build_runtime_config_contexts(payload)


def test_build_runtime_config_contexts_rejects_non_mapping_tool_confirmation() -> None:
    payload = RuntimeConfigPayload(
        source_root="config",
        environment="test",
        base_file="config/base/runtime.yaml",
        payload={
            "runtime": {"runtime_name": "test-runtime"},
            "workflow_execution": {"workflow_name": "test-workflow"},
            "node_execution": {},
            "resume_policy": {},
            "event_policy": {},
            "artifact_policy": {},
            "adapter_selection": {},
            "tool_confirmation": [],
        },
    )

    with pytest.raises(RuntimeConfigContextBuildError):
        build_runtime_config_contexts(payload)


def test_build_runtime_config_contexts_rejects_non_mapping_tool_exposure() -> None:
    payload = RuntimeConfigPayload(
        source_root="config",
        environment="test",
        base_file="config/base/runtime.yaml",
        payload={
            "runtime": {"runtime_name": "test-runtime"},
            "workflow_execution": {"workflow_name": "test-workflow"},
            "node_execution": {},
            "resume_policy": {},
            "event_policy": {},
            "artifact_policy": {},
            "adapter_selection": {},
            "tool_exposure": [],
        },
    )

    with pytest.raises(RuntimeConfigContextBuildError):
        build_runtime_config_contexts(payload)


def test_build_runtime_config_contexts_rejects_non_mapping_run_workspace() -> None:
    payload = RuntimeConfigPayload(
        source_root="config",
        environment="test",
        base_file="config/base/runtime.yaml",
        payload={
            "runtime": {"runtime_name": "test-runtime"},
            "workflow_execution": {"workflow_name": "test-workflow"},
            "node_execution": {},
            "resume_policy": {},
            "event_policy": {},
            "artifact_policy": {},
            "adapter_selection": {},
            "run_workspace": [],
        },
    )

    with pytest.raises(RuntimeConfigContextBuildError):
        build_runtime_config_contexts(payload)


def test_build_runtime_config_contexts_rejects_tool_auto_confirmation() -> None:
    payload = RuntimeConfigPayload(
        source_root="config",
        environment="test",
        base_file="config/base/runtime.yaml",
        payload={
            "runtime": {"runtime_name": "test-runtime"},
            "workflow_execution": {"workflow_name": "test-workflow"},
            "node_execution": {},
            "resume_policy": {},
            "event_policy": {},
            "artifact_policy": {},
            "adapter_selection": {},
            "tool_confirmation": {"auto_confirmation_allowed": True},
        },
    )

    with pytest.raises(ValidationError):
        build_runtime_config_contexts(payload)


def test_build_runtime_config_contexts_rejects_tool_approval_ref_metadata() -> None:
    payload = RuntimeConfigPayload(
        source_root="config",
        environment="test",
        base_file="config/base/runtime.yaml",
        payload={
            "runtime": {"runtime_name": "test-runtime"},
            "workflow_execution": {"workflow_name": "test-workflow"},
            "node_execution": {},
            "resume_policy": {},
            "event_policy": {},
            "artifact_policy": {},
            "adapter_selection": {},
            "tool_confirmation": {
                "metadata": {
                    "tool_confirmation_approval_ref": "approval://bad"
                }
            },
        },
    )

    with pytest.raises(ValidationError):
        build_runtime_config_contexts(payload)


def test_build_runtime_config_contexts_rejects_tool_exposure_allowlist_expansion() -> None:
    payload = RuntimeConfigPayload(
        source_root="config",
        environment="test",
        base_file="config/base/runtime.yaml",
        payload={
            "runtime": {"runtime_name": "test-runtime"},
            "workflow_execution": {"workflow_name": "test-workflow"},
            "node_execution": {},
            "resume_policy": {},
            "event_policy": {},
            "artifact_policy": {},
            "adapter_selection": {},
            "tool_exposure": {
                "default_profile": "readonly_reference",
                "profiles": {
                    "readonly_reference": {
                        "toolsets": [
                            {
                                "toolset_name": "local_reference_tools",
                                "source_ref": "local-reference-reader://workspace",
                                "allowlist_tool_names": ["local_reference_reader"],
                                "tool_filter": ["unapproved_tool"],
                            }
                        ]
                    }
                },
            },
        },
    )

    with pytest.raises(ValidationError):
        build_runtime_config_contexts(payload)


def test_build_runtime_config_contexts_rejects_unsafe_workspace_root() -> None:
    payload = RuntimeConfigPayload(
        source_root="config",
        environment="test",
        base_file="config/base/runtime.yaml",
        payload={
            "runtime": {"runtime_name": "test-runtime"},
            "workflow_execution": {"workflow_name": "test-workflow"},
            "node_execution": {},
            "resume_policy": {},
            "event_policy": {},
            "artifact_policy": {},
            "adapter_selection": {},
            "run_workspace": {"workspace_root": "../outside"},
        },
    )

    with pytest.raises(ValidationError):
        build_runtime_config_contexts(payload)


def test_build_runtime_config_contexts_accepts_legacy_channel_config() -> None:
    payload = RuntimeConfigPayload(
        source_root="config",
        environment="legacy",
        base_file="config/base/runtime.yaml",
        payload={
            "runtime": {
                "runtime_name": "legacy-runtime",
                "default_channel": "legacy-local",
            },
            "workflow_execution": {"workflow_name": "legacy-workflow"},
            "node_execution": {},
            "resume_policy": {},
            "event_policy": {},
            "artifact_policy": {},
            "session_policy": {
                "capture_session_state_keys": True,
                "max_state_key_count": 12,
                "session_service_source": "in_memory",
            },
            "channel_selection": {
                "default_runtime_channel": "legacy-local",
                "adk_channel_enabled": True,
                "litellm_channel_enabled": True,
                "hermes_memory_channel_enabled": True,
                "openclaw_gateway_channel_enabled": True,
                "fallback_channel": "legacy-fallback",
            },
            "adk_run_config": {
                "max_llm_calls": 6,
                "streaming_mode": "none",
                "custom_metadata": {"source": "legacy-config"},
            },
        },
    )

    bundle = build_runtime_config_contexts(payload)

    assert bundle.runtime.default_adapter == "legacy-local"
    assert bundle.adapter_selection.default_runtime_adapter == "legacy-local"
    assert bundle.adapter_selection.adk_adapter_enabled is True
    assert bundle.adapter_selection.litellm_adapter_enabled is True
    assert bundle.adapter_selection.hermes_adapter_enabled is True
    assert bundle.adapter_selection.openclaw_adapter_enabled is True
    assert bundle.adapter_selection.fallback_adapter == "legacy-fallback"
    assert bundle.adk_run_config.max_llm_calls == 6
    assert bundle.adk_run_config.streaming_mode == "none"
    assert bundle.adk_run_config.custom_metadata == {"source": "legacy-config"}
    assert bundle.session_policy.max_state_key_count == 12
    assert bundle.session_policy.session_service_source == "in_memory"
    assert bundle.live_llm.model_name == "ollama/gemma4-pro:latest"
    assert bundle.tool_confirmation.default_require_confirmation is True
