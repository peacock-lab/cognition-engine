from __future__ import annotations

from typing import Any

from adk_adapter import (
    AdkAgentServiceAdapter,
    AdkAgentShellOptions,
    AdkPluginBundle,
    AdkPluginBundleOptions,
    AdkRunnerServiceAdapter,
    create_adk_llm_agent,
)
from google.adk.plugins.base_plugin import BasePlugin


class FakePlugin(BasePlugin):
    def __init__(self, name: str = "fake_plugin") -> None:
        super().__init__(name=name)


def test_default_plugin_bundle_options_build_empty_metadata() -> None:
    bundle = AdkPluginBundleOptions().build_plugin_bundle()
    metadata = bundle.metadata()

    assert bundle.adk_plugins == []
    assert metadata["plugin_bundle_type"] == "AdkPluginBundle"
    assert metadata["plugin_bundle_source"] == "empty"
    assert metadata["plugin_count"] == 0
    assert metadata["plugin_names"] == []
    assert metadata["plugin_types"] == []
    assert metadata["raw_plugin_object_included"] is False


def test_provided_plugin_bundle_metadata_is_sanitized() -> None:
    plugin = FakePlugin(name="metadata_plugin")
    bundle = AdkPluginBundle.from_plugins(plugins=[plugin])
    metadata = bundle.metadata()

    assert bundle.adk_plugins == [plugin]
    assert metadata["plugin_bundle_source"] == "provided_plugins"
    assert metadata["plugin_count"] == 1
    assert metadata["plugin_names"] == ["metadata_plugin"]
    assert metadata["plugin_types"] == ["FakePlugin"]
    assert metadata["raw_plugin_object_included"] is False
    assert _contains_identity(metadata, plugin) is False


def test_plugin_bundle_options_reject_empty_source_with_plugins() -> None:
    plugin = FakePlugin()
    options = AdkPluginBundleOptions(source="empty", plugins=(plugin,))

    try:
        options.build_plugin_bundle()
    except ValueError as exc:
        assert "does not accept plugins" in str(exc)
    else:  # pragma: no cover - makes the failure message clearer.
        raise AssertionError("Expected empty plugin bundle options to reject plugins")


def test_explicit_empty_plugin_bundle_matches_default_runner_metadata() -> None:
    from google.adk.workflow import Workflow

    default_adapter = AdkRunnerServiceAdapter(
        workflow=Workflow(name="default_empty_bundle_workflow", edges=[]),
    )
    explicit_adapter = AdkRunnerServiceAdapter(
        workflow=Workflow(name="explicit_empty_bundle_workflow", edges=[]),
        plugin_bundle=AdkPluginBundle.empty(),
    )

    default_metadata = default_adapter.metadata()
    explicit_metadata = explicit_adapter.metadata()

    assert default_adapter.create_app().plugins == []
    assert explicit_adapter.create_app().plugins == []
    assert explicit_metadata["plugin_bundle_source"] == "empty"
    assert explicit_metadata["plugin_count"] == default_metadata["plugin_count"] == 0
    assert explicit_metadata["plugin_names"] == default_metadata["plugin_names"] == []
    assert explicit_metadata["plugin_types"] == default_metadata["plugin_types"] == []
    assert explicit_metadata["raw_plugin_object_included"] is False


def test_runner_service_uses_explicit_plugin_bundle_in_app_metadata() -> None:
    from google.adk.workflow import Workflow

    plugin = FakePlugin(name="workflow_plugin")
    workflow = Workflow(name="plugin_bundle_workflow", edges=[])
    adapter = AdkRunnerServiceAdapter(
        workflow=workflow,
        plugin_bundle=AdkPluginBundle.from_plugins(plugins=[plugin]),
    )

    app = adapter.create_app()
    metadata = adapter.metadata()

    assert app.plugins == [plugin]
    assert metadata["plugin_bundle_source"] == "provided_plugins"
    assert metadata["plugin_count"] == 1
    assert metadata["plugin_names"] == ["workflow_plugin"]
    assert metadata["plugin_types"] == ["FakePlugin"]
    assert metadata["raw_plugin_object_included"] is False
    assert _contains_identity(metadata, plugin) is False


def test_agent_service_uses_explicit_plugin_bundle_in_app_metadata() -> None:
    plugin = FakePlugin(name="agent_plugin")
    agent = create_adk_llm_agent(
        AdkAgentShellOptions(
            name="plugin_bundle_agent",
            model="gemini-2.0-flash",
            instruction="Review plugin bundle metadata.",
        )
    )
    adapter = AdkAgentServiceAdapter(
        agent=agent,
        plugin_bundle=AdkPluginBundle.from_plugins(plugins=[plugin]),
    )

    app = adapter.create_app()
    metadata = adapter.metadata()

    assert app.plugins == [plugin]
    assert metadata["plugin_bundle_source"] == "provided_plugins"
    assert metadata["plugin_count"] == 1
    assert metadata["plugin_names"] == ["agent_plugin"]
    assert metadata["plugin_types"] == ["FakePlugin"]
    assert metadata["raw_plugin_object_included"] is False
    assert _contains_identity(metadata, plugin) is False


def _contains_identity(value: Any, target: Any) -> bool:
    if value is target:
        return True
    if isinstance(value, dict):
        return any(_contains_identity(item, target) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_identity(item, target) for item in value)
    return False
