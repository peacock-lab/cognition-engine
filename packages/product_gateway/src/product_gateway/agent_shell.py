"""agent-shell product entry normalization for product_gateway."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayInputRefs,
    ProductGatewayOutputRefs,
    ProductGatewayRef,
    ProductGatewayRequest,
    ProductGatewayResponse,
    ProductGatewayStatus,
)

AGENT_SHELL_RESPONSE_SOURCE = "product_gateway.agent_shell"
AGENT_SHELL_PURPOSE = "agent_shell"

AGENT_SHELL_BLOCKING_ADVICE_STATUSES = frozenset({"blocked", "needs_evidence"})
AGENT_SHELL_FAILED_STATUSES = frozenset({"failure", "failed"})
AGENT_SHELL_SKIPPED_STATUSES = frozenset({"skipped", "not_run"})
AGENT_SHELL_SUCCESS_STATUSES = frozenset(
    {"success", "ready", "ready_for_review"}
)

FORBIDDEN_AGENT_SHELL_INPUT_KEYS = frozenset(
    {
        "AgentShellAuditReadonlyViewCandidate",
        "AgentTaskAdviceCandidate",
        "agent_shell_audit",
        "api_key",
        "artifact_content",
        "credential",
        "credentials",
        "governance_summary_payload",
        "messages",
        "prompt",
        "raw_adk_event",
        "raw_adk_object",
        "raw_adk_session",
        "raw_provider_payload",
        "raw_provider_response",
        "raw_response",
        "response",
        "response_text",
        "secret",
        "token",
        "tool_input",
        "tool_output",
    }
)


class AgentShellGatewayInput(BaseModel):
    """Sanitized agent-shell refs and facts accepted by product_gateway."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    agent_shell_evidence_ref: str | None = None
    agent_shell_run_ref: str | None = None
    agent_shell_audit_ref: str | None = None
    agent_task_advice_ref: str | None = None
    agent_task_advice_candidate_ref: str | None = None
    governance_summary_ref: str | None = None
    agent_shell_status: str | None = None
    agent_shell_failure_type: str | None = None
    agent_shell_controlled_live: bool = False
    agent_shell_runtime_call_performed: bool = False
    agent_shell_call_attempted: bool = False
    agent_shell_ready_for_review: bool = False
    agent_task_recommendation: str | None = None
    agent_task_advice_status: str | None = None
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_agent_shell_input(self) -> "AgentShellGatewayInput":
        _raise_if_forbidden_agent_shell_payload_found(
            self.model_dump(mode="python"),
            field_name="agent_shell_gateway_input",
        )
        if _would_block(self) and not self.blocking_reasons:
            raise ValueError(
                "blocked agent-shell gateway inputs require blocking_reasons."
            )
        return self


