from __future__ import annotations

import importlib
import py_compile
import sys
import tomllib
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI_PACKAGE_ROOT = REPO_ROOT / "packages" / "cli"
CLI_SRC_ROOT = CLI_PACKAGE_ROOT / "src"


def test_cli_package_metadata_owns_console_script() -> None:
    pyproject = tomllib.loads((CLI_PACKAGE_ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["name"] == "cognition-system-cli"
    assert pyproject["project"]["version"] == "0.7.0"
    assert "cognition-system-runtime-container==0.7.0" in pyproject["project"][
        "dependencies"
    ]
    assert pyproject["project"]["scripts"] == {
        "cognition": "cognition_cli.entrypoints.cognition:main",
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


def test_candidate_entrypoint_delegates_to_runtime_container(monkeypatch) -> None:
    captured: dict[str, object] = {}

    runtime_package = ModuleType("runtime_container")
    runtime_package.__path__ = []
    entrypoints_package = ModuleType("runtime_container.entrypoints")
    entrypoints_package.__path__ = []
    cognition_module = ModuleType("runtime_container.entrypoints.cognition")

    def fake_runtime_main(argv=None) -> int:
        captured["argv"] = argv
        return 17

    cognition_module.main = fake_runtime_main
    monkeypatch.setitem(sys.modules, "runtime_container", runtime_package)
    monkeypatch.setitem(sys.modules, "runtime_container.entrypoints", entrypoints_package)
    monkeypatch.setitem(
        sys.modules,
        "runtime_container.entrypoints.cognition",
        cognition_module,
    )
    monkeypatch.syspath_prepend(str(CLI_SRC_ROOT))

    candidate = importlib.import_module("cognition_cli.entrypoints.cognition")

    assert candidate.main(["chat", "--no-banner"]) == 17
    assert captured["argv"] == ["chat", "--no-banner"]
