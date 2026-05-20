"""Chat terminal output helpers for the Cognition System CLI."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from cognition_cli.constants import (
    CHAT_LIVE_NO_PREVIEW_MESSAGE,
    CHAT_NO_LIVE_ASSISTANT_MESSAGE,
    PRODUCT_NAME,
)


def _chat_banner(chat_session_id: str) -> str:
    return "\n".join(
        [
            f"{PRODUCT_NAME} chat",
            f"session: {chat_session_id}",
            "type /help, /status or /exit",
        ]
    )


def _chat_help_text() -> str:
    return "\n".join(
        [
            "commands:",
            "  /help    show chat commands",
            "  /status  show current chat session status",
            "  /status --json  show machine-readable status",
            "  /reference list   show governed reference files",
            "  /reference clear  clear governed reference files",
            "  /exit    close the chat session",
        ]
    )


def _assistant_text_from_chat_turn(
    output: Mapping[str, Any],
    entry_result: Mapping[str, Any] | None,
) -> str:
    if output.get("live_llm_call_performed") is True:
        preview = _find_sanitized_response_preview(entry_result)
        if preview:
            return _normalize_chat_assistant_preview(preview)
        return CHAT_LIVE_NO_PREVIEW_MESSAGE
    return CHAT_NO_LIVE_ASSISTANT_MESSAGE


def _normalize_chat_assistant_preview(preview: str) -> str:
    normalized = preview.strip()
    if not normalized:
        return normalized
    try:
        decoded = json.loads(normalized)
    except json.JSONDecodeError:
        return normalized
    if isinstance(decoded, Mapping):
        for key in ("response", "answer", "content"):
            value = decoded.get(key)
            if isinstance(value, str) and value.strip():
                return " ".join(value.strip().split())
    return normalized


def _find_sanitized_response_preview(value: Any) -> str | None:
    if isinstance(value, Mapping):
        display = value.get("sanitized_response_display")
        if isinstance(display, str) and display.strip():
            return display.strip()
        preview = value.get("sanitized_response_preview")
        if isinstance(preview, str) and preview.strip():
            return preview.strip()
        for nested in value.values():
            found = _find_sanitized_response_preview(nested)
            if found:
                return found
    elif isinstance(value, list | tuple):
        for item in value:
            found = _find_sanitized_response_preview(item)
            if found:
                return found
    return None


def _chat_turn_text_output(
    output: Mapping[str, Any],
    assistant_text: str,
    turn_index: int,
) -> str:
    lines = [
        f"assistant: {assistant_text}",
        f"status: {output['status']}",
        f"turn: {turn_index}",
        f"live_llm_call_performed: {str(output['live_llm_call_performed']).lower()}",
        f"ollama_call_performed: {str(output['ollama_call_performed']).lower()}",
    ]
    blocking_reasons = output.get("blocking_reasons") or []
    warnings = output.get("warnings") or []
    if blocking_reasons:
        lines.append("blocking_reasons: " + ", ".join(map(str, blocking_reasons)))
    if warnings:
        lines.append("warnings: " + ", ".join(map(str, warnings)))
    return "\n".join(lines)
