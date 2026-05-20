"""Internal mapping from release check outputs to governance cases."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from cognition_governance.models import GovernanceCase, GovernanceEvidence


RELEASE_GOVERNANCE_CASE_TYPE = "release_governance"
RELEASE_GOVERNANCE_SOURCE = "release_governance.script_output"
RELEASE_GOVERNANCE_POLICY_REF = "policy-release-governance"

SUPPORTED_RELEASE_EVIDENCE_PROVIDERS = frozenset(
    {
        "check_public_surface.py",
        "check_public_workflow_template.py",
        "check_pypi_version.py",
        "check_release_note_tag_github_release.py",
        "check_release_tokens.py",
        "check_trusted_publishing_config.py",
        "release_safety_check.py",
        "verify_pypi_release.py",
    }
)

DEFERRED_RELEASE_EVIDENCE_PROVIDERS = frozenset(
    {
        "release_material_summary.py",
        "release_multi_package.py",
    }
)

_EVIDENCE_TYPE_BY_PROVIDER = {
    "check_public_surface.py": "public_surface_check_output",
    "check_public_workflow_template.py": "public_workflow_template_check_output",
    "check_pypi_version.py": "pypi_check_output",
    "check_release_note_tag_github_release.py": "release_platform_check_output",
    "check_release_tokens.py": "release_token_env_check_output",
    "check_trusted_publishing_config.py": "trusted_publishing_check_output",
    "release_safety_check.py": "release_safety_check_output",
    "verify_pypi_release.py": "pypi_verification_output",
}

_RAW_OR_SENSITIVE_KEYS = {
    "command",
    "command_outputs",
    "env",
    "env_name",
    "fallback_token",
    "output",
    "parsed_json",
    "project_tokens",
    "raw",
    "raw_output",
    "secret",
    "stderr",
    "stderr_tail",
    "stdout",
    "stdout_tail",
    "temp_dir",
    "token",
}

class ReleaseGovernanceMappingResult(BaseModel):
    """Internal release governance mapping result; this is not a decision."""

    model_config = ConfigDict(extra="forbid")

    governance_evidence: list[GovernanceEvidence]
    governance_case: GovernanceCase
    notes: list[str] = Field(default_factory=list)


def map_release_check_output_to_governance_evidence(
    check_output: Any,
    *,
    script_name: str | None = None,
    script_path: str | None = None,
    evidence_id: str | None = None,
    phase: str | None = None,
    target_version: str | None = None,
    evidence_type: str | None = None,
) -> GovernanceEvidence:
    """Map one release check JSON/dict output to internal GovernanceEvidence."""

    output = _as_mapping(check_output)
    provider = _provider_name(script_name or output.get("script_name") or script_path)
    if provider in DEFERRED_RELEASE_EVIDENCE_PROVIDERS:
        raise ValueError(f"{provider} is deferred and cannot be mapped in this pass.")
    if provider is None:
        provider = "unknown_release_check"

    resolved_phase = _plain_str(phase) or _plain_str(output.get("phase"))
    resolved_version = (
        _plain_str(target_version) or _plain_str(output.get("target_version"))
    )
    final_status = _plain_str(output.get("final_status")) or _plain_str(
        output.get("status")
    )
    failure_codes = _failure_codes(output)
    issues_summary = _issues_summary(output.get("issues"))
    checks_summary = _checks_summary(output.get("checks"))
    warning_candidates = _warning_candidates(provider, output, final_status)
    block_candidates = _block_candidates(
        provider,
        output,
        final_status,
        failure_codes,
        issues_summary,
        checks_summary,
    )
    human_review_reasons = _human_review_reasons(
        provider,
        block_candidates,
        warning_candidates,
        failure_codes,
        checks_summary,
    )
    sensitive_fields = sorted(_sensitive_field_paths(output))
    digest = _digest_output(output)

    return GovernanceEvidence(
        evidence_id=evidence_id
        or _make_id(
            "release-evidence",
            provider,
            resolved_version,
            resolved_phase,
            digest[:10],
        ),
        evidence_type=evidence_type
        or _EVIDENCE_TYPE_BY_PROVIDER.get(provider, "release_check_output"),
        source=RELEASE_GOVERNANCE_SOURCE,
        summary=_evidence_summary(
            provider,
            resolved_phase,
            resolved_version,
            final_status,
            failure_codes,
        ),
        content_ref=None,
        metadata={
            "script_name": provider,
            "script_path": _script_path_summary(provider, script_path),
            "provider_supported": provider in SUPPORTED_RELEASE_EVIDENCE_PROVIDERS,
            "phase": resolved_phase,
            "target_version": resolved_version,
            "final_status": final_status,
            "failure_codes": failure_codes,
            "issues_summary": issues_summary,
            "checks_summary": checks_summary,
            "status_counts": _status_counts(output),
            "warning_candidates": warning_candidates,
            "block_candidates": block_candidates,
            "human_review_required": bool(human_review_reasons),
            "human_review_reasons": human_review_reasons,
            "sensitive_fields_omitted": sensitive_fields,
            "raw_output_digest": digest,
            "mapping_boundary": [
                "Only summarized release check output is mapped.",
                "No GovernanceDecision is produced.",
                "No GovernanceOutcome is produced.",
                "No release, block, pass, publish, upload, tag, or push action is executed.",
            ],
        },
    )


def map_release_evidence_to_governance_case(
    governance_evidence: list[GovernanceEvidence | dict[str, Any]],
    *,
    case_id: str | None = None,
    title: str | None = None,
    release_target: str | None = None,
    phase: str | None = None,
    target_version: str | None = None,
) -> GovernanceCase:
    """Map release GovernanceEvidence items to one internal GovernanceCase."""

    evidence_items = [_as_governance_evidence(item) for item in governance_evidence]
    resolved_phase = _first_metadata_value(evidence_items, "phase", phase)
    resolved_version = _first_metadata_value(
        evidence_items,
        "target_version",
        target_version,
    )
    checks = {
        str(item.metadata.get("script_name") or item.evidence_id): item.metadata.get(
            "final_status"
        )
        for item in evidence_items
    }
    warning_candidates = _flatten_metadata_lists(evidence_items, "warning_candidates")
    block_candidates = _flatten_metadata_lists(evidence_items, "block_candidates")
    human_review_reasons = _dedupe(
        _flatten_metadata_lists(evidence_items, "human_review_reasons")
    )
    missing_evidence = _missing_release_evidence(evidence_items)
    if missing_evidence:
        human_review_reasons.append("Some first-batch release evidence providers are missing.")

    subject = _case_subject(release_target, resolved_version, resolved_phase)
    blocked_formal_decision_reasons = [
        "090 only maps release evidence and governance case candidates.",
        "PolicySet candidate and GovernanceDecision candidate are not implemented in this pass.",
        "Human review is required before any formal release, block, or pass decision.",
        "GovernanceOutcome remains out of scope.",
    ]

    return GovernanceCase(
        case_id=case_id
        or _make_id(
            "release-governance",
            resolved_version,
            resolved_phase,
            _digest_output([item.model_dump(mode="python") for item in evidence_items])[
                :10
            ],
        ),
        title=title or f"Release governance review for {resolved_version or 'unknown version'}",
        case_type=RELEASE_GOVERNANCE_CASE_TYPE,
        subject=subject,
        context={
            "release_target": release_target,
            "target_version": resolved_version,
            "phase": resolved_phase,
            "checks": checks,
        },
        evidence_refs=[item.evidence_id for item in evidence_items],
        policy_refs=[RELEASE_GOVERNANCE_POLICY_REF],
        metadata={
            "phase": resolved_phase,
            "target_version": resolved_version,
            "provider_count": len(evidence_items),
            "providers": [
                item.metadata.get("script_name") or item.evidence_id
                for item in evidence_items
            ],
            "missing_evidence": missing_evidence,
            "warning_candidates": warning_candidates,
            "block_candidates": block_candidates,
            "human_review_required": bool(
                human_review_reasons or block_candidates or missing_evidence
            ),
            "human_review_reasons": _dedupe(human_review_reasons),
            "decision_candidate_blocked": True,
            "blocked_formal_decision_reasons": blocked_formal_decision_reasons,
            "policy_refs_status": "candidate_only",
            "mapping_boundary": [
                "Release Governance evidence/case mapping only.",
                "No GovernanceDecision is produced.",
                "No GovernanceOutcome is produced.",
                "No release, block, pass, publish, upload, tag, or push action is executed.",
            ],
        },
    )


def map_release_governance_package(
    check_outputs: list[Any],
    *,
    release_target: str | None = None,
    phase: str | None = None,
    target_version: str | None = None,
) -> ReleaseGovernanceMappingResult:
    """Map release check outputs into an internal evidence/case package."""

    evidence = [
        map_release_check_output_to_governance_evidence(
            output,
            phase=phase,
            target_version=target_version,
        )
        for output in check_outputs
    ]
    governance_case = map_release_evidence_to_governance_case(
        evidence,
        release_target=release_target,
        phase=phase,
        target_version=target_version,
    )
    return ReleaseGovernanceMappingResult(
        governance_evidence=evidence,
        governance_case=governance_case,
        notes=[
            "Internal Release Governance evidence/case mapping only.",
            "First-batch provider outputs are consumed as dict/JSON samples only.",
            "GovernanceDecision and GovernanceOutcome remain out of scope.",
            "Release, block, pass, publish, upload, tag, and push actions remain out of scope.",
        ],
    )


def _as_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        if isinstance(dumped, dict):
            return dumped
    raise TypeError("Release governance mapping expects a mapping-like input.")


def _as_governance_evidence(value: GovernanceEvidence | dict[str, Any]) -> GovernanceEvidence:
    if isinstance(value, GovernanceEvidence):
        return value
    if isinstance(value, dict):
        return GovernanceEvidence.model_validate(value)
    raise TypeError("GovernanceEvidence or compatible mapping is required.")


def _provider_name(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return PurePath(value).name


def _plain_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _script_path_summary(provider: str, script_path: str | None) -> str | None:
    if provider in SUPPORTED_RELEASE_EVIDENCE_PROVIDERS:
        return f"scripts/{provider}"
    if not script_path:
        return None
    return PurePath(script_path).name


def _failure_codes(output: dict[str, Any]) -> list[str]:
    value = output.get("failure_codes")
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if item is not None]
    single = output.get("failure_code")
    return [str(single)] if single else []


def _issues_summary(value: Any) -> list[dict[str, str | None]]:
    if not isinstance(value, (list, tuple)):
        return []
    summary: list[dict[str, str | None]] = []
    for item in value:
        issue = _as_mapping(item)
        summary.append(
            {
                "code": _plain_str(issue.get("code")),
                "message": _short_text(issue.get("message")),
                "detail": _short_text(issue.get("detail")),
            }
        )
    return summary


def _checks_summary(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    summary: list[dict[str, Any]] = []
    for item in value:
        check = _as_mapping(item)
        parsed_json = _as_mapping(check.get("parsed_json")) if check.get("parsed_json") else {}
        summary.append(
            {
                "name": _plain_str(check.get("name")),
                "status": _plain_str(check.get("status"))
                or _plain_str(parsed_json.get("final_status")),
                "blocking": check.get("blocking") if isinstance(check.get("blocking"), bool) else None,
                "failure_code": _plain_str(check.get("failure_code")),
                "summary": _short_text(check.get("summary")),
                "parsed_final_status": _plain_str(parsed_json.get("final_status")),
                "parsed_failure_codes": _failure_codes(parsed_json),
            }
        )
    return summary


def _status_counts(output: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "checks_run",
        "checks_passed",
        "checks_blocked",
        "distribution_count",
        "exists_count",
        "missing_count",
        "error_count",
        "project_token_count",
        "project_token_ok_count",
        "project_token_missing_count",
        "forbidden_paths",
        "build_artifacts",
        "missing_public_materials",
        "old_version_hits",
    )
    counts: dict[str, Any] = {}
    for key in keys:
        value = output.get(key)
        if isinstance(value, int):
            counts[key] = value
        elif isinstance(value, (list, tuple)):
            counts[f"{key}_count"] = len(value)
    return counts


def _warning_candidates(
    provider: str,
    output: dict[str, Any],
    final_status: str | None,
) -> list[str]:
    warnings: list[str] = []
    if provider == "check_release_tokens.py":
        missing_count = output.get("project_token_missing_count")
        fallback_status = output.get("fallback_token_status")
        if isinstance(missing_count, int) and missing_count > 0:
            warnings.append("Project token environment variables are missing.")
        if fallback_status == "MISS":
            warnings.append("Fallback token environment variable is missing.")
    if final_status and final_status.upper() in {"WARN", "WARNING"}:
        warnings.append(f"{provider} reported {final_status}.")
    return _dedupe(warnings)


def _block_candidates(
    provider: str,
    output: dict[str, Any],
    final_status: str | None,
    failure_codes: list[str],
    issues_summary: list[dict[str, str | None]],
    checks_summary: list[dict[str, Any]],
) -> list[str]:
    candidates: list[str] = []
    status = final_status.upper() if final_status else None
    if status in {"BLOCK", "FAIL", "FAILED", "ERROR"}:
        candidates.append(f"{provider} reported final_status={final_status}.")
    if failure_codes:
        candidates.append(f"{provider} reported failure_codes={', '.join(failure_codes)}.")
    for issue in issues_summary:
        code = issue.get("code")
        if code:
            candidates.append(f"{provider} reported issue {code}.")
    for check in checks_summary:
        if check.get("blocking") is True:
            name = check.get("name") or "unknown"
            candidates.append(f"{provider} has blocking subcheck {name}.")
        parsed_failure_codes = check.get("parsed_failure_codes")
        if parsed_failure_codes:
            candidates.append(
                f"{provider} subcheck reported failure_codes={', '.join(parsed_failure_codes)}."
            )
    if provider == "check_pypi_version.py":
        phase = output.get("phase")
        if phase == "pre-release" and "PYPI_VERSION_ALREADY_EXISTS" in failure_codes:
            candidates.append("Pre-release PyPI target version already exists.")
        if phase == "post-release" and "PYPI_VERSION_MISSING" in failure_codes:
            candidates.append("Post-release PyPI target version is missing.")
    return _dedupe(candidates)


def _human_review_reasons(
    provider: str,
    block_candidates: list[str],
    warning_candidates: list[str],
    failure_codes: list[str],
    checks_summary: list[dict[str, Any]],
) -> list[str]:
    reasons: list[str] = []
    if block_candidates:
        reasons.append("Block candidates require human release governance review.")
    if provider in {
        "check_public_surface.py",
        "check_public_workflow_template.py",
        "check_release_note_tag_github_release.py",
        "check_trusted_publishing_config.py",
        "release_safety_check.py",
    } and (block_candidates or failure_codes):
        reasons.append(f"{provider} touches public/release boundary evidence.")
    if provider == "check_release_tokens.py" and warning_candidates:
        reasons.append("Credential availability warning requires human review.")
    if any(check.get("blocking") is True for check in checks_summary):
        reasons.append("Blocking release safety subchecks require human review.")
    return _dedupe(reasons)


def _evidence_summary(
    provider: str,
    phase: str | None,
    target_version: str | None,
    final_status: str | None,
    failure_codes: list[str],
) -> str:
    codes = ", ".join(failure_codes) if failure_codes else "none"
    return (
        f"Release governance evidence from {provider}: "
        f"phase={phase or 'unknown'}, "
        f"target_version={target_version or 'unknown'}, "
        f"final_status={final_status or 'unknown'}, "
        f"failure_codes={codes}."
    )


def _first_metadata_value(
    evidence_items: list[GovernanceEvidence],
    key: str,
    fallback: str | None,
) -> str | None:
    if fallback:
        return fallback
    for item in evidence_items:
        value = item.metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _flatten_metadata_lists(
    evidence_items: list[GovernanceEvidence],
    key: str,
) -> list[str]:
    values: list[str] = []
    for item in evidence_items:
        raw = item.metadata.get(key)
        if isinstance(raw, (list, tuple)):
            values.extend(str(value) for value in raw if value)
    return _dedupe(values)


def _missing_release_evidence(evidence_items: list[GovernanceEvidence]) -> list[str]:
    providers = {
        item.metadata.get("script_name")
        for item in evidence_items
        if isinstance(item.metadata.get("script_name"), str)
    }
    return sorted(SUPPORTED_RELEASE_EVIDENCE_PROVIDERS.difference(providers))


def _case_subject(
    release_target: str | None,
    target_version: str | None,
    phase: str | None,
) -> str:
    parts = [
        release_target or "release target",
        target_version or "unknown version",
        phase or "unknown phase",
    ]
    return " / ".join(parts)


def _sensitive_field_paths(value: Any, *, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key)
            path = f"{prefix}.{key}" if prefix else key
            if _is_sensitive_key(key):
                paths.add(path)
                continue
            paths.update(_sensitive_field_paths(child, prefix=path))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            paths.update(_sensitive_field_paths(child, prefix=f"{prefix}[{index}]"))
    return paths


def _digest_output(value: Any) -> str:
    payload = json.dumps(_digest_safe(value), ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _digest_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): ("<omitted>" if _is_sensitive_key(str(key)) else _digest_safe(child))
            for key, child in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_digest_safe(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return {"object_type": type(value).__name__}


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return (
        normalized in _RAW_OR_SENSITIVE_KEYS
        or "token" in normalized
        or "secret" in normalized
        or "stdout" in normalized
        or "stderr" in normalized
        or "command" in normalized
    )


def _short_text(value: Any, limit: int = 160) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    text = _redact_text(value).replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _redact_text(value: str) -> str:
    redacted = value
    redacted = re.sub(r"pypi-[A-Za-z0-9._-]+", "<token-redacted>", redacted)
    redacted = re.sub(r"/Users/[^ \n\t]+", "<path-redacted>", redacted)
    redacted = re.sub(r"https?://[^ \n\t]+", "<url-redacted>", redacted)
    for marker in ("TWINE_TOKEN", "GITHUB_TOKEN", "PYPI_TOKEN"):
        if marker in redacted:
            redacted = redacted.replace(marker, "<token-env-redacted>")
    return redacted


def _make_id(*parts: str | None) -> str:
    raw = "-".join(part for part in parts if part)
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", raw).strip("-").lower()
    return safe or "release-governance"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
