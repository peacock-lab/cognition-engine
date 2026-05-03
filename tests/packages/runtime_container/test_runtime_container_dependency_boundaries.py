from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_CONTAINER_ROOT = REPO_ROOT / "packages" / "runtime_container"
RUNTIME_CONTAINER_SOURCE_ROOT = RUNTIME_CONTAINER_ROOT / "src" / "runtime_container"
UPSTREAM_SOURCE_ROOTS = [
    REPO_ROOT / "packages" / "runtime" / "src" / "runtime",
    REPO_ROOT / "packages" / "composition" / "src" / "composition",
]


def test_runtime_container_declares_only_allowed_layer_dependencies() -> None:
    pyproject = (RUNTIME_CONTAINER_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "cognition-engine-runtime==0.5.0" in pyproject
    assert "cognition-engine-composition==0.5.0" in pyproject
    assert "cognition-engine-contract-core==0.5.0" in pyproject
    assert "cognition-engine-adk-adapter" not in pyproject
    assert "google-adk" not in pyproject


def test_runtime_container_source_does_not_import_adk_layers() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+(?:adk_adapter|google\.adk)\b",
        re.MULTILINE,
    )

    for source_path in RUNTIME_CONTAINER_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path


def test_runtime_and_composition_do_not_reverse_depend_on_runtime_container() -> None:
    reverse_import = re.compile(r"^\s*(?:from|import)\s+runtime_container\b", re.MULTILINE)

    for source_root in UPSTREAM_SOURCE_ROOTS:
        for source_path in source_root.rglob("*.py"):
            source = source_path.read_text(encoding="utf-8")
            assert reverse_import.search(source) is None, source_path
