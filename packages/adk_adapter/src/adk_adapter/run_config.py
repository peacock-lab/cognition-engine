"""ADK RunConfig mapping helpers for workflow runner adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ADK_RUN_CONFIG_VERSION = "2.1.0"
ADK_RUN_CONFIG_FIELD_NAMES = (
    "speech_config",
    "response_modalities",
    "avatar_config",
    "save_input_blobs_as_artifacts",
    "support_cfc",
    "streaming_mode",
    "output_audio_transcription",
    "input_audio_transcription",
    "realtime_input_config",
    "enable_affective_dialog",
    "proactivity",
    "session_resumption",
    "context_window_compression",
    "save_live_blob",
    "tool_thread_pool_config",
    "save_live_audio",
    "max_llm_calls",
    "custom_metadata",
    "get_session_config",
)
ADK_RUN_CONFIG_MAPPER_SUPPORTED_FIELDS = (
    "max_llm_calls",
    "custom_metadata",
    "response_modalities",
    "support_cfc",
    "streaming_mode",
    "get_session_config",
    "enable_affective_dialog",
    "save_live_blob",
)
ADK_RUN_CONFIG_FIELD_POLICIES = {
    "speech_config": {
        "status": "deferred_native_config",
        "reason": "requires google.genai SpeechConfig construction and audio policy review",
    },
    "response_modalities": {
        "status": "mapped",
        "reason": "plain modality list is safe to map as a RunConfig option",
    },
    "avatar_config": {
        "status": "deferred_native_config",
        "reason": "requires google.genai AvatarConfig construction and media policy review",
    },
    "save_input_blobs_as_artifacts": {
        "status": "retired_deprecated",
        "reason": (
            "ADK marks this as deprecated; retired from active RunConfig mapping "
            "in favor of explicit SaveFilesAsArtifactsPlugin enable intent"
        ),
    },
    "support_cfc": {
        "status": "mapped",
        "reason": "plain boolean option",
    },
    "streaming_mode": {
        "status": "mapped",
        "reason": "mapped through ADK StreamingMode enum",
    },
    "output_audio_transcription": {
        "status": "deferred_native_config",
        "reason": "requires AudioTranscriptionConfig construction and audio policy review",
    },
    "input_audio_transcription": {
        "status": "deferred_native_config",
        "reason": "requires AudioTranscriptionConfig construction and audio policy review",
    },
    "realtime_input_config": {
        "status": "deferred_live_media",
        "reason": "realtime input must remain gated outside the no-live default",
    },
    "enable_affective_dialog": {
        "status": "mapped_guarded",
        "reason": "plain flag is mappable but remains product-gated",
    },
    "proactivity": {
        "status": "deferred_native_config",
        "reason": "requires ProactivityConfig construction and behavior policy review",
    },
    "session_resumption": {
        "status": "deferred_native_config",
        "reason": "requires SessionResumptionConfig construction and resume policy review",
    },
    "context_window_compression": {
        "status": "deferred_native_config",
        "reason": "requires ContextWindowCompressionConfig construction and context policy review",
    },
    "save_live_blob": {
        "status": "mapped_guarded",
        "reason": "plain flag is mappable but live blob persistence stays explicitly gated",
    },
    "tool_thread_pool_config": {
        "status": "deferred_tool_execution",
        "reason": "tool execution is outside the first lifecycle-core batch",
    },
    "save_live_audio": {
        "status": "legacy_input_translated",
        "reason": "ADK marks this as deprecated; translated to save_live_blob",
    },
    "max_llm_calls": {
        "status": "mapped",
        "reason": "plain numeric safety bound",
    },
    "custom_metadata": {
        "status": "mapped_metadata_keys_only",
        "reason": "only metadata keys enter governance summaries",
    },
    "get_session_config": {
        "status": "mapped",
        "reason": "mapped through ADK GetSessionConfig",
    },
}
ADK_RUN_CONFIG_DEPRECATED_FIELDS = (
    "save_input_blobs_as_artifacts",
    "save_live_audio",
)
ADK_RUN_CONFIG_RETIRED_FIELDS = ("save_input_blobs_as_artifacts",)
ADK_RUN_CONFIG_LIVE_MEDIA_FIELDS = (
    "realtime_input_config",
    "save_live_blob",
    "save_live_audio",
)
ADK_RUN_CONFIG_LEGACY_INPUT_FIELDS = ("save_live_audio",)
ADK_RUN_CONFIG_DEFERRED_FIELDS = tuple(
    field
    for field in ADK_RUN_CONFIG_FIELD_NAMES
    if field not in ADK_RUN_CONFIG_MAPPER_SUPPORTED_FIELDS
    and field not in ADK_RUN_CONFIG_LEGACY_INPUT_FIELDS
    and field not in ADK_RUN_CONFIG_RETIRED_FIELDS
)


@dataclass(frozen=True)
class AdkRunConfigOptions:
    """Local adapter options that map into a real ADK RunConfig."""

    speech_config: dict[str, Any] | None = None
    max_llm_calls: int | None = None
    custom_metadata: dict[str, Any] = field(default_factory=dict)
    response_modalities: tuple[str, ...] | None = None
    avatar_config: dict[str, Any] | None = None
    support_cfc: bool | None = None
    streaming_mode: str | None = None
    output_audio_transcription: dict[str, Any] | None = None
    input_audio_transcription: dict[str, Any] | None = None
    realtime_input_config: dict[str, Any] | None = None
    enable_affective_dialog: bool | None = None
    proactivity: dict[str, Any] | None = None
    session_resumption: dict[str, Any] | None = None
    context_window_compression: dict[str, Any] | None = None
    save_live_blob: bool | None = None
    tool_thread_pool_config: dict[str, Any] | None = None
    save_live_audio: bool | None = None
    get_session_num_recent_events: int | None = None
    get_session_after_timestamp: float | None = None

    def to_metadata(self) -> dict[str, Any]:
        """Return a plain metadata summary without exposing ADK objects."""

        return {
            "options_type": "adk_adapter.run_config.AdkRunConfigOptions",
            "adk_run_config_version": ADK_RUN_CONFIG_VERSION,
            "official_fields": list(ADK_RUN_CONFIG_FIELD_NAMES),
            "mapper_supported_fields": list(ADK_RUN_CONFIG_MAPPER_SUPPORTED_FIELDS),
            "field_policies": dict(ADK_RUN_CONFIG_FIELD_POLICIES),
            "deprecated_fields": list(ADK_RUN_CONFIG_DEPRECATED_FIELDS),
            "retired_fields": list(ADK_RUN_CONFIG_RETIRED_FIELDS),
            "live_media_fields": list(ADK_RUN_CONFIG_LIVE_MEDIA_FIELDS),
            "legacy_input_fields": self.legacy_input_fields(),
            "translated_fields": self.translated_fields(),
            "declared_fields": self.declared_fields(),
            "mapped_fields": self.mapped_fields(),
            "unmapped_fields": list(ADK_RUN_CONFIG_DEFERRED_FIELDS),
            "deferred_fields": self.deferred_fields(),
            "custom_metadata_keys": sorted(self.custom_metadata),
            "streaming_mode": self.streaming_mode,
            "live_blob_save_requested": self.effective_save_live_blob() is True,
            "live_audio_save_requested": self.save_live_audio is True,
            "does_not_enable_live_call": True,
        }

    def declared_fields(self) -> list[str]:
        """List ADK RunConfig fields explicitly expressed by these options."""

        fields = self.mapped_fields()
        fields.extend(self.legacy_input_fields())
        for field_name in ADK_RUN_CONFIG_DEFERRED_FIELDS:
            if getattr(self, field_name) is not None:
                fields.append(field_name)
        return fields

    def mapped_fields(self) -> list[str]:
        """List ADK RunConfig fields this option object can map today."""

        fields: list[str] = []
        if self.max_llm_calls is not None:
            fields.append("max_llm_calls")
        if self.custom_metadata:
            fields.append("custom_metadata")
        if self.response_modalities is not None:
            fields.append("response_modalities")
        if self.support_cfc is not None:
            fields.append("support_cfc")
        if self.streaming_mode is not None:
            fields.append("streaming_mode")
        if self.enable_affective_dialog is not None:
            fields.append("enable_affective_dialog")
        if self.effective_save_live_blob() is not None:
            fields.append("save_live_blob")
        if (
            self.get_session_num_recent_events is not None
            or self.get_session_after_timestamp is not None
        ):
            fields.append("get_session_config")
        return fields

    def legacy_input_fields(self) -> list[str]:
        """List legacy inputs accepted for compatibility but not actively mapped."""

        fields: list[str] = []
        if self.save_live_audio is not None:
            fields.append("save_live_audio")
        return fields

    def translated_fields(self) -> list[str]:
        """List legacy-to-current field translations applied by this options object."""

        if self.save_live_audio is None:
            return []
        self.effective_save_live_blob()
        return ["save_live_audio->save_live_blob"]

    def effective_save_live_blob(self) -> bool | None:
        """Return save_live_blob after applying legacy save_live_audio translation."""

        if (
            self.save_live_blob is not None
            and self.save_live_audio is not None
            and self.save_live_blob != self.save_live_audio
        ):
            raise ValueError(
                "save_live_audio is a deprecated legacy input and conflicts with "
                "save_live_blob."
            )
        if self.save_live_blob is not None:
            return self.save_live_blob
        return self.save_live_audio

    def deferred_fields(self) -> list[str]:
        """List expressed ADK RunConfig fields registered but not mapped yet."""

        return [
            field_name
            for field_name in ADK_RUN_CONFIG_DEFERRED_FIELDS
            if getattr(self, field_name) is not None
        ]


class AdkRunConfigMapper:
    """Build real ADK RunConfig instances from local adapter options."""

    def build(self, options: AdkRunConfigOptions | None = None) -> Any | None:
        """Build a google.adk RunConfig, or return None when no options exist."""

        if options is None:
            return None

        from google.adk.runners import GetSessionConfig, RunConfig

        kwargs: dict[str, Any] = {}
        if options.max_llm_calls is not None:
            kwargs["max_llm_calls"] = options.max_llm_calls
        if options.custom_metadata:
            kwargs["custom_metadata"] = dict(options.custom_metadata)
        if options.response_modalities is not None:
            kwargs["response_modalities"] = list(options.response_modalities)
        if options.support_cfc is not None:
            kwargs["support_cfc"] = options.support_cfc
        if options.streaming_mode is not None:
            kwargs["streaming_mode"] = self._streaming_mode(options.streaming_mode)
        if options.enable_affective_dialog is not None:
            kwargs["enable_affective_dialog"] = options.enable_affective_dialog
        save_live_blob = options.effective_save_live_blob()
        if save_live_blob is not None:
            kwargs["save_live_blob"] = save_live_blob
        if (
            options.get_session_num_recent_events is not None
            or options.get_session_after_timestamp is not None
        ):
            kwargs["get_session_config"] = GetSessionConfig(
                num_recent_events=options.get_session_num_recent_events,
                after_timestamp=options.get_session_after_timestamp,
            )

        return RunConfig(**kwargs)

    def metadata(self, run_config: Any | None) -> dict[str, Any]:
        """Return a stable metadata summary for a real ADK RunConfig."""

        if run_config is None:
            return {
                "mapper": "adk_adapter.run_config.AdkRunConfigMapper",
                "adk_run_config_type": None,
                "mapped": False,
            }

        custom_metadata = getattr(run_config, "custom_metadata", None) or {}
        get_session_config = getattr(run_config, "get_session_config", None)
        return {
            "mapper": "adk_adapter.run_config.AdkRunConfigMapper",
            "adk_run_config_version": ADK_RUN_CONFIG_VERSION,
            "official_fields": list(ADK_RUN_CONFIG_FIELD_NAMES),
            "mapper_supported_fields": list(ADK_RUN_CONFIG_MAPPER_SUPPORTED_FIELDS),
            "field_policies": dict(ADK_RUN_CONFIG_FIELD_POLICIES),
            "deprecated_fields": list(ADK_RUN_CONFIG_DEPRECATED_FIELDS),
            "retired_fields": list(ADK_RUN_CONFIG_RETIRED_FIELDS),
            "live_media_fields": list(ADK_RUN_CONFIG_LIVE_MEDIA_FIELDS),
            "legacy_input_fields": [],
            "translated_fields": [],
            "unmapped_fields": list(ADK_RUN_CONFIG_DEFERRED_FIELDS),
            "adk_run_config_type": type(run_config).__name__,
            "adk_run_config_module": type(run_config).__module__,
            "mapped": True,
            "max_llm_calls": getattr(run_config, "max_llm_calls", None),
            "custom_metadata_keys": sorted(custom_metadata),
            "response_modalities": getattr(run_config, "response_modalities", None),
            "support_cfc": getattr(run_config, "support_cfc", None),
            "streaming_mode": self._plain_streaming_mode(
                getattr(run_config, "streaming_mode", None)
            ),
            "enable_affective_dialog": getattr(
                run_config,
                "enable_affective_dialog",
                None,
            ),
            "save_live_blob": getattr(run_config, "save_live_blob", None),
            "live_blob_save_requested": getattr(run_config, "save_live_blob", None)
            is True,
            "live_audio_save_requested": False,
            "does_not_enable_live_call": True,
            "get_session_config": self._plain_get_session_config(get_session_config),
        }

    def _streaming_mode(self, value: str) -> Any:
        from google.adk.agents.run_config import StreamingMode

        normalized = value.lower()
        if normalized in {"none", "null"}:
            return StreamingMode.NONE
        if normalized == "sse":
            return StreamingMode.SSE
        if normalized == "bidi":
            return StreamingMode.BIDI
        raise ValueError(f"Unsupported ADK streaming_mode: {value}")

    def _plain_streaming_mode(self, value: Any) -> str | None:
        if value is None:
            return None
        enum_value = getattr(value, "value", value)
        if enum_value is None:
            return "none"
        return str(enum_value)

    def _plain_get_session_config(self, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        return {
            "num_recent_events": getattr(value, "num_recent_events", None),
            "after_timestamp": getattr(value, "after_timestamp", None),
        }
