from __future__ import annotations

import ast
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = (
    REPO_ROOT
    / "packages"
    / "product_runtime_assembly"
    / "src"
    / "product_runtime_assembly"
)
PYPROJECT_PATH = (
    REPO_ROOT / "packages" / "product_runtime_assembly" / "pyproject.toml"
)


def test_product_runtime_assembly_source_has_no_forbidden_runtime_imports() -> None:
    for source_path in PACKAGE_ROOT.rglob("*.py"):
        forbidden_prefixes = _forbidden_import_prefixes(source_path)
        for imported_module in _absolute_imports(source_path):
            for forbidden_prefix in forbidden_prefixes:
                assert not _matches_module_prefix(
                    imported_module,
                    forbidden_prefix,
                ), (source_path, imported_module)


def test_product_runtime_assembly_pyproject_declares_expected_distribution() -> None:
    project = _pyproject()["project"]

    assert project["name"] == "cognition-system-product-runtime-assembly"
    assert project["version"] == "0.8.4"
    assert project["scripts"] == {
        "cognition": "product_runtime_assembly.entrypoints.cognition:main",
        "cognition-console": (
            "product_runtime_assembly.entrypoints.cognition_console:main"
        ),
    }


def test_product_runtime_assembly_pyproject_uses_only_allowed_internal_dependencies() -> None:
    dependencies = tuple(
        dependency
        for dependency in _pyproject()["project"]["dependencies"]
        if dependency.startswith("cognition-system-")
    )

    assert dependencies == (
        "cognition-system-behavior-contracts==0.8.4",
        "cognition-system-cli==0.8.4",
        "cognition-system-config-contexts==0.8.4",
        "cognition-system-contract-core==0.8.4",
        "cognition-system-product-console==0.8.4",
        "cognition-system-product-gateway==0.8.4",
        "cognition-system-runtime-container==0.8.4",
        "cognition-system-schemas==0.8.4",
    )
    dependency_names = tuple(
        dependency.split("==", maxsplit=1)[0] for dependency in dependencies
    )
    for forbidden in (
        "cognition-system-composition",
        "cognition-system-runtime",
        "cognition-system-adk-adapter",
        "google-adk",
        "litellm",
    ):
        assert forbidden not in dependency_names


def _forbidden_import_prefixes(source_path: Path) -> tuple[str, ...]:
    forbidden_prefixes = [
        "composition",
        "runtime",
        "adk_adapter",
        "google.adk",
        "litellm",
        "cognition_operation_flows",
        "product_gateway.contracts",
        "product_gateway._operation_flows",
    ]
    if "entrypoints" not in source_path.relative_to(PACKAGE_ROOT).parts:
        forbidden_prefixes.append("cognition_cli")
    return tuple(forbidden_prefixes)


def _absolute_imports(source_path: Path) -> tuple[str, ...]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.append(node.module)
    return tuple(imports)


def _matches_module_prefix(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(f"{prefix}.")


def _pyproject() -> dict:
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
