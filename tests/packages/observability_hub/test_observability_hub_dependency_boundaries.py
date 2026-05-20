from __future__ import annotations

import re
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
OBSERVABILITY_HUB_ROOT = REPO_ROOT / "packages" / "observability_hub"
OBSERVABILITY_HUB_SOURCE_ROOT = OBSERVABILITY_HUB_ROOT / "src" / "observability_hub"
COMPOSITION_SOURCE_ROOT = REPO_ROOT / "packages" / "composition" / "src" / "composition"
FORBIDDEN_REVERSE_DEPENDENCY_SOURCE_ROOTS = [
    ("runtime", REPO_ROOT / "packages" / "runtime" / "src" / "runtime"),
    ("runtime_container", REPO_ROOT / "packages" / "runtime_container" / "src" / "runtime_container"),
    ("contract_core", REPO_ROOT / "packages" / "contract_core" / "src" / "contract_core"),
    ("product_gateway", REPO_ROOT / "packages" / "product_gateway" / "src" / "product_gateway"),
    (
        "task_workflows",
        REPO_ROOT / "packages" / "task_workflows" / "src" / "cognition_task_workflows",
    ),
    ("external_readonly", REPO_ROOT / "packages" / "external_readonly" / "src" / "external_readonly"),
    ("cli", REPO_ROOT / "packages" / "cli" / "src" / "cognition_cli"),
]


def test_observability_hub_declares_only_allowed_first_batch_dependencies() -> None:
    pyproject = tomllib.loads(
        (OBSERVABILITY_HUB_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    package_version = pyproject["project"]["version"]
    dependencies = pyproject["project"]["dependencies"]

    assert f"cognition-system-schemas=={package_version}" in dependencies
    assert f"cognition-system-contract-core=={package_version}" in dependencies
    assert "pydantic>=2.13.0" in dependencies
    assert all(
        not dependency.startswith("cognition-system-runtime-container")
        for dependency in dependencies
    )
    assert all(
        not dependency.startswith("cognition-system-adk-adapter")
        for dependency in dependencies
    )
    assert all(not dependency.startswith("google-adk") for dependency in dependencies)
    assert all(
        not dependency.startswith("cognition-system-runtime")
        for dependency in dependencies
    )
    assert all(
        not dependency.startswith("cognition-system-composition")
        for dependency in dependencies
    )
    assert all(
        not dependency.startswith("cognition-system-behavior-contracts")
        for dependency in dependencies
    )
    assert all(
        not dependency.startswith("cognition-system-config-contexts")
        for dependency in dependencies
    )


def test_observability_hub_source_does_not_import_forbidden_layers() -> None:
    forbidden_imports = re.compile(
        (
            r"^\s*(?:from|import)\s+(?:"
            r"adk_adapter|behavior_contracts|config_contexts|google\.adk|"
            r"runtime_container|runtime|composition|product_gateway|"
            r"product_runtime_assembly|cognition_cli"
            r")\b"
        ),
        re.MULTILINE,
    )

    for source_path in OBSERVABILITY_HUB_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path


def test_non_composition_packages_do_not_reverse_depend_on_observability_hub() -> None:
    reverse_import = re.compile(r"^\s*(?:from|import)\s+observability_hub\b", re.MULTILINE)

    for package_name, source_root in FORBIDDEN_REVERSE_DEPENDENCY_SOURCE_ROOTS:
        assert source_root.exists(), f"{package_name}: {source_root}"
        for source_path in source_root.rglob("*.py"):
            source = source_path.read_text(encoding="utf-8")
            assert reverse_import.search(source) is None, f"{package_name}: {source_path}"


def test_composition_is_the_allowed_observability_hub_assembly_root() -> None:
    reverse_import = re.compile(r"^\s*(?:from|import)\s+observability_hub\b", re.MULTILINE)
    assert COMPOSITION_SOURCE_ROOT.exists()

    composition_imports = [
        source_path
        for source_path in COMPOSITION_SOURCE_ROOT.rglob("*.py")
        if reverse_import.search(source_path.read_text(encoding="utf-8"))
    ]

    assert composition_imports
