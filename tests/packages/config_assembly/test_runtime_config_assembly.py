from pathlib import Path

import pytest

from config_assembly.runtime import (
    RuntimeConfigAssemblyError,
    assemble_runtime_config_payload,
    deep_merge,
    load_yaml_file,
)


def test_deep_merge_preserves_base_and_applies_override() -> None:
    base = {
        "runtime": {"timeout_seconds": 300, "default_adapter": "local"},
        "event_policy": {"enable_event_stream": True},
    }
    override = {
        "runtime": {"timeout_seconds": 180},
    }

    merged = deep_merge(base, override)

    assert merged["runtime"]["timeout_seconds"] == 180
    assert merged["runtime"]["default_adapter"] == "local"
    assert merged["event_policy"]["enable_event_stream"] is True


def test_assemble_runtime_config_payload_from_project_config() -> None:
    payload = assemble_runtime_config_payload(Path("config"), environment="local")

    assert payload.environment == "local"
    assert payload.payload["runtime"]["runtime_name"] == "local-runtime"
    assert payload.payload["runtime"]["timeout_seconds"] == 180
    assert payload.payload["workflow_execution"]["graph_mode"] is True
    assert payload.payload["artifact_policy"]["artifact_name_prefix"] == "ce-runtime-local"


def test_assemble_runtime_config_payload_without_env_override(tmp_path: Path) -> None:
    config_root = tmp_path / "config"
    (config_root / "base").mkdir(parents=True)
    (config_root / "env").mkdir(parents=True)
    (config_root / "base" / "runtime.yaml").write_text(
        "runtime:\n  runtime_name: test-runtime\n  timeout_seconds: 30\n",
        encoding="utf-8",
    )

    payload = assemble_runtime_config_payload(config_root, environment="missing")

    assert payload.environment == "missing"
    assert payload.env_file is None
    assert payload.payload["runtime"]["runtime_name"] == "test-runtime"


def test_load_yaml_file_rejects_non_mapping(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("- item\n", encoding="utf-8")

    with pytest.raises(RuntimeConfigAssemblyError):
        load_yaml_file(path)
