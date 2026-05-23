from __future__ import annotations

import re
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_CORE_ROOT = REPO_ROOT / "packages" / "contract_core"
CONTRACT_CORE_SOURCE_ROOT = CONTRACT_CORE_ROOT / "src" / "contract_core"
UPSTREAM_SOURCE_ROOTS = [
    REPO_ROOT / "packages" / "behavior_contracts" / "src" / "behavior_contracts",
    REPO_ROOT / "packages" / "schemas" / "src" / "schemas",
    REPO_ROOT / "packages" / "config_contexts" / "src" / "config_contexts",
    REPO_ROOT / "packages" / "config_assembly" / "src" / "config_assembly",
]


def test_contract_core_has_no_runtime_container_or_adapter_dependencies() -> None:
    pyproject = tomllib.loads(
        (CONTRACT_CORE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    dependencies = pyproject["project"]["dependencies"]

    forbidden_distribution_names = [
        "cognition-system-runtime",
        "cognition-system-composition",
        "cognition-system-adk-adapter",
        "google-adk",
        "litellm",
    ]

    for distribution_name in forbidden_distribution_names:
        assert all(
            not dependency.startswith(distribution_name)
            for dependency in dependencies
        )


def test_contract_core_declares_config_contexts_without_config_assembly() -> None:
    pyproject = tomllib.loads(
        (CONTRACT_CORE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    package_version = pyproject["project"]["version"]
    dependencies = pyproject["project"]["dependencies"]
    uv_sources = pyproject["tool"]["uv"]["sources"]

    assert f"cognition-system-config-contexts=={package_version}" in dependencies
    assert "cognition-system-config-contexts" in uv_sources
    assert all(
        not dependency.startswith("cognition-system-config-assembly")
        for dependency in dependencies
    )
    assert "cognition-system-config-assembly" not in uv_sources


def test_contract_core_source_does_not_import_execution_layers() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:runtime|composition|adk_adapter|google\.adk|litellm|"
        r"cognition_cli|cognition_operation_flows|external_readonly|"
        r"product_gateway|runtime_container)\b",
        re.MULTILINE,
    )

    for source_path in CONTRACT_CORE_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path


def test_contract_core_source_does_not_import_config_assembly() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+config_assembly\b",
        re.MULTILINE,
    )

    for source_path in CONTRACT_CORE_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path


def test_specialist_contract_packages_do_not_reverse_depend_on_contract_core() -> None:
    reverse_import = re.compile(r"^\s*(?:from|import)\s+contract_core\b", re.MULTILINE)

    for source_root in UPSTREAM_SOURCE_ROOTS:
        for source_path in source_root.rglob("*.py"):
            source = source_path.read_text(encoding="utf-8")
            assert reverse_import.search(source) is None, source_path
