from __future__ import annotations

from pathlib import Path

from config_assembly import assemble_runtime_config_payload, init_default_config_root
from config_contexts.runtime_builder import build_runtime_config_contexts


def test_init_default_config_root_writes_sanitized_baseline(tmp_path: Path) -> None:
    config_root = tmp_path / "config"

    result = init_default_config_root(config_root)

    assert result.source == "package://config_assembly/default_config"
    assert {file.relative_path for file in result.files} == {
        "base/runtime.yaml",
        "templates/runtime.template.yaml",
    }
    assert {file.status for file in result.files} == {"created"}
    assert (config_root / "base" / "runtime.yaml").is_file()
    assert not (config_root / "env" / "local.yaml").exists()

    payload = assemble_runtime_config_payload(config_root, environment="local")
    bundle = build_runtime_config_contexts(payload)

    assert bundle.runtime.runtime_name == "default-runtime"
    assert bundle.tool_exposure.default_profile == "readonly_reference"
    assert bundle.run_workspace.enabled_by_default is False


def test_init_default_config_root_does_not_overwrite_by_default(
    tmp_path: Path,
) -> None:
    config_root = tmp_path / "config"
    result = init_default_config_root(config_root)
    runtime_file = config_root / "base" / "runtime.yaml"
    runtime_file.write_text("runtime:\n  runtime_name: user-owned\n", encoding="utf-8")

    second_result = init_default_config_root(config_root)

    assert {file.status for file in second_result.files} == {"skipped"}
    assert runtime_file.read_text(encoding="utf-8") == (
        "runtime:\n  runtime_name: user-owned\n"
    )
    assert result.config_root == second_result.config_root


def test_init_default_config_root_overwrites_when_explicit(
    tmp_path: Path,
) -> None:
    config_root = tmp_path / "config"
    init_default_config_root(config_root)
    runtime_file = config_root / "base" / "runtime.yaml"
    runtime_file.write_text("runtime:\n  runtime_name: user-owned\n", encoding="utf-8")

    result = init_default_config_root(config_root, overwrite=True)

    assert {file.status for file in result.files} == {"overwritten"}
    assert "runtime_name: default-runtime" in runtime_file.read_text(encoding="utf-8")
