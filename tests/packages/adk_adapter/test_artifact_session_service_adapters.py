from __future__ import annotations

from adk_adapter import AdkArtifactServiceAdapter, AdkSessionServiceAdapter
from google.genai import types


def test_artifact_service_adapter_wraps_adk_save_load_list_version_delete() -> None:
    adapter = AdkArtifactServiceAdapter(
        app_name="test_adk_adapter",
        user_id="test-user",
        session_id="session-001",
    )

    version = adapter.save_artifact_sync(
        filename="artifact.txt",
        artifact=types.Part(text="artifact payload"),
        custom_metadata={"case": "service-adapter"},
    )

    assert version == 0
    assert adapter.list_artifact_keys_sync() == ["artifact.txt"]
    assert adapter.list_versions_sync(filename="artifact.txt") == [0]
    assert adapter.load_artifact_sync(filename="artifact.txt").text == "artifact payload"


def test_session_service_adapter_wraps_adk_create_get_list_append_event() -> None:
    from google.adk.events import Event

    adapter = AdkSessionServiceAdapter(app_name="test_adk_adapter", user_id="test-user")

    session = adapter.create_session_sync(
        state={"phase": "service-adapter"},
        session_id="session-001",
    )
    appended = adapter.append_event_sync(
        session=session,
        event=Event(invocation_id="invocation-001", author="test-node", output={"ok": True}),
    )

    assert session.id == "session-001"
    assert session.app_name == "test_adk_adapter"
    assert session.user_id == "test-user"
    assert appended.invocation_id == "invocation-001"

    loaded = adapter.get_session_sync(session_id="session-001")
    sessions = adapter.list_sessions_sync()

    assert loaded.id == "session-001"
    assert loaded.state["phase"] == "service-adapter"
    assert len(loaded.events) == 1
    assert sessions.sessions[0].id == "session-001"
