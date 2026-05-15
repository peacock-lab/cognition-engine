"""Model-routing fact contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


FORBIDDEN_MODEL_ROUTE_METADATA_KEYS = frozenset(
    {
        "completion",
        "message",
        "messages",
        "prompt",
        "response",
        "response_text",
        "text",
    }
)

FORBIDDEN_MODEL_ROUTE_MODULE_PREFIXES = (
    "google.adk",
    "litellm",
    "adk_adapter",
    "runtime_container",
)


class ModelRouteFacts(BaseModel):
    """Public facts for a model route; no model call is represented."""

    model_config = ConfigDict(extra="forbid")

    model_name: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    adk_version: str | None = None
    litellm_version: str | None = None
    pydantic_version: str | None = None
    pydantic_core_version: str | None = None
    runtime_call_performed: bool = False
    direct_litellm_completion: bool = False
    governance_direct_model_call: bool = False
    source: str = Field(default="model_route_facts", min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_route_facts_are_non_executing(self) -> "ModelRouteFacts":
        """Keep model-routing facts separate from model execution."""

        violations: list[str] = []
        if self.runtime_call_performed:
            violations.append("runtime_call_performed must remain false.")
        if self.direct_litellm_completion:
            violations.append("direct_litellm_completion must remain false.")
        if self.governance_direct_model_call:
            violations.append("governance_direct_model_call must remain false.")
        violations.extend(_metadata_boundary_violations(self.metadata))
        if violations:
            raise ValueError("; ".join(violations))
        return self

    def to_observability_input(self) -> dict[str, Any]:
        """Return a plain route-facts payload for observability intake."""

        return {
            "candidate_target": "observability_hub.ModelRouteObservation",
            "model_name": self.model_name,
            "provider": self.provider,
            "adk_version": self.adk_version,
            "litellm_version": self.litellm_version,
            "pydantic_version": self.pydantic_version,
            "pydantic_core_version": self.pydantic_core_version,
            "runtime_call_performed": self.runtime_call_performed,
            "direct_litellm_completion": self.direct_litellm_completion,
            "governance_direct_model_call": self.governance_direct_model_call,
            "source": self.source,
            "metadata": dict(self.metadata),
        }


def _metadata_boundary_violations(value: Any, path: str = "$.metadata") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            key_path = f"{path}.{key_text}"
            if key_text.lower() in FORBIDDEN_MODEL_ROUTE_METADATA_KEYS:
                violations.append(f"model execution payload key is forbidden at {key_path}")
            if key_text == "object_module" and isinstance(item, str):
                if item.startswith(FORBIDDEN_MODEL_ROUTE_MODULE_PREFIXES):
                    violations.append(f"runtime object module is forbidden at {key_path}")
            violations.extend(_metadata_boundary_violations(item, key_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(_metadata_boundary_violations(item, f"{path}[{index}]"))
    return violations
