"""Read-only product gateway response view for cognition agent consumers."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator
from schemas.product_gateway_response_summary import (
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_ENTRY_KINDS,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_STATUSES,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION,
    validate_product_gateway_response_summary,
)

from cognition_agent.models import AgentBaseCandidate


AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_VERSION = (
    "agent_product_gateway_response_view_v1"
)
AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_SOURCE = (
    "cognition_agent.product_gateway_response_view"
)

PRODUCT_GATEWAY_ENTRY_KINDS = PRODUCT_GATEWAY_RESPONSE_SUMMARY_ENTRY_KINDS
PRODUCT_GATEWAY_STATUSES = PRODUCT_GATEWAY_RESPONSE_SUMMARY_STATUSES

FORBIDDEN_PRODUCT_GATEWAY_RESPONSE_KEYS = frozenset(
    {
        "api_key",
        "artifact_content",
        "completion",
        "credential",
        "credentials",
        "full_response",
        "message",
        "messages",
        "prompt",
        "raw_provider_response",
        "raw_response",
        "raw_tool_input",
        "raw_tool_output",
        "response",
        "response_text",
        "secret",
        "system_prompt",
        "text",
        "token",
    }
)


class AgentProductGatewayRefViewCandidate(AgentBaseCandidate):
    """Read-only reference projected from a product gateway response summary."""

    candidate_type: str = "agent_product_gateway_ref_view_candidate"
    ref: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1)
    purpose: str | None = None
    readonly: bool = True
    candidate_only: bool = True

    @model_validator(mode="after")
    def validate_product_gateway_ref_view(
        self,
    ) -> "AgentProductGatewayRefViewCandidate":
        if not self.readonly:
            raise ValueError("readonly must remain true.")
        if not self.candidate_only:
            raise ValueError("candidate_only must remain true.")
        violations = _forbidden_response_summary_violations(
            self.model_dump(mode="python")
        )
        if violations:
            raise ValueError("; ".join(violations))
        return self


class AgentProductGatewayResponseViewCandidate(AgentBaseCandidate):
    """Agent-facing read-only view over a product gateway response summary."""

    candidate_type: str = "agent_product_gateway_response_view_candidate"
    view_version: str = AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_VERSION
    product_gateway_request_id: str
    product_gateway_entry_kind: str
    product_gateway_status: str
    product_gateway_exit_code: int | None = None
    product_gateway_response_ref: str | None = None
    product_gateway_governance_summary_ref: str | None = None
    product_gateway_evidence_refs: list[AgentProductGatewayRefViewCandidate] = Field(
        default_factory=list
    )
    product_gateway_audit_refs: list[AgentProductGatewayRefViewCandidate] = Field(
        default_factory=list
    )
    product_gateway_agent_advice_refs: list[
        AgentProductGatewayRefViewCandidate
    ] = Field(default_factory=list)
    product_gateway_tool_audit_refs: list[AgentProductGatewayRefViewCandidate] = Field(
        default_factory=list
    )
    product_gateway_blocking_reasons: list[str] = Field(default_factory=list)
    product_gateway_warnings: list[str] = Field(default_factory=list)
    product_gateway_ready_for_review: bool = False
    product_gateway_requires_review: bool = False
    readonly: bool = True
    candidate_only: bool = True
    execution_enabled: bool = False
    runtime_permission_granted: bool = False
    agent_runtime_enabled: bool = False
    llm_call_enabled: bool = False
    action_execution_enabled: bool = False
    chat_enabled: bool = False
    gateway_enabled: bool = False
    tool_execution_enabled: bool = False

    @model_validator(mode="after")
    def validate_product_gateway_response_view(
        self,
    ) -> "AgentProductGatewayResponseViewCandidate":
        if self.product_gateway_entry_kind not in PRODUCT_GATEWAY_ENTRY_KINDS:
            raise ValueError("unsupported product_gateway entry_kind.")
        if self.product_gateway_status not in PRODUCT_GATEWAY_STATUSES:
            raise ValueError("unsupported product_gateway status.")
        if (
            self.product_gateway_status == "blocked"
            and not self.product_gateway_blocking_reasons
        ):
            raise ValueError("blocked product_gateway summaries require blocking_reasons.")
        _validate_non_executing_flags(self)
        violations = _forbidden_response_summary_violations(
            self.model_dump(mode="python")
        )
        if violations:
            raise ValueError("; ".join(violations))
        return self


def build_agent_product_gateway_response_view_candidate(
    *,
    candidate_id: str,
    summary: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> AgentProductGatewayResponseViewCandidate:
    """Build a non-executing agent view from a product gateway response summary."""

    summary_contract = validate_product_gateway_response_summary(summary)
    safe_summary = summary_contract.model_dump(mode="python")
    safe_metadata = _safe_mapping(metadata or {}, path="$.metadata")
    safe_domain_metadata = _safe_mapping(
        domain_metadata or {}, path="$.domain_metadata"
    )

    status = summary_contract.status
    blocking_reasons = list(summary_contract.blocking_reasons)
    warnings = list(summary_contract.warnings)
    ready_for_review = status in {"success", "skipped"} and not blocking_reasons
    requires_review = status in {"blocked", "failed"} or bool(blocking_reasons)
    response_ref = summary_contract.product_gateway_response_ref
    governance_summary_ref = summary_contract.governance_summary_ref

    return AgentProductGatewayResponseViewCandidate(
        candidate_id=candidate_id,
        source=AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_SOURCE,
        summary=_summary_text(
            entry_kind=str(safe_summary["entry_kind"]),
            status=status,
            ready_for_review=ready_for_review,
            requires_review=requires_review,
        ),
        product_gateway_request_id=str(safe_summary["request_id"]),
        product_gateway_entry_kind=str(safe_summary["entry_kind"]),
        product_gateway_status=status,
        product_gateway_exit_code=_optional_int(safe_summary.get("exit_code")),
        product_gateway_response_ref=response_ref,
        product_gateway_governance_summary_ref=governance_summary_ref,
        product_gateway_evidence_refs=_refs(
            safe_summary.get("evidence_refs") or (),
            category="evidence_refs",
        ),
        product_gateway_audit_refs=_refs(
            safe_summary.get("audit_refs") or (),
            category="audit_refs",
        ),
        product_gateway_agent_advice_refs=_refs(
            safe_summary.get("agent_advice_refs") or (),
            category="agent_advice_refs",
        ),
        product_gateway_tool_audit_refs=_refs(
            safe_summary.get("tool_audit_refs") or (),
            category="tool_audit_refs",
        ),
        product_gateway_blocking_reasons=blocking_reasons,
        product_gateway_warnings=warnings,
        product_gateway_ready_for_review=ready_for_review,
        product_gateway_requires_review=requires_review,
        governance_refs=_governance_refs(
            governance_summary_ref=governance_summary_ref,
            evidence_refs=safe_summary.get("evidence_refs") or (),
            audit_refs=safe_summary.get("audit_refs") or (),
            tool_audit_refs=safe_summary.get("tool_audit_refs") or (),
        ),
        metadata={
            "view_semantics": "agent_product_gateway_response_readonly_view",
            "readonly": True,
            "candidate_only": True,
            "view_version": AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_VERSION,
            "product_gateway_response_summary_version": (
                PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION
            ),
            "does_not_call_product_gateway": True,
            "does_not_call_runtime": True,
            "does_not_call_runtime_container": True,
            "does_not_call_llm": True,
            "does_not_execute_action": True,
            "does_not_enable_gateway": True,
            "does_not_enable_tool_executor": True,
            "product_gateway_response_is_readonly_summary": True,
            "product_gateway_response_is_not_public_contract": True,
            "product_gateway_source": _metadata_source(safe_summary.get("metadata")),
            **safe_metadata,
        },
        domain_metadata=safe_domain_metadata,
    )


def _validate_non_executing_flags(
    candidate: AgentProductGatewayResponseViewCandidate,
) -> None:
    if not candidate.readonly:
        raise ValueError("readonly must remain true.")
    if not candidate.candidate_only:
        raise ValueError("candidate_only must remain true.")
    if candidate.execution_enabled:
        raise ValueError("execution_enabled must remain false.")
    if candidate.runtime_permission_granted:
        raise ValueError("runtime_permission_granted must remain false.")
    if candidate.agent_runtime_enabled:
        raise ValueError("agent_runtime_enabled must remain false.")
    if candidate.llm_call_enabled:
        raise ValueError("llm_call_enabled must remain false.")
    if candidate.action_execution_enabled:
        raise ValueError("action_execution_enabled must remain false.")
    if candidate.chat_enabled:
        raise ValueError("chat_enabled must remain false.")
    if candidate.gateway_enabled:
        raise ValueError("gateway_enabled must remain false.")
    if candidate.tool_execution_enabled:
        raise ValueError("tool_execution_enabled must remain false.")


def _refs(
    values: Any,
    *,
    category: str,
) -> list[AgentProductGatewayRefViewCandidate]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"{category} must be a list.")
    result: list[AgentProductGatewayRefViewCandidate] = []
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            raise ValueError(f"{category}[{index}] must be a mapping.")
        safe_value = _safe_mapping(value, path=f"$.summary.{category}[{index}]")
        ref = _optional_string(safe_value.get("ref"))
        kind = _optional_string(safe_value.get("kind"))
        if ref is None or kind is None:
            raise ValueError(f"{category}[{index}] requires ref and kind.")
        result.append(
            AgentProductGatewayRefViewCandidate(
                candidate_id=f"product-gateway-ref-{category}-{index}",
                source=AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_SOURCE,
                summary=(
                    "Product gateway response ref view: "
                    f"category={category}, kind={kind}."
                ),
                ref=ref,
                kind=kind,
                purpose=_optional_string(safe_value.get("purpose")),
                metadata=_safe_mapping(
                    safe_value.get("metadata") or {},
                    path=f"$.summary.{category}[{index}].metadata",
                ),
            )
        )
    return result


def _governance_refs(
    *,
    governance_summary_ref: str | None,
    evidence_refs: Any,
    audit_refs: Any,
    tool_audit_refs: Any,
) -> list[str]:
    refs = []
    if governance_summary_ref:
        refs.append(governance_summary_ref)
    for values in (evidence_refs, audit_refs, tool_audit_refs):
        if isinstance(values, (list, tuple)):
            refs.extend(
                ref
                for ref in (_ref_value(value) for value in values)
                if ref is not None
            )
    return _unique(refs)


def _ref_value(value: Any) -> str | None:
    if isinstance(value, dict):
        return _optional_string(value.get("ref"))
    return None


def _summary_text(
    *,
    entry_kind: str,
    status: str,
    ready_for_review: bool,
    requires_review: bool,
) -> str:
    return (
        "Agent product gateway response view: "
        f"entry_kind={entry_kind}, status={status}, "
        f"ready_for_review={ready_for_review}, "
        f"requires_review={requires_review}. "
        "This is a read-only view over the public response summary contract."
    )


def _safe_mapping(value: dict[str, Any], *, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a mapping.")
    violations = _forbidden_response_summary_violations(value, path=path)
    if violations:
        raise ValueError("; ".join(violations))
    return dict(value)


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("exit_code must be an integer.")
    if isinstance(value, int):
        return value
    raise ValueError("exit_code must be an integer.")


def _metadata_source(value: Any) -> str | None:
    if isinstance(value, dict):
        return _optional_string(value.get("source"))
    return None


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _forbidden_response_summary_violations(
    value: Any,
    path: str = "$",
) -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}"
            if str(key).lower() in FORBIDDEN_PRODUCT_GATEWAY_RESPONSE_KEYS:
                violations.append(
                    f"product gateway response summary field is forbidden at {key_path}"
                )
            violations.extend(_forbidden_response_summary_violations(item, key_path))
        return violations
    if isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(
                _forbidden_response_summary_violations(item, f"{path}[{index}]")
            )
        return violations
    if isinstance(value, str) and _looks_like_raw_payload(value):
        violations.append(
            f"raw product gateway response summary payload is forbidden at {path}"
        )
    return violations


def _looks_like_raw_payload(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in (
            "raw provider response",
            "raw_response",
            "response_text",
            "system_prompt",
            "api_key",
            "raw_tool_input",
            "raw_tool_output",
        )
    )
