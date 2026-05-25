"""Evidence bridge helpers for external-readonly ask product entries."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from contract_core.external_readonly_evidence import (
    validate_external_readonly_evidence_path,
)
from external_readonly.governed_summary_facts import (
    build_external_readonly_governed_summary_facts,
)
from product_gateway.external_readonly import (
    execute_external_readonly_fetch_gateway_request,
)


PRODUCT_GATEWAY_EXTERNAL_READONLY_ASK_BRIDGE_SOURCE = (
    "product_gateway.external_readonly_ask_bridge"
)
EXTERNAL_READONLY_ASK_FETCH_FAILED = "external_readonly_ask_fetch_failed"


@dataclass(frozen=True)
class ExternalReadonlyAskEvidenceBridgeResult:
    """Gateway-owned evidence bridge material for ask product assembly."""

    facts_payloads: tuple[Mapping[str, Any], ...]
    blocking_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    readonly_refs_status: str
    evidence_refs: tuple[Mapping[str, Any], ...] = ()
    additional_refs: tuple[Mapping[str, Any], ...] = ()
    fetch_request_id: str | None = None
    external_readonly_fetch_performed: bool = False
    external_readonly_network_call_performed: bool = False
    external_network_call_performed: bool = False


ExternalReadonlyAskFetchExecutor = Callable[[Mapping[str, Any]], Any]


def build_external_readonly_ask_bridge_from_source_url(
    *,
    fetch_gateway_input: Mapping[str, Any],
    fetch_request_id: str,
    fetch_executor: ExternalReadonlyAskFetchExecutor | None = None,
) -> ExternalReadonlyAskEvidenceBridgeResult:
    """Fetch a governed URL and expose compact facts for product assembly."""

    execution = (fetch_executor or execute_external_readonly_fetch_gateway_request)(
        fetch_gateway_input
    )
    product_response = execution.product_response
    runtime_result = getattr(execution, "runtime_result", None)
    fetch_metadata = dict(getattr(product_response, "metadata", {}) or {})
    fetch_status = getattr(getattr(product_response, "status", None), "value", None)
    fetch_blocking = tuple(str(item) for item in product_response.blocking_reasons)
    fetch_warnings = tuple(str(item) for item in product_response.warnings)
    external_fetch_performed = bool(
        fetch_metadata.get("runtime_fetch_performed", False)
    )
    external_network_call_performed = bool(
        fetch_metadata.get("external_network_call_performed", False)
    )
    if fetch_status != "success" or runtime_result is None:
        return _result(
            blocking_reasons=fetch_blocking or (EXTERNAL_READONLY_ASK_FETCH_FAILED,),
            warnings=fetch_warnings,
            readonly_refs_status="blocked",
            fetch_request_id=fetch_request_id,
            external_readonly_fetch_performed=external_fetch_performed,
            external_readonly_network_call_performed=external_network_call_performed,
            external_network_call_performed=external_network_call_performed,
        )

    facts = build_external_readonly_governed_summary_facts(
        getattr(runtime_result, "envelope", None),
        evidence_output_path=None,
        evidence_written=getattr(runtime_result, "status", None) == "completed",
        reference_review_ready=(
            getattr(runtime_result, "status", None) == "completed"
            and getattr(runtime_result, "allowed_for_model_context", False) is True
        ),
    )
    return _result(
        facts_payloads=(facts.model_dump(mode="python"),),
        warnings=fetch_warnings,
        readonly_refs_status=str(facts.status),
        fetch_request_id=fetch_request_id,
        external_readonly_fetch_performed=external_fetch_performed,
        external_readonly_network_call_performed=external_network_call_performed,
        external_network_call_performed=external_network_call_performed,
    )


def build_external_readonly_ask_bridge_from_archives(
    *,
    evidence_paths: tuple[str, ...],
    repo_root: str | None,
    source: str,
    product_path: str,
) -> ExternalReadonlyAskEvidenceBridgeResult:
    """Load governed summary facts from evidence archives for ask assembly."""

    root = Path(repo_root or ".").resolve()
    path_issues = _evidence_path_issues(evidence_paths, repo_root=root)
    if path_issues:
        return _result(
            blocking_reasons=path_issues,
            readonly_refs_status="blocked",
        )

    facts_payloads, blocking_reasons = _archived_governed_summary_facts(
        evidence_paths,
        repo_root=root,
        source=source,
        product_path=product_path,
    )
    if blocking_reasons:
        return _result(
            facts_payloads=tuple(facts_payloads),
            blocking_reasons=blocking_reasons,
            readonly_refs_status="blocked",
        )
    return _result(
        facts_payloads=tuple(facts_payloads),
        readonly_refs_status=_readonly_refs_status_from_facts(facts_payloads),
    )


def _evidence_path_issues(
    evidence_paths: tuple[str, ...],
    *,
    repo_root: Path,
) -> tuple[str, ...]:
    issues: list[str] = []
    for evidence_path in evidence_paths:
        issue = validate_external_readonly_evidence_path(
            evidence_path=evidence_path,
            repo_root=repo_root,
        )
        if issue:
            issues.append(f"{evidence_path}:{issue}")
    return tuple(issues)


def _archived_governed_summary_facts(
    evidence_paths: tuple[str, ...],
    *,
    repo_root: Path,
    source: str,
    product_path: str,
) -> tuple[list[Mapping[str, Any]], tuple[str, ...]]:
    payloads: list[Mapping[str, Any]] = []
    blocking_reasons: list[str] = []
    for evidence_path in evidence_paths:
        target = (repo_root / evidence_path).resolve()
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            blocking_reasons.append(
                f"{evidence_path}:external_readonly_evidence_archive_unreadable"
            )
            continue
        if not isinstance(payload, Mapping):
            blocking_reasons.append(
                f"{evidence_path}:external_readonly_evidence_archive_not_object"
            )
            continue

        facts = _mapping(payload.get("governed_summary_facts"))
        if facts:
            payloads.append(facts)
            continue
        payloads.append(
            _blocked_governed_summary_facts_payload(
                payload,
                evidence_path=evidence_path,
                reason="external_readonly_governed_summary_facts_required",
                source=source,
                product_path=product_path,
            )
        )
    return payloads, tuple(blocking_reasons)


def _blocked_governed_summary_facts_payload(
    archive_payload: Mapping[str, Any],
    *,
    evidence_path: str,
    reason: str,
    source: str,
    product_path: str,
) -> dict[str, Any]:
    return {
        "payload_type": "external_readonly_governed_summary_facts",
        "payload_version": "external_readonly_governed_summary_facts_v1",
        "status": "blocked",
        "evidence_ref": _archive_evidence_ref(archive_payload, evidence_path),
        "evidence_output_path": evidence_path,
        "reference_review_ready": False,
        "allowed_for_model_context": False,
        "evidence_written": archive_payload.get("evidence_written") is True,
        "facts": [],
        "fact_count": 0,
        "total_fact_chars": 0,
        "blocking_reasons": [reason],
        "warnings": [],
        "metadata": {
            "source": source,
            "archive_bridge": True,
            "product_path": product_path,
        },
    }


def _archive_evidence_ref(
    archive_payload: Mapping[str, Any],
    evidence_path: str,
) -> str:
    value = archive_payload.get("evidence_ref")
    if isinstance(value, str) and value.startswith("evidence://external-readonly/"):
        return value
    try:
        relative = Path(evidence_path).relative_to("outputs/external-readonly")
    except ValueError:
        return "evidence://external-readonly/governed-summary-facts/unavailable"
    return f"evidence://external-readonly/{relative.as_posix()}"


def _readonly_refs_status_from_facts(
    facts_payloads: list[Mapping[str, Any]],
) -> str:
    if not facts_payloads:
        return "blocked"
    statuses = [str(_mapping(facts).get("status") or "") for facts in facts_payloads]
    if all(status == "ready" for status in statuses):
        return "ready"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    return statuses[0] or "ready"


def _result(
    *,
    facts_payloads: tuple[Mapping[str, Any], ...] = (),
    blocking_reasons: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
    readonly_refs_status: str,
    evidence_refs: tuple[Mapping[str, Any], ...] = (),
    additional_refs: tuple[Mapping[str, Any], ...] = (),
    fetch_request_id: str | None = None,
    external_readonly_fetch_performed: bool = False,
    external_readonly_network_call_performed: bool = False,
    external_network_call_performed: bool = False,
) -> ExternalReadonlyAskEvidenceBridgeResult:
    return ExternalReadonlyAskEvidenceBridgeResult(
        facts_payloads=facts_payloads,
        blocking_reasons=blocking_reasons,
        warnings=warnings,
        readonly_refs_status=readonly_refs_status,
        evidence_refs=evidence_refs,
        additional_refs=additional_refs,
        fetch_request_id=fetch_request_id,
        external_readonly_fetch_performed=external_readonly_fetch_performed,
        external_readonly_network_call_performed=(
            external_readonly_network_call_performed
        ),
        external_network_call_performed=external_network_call_performed,
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = (
    "ExternalReadonlyAskEvidenceBridgeResult",
    "ExternalReadonlyAskFetchExecutor",
    "PRODUCT_GATEWAY_EXTERNAL_READONLY_ASK_BRIDGE_SOURCE",
    "build_external_readonly_ask_bridge_from_archives",
    "build_external_readonly_ask_bridge_from_source_url",
)
