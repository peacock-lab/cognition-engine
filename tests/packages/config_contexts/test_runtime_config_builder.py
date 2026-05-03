from pathlib import Path

import pytest

from config_assembly.runtime import RuntimeConfigPayload, assemble_runtime_config_payload
from config_contexts.runtime import ExecutionMode
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
        },
    )

    with pytest.raises(RuntimeConfigContextBuildError):
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
            "channel_selection": {
                "default_runtime_channel": "legacy-local",
                "adk_channel_enabled": True,
                "litellm_channel_enabled": True,
                "hermes_memory_channel_enabled": True,
                "openclaw_gateway_channel_enabled": True,
                "fallback_channel": "legacy-fallback",
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