class AgentShellCompatibilityProjection(BaseModel):
    """Product-normalized agent-shell projection without execution objects."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    entry_kind: str = Field(..., min_length=1)
    execution_mode: str = Field(..., min_length=1)
    agent_shell_evidence_ref: str | None = None
    agent_shell_run_ref: str | None = None
    agent_shell_audit_ref: str | None = None
    agent_task_advice_ref: str | None = None
    agent_task_advice_candidate_ref: str | None = None
    governance_summary_ref: str | None = None
    agent_shell_status: str | None = None
    agent_shell_failure_type: str | None = None
    agent_shell_controlled_live: bool = False
    agent_shell_runtime_call_performed: bool = False
    agent_shell_call_attempted: bool = False
    agent_shell_ready_for_review: bool = False
    agent_task_recommendation: str | None = None
    agent_task_advice_status: str | None = None
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_agent_shell_gateway_request(
    gateway_input: AgentShellGatewayInput | Mapping[str, Any],
) -> ProductGatewayRequest:
    """Build a product-level agent-shell request from sanitized refs."""

    normalized_input = _coerce_gateway_input(gateway_input)

    return ProductGatewayRequest(
        request_id=normalized_input.request_id,
        entry_kind=ProductGatewayEntryKind.AGENT_SHELL,
        execution_mode=ProductGatewayExecutionMode.NO_LIVE,
        input_refs=ProductGatewayInputRefs(
            governance_summary_ref=normalized_input.governance_summary_ref,
            additional_refs=_input_additional_refs(normalized_input),
        ),
        metadata=_request_metadata(normalized_input),
    )


def build_agent_shell_compatibility_projection(
    gateway_input: AgentShellGatewayInput | Mapping[str, Any],
) -> AgentShellCompatibilityProjection:
    """Build an agent-shell projection without upstream payloads or objects."""

    normalized_input = _coerce_gateway_input(gateway_input)
    gateway_request = build_agent_shell_gateway_request(normalized_input)

    return AgentShellCompatibilityProjection(
        request_id=gateway_request.request_id,
        entry_kind=gateway_request.entry_kind.value,
        execution_mode=gateway_request.execution_mode.value,
        agent_shell_evidence_ref=normalized_input.agent_shell_evidence_ref,
        agent_shell_run_ref=normalized_input.agent_shell_run_ref,
        agent_shell_audit_ref=normalized_input.agent_shell_audit_ref,
        agent_task_advice_ref=normalized_input.agent_task_advice_ref,
        agent_task_advice_candidate_ref=(
            normalized_input.agent_task_advice_candidate_ref
        ),
        governance_summary_ref=normalized_input.governance_summary_ref,
        agent_shell_status=normalized_input.agent_shell_status,
        agent_shell_failure_type=normalized_input.agent_shell_failure_type,
        agent_shell_controlled_live=normalized_input.agent_shell_controlled_live,
        agent_shell_runtime_call_performed=(
            normalized_input.agent_shell_runtime_call_performed
        ),
        agent_shell_call_attempted=normalized_input.agent_shell_call_attempted,
        agent_shell_ready_for_review=(
            normalized_input.agent_shell_ready_for_review
        ),
        agent_task_recommendation=normalized_input.agent_task_recommendation,
        agent_task_advice_status=normalized_input.agent_task_advice_status,
        blocking_reasons=list(normalized_input.blocking_reasons),
        warnings=list(normalized_input.warnings),
        metadata=dict(gateway_request.metadata),
    )


def run_agent_shell_gateway_request(
    gateway_input: AgentShellGatewayInput | Mapping[str, Any],
) -> ProductGatewayResponse:
    """Normalize agent-shell refs and facts into ProductGatewayResponse."""

    gateway_request = build_agent_shell_gateway_request(gateway_input)
    projection = build_agent_shell_compatibility_projection(gateway_input)
    return _product_gateway_response_from_projection(
        gateway_request=gateway_request,
        projection=projection,
    )


def _coerce_gateway_input(
    gateway_input: AgentShellGatewayInput | Mapping[str, Any],
) -> AgentShellGatewayInput:
    if isinstance(gateway_input, AgentShellGatewayInput):
        return gateway_input
    return AgentShellGatewayInput.model_validate(dict(gateway_input))


def _input_additional_refs(
    gateway_input: AgentShellGatewayInput,
) -> list[ProductGatewayRef]:
    return [
        *_refs_from_input(
            gateway_input,
            ("agent_shell_evidence_ref",),
            kind="agent_shell_evidence",
        ),
        *_refs_from_input(
            gateway_input,
            ("agent_shell_run_ref",),
            kind="agent_shell_run",
        ),
        *_refs_from_input(
            gateway_input,
            ("agent_shell_audit_ref",),
            kind="agent_shell_audit",
        ),
        *_refs_from_input(
            gateway_input,
            ("agent_task_advice_ref",),
            kind="agent_task_advice",
        ),
        *_refs_from_input(
            gateway_input,
            ("agent_task_advice_candidate_ref",),
            kind="agent_task_advice_candidate",
        ),
    ]


def _request_metadata(gateway_input: AgentShellGatewayInput) -> dict[str, Any]:
    metadata = dict(gateway_input.metadata)
    metadata.update(_status_metadata(gateway_input))
    metadata["source"] = AGENT_SHELL_RESPONSE_SOURCE
    return _without_none(metadata)


def _product_gateway_response_from_projection(
    *,
    gateway_request: ProductGatewayRequest,
    projection: AgentShellCompatibilityProjection,
) -> ProductGatewayResponse:
    status = _response_status(projection)
    evidence_refs = _refs_from_projection(
        projection,
        ("agent_shell_evidence_ref",),
        kind="agent_shell_evidence",
    )
    audit_refs = _refs_from_projection(
        projection,
        ("agent_shell_run_ref",),
        kind="agent_shell_run",
    )
    audit_refs.extend(
        _refs_from_projection(
            projection,
            ("agent_shell_audit_ref",),
            kind="agent_shell_audit",
        )
    )
    agent_advice_refs = _refs_from_projection(
        projection,
        ("agent_task_advice_ref",),
        kind="agent_task_advice",
    )
    agent_advice_refs.extend(
        _refs_from_projection(
            projection,
            ("agent_task_advice_candidate_ref",),
            kind="agent_task_advice_candidate",
        )
    )

    return ProductGatewayResponse(
        request_id=gateway_request.request_id,
        entry_kind=gateway_request.entry_kind,
        status=status,
        exit_code=_exit_code_for_status(status),
        blocking_reasons=list(projection.blocking_reasons),
        warnings=list(projection.warnings),
        output_refs=ProductGatewayOutputRefs(
            governance_summary_ref=projection.governance_summary_ref,
            evidence_refs=evidence_refs,
            audit_refs=audit_refs,
            agent_advice_refs=agent_advice_refs,
        ),
        governance_summary_ref=projection.governance_summary_ref,
        evidence_refs=evidence_refs,
        audit_refs=audit_refs,
        agent_advice_refs=agent_advice_refs,
        metadata=_response_metadata(projection),
    )


def _response_status(
    projection: AgentShellCompatibilityProjection,
) -> ProductGatewayStatus:
    advice_status = _status_text(projection.agent_task_advice_status)
    shell_status = _status_text(projection.agent_shell_status)

    if advice_status in AGENT_SHELL_BLOCKING_ADVICE_STATUSES:
        return ProductGatewayStatus.BLOCKED
    if shell_status in AGENT_SHELL_FAILED_STATUSES:
        return ProductGatewayStatus.FAILED
    if shell_status in AGENT_SHELL_SKIPPED_STATUSES:
        return ProductGatewayStatus.SKIPPED
    return ProductGatewayStatus.SUCCESS


def _exit_code_for_status(status: ProductGatewayStatus) -> int:
    if status is ProductGatewayStatus.BLOCKED:
        return 2
    if status is ProductGatewayStatus.FAILED:
        return 1
    return 0


def _response_metadata(
    projection: AgentShellCompatibilityProjection,
) -> dict[str, Any]:
    metadata = dict(projection.metadata)
    metadata.update(_status_metadata(projection))
    metadata["source"] = AGENT_SHELL_RESPONSE_SOURCE
    return _without_none(metadata)


def _status_metadata(
    value: AgentShellGatewayInput | AgentShellCompatibilityProjection,
) -> dict[str, Any]:
    return {
        "agent_shell_status": value.agent_shell_status,
        "agent_shell_failure_type": value.agent_shell_failure_type,
        "agent_shell_controlled_live": value.agent_shell_controlled_live,
        "agent_shell_runtime_call_performed": (
            value.agent_shell_runtime_call_performed
        ),
        "agent_shell_call_attempted": value.agent_shell_call_attempted,
        "agent_shell_ready_for_review": value.agent_shell_ready_for_review,
        "agent_task_recommendation": value.agent_task_recommendation,
        "agent_task_advice_status": value.agent_task_advice_status,
    }


def _refs_from_input(
    gateway_input: AgentShellGatewayInput,
    keys: tuple[str, ...],
    *,
    kind: str,
) -> list[ProductGatewayRef]:
    return [
        ProductGatewayRef(
            ref=ref,
            kind=kind,
            purpose=AGENT_SHELL_PURPOSE,
            metadata={"source_key": key},
        )
        for key in keys
        if (ref := _optional_text(getattr(gateway_input, key)))
    ]


def _refs_from_projection(
    projection: AgentShellCompatibilityProjection,
    keys: tuple[str, ...],
    *,
    kind: str,
) -> list[ProductGatewayRef]:
    return [
        ProductGatewayRef(
            ref=ref,
            kind=kind,
            purpose=AGENT_SHELL_PURPOSE,
            metadata={"source_key": key},
        )
        for key in keys
        if (ref := _optional_text(getattr(projection, key)))
    ]


def _would_block(gateway_input: AgentShellGatewayInput) -> bool:
    return (
        _status_text(gateway_input.agent_task_advice_status)
        in AGENT_SHELL_BLOCKING_ADVICE_STATUSES
    )


def _status_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().lower()
    return text or None


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _without_none(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


def _raise_if_forbidden_agent_shell_payload_found(
    value: Any,
    *,
    field_name: str,
) -> None:
    violations = [
        f"{field_name} contains forbidden agent-shell payload at {path}."
        for path, item in _walk(value)
        if _is_forbidden_agent_shell_payload(path, item)
    ]
    if violations:
        raise ValueError("; ".join(violations))


def _is_forbidden_agent_shell_payload(path: str, value: Any) -> bool:
    key = path.rsplit(".", maxsplit=1)[-1].strip("[]'")
    if key in FORBIDDEN_AGENT_SHELL_INPUT_KEYS:
        return True
    if isinstance(value, str):
        return any(token in value for token in FORBIDDEN_AGENT_SHELL_INPUT_KEYS)
    return False


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, dict):
        for key, item in value.items():
            items.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_walk(item, f"{path}[{index}]"))
    return items


__all__ = [
    "AGENT_SHELL_PURPOSE",
    "AGENT_SHELL_RESPONSE_SOURCE",
    "AgentShellCompatibilityProjection",
    "AgentShellGatewayInput",
    "build_agent_shell_compatibility_projection",
    "build_agent_shell_gateway_request",
    "run_agent_shell_gateway_request",
]
