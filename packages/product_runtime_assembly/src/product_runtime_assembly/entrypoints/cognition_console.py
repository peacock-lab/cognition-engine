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
        from product_runtime_assembly.continuable_evidence_session_entry import (
            build_product_console_session_action_handler,
            build_product_console_session_save_handler,
        )
    finally:
        warnings.showwarning = showwarning
    storage_config = _load_continuable_evidence_session_storage_config()

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
        session_save_handler=build_product_console_session_save_handler(
            storage_config=storage_config,
        ),
        session_action_handler=build_product_console_session_action_handler(
            storage_config=storage_config,
        ),
        provider_credential_store_factory=build_default_deepseek_credential_store,
    )


def _suppress_import_warning(*args: object, **kwargs: object) -> None:
    return None


def _load_continuable_evidence_session_storage_config():
    from config_assembly.runtime import assemble_packaged_default_runtime_config_payload
    from config_contexts.runtime_builder import build_runtime_config_contexts

    config_context = build_runtime_config_contexts(
        assemble_packaged_default_runtime_config_payload()
    )
    return config_context.continuable_evidence_session_storage


__all__ = ("main",)
