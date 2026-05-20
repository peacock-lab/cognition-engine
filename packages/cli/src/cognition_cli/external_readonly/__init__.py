"""CLI channel helpers for external read-only reference tools."""

from __future__ import annotations

from cognition_cli.external_readonly.answer import (
    EXTERNAL_READONLY_ANSWER_COMMAND,
    EXTERNAL_READONLY_ANSWER_INTERACTION_MODE,
    EXTERNAL_READONLY_ANSWER_REQUEST_ID,
    ExternalReadonlyAnswerLlmInvocationServiceFactory,
    external_readonly_answer_command,
)
from cognition_cli.external_readonly.ask import (
    EXTERNAL_READONLY_ASK_COMMAND,
    EXTERNAL_READONLY_ASK_INTERACTION_MODE,
    EXTERNAL_READONLY_ASK_REQUEST_ID,
    ExternalReadonlyAskLlmInvocationServiceFactory,
    external_readonly_ask_command,
)
from cognition_cli.external_readonly.fetch import (
    REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION,
    external_readonly_fetch_command,
)
from cognition_cli.external_readonly.refs import (
    EXTERNAL_READONLY_REFS_COMMAND,
    ExternalReadonlyRefsApplicationExecutor,
    external_readonly_refs_command,
)

__all__ = [
    "EXTERNAL_READONLY_ANSWER_COMMAND",
    "EXTERNAL_READONLY_ANSWER_INTERACTION_MODE",
    "EXTERNAL_READONLY_ANSWER_REQUEST_ID",
    "EXTERNAL_READONLY_ASK_COMMAND",
    "EXTERNAL_READONLY_ASK_INTERACTION_MODE",
    "EXTERNAL_READONLY_ASK_REQUEST_ID",
    "EXTERNAL_READONLY_REFS_COMMAND",
    "ExternalReadonlyAnswerLlmInvocationServiceFactory",
    "ExternalReadonlyAskLlmInvocationServiceFactory",
    "ExternalReadonlyRefsApplicationExecutor",
    "REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION",
    "external_readonly_answer_command",
    "external_readonly_ask_command",
    "external_readonly_fetch_command",
    "external_readonly_refs_command",
]
