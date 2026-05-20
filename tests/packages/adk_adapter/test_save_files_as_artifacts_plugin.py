from __future__ import annotations

from typing import Any

import pytest
from adk_adapter import (
    AdkRunnerServiceAdapter,
    AdkSaveFilesAsArtifactsPluginOptions,
    build_save_files_as_artifacts_plugin_bundle,
)
from adk_adapter.async_utils import run_sync
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import InvocationContext
from google.adk.sessions import InMemorySessionService, Session
from google.adk.workflow import Workflow
from google.genai import types


def test_save_files_as_artifacts_plugin_default_intent_is_disabled() -> None:
    options = AdkSaveFilesAsArtifactsPluginOptions()
    bundle = options.build_plugin_bundle()
    metadata = options.metadata()

    assert bundle.adk_plugins == []
    assert metadata["plugin_enable_intent"] is False
    assert metadata["plugin_count"] == 0
    assert metadata["plugin_bundle_source"] == "save_files_as_artifacts_plugin_disabled"
    assert metadata["attach_file_reference"] is False
    assert metadata["model_accessible_file_reference_enabled"] is False
    assert metadata["raw_plugin_object_included"] is False
    assert metadata["raw_inline_data_included"] is False
    assert metadata["raw_artifact_content_included"] is False


def test_save_files_as_artifacts_plugin_explicit_enable_builds_safe_bundle() -> None:
    options = AdkSaveFilesAsArtifactsPluginOptions(enabled=True)
    bundle = build_save_files_as_artifacts_plugin_bundle(options)
    plugin = bundle.adk_plugins[0]
    metadata = bundle.metadata()

    assert len(bundle.adk_plugins) == 1
    assert type(plugin).__name__ == "SaveFilesAsArtifactsPlugin"
    assert plugin.name == "save_files_as_artifacts_plugin"
    assert getattr(plugin, "_attach_file_reference") is False
    assert metadata["plugin_bundle_source"] == "save_files_as_artifacts_plugin_enabled"
    assert metadata["plugin_count"] == 1
    assert metadata["plugin_names"] == ["save_files_as_artifacts_plugin"]
    assert metadata["plugin_types"] == ["SaveFilesAsArtifactsPlugin"]
    assert metadata["raw_plugin_object_included"] is False
    assert _contains_identity(metadata, plugin) is False


def test_save_files_as_artifacts_plugin_rejects_file_reference_without_policy() -> None:
    options = AdkSaveFilesAsArtifactsPluginOptions(
        enabled=True,
        attach_file_reference=True,
    )

    with pytest.raises(ValueError, match="model-accessible file reference policy"):
        options.build_plugin_bundle()


def test_save_files_as_artifacts_plugin_can_feed_runner_app_only_when_explicit() -> None:
    workflow = Workflow(name="save_files_as_artifacts_workflow", edges=[])
    default_adapter = AdkRunnerServiceAdapter(workflow=workflow)
    enabled_adapter = AdkRunnerServiceAdapter(
        workflow=workflow,
        plugin_bundle=AdkSaveFilesAsArtifactsPluginOptions(
            enabled=True
        ).build_plugin_bundle(),
    )

    assert default_adapter.create_app().plugins == []
    assert len(enabled_adapter.create_app().plugins) == 1
    assert enabled_adapter.metadata()["plugin_names"] == [
        "save_files_as_artifacts_plugin"
    ]
    assert enabled_adapter.metadata()["raw_plugin_object_included"] is False


def test_save_files_as_artifacts_plugin_no_live_inline_data_smoke() -> None:
    options = AdkSaveFilesAsArtifactsPluginOptions(enabled=True)
    bundle = options.build_plugin_bundle()
    plugin = bundle.adk_plugins[0]
    artifact_service = InMemoryArtifactService()
    session = Session(id="session-643", app_name="app-643", user_id="user-643")
    invocation_context = InvocationContext(
        artifact_service=artifact_service,
        session_service=InMemorySessionService(),
        invocation_id="invocation-643",
        session=session,
    )
    raw_bytes = b"small governed bytes"
    user_message = types.Content(
        role="user",
        parts=[
            types.Part(text="before"),
            types.Part(
                inline_data=types.Blob(
                    data=raw_bytes,
                    mime_type="text/plain",
                    display_name="sample.txt",
                )
            ),
            types.Part(text="after"),
        ],
    )

    modified = run_sync(
        plugin.on_user_message_callback(
            invocation_context=invocation_context,
            user_message=user_message,
        )
    )

    assert modified is not None
    assert [part.text for part in modified.parts] == [
        "before",
        '[Uploaded Artifact: "sample.txt"]',
        "after",
    ]
    assert all(part.inline_data is None for part in modified.parts)
    assert all(part.file_data is None for part in modified.parts)
    assert session.state[f"{plugin.name}:pending_delta"] == {"sample.txt": 0}

    artifact_keys = run_sync(
        artifact_service.list_artifact_keys(
            app_name="app-643",
            user_id="user-643",
            session_id="session-643",
        )
    )
    artifact = run_sync(
        artifact_service.load_artifact(
            app_name="app-643",
            user_id="user-643",
            session_id="session-643",
            filename="sample.txt",
        )
    )
    metadata = {
        "options": options.metadata(),
        "bundle": bundle.metadata(),
    }

    assert artifact_keys == ["sample.txt"]
    assert artifact.inline_data.data == raw_bytes
    assert _contains_identity(metadata, plugin) is False
    assert _contains_text(metadata, raw_bytes.decode("utf-8")) is False
    assert _contains_bytes(metadata) is False


def _contains_identity(value: Any, target: Any) -> bool:
    if value is target:
        return True
    if isinstance(value, dict):
        return any(_contains_identity(item, target) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_identity(item, target) for item in value)
    return False


def _contains_text(value: Any, target: str) -> bool:
    if isinstance(value, str):
        return target in value
    if isinstance(value, dict):
        return any(_contains_text(item, target) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_text(item, target) for item in value)
    return False


def _contains_bytes(value: Any) -> bool:
    if isinstance(value, bytes):
        return True
    if isinstance(value, dict):
        return any(_contains_bytes(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_bytes(item) for item in value)
    return False
