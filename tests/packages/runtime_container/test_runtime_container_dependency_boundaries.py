from __future__ import annotations

import re
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_CONTAINER_ROOT = REPO_ROOT / "packages" / "runtime_container"
RUNTIME_CONTAINER_SOURCE_ROOT = RUNTIME_CONTAINER_ROOT / "src" / "runtime_container"
UPSTREAM_SOURCE_ROOTS = [
    REPO_ROOT / "packages" / "runtime" / "src" / "runtime",
    REPO_ROOT / "packages" / "composition" / "src" / "composition",
]


def test_runtime_container_declares_only_allowed_layer_dependencies() -> None:
    pyproject = tomllib.loads((RUNTIME_CONTAINER_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_version = pyproject["project"]["version"]
    dependencies = pyproject["project"]["dependencies"]

    assert f"cognition-system-runtime=={package_version}" in dependencies
    assert f"cognition-system-composition=={package_version}" in dependencies
    assert f"cognition-system-contract-core=={package_version}" in dependencies
    assert all(
        not dependency.startswith("cognition-system-external-readonly")
        for dependency in dependencies
    )
    assert all(
        not dependency.startswith("cognition-system-cli")
        for dependency in dependencies
    )
    assert all(not dependency.startswith("cognition-system-adk-adapter") for dependency in dependencies)
    assert all(not dependency.startswith("cognition-system-observability-hub") for dependency in dependencies)
    assert all(not dependency.startswith("google-adk") for dependency in dependencies)


def test_runtime_container_source_does_not_import_adk_layers() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+(?:adk_adapter|observability_hub|google\.adk)\b",
        re.MULTILINE,
    )

    for source_path in RUNTIME_CONTAINER_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path


def test_runtime_container_source_does_not_import_external_readonly() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+external_readonly\b",
        re.MULTILINE,
    )

    for source_path in RUNTIME_CONTAINER_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path


def test_runtime_container_source_does_not_import_operation_flows() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+cognition_operation_flows\b",
        re.MULTILINE,
    )

    for source_path in RUNTIME_CONTAINER_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path


def test_runtime_container_source_does_not_import_cli() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+cognition_cli\b",
        re.MULTILINE,
    )

    for source_path in RUNTIME_CONTAINER_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path


def test_runtime_container_old_cli_entrypoint_shim_is_removed() -> None:
    old_entrypoint = RUNTIME_CONTAINER_SOURCE_ROOT / "entrypoints" / "cognition.py"

    assert not old_entrypoint.exists()


def test_runtime_container_source_does_not_read_config_or_assemble_overlay() -> None:
    forbidden_usage = re.compile(
        r"(?:config_assembly|assemble_runtime_config_payload|Path\\([\"']config[\"']\\))"
    )

    for source_path in RUNTIME_CONTAINER_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_usage.search(source) is None, source_path


def test_runtime_and_composition_do_not_reverse_depend_on_runtime_container() -> None:
    reverse_import = re.compile(r"^\s*(?:from|import)\s+runtime_container\b", re.MULTILINE)

    for source_root in UPSTREAM_SOURCE_ROOTS:
        for source_path in source_root.rglob("*.py"):
            source = source_path.read_text(encoding="utf-8")
            assert reverse_import.search(source) is None, source_path
