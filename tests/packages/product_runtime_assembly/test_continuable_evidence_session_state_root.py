from __future__ import annotations

from pathlib import Path

import pytest

from config_contexts.runtime import ContinuableEvidenceSessionStoragePolicyConfigView
from product_runtime_assembly.continuable_evidence_session_state_root import (
    resolve_continuable_evidence_session_state_root,
)


def test_state_root_resolver_prefers_explicit_state_root(tmp_path) -> None:
    explicit_root = tmp_path / "explicit-session-state"

    result = resolve_continuable_evidence_session_state_root(
        explicit_state_root=str(explicit_root),
        env={"COGNITION_SESSION_STATE_DIR": str(tmp_path / "env-session-state")},
        home_path=tmp_path / "home",
        platform_name="linux",
    )

    assert result.state_root == str(explicit_root)
    assert result.state_root_source == "explicit_cli"


def test_state_root_resolver_uses_env_override_when_allowed(tmp_path) -> None:
    env_root = tmp_path / "env-session-state"

    result = resolve_continuable_evidence_session_state_root(
        config_view=ContinuableEvidenceSessionStoragePolicyConfigView(),
        env={"COGNITION_SESSION_STATE_DIR": str(env_root)},
        home_path=tmp_path / "home",
        platform_name="linux",
    )

    assert result.state_root == str(env_root)
    assert result.state_root_source == "env_override"


def test_state_root_resolver_uses_platform_default(tmp_path) -> None:
    result = resolve_continuable_evidence_session_state_root(
        env={},
        home_path=tmp_path / "home",
        platform_name="linux",
    )

    assert result.state_root == str(
        tmp_path
        / "home"
        / ".local"
        / "state"
        / "cognition-system"
        / "continuable-evidence-sessions"
    )
    assert result.state_root_source == "platform_default"


def test_state_root_resolver_rejects_outputs_path(tmp_path) -> None:
    with pytest.raises(ValueError):
        resolve_continuable_evidence_session_state_root(
            explicit_state_root=str(Path("outputs") / "session-state"),
            env={},
            home_path=tmp_path / "home",
            platform_name="linux",
        )


def test_state_root_resolver_respects_disabled_default(tmp_path) -> None:
    with pytest.raises(ValueError):
        resolve_continuable_evidence_session_state_root(
            config_view=ContinuableEvidenceSessionStoragePolicyConfigView(
                default_local_state_dir_enabled=False,
                env_override_enabled=False,
            ),
            env={},
            home_path=tmp_path / "home",
            platform_name="linux",
        )
