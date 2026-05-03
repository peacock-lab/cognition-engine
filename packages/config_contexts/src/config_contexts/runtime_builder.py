"""Build runtime configuration contexts from assembled configuration payloads."""

from __future__ import annotations

from typing import Any

from config_assembly.runtime import RuntimeConfigPayload

from config_contexts.runtime import (
    AdapterSelectionConfigView,
    ArtifactPolicyConfigView,
    EventPolicyConfigView,
    NodeExecutionConfigView,
    ResumePolicyConfigView,
    RuntimeConfigContextBundle,
    RuntimeConfigView,
    WorkflowExecutionConfigView,
)


class RuntimeConfigContextBuildError(RuntimeError):
    """Raised when runtime configuration context construction fails."""


_LEGACY_SECTION_NAMES = {
    "adapter_selection": "channel_selection",
}

_LEGACY_FIELD_NAMES = {
    "runtime": {
        "default_adapter": "default_channel",
    },
    "adapter_selection": {
        "default_runtime_adapter": "default_runtime_channel",
        "adk_adapter_enabled": "adk_channel_enabled",
        "litellm_adapter_enabled": "litellm_channel_enabled",
        "hermes_adapter_enabled": "hermes_memory_channel_enabled",
        "openclaw_adapter_enabled": "openclaw_gateway_channel_enabled",
        "fallback_adapter": "fallback_channel",
    },
}


def _section(payload: dict[str, Any], name: str) -> dict[str, Any]:
    """Return one named config section as a mapping."""

    value = payload.get(name)
    if value is None:
        legacy_name = _LEGACY_SECTION_NAMES.get(name)
        if legacy_name is not None:
            value = payload.get(legacy_name)

    if value is None:
        raise RuntimeConfigContextBuildError(f"Missing runtime config section: {name}")

    if not isinstance(value, dict):
        raise RuntimeConfigContextBuildError(f"Runtime config section must be a mapping: {name}")

    return _normalize_legacy_fields(name, value)


def _normalize_legacy_fields(section_name: str, section: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy channel field names to adapter field names."""

    normalized = dict(section)
    for adapter_field, legacy_field in _LEGACY_FIELD_NAMES.get(section_name, {}).items():
        if adapter_field not in normalized and legacy_field in normalized:
            normalized[adapter_field] = normalized.pop(legacy_field)

    return normalized


def build_runtime_config_contexts(
    config_payload: RuntimeConfigPayload,
) -> RuntimeConfigContextBundle:
    """Build runtime Config Views from an assembled runtime config payload."""

    payload = config_payload.payload

    return RuntimeConfigContextBundle(
        runtime=RuntimeConfigView(**_section(payload, "runtime")),
        workflow_execution=WorkflowExecutionConfigView(
            **_section(payload, "workflow_execution"),
        ),
        node_execution=NodeExecutionConfigView(
            **_section(payload, "node_execution"),
        ),
        resume_policy=ResumePolicyConfigView(
            **_section(payload, "resume_policy"),
        ),
        event_policy=EventPolicyConfigView(
            **_section(payload, "event_policy"),
        ),
        artifact_policy=ArtifactPolicyConfigView(
            **_section(payload, "artifact_policy"),
        ),
        adapter_selection=AdapterSelectionConfigView(
            **_section(payload, "adapter_selection"),
        ),
    )
