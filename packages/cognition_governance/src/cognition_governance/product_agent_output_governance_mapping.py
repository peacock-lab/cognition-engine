"""Product and agent output governance candidate mapping.

This module consumes plain dict summaries only. It does not import product,
agent, runtime, tool, or provider packages, and it does not create a formal
governance decision or outcome.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from schemas.product_gateway_response_summary import (
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_PAYLOAD_TYPE,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_PRODUCT,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION,
    validate_product_gateway_response_summary,
)

from cognition_governance.models import GovernanceCase, GovernanceEvidence


POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE = "product_agent_output_governance"
PRODUCT_AGENT_OUTPUT_GOVERNANCE_CASE_TYPE = "product_agent_output_governance_review"
PRODUCT_AGENT_OUTPUT_GOVERNANCE_SOURCE = (
    "cognition_governance.product_agent_output_governance_mapping"
)
PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_REF = (
    "policy-product-agent-output-governance"
)
PRODUCT_GATEWAY_RESPONSE_SUMMARY_EVIDENCE_TYPE = "product_gateway_response_summary"
AGENT_TASK_ADVICE_PAYLOAD_EVIDENCE_TYPE = "agent_task_advice_consumption_payload"

AGENT_TASK_ADVICE_PAYLOAD_PRODUCT = "cognition_agent"
AGENT_TASK_ADVICE_PAYLOAD_TYPE = "agent_task_advice_consumption_payload"
AGENT_TASK_ADVICE_PAYLOAD_VERSION = "agent_task_advice_consumption_payload_v1"

_RAW_OR_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "artifact_content",
        "completion",
        "credential",
        "credentials",
        "full_response",
        "message",
        "messages",
        "payload",
        "prompt",
        "provider_payload",
        "provider_response",
        "raw",
        "raw_adk_object",
        "raw_api_payload",
        "raw_input",
        "raw_output",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_provider_response",
        "raw_response",
        "raw_tool_input",
        "raw_tool_output",
        "raw_user_message",
        "response",
        "response_text",
        "secret",
        "system_prompt",
        "text",
        "token",
        "tool_context",
        "tool_input",
        "tool_output",
        "user_message",
    }
)

_SENSITIVE_KEY_EXCEPTIONS = frozenset({"raw_output_digest"})

_FORBIDDEN_OBJECT_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "runtime_container",
    "composition",
    "litellm",
)


class ProductAgentOutputGovernanceMappingResult(BaseModel):
    """Internal mapping result; this is not a governance decision."""

    model_config = ConfigDict(extra="forbid")

    governance_evidence: list[GovernanceEvidence]
    governance_case: GovernanceCase
    notes: list[str] = Field(default_factory=list)


def map_product_gateway_response_summary_to_governance_evidence(
    summary: Any,
    *,
    evidence_id: str | None = None,
) -> GovernanceEvidence:
    """Map a product_gateway response summary dict to GovernanceEvidence."""

    summary_mapping = validate_product_gateway_response_summary(
        _as_plain_mapping(summary, "product_gateway response summary")
    ).model_dump(mode="python")

    request_id = _required_str(summary_mapping.get("request_id"), "request_id")
    entry_kind = _required_str(summary_mapping.get("entry_kind"), "entry_kind")
    status = _required_str(summary_mapping.get("status"), "status")
    blocking_reasons = _str_list(summary_mapping.get("blocking_reasons"))
    warnings = _str_list(summary_mapping.get("warnings"))
    warning_candidates = _product_gateway_warning_candidates(status, warnings)
    block_candidates = _product_gateway_block_candidates(status, blocking_reasons)
    human_review_reasons = _product_gateway_human_review_reasons(
        status,
        blocking_reasons,
        warnings,
    )

    return GovernanceEvidence(
        evidence_id=evidence_id
        or _make_id("product-gateway-response-summary", request_id),
        evidence_type=PRODUCT_GATEWAY_RESPONSE_SUMMARY_EVIDENCE_TYPE,
        source=PRODUCT_AGENT_OUTPUT_GOVERNANCE_SOURCE,
        summary=(
            f"Product gateway response summary for {request_id}: "
            f"entry_kind={entry_kind}, status={status}."
        ),
        content_ref=_plain_str(summary_mapping.get("product_gateway_response_ref")),
        metadata={
            "product": PRODUCT_GATEWAY_RESPONSE_SUMMARY_PRODUCT,
            "payload_type": PRODUCT_GATEWAY_RESPONSE_SUMMARY_PAYLOAD_TYPE,
            "payload_version": PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION,
            "request_id": request_id,
            "entry_kind": entry_kind,
            "status": status,
            "exit_code": _int_or_none(summary_mapping.get("exit_code")),
            "product_gateway_response_ref": _plain_str(
                summary_mapping.get("product_gateway_response_ref")
            ),
            "governance_summary_ref": _plain_str(
                summary_mapping.get("governance_summary_ref")
            ),
            "evidence_refs": _ref_list(summary_mapping.get("evidence_refs")),
            "audit_refs": _ref_list(summary_mapping.get("audit_refs")),
            "agent_advice_refs": _ref_list(summary_mapping.get("agent_advice_refs")),
            "tool_audit_refs": _ref_list(summary_mapping.get("tool_audit_refs")),
            "blocking_reasons": blocking_reasons,
            "warnings": warnings,
            "warning_candidates": warning_candidates,
            "block_candidates": block_candidates,
            "human_review_required": bool(human_review_reasons),
            "human_review_reasons": human_review_reasons,
            "ready_for_review": status in {"success", "skipped"},
            "summary_only": True,
            "refs_only": True,
            "candidate_only": True,
            "mapping_boundary": _mapping_boundary(),
        },
    )


def map_agent_task_advice_payload_to_governance_evidence(
    payload: Any,
    *,
    evidence_id: str | None = None,
) -> GovernanceEvidence:
    """Map a cognition_agent task advice payload dict to GovernanceEvidence."""

    payload_mapping = _as_plain_mapping(payload, "agent task advice payload")
    _raise_if_forbidden_payload_found(payload_mapping)
    _validate_agent_task_advice_payload_header(payload_mapping)

    candidate_id = _required_str(payload_mapping.get("candidate_id"), "candidate_id")
    recommendation = _required_str(payload_mapping.get("recommendation"), "recommendation")
    status = _required_str(payload_mapping.get("status"), "status")
    product_gateway_status = _plain_str(payload_mapping.get("product_gateway_status"))
    blocking_reasons = _str_list(payload_mapping.get("blocking_reasons"))
    warnings = _str_list(payload_mapping.get("warnings"))
    product_gateway_blocking_reasons = _str_list(
        payload_mapping.get("product_gateway_blocking_reasons")
    )
    product_gateway_warnings = _str_list(payload_mapping.get("product_gateway_warnings"))
    warning_candidates = _agent_payload_warning_candidates(
        status,
        recommendation,
        product_gateway_status,
        warnings,
        product_gateway_warnings,
    )
    block_candidates = _agent_payload_block_candidates(
        status,
        recommendation,
        product_gateway_status,
        blocking_reasons,
        product_gateway_blocking_reasons,
    )
    human_review_reasons = _agent_payload_human_review_reasons(
        status,
        recommendation,
        product_gateway_status,
        blocking_reasons,
        product_gateway_blocking_reasons,
    )

    return GovernanceEvidence(
        evidence_id=evidence_id or _make_id("agent-task-advice-consumption", candidate_id),
        evidence_type=AGENT_TASK_ADVICE_PAYLOAD_EVIDENCE_TYPE,
        source=PRODUCT_AGENT_OUTPUT_GOVERNANCE_SOURCE,
        summary=(
            f"Agent task advice payload for {candidate_id}: "
            f"recommendation={recommendation}, status={status}."
        ),
        content_ref=None,
        metadata={
            "product": AGENT_TASK_ADVICE_PAYLOAD_PRODUCT,
            "payload_type": AGENT_TASK_ADVICE_PAYLOAD_TYPE,
            "payload_version": AGENT_TASK_ADVICE_PAYLOAD_VERSION,
            "candidate_id": candidate_id,
            "task_context_candidate_id": _required_str(
                payload_mapping.get("task_context_candidate_id"),
                "task_context_candidate_id",
            ),
            "task_candidate_id": _plain_str(payload_mapping.get("task_candidate_id")),
            "recommendation": recommendation,
            "status": status,
            "product_gateway_response_view_candidate_id": _plain_str(
                payload_mapping.get("product_gateway_response_view_candidate_id")
            ),
            "product_gateway_request_id": _plain_str(
                payload_mapping.get("product_gateway_request_id")
            ),
            "product_gateway_entry_kind": _plain_str(
                payload_mapping.get("product_gateway_entry_kind")
            ),
            "product_gateway_status": product_gateway_status,
            "product_gateway_exit_code": _int_or_none(
                payload_mapping.get("product_gateway_exit_code")
            ),
            "product_gateway_response_ref": _plain_str(
                payload_mapping.get("product_gateway_response_ref")
            ),
            "product_gateway_governance_summary_ref": _plain_str(
                payload_mapping.get("product_gateway_governance_summary_ref")
            ),
            "product_gateway_evidence_refs": _ref_list(
                payload_mapping.get("product_gateway_evidence_refs")
            ),
            "product_gateway_audit_refs": _ref_list(
                payload_mapping.get("product_gateway_audit_refs")
            ),
            "product_gateway_agent_advice_refs": _ref_list(
                payload_mapping.get("product_gateway_agent_advice_refs")
            ),
            "product_gateway_tool_audit_refs": _ref_list(
                payload_mapping.get("product_gateway_tool_audit_refs")
            ),
            "product_gateway_blocking_reasons": product_gateway_blocking_reasons,
            "product_gateway_warnings": product_gateway_warnings,
            "product_gateway_ready_for_review": _bool_or_none(
                payload_mapping.get("product_gateway_ready_for_review")
            ),
            "plan_steps": _str_list(payload_mapping.get("plan_steps")),
            "risk_notes": _str_list(payload_mapping.get("risk_notes")),
            "next_step": _plain_str(payload_mapping.get("next_step")),
            "blocking_reasons": blocking_reasons,
            "warnings": warnings,
            "governance_refs": _str_list(payload_mapping.get("governance_refs")),
            "config_refs": _str_list(payload_mapping.get("config_refs")),
            "readonly": True,
            "candidate_only": True,
            "execution_enabled": False,
            "warning_candidates": warning_candidates,
            "block_candidates": block_candidates,
            "human_review_required": bool(human_review_reasons),
            "human_review_reasons": human_review_reasons,
            "summary_only": True,
            "refs_only": True,
            "mapping_boundary": _mapping_boundary(),
        },
    )


def map_product_agent_output_evidence_to_governance_case(
    governance_evidence: list[GovernanceEvidence | dict[str, Any]],
    *,
    case_id: str | None = None,
    title: str | None = None,
    subject: str | None = None,
) -> GovernanceCase:
    """Map product/agent output GovernanceEvidence items to a GovernanceCase."""

    evidence_items = [_as_governance_evidence(item) for item in governance_evidence]
    missing_evidence = _missing_product_agent_output_evidence(evidence_items)
    warning_candidates = _dedupe(
        _flatten_metadata_lists(evidence_items, "warning_candidates")
    )
    block_candidates = _dedupe(
        _flatten_metadata_lists(evidence_items, "block_candidates")
    )
    human_review_reasons = _dedupe(
        _flatten_metadata_lists(evidence_items, "human_review_reasons")
    )
    if missing_evidence:
        human_review_reasons.append(
            "Product gateway summary and agent advice payload evidence must both be present."
        )

    request_id = _first_metadata_value(evidence_items, "request_id") or _first_metadata_value(
        evidence_items,
        "product_gateway_request_id",
    )
    task_candidate_id = _first_metadata_value(evidence_items, "task_candidate_id")
    resolved_subject = subject or request_id or task_candidate_id or case_id
    evidence_statuses = {
        item.evidence_id: item.metadata.get("status") for item in evidence_items
    }
    resolved_case_id = case_id or _make_id(
        "product-agent-output-governance",
        request_id or task_candidate_id or _digest_evidence(evidence_items)[:10],
    )

    return GovernanceCase(
        case_id=resolved_case_id,
        title=title or "Product agent output governance review",
        case_type=PRODUCT_AGENT_OUTPUT_GOVERNANCE_CASE_TYPE,
        subject=resolved_subject,
        context={
            "product_gateway_request_id": request_id,
            "product_gateway_entry_kind": _first_metadata_value(
                evidence_items,
                "entry_kind",
            )
            or _first_metadata_value(evidence_items, "product_gateway_entry_kind"),
            "product_gateway_status": _first_metadata_value(evidence_items, "status")
            or _first_metadata_value(evidence_items, "product_gateway_status"),
            "product_gateway_exit_code": _first_metadata_value(
                evidence_items,
                "exit_code",
            )
            or _first_metadata_value(evidence_items, "product_gateway_exit_code"),
            "agent_advice_candidate_id": _first_metadata_value(
                evidence_items,
                "candidate_id",
            ),
            "agent_advice_status": _agent_advice_metadata_value(
                evidence_items,
                "status",
            ),
            "agent_advice_recommendation": _first_metadata_value(
                evidence_items,
                "recommendation",
            ),
            "ready_for_review": _ready_for_review(evidence_items),
            "evidence_statuses": evidence_statuses,
        },
        evidence_refs=[item.evidence_id for item in evidence_items],
        policy_refs=[PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_REF],
        metadata={
            "policy_domain": POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE,
            "missing_evidence": missing_evidence,
            "warning_candidates": warning_candidates,
            "block_candidates": block_candidates,
            "human_review_required": bool(
                human_review_reasons or block_candidates or warning_candidates or missing_evidence
            ),
            "human_review_reasons": _dedupe(human_review_reasons),
            "decision_candidate_blocked": bool(missing_evidence or block_candidates),
            "blocked_formal_decision_reasons": [
                "Product-agent output governance mapping is candidate-only.",
                "PolicySet candidate and GovernanceDecision remain candidate-only.",
                "Human review is required before any formal action.",
                "GovernanceOutcome remains out of scope.",
            ],
            "policy_refs_status": "candidate_only",
            "mapping_boundary": _mapping_boundary(),
            "summary_only": True,
            "refs_only": True,
            "candidate_only": True,
        },
    )


def map_product_agent_output_governance_package(
    *,
    product_gateway_summary: Any | None = None,
    agent_task_advice_payload: Any | None = None,
    case_id: str | None = None,
) -> ProductAgentOutputGovernanceMappingResult:
    """Map product and agent output summaries into evidence and a case only."""

    evidence: list[GovernanceEvidence] = []
    if product_gateway_summary is not None:
        evidence.append(
            map_product_gateway_response_summary_to_governance_evidence(
                product_gateway_summary
            )
        )
    if agent_task_advice_payload is not None:
        evidence.append(
            map_agent_task_advice_payload_to_governance_evidence(
                agent_task_advice_payload
            )
        )
    governance_case = map_product_agent_output_evidence_to_governance_case(
        evidence,
        case_id=case_id,
    )
    return ProductAgentOutputGovernanceMappingResult(
        governance_evidence=evidence,
        governance_case=governance_case,
        notes=[
            "Internal Product-Agent output governance evidence/case mapping only.",
            "Plain dict summaries and refs are consumed; upstream packages are not imported.",
            "GovernanceDecision and GovernanceOutcome remain out of scope.",
            "Policy, product, agent, runtime, LLM, tool, and release actions are not executed.",
        ],
    )


def _validate_agent_task_advice_payload_header(payload: dict[str, Any]) -> None:
    expected = {
        "product": AGENT_TASK_ADVICE_PAYLOAD_PRODUCT,
        "payload_type": AGENT_TASK_ADVICE_PAYLOAD_TYPE,
        "payload_version": AGENT_TASK_ADVICE_PAYLOAD_VERSION,
    }
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            raise ValueError(f"{key} must be {expected_value}.")
    _required_str(payload.get("candidate_id"), "candidate_id")
    _required_str(payload.get("task_context_candidate_id"), "task_context_candidate_id")
    _required_str(payload.get("recommendation"), "recommendation")
    _required_str(payload.get("status"), "status")
    if payload.get("readonly") is not True:
        raise ValueError("agent task advice payload must be readonly.")
    if payload.get("candidate_only") is not True:
        raise ValueError("agent task advice payload must be candidate_only.")
    if payload.get("execution_enabled") is not False:
        raise ValueError("agent task advice payload must disable execution.")


def _product_gateway_warning_candidates(status: str, warnings: list[str]) -> list[str]:
    candidates = list(warnings)
    if status == "skipped":
        candidates.append("product_gateway_response_skipped")
    return _dedupe(candidates)


def _product_gateway_block_candidates(
    status: str,
    blocking_reasons: list[str],
) -> list[str]:
    candidates = list(blocking_reasons)
    if status == "blocked":
        candidates.append("product_gateway_response_blocked")
    if status == "failed":
        candidates.append("product_gateway_response_failed")
    return _dedupe(candidates)


def _product_gateway_human_review_reasons(
    status: str,
    blocking_reasons: list[str],
    warnings: list[str],
) -> list[str]:
    reasons: list[str] = []
    if status == "blocked":
        reasons.append("Product gateway response is blocked.")
    if status == "failed":
        reasons.append("Product gateway response failed.")
    if status == "skipped":
        reasons.append("Product gateway response was skipped and needs review.")
    reasons.extend(blocking_reasons)
    reasons.extend(warnings)
    return _dedupe(reasons)


def _agent_payload_warning_candidates(
    status: str,
    recommendation: str,
    product_gateway_status: str | None,
    warnings: list[str],
    product_gateway_warnings: list[str],
) -> list[str]:
    candidates = list(warnings + product_gateway_warnings)
    if status.endswith("_skipped_review") or recommendation.endswith("_skipped_review"):
        candidates.append("agent_advice_product_gateway_skipped_review")
    if product_gateway_status == "skipped":
        candidates.append("product_gateway_response_skipped")
    return _dedupe(candidates)


def _agent_payload_block_candidates(
    status: str,
    recommendation: str,
    product_gateway_status: str | None,
    blocking_reasons: list[str],
    product_gateway_blocking_reasons: list[str],
) -> list[str]:
    candidates = list(blocking_reasons + product_gateway_blocking_reasons)
    if status == "needs_product_gateway_review":
        candidates.append("agent_advice_needs_product_gateway_review")
    if recommendation in {
        "review_product_gateway_blocking_reasons",
        "review_product_gateway_failure",
    }:
        candidates.append(recommendation)
    if product_gateway_status in {"blocked", "failed"}:
        candidates.append(f"product_gateway_response_{product_gateway_status}")
    return _dedupe(candidates)


def _agent_payload_human_review_reasons(
    status: str,
    recommendation: str,
    product_gateway_status: str | None,
    blocking_reasons: list[str],
    product_gateway_blocking_reasons: list[str],
) -> list[str]:
    reasons: list[str] = []
    if status == "needs_product_gateway_review":
        reasons.append("Agent advice requires product gateway review.")
    if recommendation == "review_product_gateway_blocking_reasons":
        reasons.append("Agent advice asks to review product gateway blocking reasons.")
    if recommendation == "review_product_gateway_failure":
        reasons.append("Agent advice asks to review product gateway failure.")
    if product_gateway_status in {"blocked", "failed"}:
        reasons.append(f"Product gateway status is {product_gateway_status}.")
    reasons.extend(blocking_reasons)
    reasons.extend(product_gateway_blocking_reasons)
    return _dedupe(reasons)


def _missing_product_agent_output_evidence(
    evidence_items: list[GovernanceEvidence],
) -> list[str]:
    types = {item.evidence_type for item in evidence_items}
    missing: list[str] = []
    if PRODUCT_GATEWAY_RESPONSE_SUMMARY_EVIDENCE_TYPE not in types:
        missing.append(PRODUCT_GATEWAY_RESPONSE_SUMMARY_EVIDENCE_TYPE)
    if AGENT_TASK_ADVICE_PAYLOAD_EVIDENCE_TYPE not in types:
        missing.append(AGENT_TASK_ADVICE_PAYLOAD_EVIDENCE_TYPE)
    return missing


def _ready_for_review(evidence_items: list[GovernanceEvidence]) -> bool:
    if _missing_product_agent_output_evidence(evidence_items):
        return False
    if _flatten_metadata_lists(evidence_items, "block_candidates"):
        return False
    return True


def _agent_advice_metadata_value(
    evidence_items: list[GovernanceEvidence],
    key: str,
) -> Any:
    for evidence in evidence_items:
        if evidence.evidence_type == AGENT_TASK_ADVICE_PAYLOAD_EVIDENCE_TYPE:
            value = evidence.metadata.get(key)
            if value is not None:
                return value
    return None


def _first_metadata_value(
    evidence_items: list[GovernanceEvidence],
    key: str,
) -> Any:
    for evidence in evidence_items:
        value = evidence.metadata.get(key)
        if value is not None:
            return value
    return None


def _flatten_metadata_lists(
    evidence_items: list[GovernanceEvidence],
    key: str,
) -> list[str]:
    result: list[str] = []
    for evidence in evidence_items:
        result.extend(str(item) for item in _list(evidence.metadata.get(key)) if item)
    return result


def _as_plain_mapping(value: Any, value_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{value_name} must be a plain dict.")
    return dict(value)


def _as_governance_evidence(value: GovernanceEvidence | dict[str, Any]) -> GovernanceEvidence:
    if isinstance(value, GovernanceEvidence):
        return value
    if isinstance(value, dict):
        return GovernanceEvidence.model_validate(value)
    raise TypeError("GovernanceEvidence or compatible mapping is required.")


def _ref_list(value: Any) -> list[dict[str, Any]]:
    refs = _list(value)
    result: list[dict[str, Any]] = []
    for item in refs:
        if not isinstance(item, dict):
            raise ValueError("refs must contain dict items.")
        _raise_if_forbidden_payload_found(item)
        ref = _required_str(item.get("ref"), "ref")
        kind = _required_str(item.get("kind"), "kind")
        result.append(
            {
                "ref": ref,
                "kind": kind,
                "purpose": _plain_str(item.get("purpose")),
                "metadata": _sanitize_mapping(_mapping(item.get("metadata"))),
            }
        )
    return result


def _raise_if_forbidden_payload_found(value: Any) -> None:
    violations = [
        f"forbidden raw or sensitive payload at {path}"
        for path, item in _walk(value)
        if _is_forbidden_payload(path, item)
    ]
    if violations:
        raise ValueError("; ".join(violations))


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, dict):
        for key, item in value.items():
            items.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_walk(item, f"{path}[{index}]"))
    return items


def _is_forbidden_payload(path: str, value: Any) -> bool:
    key = path.rsplit(".", maxsplit=1)[-1].lower()
    if key in _SENSITIVE_KEY_EXCEPTIONS:
        return False
    if (
        key in _RAW_OR_SENSITIVE_KEYS
        or key.endswith("_token")
        or key.endswith("_credential")
        or key.endswith("_secret")
    ):
        return True
    if isinstance(value, dict):
        module_name = value.get("object_module")
        return isinstance(module_name, str) and module_name.startswith(
            _FORBIDDEN_OBJECT_MODULE_PREFIXES
        )
    if value is None or isinstance(value, (str, int, float, bool, list, tuple, dict)):
        return False
    return type(value).__module__.startswith(_FORBIDDEN_OBJECT_MODULE_PREFIXES)


def _mapping_boundary() -> list[str]:
    return [
        "Product-agent output governance mapping only.",
        "Only plain dict summaries and sanitized refs are consumed.",
        "No GovernanceDecision is produced by this mapping.",
        "No GovernanceOutcome is produced.",
        "No product, agent, runtime, LLM, tool, policy, release, or action execution is performed.",
    ]


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _str_list(value: Any) -> list[str]:
    return [str(item) for item in _list(value) if item is not None and str(item)]


def _plain_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _required_str(value: Any, field_name: str) -> str:
    if isinstance(value, str) and value:
        return value
    raise ValueError(f"{field_name} is required.")


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _bool_or_none(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _sanitize_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _sanitize(value) for key, value in mapping.items()}


def _sanitize(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, bool, str)):
        return value
    if isinstance(value, dict):
        return _sanitize_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return {
        "object_type": type(value).__name__,
        "object_module": _sanitize_module(type(value).__module__),
    }


def _sanitize_module(module_name: str) -> str:
    if module_name.startswith(_FORBIDDEN_OBJECT_MODULE_PREFIXES):
        return "external_runtime_object"
    return module_name


def _make_id(prefix: str, *parts: object) -> str:
    slug = "-".join(_slug(str(part)) for part in parts if part not in {None, ""})
    if slug:
        return f"{prefix}-{slug}"
    return f"{prefix}-{hashlib.sha256(prefix.encode()).hexdigest()[:10]}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-").lower()
    return slug or "unknown"


def _digest_evidence(evidence_items: list[GovernanceEvidence]) -> str:
    payload = [item.model_dump(mode="python") for item in evidence_items]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
