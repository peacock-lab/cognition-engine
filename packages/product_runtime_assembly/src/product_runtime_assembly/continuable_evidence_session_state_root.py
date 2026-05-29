"""State-root resolution for continuable evidence session local storage."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from config_contexts.runtime import ContinuableEvidenceSessionStoragePolicyConfigView

from product_runtime_assembly.continuable_evidence_session_store import (
    resolve_continuable_evidence_session_store_paths,
)


ContinuableEvidenceSessionStateRootSource = Literal[
    "explicit_cli",
    "prompt_selected",
    "env_override",
    "platform_default",
]


@dataclass(frozen=True)
class ContinuableEvidenceSessionStateRootResolution:
    """Resolved local state root plus the user-visible source."""

    state_root: str
    state_root_source: ContinuableEvidenceSessionStateRootSource


def resolve_continuable_evidence_session_state_root(
    *,
    explicit_state_root: str | None = None,
    prompt_selected_state_root: str | None = None,
    config_view: ContinuableEvidenceSessionStoragePolicyConfigView | None = None,
    env: Mapping[str, str] | None = None,
    home_path: Path | None = None,
    platform_name: str | None = None,
) -> ContinuableEvidenceSessionStateRootResolution:
    """Resolve a product-level session state root without touching ADK runtime."""

    config = config_view or ContinuableEvidenceSessionStoragePolicyConfigView()
    environment = env if env is not None else os.environ

    resolution = _first_explicit_resolution(
        explicit_state_root=explicit_state_root,
        prompt_selected_state_root=prompt_selected_state_root,
    )
    if resolution is not None:
        return _validated_resolution(resolution)

    if config.env_override_enabled:
        override_value = _non_blank(environment.get(config.env_override_name))
        if override_value:
            return _validated_resolution(
                ContinuableEvidenceSessionStateRootResolution(
                    state_root=override_value,
                    state_root_source="env_override",
                )
            )

    if not config.default_local_state_dir_enabled:
        raise ValueError("default local state root is disabled.")

    return _validated_resolution(
        ContinuableEvidenceSessionStateRootResolution(
            state_root=str(
                _platform_default_state_root(
                    env=environment,
                    home_path=home_path,
                    platform_name=platform_name,
                )
            ),
            state_root_source="platform_default",
        )
    )


def _first_explicit_resolution(
    *,
    explicit_state_root: str | None,
    prompt_selected_state_root: str | None,
) -> ContinuableEvidenceSessionStateRootResolution | None:
    explicit_value = _non_blank(explicit_state_root)
    if explicit_value:
        return ContinuableEvidenceSessionStateRootResolution(
            state_root=explicit_value,
            state_root_source="explicit_cli",
        )
    prompt_value = _non_blank(prompt_selected_state_root)
    if prompt_value:
        return ContinuableEvidenceSessionStateRootResolution(
            state_root=prompt_value,
            state_root_source="prompt_selected",
        )
    return None


def _platform_default_state_root(
    *,
    env: Mapping[str, str],
    home_path: Path | None,
    platform_name: str | None,
) -> Path:
    home = home_path or Path.home()
    platform = (platform_name or sys.platform).lower()

    if platform.startswith("darwin"):
        return (
            home
            / "Library"
            / "Application Support"
            / "Cognition System"
            / "continuable-evidence-sessions"
        )
    if platform.startswith("win"):
        local_app_data = _non_blank(env.get("LOCALAPPDATA"))
        root = Path(local_app_data) if local_app_data else home / "AppData" / "Local"
        return root / "Cognition System" / "continuable-evidence-sessions"

    xdg_state_home = _non_blank(env.get("XDG_STATE_HOME"))
    root = Path(xdg_state_home) if xdg_state_home else home / ".local" / "state"
    return root / "cognition-system" / "continuable-evidence-sessions"


def _validated_resolution(
    resolution: ContinuableEvidenceSessionStateRootResolution,
) -> ContinuableEvidenceSessionStateRootResolution:
    resolve_continuable_evidence_session_store_paths(resolution.state_root)
    return resolution


def _non_blank(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


__all__ = (
    "ContinuableEvidenceSessionStateRootResolution",
    "ContinuableEvidenceSessionStateRootSource",
    "resolve_continuable_evidence_session_state_root",
)
