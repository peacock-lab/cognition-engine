"""Thin ADK plugin bundle helpers with safe metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AdkPluginBundleOptions:
    """Local options for building an ADK plugin bundle."""

    source: str = "empty"
    plugins: tuple[Any, ...] = field(default_factory=tuple)
    plugin_labels: tuple[str | None, ...] = field(default_factory=tuple)

    def build_plugin_bundle(self) -> "AdkPluginBundle":
        """Build a plugin bundle from local options."""

        if self.source in {"empty", "none"}:
            if self.plugins:
                raise ValueError(f"{self.source} plugin bundle does not accept plugins")
            return AdkPluginBundle.empty(source=self.source)
        if self.source == "provided_plugins":
            return AdkPluginBundle.from_plugins(
                plugins=self.plugins,
                source=self.source,
                plugin_labels=self.plugin_labels,
            )
        raise ValueError(f"Unsupported ADK plugin bundle source: {self.source}")

    def metadata(self) -> dict[str, Any]:
        """Return option metadata without exposing plugin objects."""

        bundle = self.build_plugin_bundle()
        return {
            "options_type": "adk_adapter.plugin_bundle.AdkPluginBundleOptions",
            "source": self.source,
            "requested_plugin_count": len(self.plugins),
            **bundle.metadata(),
        }


@dataclass(frozen=True)
class AdkPluginBundle:
    """ADK plugins plus safe metadata for App assembly."""

    plugins: tuple[Any, ...] = field(default_factory=tuple)
    source: str = "empty"
    plugin_labels: tuple[str | None, ...] = field(default_factory=tuple)

    @classmethod
    def empty(cls, *, source: str = "empty") -> "AdkPluginBundle":
        """Create an empty plugin bundle."""

        return cls(source=source)

    @classmethod
    def from_plugins(
        cls,
        *,
        plugins: tuple[Any, ...] | list[Any],
        source: str = "provided_plugins",
        plugin_labels: tuple[str | None, ...] | list[str | None] = (),
    ) -> "AdkPluginBundle":
        """Create a plugin bundle from prebuilt ADK plugin objects."""

        plugin_tuple = tuple(plugins)
        label_tuple = tuple(plugin_labels)
        if label_tuple and len(label_tuple) != len(plugin_tuple):
            raise ValueError("plugin_labels length must match plugins length")
        return cls(
            plugins=plugin_tuple,
            source=source,
            plugin_labels=label_tuple,
        )

    @property
    def adk_plugins(self) -> list[Any]:
        """Return ADK plugin objects for App(plugins=...)."""

        return list(self.plugins)

    def metadata(self) -> dict[str, Any]:
        """Return plugin metadata without exposing raw plugin objects."""

        plugin_names = [
            self._plugin_name(plugin, index=index)
            for index, plugin in enumerate(self.plugins)
        ]
        return {
            "plugin_bundle_type": "AdkPluginBundle",
            "plugin_bundle_source": self.source,
            "plugin_count": len(self.plugins),
            "plugin_names": plugin_names,
            "plugin_types": [type(plugin).__name__ for plugin in self.plugins],
            "raw_plugin_object_included": False,
            "duplicate_plugin_names_detected": len(plugin_names)
            != len(set(plugin_names)),
        }

    def _plugin_name(self, plugin: Any, *, index: int) -> str:
        label = self.plugin_labels[index] if index < len(self.plugin_labels) else None
        if label:
            return str(label)
        name = getattr(plugin, "name", None)
        if name:
            return str(name)
        return type(plugin).__name__
