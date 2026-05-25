"""CLI-local runtime-adjacent helpers."""

from __future__ import annotations

import argparse
import logging
import warnings
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from contract_core.llm_invocation import GovernedLlmInvocationServiceFactory

EntryRunner = Callable[[Any], Mapping[str, Any]]
RequestBuilder = Callable[
    [argparse.Namespace, Mapping[str, Any]], Any
]
RunGatewayExecutor = Callable[..., Any]
OperationFlowLlmInvocationServiceFactory = GovernedLlmInvocationServiceFactory
ExternalReadonlyAskLlmInvocationServiceFactory = GovernedLlmInvocationServiceFactory
ExternalReadonlyAskProviderCredentialStoreFactory = Callable[[], Any]


@contextmanager
def _known_cli_warning_discipline() -> Iterator[None]:
    with warnings.catch_warnings():
        litellm_logger = logging.getLogger("LiteLLM")
        litellm_previous_level = litellm_logger.level
        litellm_logger.setLevel(logging.ERROR)
        warnings.filterwarnings(
            "ignore",
            message=r"authlib\.jose module is deprecated.*",
            category=Warning,
        )
        warnings.filterwarnings(
            "ignore",
            category=Warning,
            module=r"authlib\._joserfc_helpers",
        )
        warnings.filterwarnings(
            "ignore",
            message=r"\[EXPERIMENTAL\] feature FeatureName\..* is enabled\.",
            category=Warning,
        )
        warnings.filterwarnings(
            "ignore",
            category=Warning,
            module=r"google\.adk\.features\._feature_decorator",
        )
        try:
            from authlib.deprecate import AuthlibDeprecationWarning
        except ImportError:
            pass
        else:
            warnings.filterwarnings("ignore", category=AuthlibDeprecationWarning)
        try:
            yield
        finally:
            litellm_logger.setLevel(litellm_previous_level)


def _full_controlled_live_args(args: argparse.Namespace) -> bool:
    return (
        args.request_live_llm is True
        and args.request_ollama is True
        and args.allow_live_llm is True
        and args.allow_ollama is True
        and bool(args.live_llm_approval_ref)
        and (
            args.live_llm_timeout_seconds is None
            or args.live_llm_timeout_seconds > 0
        )
    )
