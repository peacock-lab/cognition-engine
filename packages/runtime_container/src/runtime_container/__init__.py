"""Public runtime-container service modules for Cognition Engine."""

from importlib import import_module
from types import ModuleType

__all__ = [
    "controlled_execution_service",
    "llm_invocation_provider_service",
]

_EXPORTED_SUBMODULES = frozenset(__all__)


def __getattr__(name: str) -> ModuleType:
    if name in _EXPORTED_SUBMODULES:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | _EXPORTED_SUBMODULES)
