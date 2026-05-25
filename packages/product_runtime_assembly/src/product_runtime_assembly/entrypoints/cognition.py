"""Console entrypoint assembly for the Cognition System."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def run_cli(argv: Sequence[str] | None = None, **kwargs: Any) -> int:
    """Run cognition CLI with the default product runtime assembly injected."""

    from cognition_cli.entrypoints.cognition import run_cli as _run_cli
    from product_runtime_assembly.cognition_run import (
        execute_cognition_run_with_default_runtime,
    )
    from product_runtime_assembly.external_readonly_ask_provider_factory import (
        build_external_readonly_ask_default_llm_invocation_service_factory,
    )
    from product_runtime_assembly.deepseek_credentials import (
        build_default_deepseek_credential_store,
    )
    from product_runtime_assembly.operation_flow_provider_factory import (
        build_operation_flow_default_llm_invocation_service_factory,
    )

    kwargs.setdefault(
        "run_gateway_executor",
        execute_cognition_run_with_default_runtime,
    )
    kwargs.setdefault(
        "operation_flow_llm_invocation_service_factory",
        build_operation_flow_default_llm_invocation_service_factory(
            metadata={"source": "product_runtime_assembly.entrypoints.cognition"},
        ),
    )
    kwargs.setdefault(
        "external_readonly_ask_llm_invocation_service_factory",
        build_external_readonly_ask_default_llm_invocation_service_factory(
            metadata={"source": "product_runtime_assembly.entrypoints.cognition"},
        ),
    )
    kwargs.setdefault(
        "external_readonly_ask_provider_credential_store_factory",
        build_default_deepseek_credential_store,
    )
    return _run_cli(argv, **kwargs)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Cognition System default command."""

    return run_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
