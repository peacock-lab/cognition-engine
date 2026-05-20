"""Explicit enable intent for ADK SaveFilesAsArtifactsPlugin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from adk_adapter.plugin_bundle import AdkPluginBundle


DEFAULT_SAVE_FILES_AS_ARTIFACTS_PLUGIN_NAME = "save_files_as_artifacts_plugin"


@dataclass(frozen=True)
class AdkSaveFilesAsArtifactsPluginOptions:
    """Adapter-local intent for enabling ADK SaveFilesAsArtifactsPlugin."""

    enabled: bool = False
    name: str = DEFAULT_SAVE_FILES_AS_ARTIFACTS_PLUGIN_NAME
    attach_file_reference: bool = False

    def build_plugin_bundle(self) -> AdkPluginBundle:
        """Build a plugin bundle from an explicit enable intent."""

        if not self.name:
            raise ValueError("SaveFilesAsArtifactsPlugin name must not be empty")
        if self.attach_file_reference:
            raise ValueError(
                "attach_file_reference requires an explicit model-accessible "
                "file reference policy."
            )
        if not self.enabled:
            return AdkPluginBundle.empty(
                source="save_files_as_artifacts_plugin_disabled"
            )

        from google.adk.plugins.save_files_as_artifacts_plugin import (
            SaveFilesAsArtifactsPlugin,
        )

        plugin = SaveFilesAsArtifactsPlugin(
            name=self.name,
            attach_file_reference=False,
        )
        return AdkPluginBundle.from_plugins(
            plugins=[plugin],
            source="save_files_as_artifacts_plugin_enabled",
            plugin_labels=[self.name],
        )

    def metadata(self) -> dict[str, Any]:
        """Return explicit enable intent metadata without raw plugin objects."""

        bundle = self.build_plugin_bundle()
        return {
            "options_type": (
                "adk_adapter.save_files_as_artifacts_plugin."
                "AdkSaveFilesAsArtifactsPluginOptions"
            ),
            "plugin_enable_intent": self.enabled,
            "plugin_name": self.name,
            "attach_file_reference": False,
            "model_accessible_file_reference_enabled": False,
            "default_enabled": False,
            "raw_inline_data_included": False,
            "raw_artifact_content_included": False,
            **bundle.metadata(),
        }


def build_save_files_as_artifacts_plugin_bundle(
    options: AdkSaveFilesAsArtifactsPluginOptions | None = None,
) -> AdkPluginBundle:
    """Build the ADK plugin bundle for explicit file-artifact capture intent."""

    return (options or AdkSaveFilesAsArtifactsPluginOptions()).build_plugin_bundle()
