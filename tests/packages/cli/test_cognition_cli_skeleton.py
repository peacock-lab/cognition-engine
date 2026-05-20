from __future__ import annotations

import importlib
import py_compile
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI_PACKAGE_ROOT = REPO_ROOT / "packages" / "cli"
CLI_SRC_ROOT = CLI_PACKAGE_ROOT / "src"
PRODUCT_RUNTIME_ASSEMBLY_PYPROJECT = (
    REPO_ROOT / "packages" / "product_runtime_assembly" / "pyproject.toml"
)


def test_cli_package_metadata_does_not_own_console_script() -> None:
    pyproject = tomllib.loads((CLI_PACKAGE_ROOT / "pyproject.toml").read_text())
    product_runtime_pyproject = tomllib.loads(
        PRODUCT_RUNTIME_ASSEMBLY_PYPROJECT.read_text()
    )

    assert pyproject["project"]["name"] == "cognition-system-cli"
    assert pyproject["project"]["version"] == "0.8.0"
    assert "cognition-system-runtime-container==0.8.0" not in pyproject["project"][
        "dependencies"
    ]
    assert "cognition-system-config-assembly==0.8.0" in pyproject["project"][
        "dependencies"
    ]
    assert "cognition-system-config-contexts==0.8.0" in pyproject["project"][
        "dependencies"
    ]
    assert "cognition-system-contract-core==0.8.0" in pyproject["project"][
        "dependencies"
    ]
    assert "scripts" not in pyproject["project"]
    assert product_runtime_pyproject["project"]["scripts"] == {
        "cognition": "product_runtime_assembly.entrypoints.cognition:main",
    }


def test_candidate_entrypoint_compiles() -> None:
    py_compile.compile(
        str(CLI_SRC_ROOT / "cognition_cli" / "__main__.py"),
        doraise=True,
    )
    py_compile.compile(
        str(CLI_SRC_ROOT / "cognition_cli" / "entrypoints" / "cognition.py"),
        doraise=True,
    )


def test_entrypoint_is_console_script_facade(monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(CLI_SRC_ROOT))

    candidate = importlib.import_module("cognition_cli.entrypoints.cognition")
    source = (CLI_SRC_ROOT / "cognition_cli" / "entrypoints" / "cognition.py").read_text(
        encoding="utf-8"
    )

    assert callable(candidate.main)
    assert callable(candidate.run_cli)
    assert "from cognition_cli.application import main as _main" in source
    assert "def _build_parser" not in source
    assert "from runtime_container.entrypoints.cognition import" not in source
