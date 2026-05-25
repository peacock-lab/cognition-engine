"""Product console installed command facade."""

from __future__ import annotations

from collections.abc import Sequence
import warnings


def main(argv: Sequence[str] | None = None) -> int:
    showwarning = warnings.showwarning
    warnings.showwarning = _suppress_import_warning
    try:
        from product_console.console import (
            EvidenceSummaryAnswerAskEntryServices,
            run_product_console,
        )
        from product_runtime_assembly.external_readonly_ask_provider_factory import (
            build_external_readonly_ask_default_llm_invocation_service_factory,
        )
        from product_runtime_assembly.deepseek_credentials import (
            build_default_deepseek_credential_store,
        )
    finally:
        warnings.showwarning = showwarning

    return run_product_console(
        argv,
        ask_services=EvidenceSummaryAnswerAskEntryServices(
            llm_invocation_service_factory=(
                build_external_readonly_ask_default_llm_invocation_service_factory(
                    metadata={
                        "source": (
                            "product_runtime_assembly.entrypoints."
                            "cognition_console"
                        ),
                    },
                )
            ),
        ),
        provider_credential_store_factory=build_default_deepseek_credential_store,
    )


def _suppress_import_warning(*args: object, **kwargs: object) -> None:
    return None


__all__ = ("main",)
