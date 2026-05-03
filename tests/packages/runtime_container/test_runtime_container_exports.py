from composition.runtime import RuntimeCompositionOptions, build_standard_runtime_runner
from runtime.orchestrator import RuntimeDependencies, StandardRuntimeRunner

from runtime_container import runtime


def test_runtime_container_reexports_stable_runtime_entries() -> None:
    assert runtime.StandardRuntimeRunner is StandardRuntimeRunner
    assert runtime.RuntimeDependencies is RuntimeDependencies
    assert runtime.RuntimeCompositionOptions is RuntimeCompositionOptions
    assert runtime.build_standard_runtime_runner is build_standard_runtime_runner


def test_runtime_container_exports_are_explicit() -> None:
    assert set(runtime.__all__) == {
        "RuntimeCompositionOptions",
        "RuntimeDependencies",
        "StandardRuntimeRunner",
        "build_standard_runtime_runner",
    }
