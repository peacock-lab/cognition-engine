from __future__ import annotations

import importlib
from pathlib import Path

import runtime_container


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_CONTAINER_ROOT = (
    REPO_ROOT / "packages" / "runtime_container" / "src" / "runtime_container"
)


def test_runtime_container_root_public_surface_is_narrow() -> None:
    assert set(runtime_container.__all__) == {
        "controlled_execution_service",
        "llm_invocation_provider_service",
    }


def test_runtime_container_root_does_not_expose_low_level_facades() -> None:
    forbidden = {
        "adk_workflow_runner_runtime",
        "controlled_adk_run_entry",
        "controlled_live_llm_service",
        "controlled_run_facade",
        "governance_summary_pipeline",
        "llm_invocation_facade",
        "runtime",
    }

    assert forbidden.isdisjoint(set(runtime_container.__all__))
    assert forbidden.isdisjoint(runtime_container._EXPORTED_SUBMODULES)

    for name in forbidden:
        runtime_container.__dict__.pop(name, None)
        try:
            getattr(runtime_container, name)
        except AttributeError:
            continue
        raise AssertionError(f"runtime_container root exposed {name!r}")


def test_runtime_container_reexport_facade_modules_are_removed() -> None:
    removed_modules = (
        "runtime_container.runtime",
        "runtime_container.adk_workflow_runner_runtime",
        "runtime_container.controlled_run_facade",
    )

    for module_name in removed_modules:
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        raise AssertionError(f"{module_name} should not remain importable")


def test_runtime_container_low_level_facade_is_private_module() -> None:
    private_module = importlib.import_module("runtime_container._controlled_run_facade")

    assert hasattr(private_module, "run_controlled_run_facade")
    assert hasattr(private_module, "coerce_controlled_run_facade_input")


def test_runtime_container_root_does_not_list_removed_modules_in_source() -> None:
    source = (RUNTIME_CONTAINER_ROOT / "__init__.py").read_text(encoding="utf-8")

    assert "controlled_run_facade" not in source
    assert "adk_workflow_runner_runtime" not in source
    assert '"runtime"' not in source
