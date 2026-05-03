from __future__ import annotations

import re
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
    pyproject = (CONTRACT_CORE_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    forbidden_distribution_names = [
        "cognition-engine-runtime",
        "cognition-engine-composition",
        "cognition-engine-adk-adapter",
        "google-adk",
    ]

    for distribution_name in forbidden_distribution_names:
        assert distribution_name not in pyproject


def test_contract_core_source_does_not_import_execution_layers() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+(?:runtime|composition|adk_adapter|google\.adk)\b",
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
