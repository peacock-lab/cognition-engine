"""Product-level provider key setup flow for evidence-summary-answer ask."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal


PROVIDER_KEY_SOURCE_ENVIRONMENT = "environment"
PROVIDER_KEY_SOURCE_PROMPT_ONCE = "prompt_once"
PROVIDER_KEY_SOURCE_PROMPT_STORE = "prompt_store"
PROVIDER_KEY_SOURCE_STORED_KEYCHAIN = "stored_keychain"


@dataclass(frozen=True)
class EvidenceSummaryAnswerProviderKeySetupInput:
    """Channel-collected facts for provider key setup."""

    provider_selected: bool
    environment_key_present: bool
    use_stored_provider_key: bool
    prompt_provider_key: bool
    json_output: bool
    prompt_available: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceSummaryAnswerProviderKeyPromptHandlers:
    """Terminal prompt handlers supplied by a channel adapter."""

    read_secret: Callable[[], str | None]
    read_persistence_choice: Callable[[], Literal["once", "store", "cancel"]]


@dataclass(frozen=True)
class EvidenceSummaryAnswerProviderKeySetupResult:
    """Sanitized provider key setup result."""

    provider_key: str | None = field(default=None, repr=False)
    blocking_reasons: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


def resolve_evidence_summary_answer_provider_key_setup(
    setup_input: EvidenceSummaryAnswerProviderKeySetupInput,
    *,
    prompt_handlers: EvidenceSummaryAnswerProviderKeyPromptHandlers,
    credential_store_factory: Callable[[], Any] | None = None,
    provider_key_required_reason: str = "deepseek_provider_key_required",
    prompt_unavailable_for_json_reason: str = (
        "provider_key_prompt_unavailable_for_json_output"
    ),
    prompt_requires_terminal_reason: str = (
        "provider_key_prompt_requires_interactive_terminal"
    ),
    input_required_reason: str = "provider_key_input_required",
    prompt_cancelled_reason: str = "provider_key_prompt_cancelled",
    stored_not_found_reason: str = "provider_key_stored_credential_not_found",
    stored_load_failed_reason: str = "provider_key_stored_credential_load_failed",
    persistent_save_failed_reason: str = "provider_key_persistent_save_failed",
) -> EvidenceSummaryAnswerProviderKeySetupResult:
    """Resolve provider key availability without exposing raw key in metadata."""

    if not setup_input.provider_selected:
        return EvidenceSummaryAnswerProviderKeySetupResult()
    if setup_input.environment_key_present:
        return EvidenceSummaryAnswerProviderKeySetupResult(
            metadata={
                **dict(setup_input.metadata),
                "provider_key_source": PROVIDER_KEY_SOURCE_ENVIRONMENT,
                "provider_key_store_used": False,
                "provider_key_persistent_save": False,
            },
        )
    if setup_input.use_stored_provider_key:
        stored_result = _load_stored_provider_key(
            credential_store_factory,
            stored_load_failed_reason=stored_load_failed_reason,
            stored_not_found_reason=stored_not_found_reason,
        )
        if stored_result.provider_key:
            return stored_result
        if setup_input.prompt_provider_key is not True:
            return stored_result
    if setup_input.prompt_provider_key is not True:
        return EvidenceSummaryAnswerProviderKeySetupResult(
            blocking_reasons=(provider_key_required_reason,),
            metadata=dict(setup_input.metadata),
        )
    if setup_input.json_output:
        return EvidenceSummaryAnswerProviderKeySetupResult(
            blocking_reasons=(prompt_unavailable_for_json_reason,),
            metadata=dict(setup_input.metadata),
        )
    if not setup_input.prompt_available:
        return EvidenceSummaryAnswerProviderKeySetupResult(
            blocking_reasons=(prompt_requires_terminal_reason,),
            metadata=dict(setup_input.metadata),
        )

    provider_key = prompt_handlers.read_secret()
    if provider_key is None:
        return EvidenceSummaryAnswerProviderKeySetupResult(
            blocking_reasons=(prompt_cancelled_reason,),
            metadata=dict(setup_input.metadata),
        )
    provider_key = provider_key.strip()
    if not provider_key:
        return EvidenceSummaryAnswerProviderKeySetupResult(
            blocking_reasons=(input_required_reason,),
            metadata=dict(setup_input.metadata),
        )

    choice = prompt_handlers.read_persistence_choice()
    if choice == "once":
        return EvidenceSummaryAnswerProviderKeySetupResult(
            provider_key=provider_key,
            metadata={
                **dict(setup_input.metadata),
                "provider_key_source": PROVIDER_KEY_SOURCE_PROMPT_ONCE,
                "provider_key_supplied_by_prompt": True,
                "provider_key_store_used": False,
                "provider_key_persistent_save": False,
            },
        )
    if choice == "store":
        stored_result = _save_provider_key(
            credential_store_factory,
            provider_key,
            persistent_save_failed_reason=persistent_save_failed_reason,
        )
        if stored_result.blocking_reasons:
            return stored_result
        return EvidenceSummaryAnswerProviderKeySetupResult(
            provider_key=provider_key,
            metadata={
                **dict(setup_input.metadata),
                **dict(stored_result.metadata),
                "provider_key_source": PROVIDER_KEY_SOURCE_PROMPT_STORE,
                "provider_key_supplied_by_prompt": True,
                "provider_key_store_used": False,
                "provider_key_persistent_save": True,
            },
        )
    return EvidenceSummaryAnswerProviderKeySetupResult(
        blocking_reasons=(prompt_cancelled_reason,),
        metadata=dict(setup_input.metadata),
    )


def _load_stored_provider_key(
    credential_store_factory: Callable[[], Any] | None,
    *,
    stored_load_failed_reason: str,
    stored_not_found_reason: str,
) -> EvidenceSummaryAnswerProviderKeySetupResult:
    try:
        if credential_store_factory is None:
            raise RuntimeError("provider_key_store_unavailable")
        load_result = credential_store_factory().load_api_key()
    except Exception:
        return EvidenceSummaryAnswerProviderKeySetupResult(
            blocking_reasons=(stored_load_failed_reason,),
            metadata={"provider_key_store_backend": "unknown"},
        )
    metadata = {"provider_key_store_backend": str(load_result.backend)}
    if load_result.status == "success" and load_result.secret_value:
        return EvidenceSummaryAnswerProviderKeySetupResult(
            provider_key=load_result.secret_value,
            metadata={
                **metadata,
                "provider_key_source": PROVIDER_KEY_SOURCE_STORED_KEYCHAIN,
                "provider_key_loaded_from_store": True,
                "provider_key_store_used": True,
                "provider_key_persistent_save": True,
            },
        )
    blocking_reason = load_result.blocking_reason or stored_not_found_reason
    return EvidenceSummaryAnswerProviderKeySetupResult(
        blocking_reasons=(str(blocking_reason),),
        metadata=metadata,
    )

def _save_provider_key(
    credential_store_factory: Callable[[], Any] | None,
    provider_key: str,
    *,
    persistent_save_failed_reason: str,
) -> EvidenceSummaryAnswerProviderKeySetupResult:
    try:
        if credential_store_factory is None:
            raise RuntimeError("provider_key_store_unavailable")
        save_result = credential_store_factory().save_api_key(provider_key)
    except Exception:
        return EvidenceSummaryAnswerProviderKeySetupResult(
            blocking_reasons=(persistent_save_failed_reason,),
            metadata={"provider_key_store_backend": "unknown"},
        )
    metadata = {"provider_key_store_backend": str(save_result.backend)}
    if save_result.status == "success":
        return EvidenceSummaryAnswerProviderKeySetupResult(metadata=metadata)
    blocking_reason = save_result.blocking_reason or persistent_save_failed_reason
    return EvidenceSummaryAnswerProviderKeySetupResult(
        blocking_reasons=(str(blocking_reason),),
        metadata=metadata,
    )
