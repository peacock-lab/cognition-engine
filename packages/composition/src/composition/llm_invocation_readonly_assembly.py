"""Read-only product assembly for governed LLM invocation facts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cognition_agent import (
    AgentLlmInvocationSummaryCandidate,
    build_agent_llm_invocation_summary_from_observation_candidate,
)
from observability_hub import (
    LlmCallObservationCandidate,
    build_llm_call_observation_from_invocation_result,
)
from schemas.llm_invocation import LlmInvocationResult


@dataclass(frozen=True)
class LlmInvocationReadonlyProductBundle:
    """Compact product bundle for read-only LLM invocation consumption."""

    observation_candidate: LlmCallObservationCandidate
    agent_summary_candidate: AgentLlmInvocationSummaryCandidate
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_public_refs(self) -> dict[str, Any]:
        """Return refs and compact facts without exposing full candidates."""

        request_id = self.observation_candidate.request_id
        return {
            "llm_invocation_observation_ref": f"llm-call-observation://{request_id}",
            "llm_invocation_summary_ref": (
                f"agent-llm-invocation-summary://{request_id}"
            ),
            "llm_invocation_readonly_facts": {
                "observation_candidate_id": (
                    self.observation_candidate.observation_id
                ),
                "agent_summary_candidate_id": (
                    self.agent_summary_candidate.candidate_id
                ),
                "request_id": request_id,
                "model_name": self.observation_candidate.model_name,
                "provider": self.observation_candidate.provider,
                "backend_provider": self.observation_candidate.backend_provider,
                "route_kind": self.observation_candidate.route_kind,
                "route_target": self.observation_candidate.route_target,
                "call_allowed": self.observation_candidate.call_allowed,
                "call_attempted": self.observation_candidate.call_attempted,
                "runtime_call_performed": (
                    self.observation_candidate.runtime_call_performed
                ),
                "success": self.observation_candidate.success,
                "response_non_empty": self.observation_candidate.response_non_empty,
                "sanitized_response_length": (
                    self.observation_candidate.sanitized_response_length
                ),
                "sanitized_response_preview": (
                    self.observation_candidate.sanitized_response_preview
                ),
                "failure_type": self.observation_candidate.failure_type,
                "live_profile": _live_profile_facts(
                    self.observation_candidate.metadata
                ),
                "readonly": self.agent_summary_candidate.readonly,
                "candidate_only": self.agent_summary_candidate.candidate_only,
                "does_not_call_model": True,
                "does_not_store_prompt": True,
                "does_not_store_raw_provider_response": True,
                "metadata": dict(self.metadata),
            },
        }


def build_llm_invocation_readonly_product_bundle(
    invocation_result: LlmInvocationResult | dict[str, Any],
    *,
    metadata: dict[str, Any] | None = None,
) -> LlmInvocationReadonlyProductBundle:
    """Build observation and agent read-only candidates from sanitized result."""

    observation_candidate = build_llm_call_observation_from_invocation_result(
        invocation_result
    )
    agent_summary_candidate = (
        build_agent_llm_invocation_summary_from_observation_candidate(
            candidate_id=(
                f"agent-llm-summary-{observation_candidate.request_id}"
            ),
            observation_candidate=observation_candidate,
            metadata={
                "source": "composition.llm_invocation_readonly_assembly",
                "does_not_call_runtime_container": True,
                "does_not_call_runtime": True,
                "does_not_call_service_invoke": True,
                **(metadata or {}),
            },
            domain_metadata={
                "observation_candidate_ref": (
                    f"llm-call-observation://{observation_candidate.request_id}"
                ),
            },
        )
    )
    return LlmInvocationReadonlyProductBundle(
        observation_candidate=observation_candidate,
        agent_summary_candidate=agent_summary_candidate,
        metadata={
            "assembly": "composition.llm_invocation_readonly_assembly",
            "readonly": True,
            "candidate_only": True,
            "does_not_call_model": True,
            "does_not_call_runtime": True,
            "does_not_call_runtime_container": True,
            "does_not_call_service_invoke": True,
            "does_not_store_prompt": True,
            "does_not_store_completion": True,
            "does_not_store_raw_provider_response": True,
            **(metadata or {}),
        },
    )


def _live_profile_facts(metadata: dict[str, Any]) -> dict[str, Any] | None:
    direct_profile = metadata.get("llm_live_profile")
    if isinstance(direct_profile, dict):
        profile = _compact_live_profile(direct_profile)
        if profile:
            return profile

    result_metadata = metadata.get("result_metadata")
    if isinstance(result_metadata, dict):
        nested_profile = result_metadata.get("llm_live_profile")
        if isinstance(nested_profile, dict):
            profile = _compact_live_profile(nested_profile)
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
