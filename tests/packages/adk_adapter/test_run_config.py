from __future__ import annotations

import re
from pathlib import Path

import pytest

from adk_adapter import AdkRunConfigMapper, AdkRunConfigOptions
from adk_adapter.run_config import (
    ADK_RUN_CONFIG_DEPRECATED_FIELDS,
    ADK_RUN_CONFIG_FIELD_NAMES,
    ADK_RUN_CONFIG_FIELD_POLICIES,
    ADK_RUN_CONFIG_LEGACY_INPUT_FIELDS,
    ADK_RUN_CONFIG_LIVE_MEDIA_FIELDS,
    ADK_RUN_CONFIG_MAPPER_SUPPORTED_FIELDS,
    ADK_RUN_CONFIG_RETIRED_FIELDS,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
ADK_RUN_CONFIG_SOURCE = (
    REPO_ROOT / "packages" / "adk_adapter" / "src" / "adk_adapter" / "run_config.py"
)


def test_run_config_options_build_real_adk_run_config() -> None:
    from google.adk.agents.run_config import StreamingMode
    from google.adk.runners import RunConfig

    options = AdkRunConfigOptions(
        max_llm_calls=7,
        custom_metadata={"assembly": "run-config-test"},
        response_modalities=("TEXT",),
        support_cfc=True,
        streaming_mode="sse",
        enable_affective_dialog=False,
        save_live_blob=False,
        save_live_audio=False,
        get_session_num_recent_events=3,
    )

    run_config = AdkRunConfigMapper().build(options)
    metadata = AdkRunConfigMapper().metadata(run_config)

    assert isinstance(run_config, RunConfig)
    assert run_config.max_llm_calls == 7
    assert run_config.custom_metadata == {"assembly": "run-config-test"}
    assert run_config.response_modalities == ["TEXT"]
    assert run_config.support_cfc is True
    assert run_config.streaming_mode is StreamingMode.SSE
    assert run_config.enable_affective_dialog is False
    assert run_config.save_live_blob is False
    assert run_config.get_session_config.num_recent_events == 3
    assert metadata["adk_run_config_module"] == "google.adk.agents.run_config"
    assert metadata["streaming_mode"] == "sse"
    assert metadata["adk_run_config_version"] == "2.0.0"
    assert "speech_config" in metadata["official_fields"]
    assert "tool_thread_pool_config" in metadata["unmapped_fields"]
    assert metadata["field_policies"]["tool_thread_pool_config"]["status"] == (
        "deferred_tool_execution"
    )
    assert metadata["deprecated_fields"] == list(ADK_RUN_CONFIG_DEPRECATED_FIELDS)
    assert metadata["retired_fields"] == list(ADK_RUN_CONFIG_RETIRED_FIELDS)
    assert metadata["live_media_fields"] == list(ADK_RUN_CONFIG_LIVE_MEDIA_FIELDS)
    assert metadata["legacy_input_fields"] == []
    assert metadata["translated_fields"] == []
    assert "save_input_blobs_as_artifacts" not in metadata
    assert "save_input_blobs_as_artifacts" not in metadata["mapper_supported_fields"]
    assert metadata["field_policies"]["save_input_blobs_as_artifacts"]["status"] == (
        "retired_deprecated"
    )
    assert "save_live_audio" not in metadata
    assert "save_live_audio" not in metadata["mapper_supported_fields"]
    assert metadata["does_not_enable_live_call"] is True


def test_run_config_options_reject_retired_save_input_blobs_active_mapping() -> None:
    with pytest.raises(TypeError, match="save_input_blobs_as_artifacts"):
        AdkRunConfigOptions(save_input_blobs_as_artifacts=True)  # type: ignore[call-arg]

    assert "save_input_blobs_as_artifacts" not in ADK_RUN_CONFIG_MAPPER_SUPPORTED_FIELDS
    assert "save_input_blobs_as_artifacts" in ADK_RUN_CONFIG_DEPRECATED_FIELDS
    assert "save_input_blobs_as_artifacts" in ADK_RUN_CONFIG_RETIRED_FIELDS
    assert ADK_RUN_CONFIG_FIELD_POLICIES["save_input_blobs_as_artifacts"][
        "status"
    ] == "retired_deprecated"


def test_run_config_options_translate_legacy_save_live_audio_to_save_live_blob() -> None:
    options = AdkRunConfigOptions(save_live_audio=True)

    run_config = AdkRunConfigMapper().build(options)
    metadata = options.to_metadata()

    assert run_config.save_live_blob is True
    assert "save_live_audio" not in ADK_RUN_CONFIG_MAPPER_SUPPORTED_FIELDS
    assert metadata["legacy_input_fields"] == list(ADK_RUN_CONFIG_LEGACY_INPUT_FIELDS)
    assert metadata["translated_fields"] == ["save_live_audio->save_live_blob"]
    assert metadata["mapped_fields"] == ["save_live_blob"]
    assert metadata["declared_fields"] == ["save_live_blob", "save_live_audio"]
    assert metadata["live_blob_save_requested"] is True
    assert metadata["live_audio_save_requested"] is True


def test_run_config_options_reject_conflicting_live_audio_legacy_input() -> None:
    options = AdkRunConfigOptions(save_live_blob=False, save_live_audio=True)

    with pytest.raises(ValueError, match="save_live_audio.*deprecated.*save_live_blob"):
        AdkRunConfigMapper().build(options)


def test_run_config_options_register_full_adk_2_0_0_capability_surface() -> None:
    from google.adk.runners import RunConfig

    options = AdkRunConfigOptions(
        max_llm_calls=1,
        speech_config={"language_code": "zh-CN"},
        context_window_compression={"kind": "registered-only"},
        tool_thread_pool_config={"max_workers": 2},
    )

    metadata = options.to_metadata()

    assert tuple(RunConfig.model_fields) == ADK_RUN_CONFIG_FIELD_NAMES
    assert metadata["official_fields"] == list(ADK_RUN_CONFIG_FIELD_NAMES)
    assert metadata["field_policies"] == ADK_RUN_CONFIG_FIELD_POLICIES
    assert metadata["declared_fields"] == [
        "max_llm_calls",
        "speech_config",
        "context_window_compression",
        "tool_thread_pool_config",
    ]
    assert metadata["mapped_fields"] == ["max_llm_calls"]
    assert metadata["deferred_fields"] == [
        "speech_config",
        "context_window_compression",
        "tool_thread_pool_config",
    ]


def test_adk_run_config_does_not_import_configuration_center_layers() -> None:
    source = ADK_RUN_CONFIG_SOURCE.read_text(encoding="utf-8")
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+(?:config_assembly|config_contexts)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None
