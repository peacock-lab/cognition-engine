"""LLM invocation observation candidates for observability-hub."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from schemas.llm_invocation import LlmInvocationResult


class LlmCallObservationCandidate(BaseModel):
    """Internal sanitized observation candidate for an LLM invocation."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str
    request_id: str
    model_name: str
    provider: str
    backend_provider: str | None = None
    route_kind: str | None = None
    route_target: str | None = None
    call_attempted: bool = False
    call_allowed: bool = False
    runtime_call_performed: bool = False
    success: bool = False
    response_non_empty: bool = False
    sanitized_response_length: int | None = None
    sanitized_response_preview: str | None = None
    latency_ms: int | None = None
    failure_type: str | None = None
    error_message_sanitized: str | None = None
    governance_decision_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


def build_llm_call_observation_candidate(
    invocation_result: LlmInvocationResult | dict[str, Any],
) -> LlmCallObservationCandidate:
    """Build a sanitized observation candidate from invocation result facts."""

    result = (
        invocation_result
        if isinstance(invocation_result, LlmInvocationResult)
        else LlmInvocationResult.model_validate(invocation_result)
    )
    route_metadata = dict(result.route_facts.metadata)
    result_metadata = dict(result.metadata)
    live_profile = _llm_live_profile(result_metadata)
    metadata: dict[str, Any] = {
        "observation_semantics": "llm_invocation_sanitized_candidate",
        "does_not_store_prompt": True,
        "does_not_store_completion": True,
        "does_not_store_raw_provider_response": True,
        "does_not_call_model": True,
        "route_metadata": route_metadata,
        "result_metadata": result_metadata,
    }
    if live_profile is not None:
        metadata["llm_live_profile"] = live_profile
    return LlmCallObservationCandidate(
        observation_id=f"llm-call-observation-candidate-{uuid4()}",
        request_id=result.request_id,
        model_name=result.route_facts.model_name,
        provider=result.route_facts.provider,
        backend_provider=_optional_str(route_metadata.get("backend_provider")),
        route_kind=_optional_str(route_metadata.get("route_kind")),
        route_target=_optional_str(route_metadata.get("route_target")),
        call_attempted=result.call_attempted,
        call_allowed=result.call_allowed,
        runtime_call_performed=result.runtime_call_performed,
        success=result.success,
        response_non_empty=result.response_non_empty,
        sanitized_response_length=result.sanitized_response_length,
        sanitized_response_preview=result.sanitized_response_preview,
        latency_ms=result.latency_ms,
        failure_type=result.failure_type.value if result.failure_type else None,
        error_message_sanitized=result.error_message_sanitized,
        governance_decision_ref=(
            result.governance_precondition.governance_decision_ref
        ),
        metadata=metadata,
        created_at=datetime.now(UTC).isoformat(),
    )


def build_llm_call_observation_from_invocation_result(
    invocation_result: LlmInvocationResult | dict[str, Any],
) -> LlmCallObservationCandidate:
    """Build a candidate by only reading sanitized invocation result facts."""

    return build_llm_call_observation_candidate(invocation_result)


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _llm_live_profile(result_metadata: dict[str, Any]) -> dict[str, Any] | None:
    direct_profile = result_metadata.get("llm_live_profile")
    if isinstance(direct_profile, dict):
        profile = _compact_live_profile(direct_profile)
        if profile:
            return profile

    options = result_metadata.get("options")
    if isinstance(options, dict):
        profile = _compact_live_profile(options)
        if profile:
            return profile
    return None


def _compact_live_profile(value: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = (
        "controlled_live",
        "live_options_source",
        "live_service_profile",
        "configured_model_name",
        "timeout_seconds",
        "temperature",
        "max_tokens",
        "local_no_proxy_applied",
    )
    return {
        key: item
        for key in allowed_keys
        if (item := value.get(key)) is not None
        and isinstance(item, bool | int | float | str)
    }
