from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOTS = {
    "runtime": REPO_ROOT / "packages" / "runtime" / "src" / "runtime",
    "runtime_container": (
        REPO_ROOT / "packages" / "runtime_container" / "src" / "runtime_container"
    ),
    "composition": REPO_ROOT / "packages" / "composition" / "src" / "composition",
    "product_gateway": (
        REPO_ROOT / "packages" / "product_gateway" / "src" / "product_gateway"
    ),
    "product_runtime_assembly": (
        REPO_ROOT
        / "packages"
        / "product_runtime_assembly"
        / "src"
        / "product_runtime_assembly"
    ),
    "operation_flows": (
        REPO_ROOT
        / "packages"
        / "operation_flows"
        / "src"
        / "cognition_operation_flows"
    ),
    "cli": REPO_ROOT / "packages" / "cli" / "src" / "cognition_cli",
}


def test_runtime_support_layer_does_not_import_container_or_assembly_layers() -> None:
    forbidden = (
        "runtime_container",
        "composition",
        "adk_adapter",
        "google.adk",
        "litellm",
        "product_gateway",
        "cognition_cli",
    )

    _assert_sources_do_not_import(PACKAGE_ROOTS["runtime"], forbidden)


def test_runtime_container_does_not_import_product_or_adapter_layers() -> None:
    forbidden = (
        "product_gateway",
        "cognition_cli",
        "cognition_operation_flows",
        "adk_adapter",
        "google.adk",
        "litellm",
    )

    _assert_sources_do_not_import(PACKAGE_ROOTS["runtime_container"], forbidden)


def test_composition_root_does_not_import_runtime_container_or_product_layers() -> None:
    forbidden = (
        "runtime_container",
        "product_gateway",
        "cognition_cli",
        "cognition_operation_flows",
    )

    _assert_sources_do_not_import(PACKAGE_ROOTS["composition"], forbidden)


def test_product_gateway_does_not_import_runtime_container() -> None:
    _assert_sources_do_not_import(
        PACKAGE_ROOTS["product_gateway"],
        ("runtime_container",),
    )


def test_product_runtime_assembly_stays_out_of_composition_and_runtime_layers() -> None:
    base_forbidden = (
        "composition",
        "runtime",
        "adk_adapter",
        "google.adk",
        "litellm",
        "cognition_operation_flows",
        "product_gateway._operation_flows",
        "product_gateway.contracts",
    )

    for source_path in PACKAGE_ROOTS["product_runtime_assembly"].rglob("*.py"):
        forbidden = base_forbidden
        if "entrypoints" not in source_path.relative_to(
            PACKAGE_ROOTS["product_runtime_assembly"]
        ).parts:
            forbidden = (*forbidden, "cognition_cli")
        _assert_source_does_not_import(source_path, forbidden)


def test_cli_and_operation_flows_do_not_import_runtime_container_or_composition() -> None:
    forbidden = ("runtime_container", "composition")

    _assert_sources_do_not_import(PACKAGE_ROOTS["cli"], forbidden)
    _assert_sources_do_not_import(PACKAGE_ROOTS["operation_flows"], forbidden)


def _assert_sources_do_not_import(source_root: Path, forbidden: tuple[str, ...]) -> None:
    for source_path in source_root.rglob("*.py"):
        _assert_source_does_not_import(source_path, forbidden)


def _assert_source_does_not_import(source_path: Path, forbidden: tuple[str, ...]) -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+(?:"
        + "|".join(re.escape(module) for module in forbidden)
        + r")\b",
        re.MULTILINE,
    )

    source = source_path.read_text(encoding="utf-8")
    assert forbidden_imports.search(source) is None, source_path
