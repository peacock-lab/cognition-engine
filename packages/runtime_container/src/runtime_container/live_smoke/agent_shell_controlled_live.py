"""Gated real-provider smoke for the ADK Agent shell controlled-live path."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

from composition import run_controlled_live_adk_agent_shell_smoke
from composition.runtime import RuntimeCompositionOptions


SMOKE_NAME = "adk_agent_shell_controlled_live"
DEFAULT_INPUT_TEXT = "cognition run product input"
DEFAULT_INVOCATION_ID = "agent-shell-controlled-live-real-smoke"
DEFAULT_RUNTIME_ID = "runtime-agent-shell-controlled-live-real-smoke"
TRUE_VALUES = {"1", "true", "yes", "on"}


def build_agent_shell_controlled_live_smoke_result(
    *,
    env: Mapping[str, str] | None = None,
    live_client: Any | None = None,
) -> dict[str, Any]:
    """Run or skip the controlled-live Agent shell smoke with sanitized output."""

    values = dict(os.environ if env is None else env)
    live_enabled = _is_enabled(values.get("CE_ENABLE_LIVE_LLM_SMOKE"))
    config_root = values.get("CE_CONFIG_ROOT") or "config"
    environment = values.get("CE_ENVIRONMENT") or "local"
    input_text = values.get("CE_AGENT_SHELL_SMOKE_INPUT") or DEFAULT_INPUT_TEXT
    invocation_id = (
        values.get("CE_AGENT_SHELL_SMOKE_INVOCATION_ID") or DEFAULT_INVOCATION_ID
    )
    runtime_id = values.get("CE_AGENT_SHELL_SMOKE_RUNTIME_ID") or DEFAULT_RUNTIME_ID
    model_name = _blank_to_none(values.get("CE_LIVE_LLM_MODEL"))
    ollama_api_base = _blank_to_none(values.get("OLLAMA_API_BASE"))
    timeout_seconds = _parse_positive_int(values.get("CE_MODEL_TIMEOUT_SECONDS"))
    temperature = _parse_float(values.get("CE_MODEL_TEMPERATURE"))
    max_tokens = _parse_positive_int(values.get("CE_MODEL_MAX_TOKENS"))
    options = RuntimeCompositionOptions(
        config_root=Path(config_root),
        environment=environment,
    )
    metadata = {
        "source": "runtime_container.live_smoke.agent_shell_controlled_live",
        "smoke": SMOKE_NAME,
        "real_provider_smoke": live_enabled and live_client is None,
        "explicit_live_gate": live_enabled,
        "config_root": config_root,
        "environment": environment,
    }

    try:
        result = run_controlled_live_adk_agent_shell_smoke(
            options=options,
            input_text=input_text,
            invocation_id=invocation_id,
            runtime_id=runtime_id,
            live_enabled=live_enabled,
            live_client=live_client,
            model_name=model_name,
            ollama_api_base=ollama_api_base,
            timeout_seconds=timeout_seconds,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=metadata,
        )
        return _build_output(
            live_enabled=live_enabled,
            config_root=config_root,
            environment=environment,
            result=result.to_governance_audit(),
            status=result.status,
            success=result.success,
            failure_type=result.failure_type,
            runtime_call_performed=result.runtime_call_performed,
            call_attempted=result.call_attempted,
            error_message_sanitized=result.error_message_sanitized,
        )
    except Exception as exc:  # noqa: BLE001 - smoke must classify local setup failures.
        failure_type = _classify_environment_failure(exc)
        return _build_output(
            live_enabled=live_enabled,
            config_root=config_root,
            environment=environment,
            result=None,
            status="failure",
            success=False,
            failure_type=failure_type,
            runtime_call_performed=False,
            call_attempted=False,
            error_message_sanitized=_sanitize_error(str(exc)),
        )


def main(argv: list[str] | None = None) -> int:
    """Print sanitized smoke JSON for manual gated execution."""

    parser = argparse.ArgumentParser(
        description="Run the gated ADK Agent shell controlled-live smoke."
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of indented JSON.",
    )
    args = parser.parse_args(argv)
    result = build_agent_shell_controlled_live_smoke_result()
    indent = None if args.compact else 2
    print(json.dumps(result, ensure_ascii=False, indent=indent, sort_keys=True))
    return 0


def _build_output(
    *,
    live_enabled: bool,
    config_root: str,
    environment: str,
    result: dict[str, Any] | None,
    status: str,
    success: bool,
    failure_type: str | None,
    runtime_call_performed: bool,
    call_attempted: bool,
    error_message_sanitized: str | None,
) -> dict[str, Any]:
    audit = _compact_audit(result)
    live_profile = audit.get("live_profile", {})
    return {
        "smoke": SMOKE_NAME,
        "status": status,
        "success": success,
        "failure_type": failure_type,
        "live_enabled": live_enabled,
        "explicit_live_gate": live_enabled,
        "runtime_call_performed": runtime_call_performed,
        "call_attempted": call_attempted,
        "error_message_sanitized": error_message_sanitized,
        "config": {
            "config_root": config_root,
            "environment": environment,
            "model": live_profile.get("configured_model_name"),
            "ollama_api_base": live_profile.get("ollama_api_base"),
            "timeout_seconds": live_profile.get("timeout_seconds"),
            "temperature": live_profile.get("temperature"),
            "max_tokens": live_profile.get("max_tokens"),
            "live_service_profile": live_profile.get("live_service_profile"),
        },
        "agent_shell_audit": audit,
        "does_not_store_prompt": True,
        "does_not_store_messages": True,
        "does_not_store_raw_response": True,
        "raw_provider_payload_included": False,
    }


def _compact_audit(audit: dict[str, Any] | None) -> dict[str, Any]:
    if not audit:
        return {}
    return {
        "agent_shell_evidence_ref": audit.get("agent_shell_evidence_ref"),
        "agent_shell_run_ref": audit.get("agent_shell_run_ref"),
        "agent_name": audit.get("agent_name"),
        "agent_type": audit.get("agent_type"),
        "app_name": audit.get("app_name"),
        "status": audit.get("status"),
        "event_count": audit.get("event_count"),
        "controlled_live": audit.get("controlled_live"),
        "controlled_live_smoke": audit.get("controlled_live_smoke"),
        "controlled_live_smoke_enabled": audit.get("controlled_live_smoke_enabled"),
        "runtime_call_performed": audit.get("runtime_call_performed"),
        "call_attempted": audit.get("call_attempted"),
        "failure_type": audit.get("failure_type"),
        "error_message_sanitized": audit.get("error_message_sanitized"),
        "live_profile": dict(audit.get("live_profile") or {}),
        "does_not_store_prompt": audit.get("does_not_store_prompt"),
        "does_not_store_raw_response": audit.get("does_not_store_raw_response"),
        "raw_adk_object_included": audit.get("raw_adk_object_included"),
        "raw_adk_event_included": audit.get("raw_adk_event_included"),
        "raw_adk_session_included": audit.get("raw_adk_session_included"),
    }


def _is_enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in TRUE_VALUES


def _blank_to_none(value: str | None) -> str | None:
    stripped = str(value or "").strip()
    return stripped or None


def _parse_positive_int(value: str | None) -> int | None:
    stripped = _blank_to_none(value)
    if stripped is None:
        return None
    parsed = int(stripped)
    if parsed <= 0:
        raise ValueError(f"expected positive integer, got {parsed}")
    return parsed


def _parse_float(value: str | None) -> float | None:
    stripped = _blank_to_none(value)
    if stripped is None:
        return None
    return float(stripped)


def _classify_environment_failure(exc: Exception) -> str:
    message = str(exc).lower()
    if "timeout" in message:
        return "timeout_failure"
    if any(
        marker in message
        for marker in (
            "connection refused",
            "connecterror",
            "connection error",
            "provider unavailable",
            "ollama",
            "api_base",
        )
    ):
        return "provider_unavailable"
    if isinstance(exc, (FileNotFoundError, ValueError, KeyError)):
        return "environment_unavailable"
    return "live_call_failure"


def _sanitize_error(value: str, limit: int = 240) -> str:
    sanitized = " ".join(str(value).split())
    for marker in (
        "api_key",
        "completion",
        "message",
        "messages",
        "prompt",
        "raw_provider_response",
        "raw_response",
        "response_text",
        "system_prompt",
        "token",
        "secret",
    ):
        sanitized = sanitized.replace(marker, "[redacted]")
    if len(sanitized) <= limit:
        return sanitized
    return sanitized[:limit]


if __name__ == "__main__":
    raise SystemExit(main())
