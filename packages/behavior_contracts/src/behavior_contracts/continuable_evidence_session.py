"""Behavior guards for continuable evidence session contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from typing import Any

from behavior_contracts.governance_candidate import CandidateGuardResult
from schemas.continuable_evidence_session import (
    CONTINUABLE_EVIDENCE_SESSION_ARTIFACT_INDEX_REF_PREFIX,
    CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX,
    CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_REF_PREFIX,
    CONTINUABLE_EVIDENCE_SESSION_SEED_REF_PREFIX,
    CONTINUABLE_EVIDENCE_SESSION_SUMMARY_REF_PREFIX,
    CONTINUABLE_EVIDENCE_SESSION_TRAJECTORY_REF_PREFIX,
    CONTINUABLE_EVIDENCE_SESSION_TURN_REF_PREFIX,
    FORBIDDEN_CONTINUABLE_EVIDENCE_SESSION_KEYS,
    SAFE_REF_PREFIXES,
)


RUNTIME_CLAIM_FIELDS = frozenset(
    {
        "runtime_backed",
        "backed_by_adk_session",
        "backed_by_adk_event_stream",
        "backed_by_adk_artifact_service",
        "backed_by_adk_task_runtime",
        "backed_by_adk_workflow_runtime",
        "memory_enabled",
    }
)
SAFE_SCALAR_TYPES = (str, int, float, bool, type(None))
RUNTIME_BINDING_FORBIDDEN_TRUE_FIELDS = frozenset(
    {
        "raw_runtime_object_included",
        "raw_event_payload_included",
        "artifact_body_included",
        "adk_eval_raw_data_included",
        "user_product_runtime_path_enabled",
        "default_local_state_dir_enabled",
        "auto_resume_answer_enabled",
        "skills_loaded",
        "memory_enabled",
        "tools_mcp_enabled",
        "callbacks_enabled",
        "plugins_enabled",
    }
)
RUNTIME_VISIBLE_SUMMARY_FORBIDDEN_TRUE_FIELDS = frozenset(
    {
        "user_product_runtime_path_enabled",
        "default_local_state_dir_enabled",
        "auto_resume_answer_enabled",
        "workflow_replay_enabled",
        "llm_call_enabled",
        "task_runtime_implementation_enabled",
        "raw_runtime_object_included",
        "raw_event_payload_included",
        "artifact_body_included",
        "adk_eval_raw_data_included",
        "skills_loaded",
        "memory_enabled",
        "tools_mcp_enabled",
        "callbacks_enabled",
        "plugins_enabled",
    }
)
SENSITIVE_TEXT_MARKERS = (
    "api_key",
    "authorization:",
    "bearer ",
    "config_context",
    "cookie:",
    "credential",
    "full_answer",
    "provider_response",
    "raw prompt",
    "raw_prompt",
    "raw provider",
    "secret",
    "system_prompt",
    "token",
    "traceback",
)


def guard_continuable_evidence_session_raw_boundary(payload: Any) -> CandidateGuardResult:
    """Block raw evidence, prompts, provider payloads, secrets, and raw objects."""

    violations = tuple(_raw_boundary_violations(_mapping(payload), path="$"))
    return CandidateGuardResult(passed=not violations, violations=violations)


def guard_continuable_evidence_session_ref_prefixes(
    payload: Any,
) -> CandidateGuardResult:
    """Validate approved product ref prefixes for known session refs."""

    data = _mapping(payload)
    checks = {
        "continuable_evidence_session_ref": CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX,
        "session_seed_ref": CONTINUABLE_EVIDENCE_SESSION_SEED_REF_PREFIX,
        "session_turn_ref": CONTINUABLE_EVIDENCE_SESSION_TURN_REF_PREFIX,
        "session_summary_ref": CONTINUABLE_EVIDENCE_SESSION_SUMMARY_REF_PREFIX,
        "session_artifact_index_ref": CONTINUABLE_EVIDENCE_SESSION_ARTIFACT_INDEX_REF_PREFIX,
        "session_trajectory_ref": CONTINUABLE_EVIDENCE_SESSION_TRAJECTORY_REF_PREFIX,
    }
    violations: list[str] = []
    for field_name, prefix in checks.items():
        value = data.get(field_name)
        if value is None:
            continue
        if not isinstance(value, str) or not value.startswith(prefix):
            violations.append(f"{field_name}:invalid_ref_prefix")
    for field_name in (
        "source_answer_run_ref",
        "latest_answer_run_ref",
        "answer_run_ref",
        "parent_answer_run_ref",
        "answer_artifact_ref",
        "trace_inspect_ref",
        "observability_summary_ref",
        "resume_summary_ref",
        "latest_resume_summary_ref",
        "temporary_follow_up_seed_ref",
    ):
        value = data.get(field_name)
        if value is None:
            continue
        if not isinstance(value, str) or not _has_safe_ref_prefix(value):
            violations.append(f"{field_name}:unsupported_ref_prefix")
    for field_name in (
        "answer_run_refs",
        "answer_artifact_refs",
        "trace_inspect_refs",
        "observability_summary_refs",
        "export_package_refs",
        "developer_review_refs",
        "source_refs",
        "digest_refs",
    ):
        for value in _sequence(data.get(field_name)):
            if not isinstance(value, str) or not _has_safe_ref_prefix(value):
                violations.append(f"{field_name}:unsupported_ref_prefix")
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_continuable_evidence_session_resume_policy(
    payload: Any,
) -> CandidateGuardResult:
    """Validate resume policy status, blockers, and authorization requirements."""

    data = _mapping(payload)
    violations: list[str] = []
    resume_status = data.get("resume_status")
    resume_allowed = data.get("resume_allowed")
    blockers = _sequence(data.get("blocking_reasons"))
    if resume_allowed is True and resume_status not in {
        "resumable",
        "requires_confirmation",
    }:
        violations.append("resume_allowed:invalid_status")
    if resume_allowed is True and blockers:
        violations.append("resume_allowed:must_not_have_blockers")
    if resume_status in {"expired", "deleted", "blocked"} and not blockers:
        violations.append(f"{resume_status}:requires_blocking_reasons")
    if data.get("requires_user_confirmation") is False:
        violations.append("requires_user_confirmation:must_be_true")
    if data.get("requires_external_readonly_authorization") is False and resume_status in {
        "resumable",
        "requires_confirmation",
        "requires_ref_reload",
    }:
        violations.append("requires_external_readonly_authorization:must_be_true")
    if data.get("requires_model_authorization") is False and resume_allowed is True:
        violations.append("requires_model_authorization:must_be_true")
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_continuable_evidence_session_turn_kind(payload: Any) -> CandidateGuardResult:
    """Keep evidence follow-up and answer-scoped transformation distinct."""

    data = _mapping(payload)
    violations: list[str] = []
    turn_kind = data.get("turn_kind")
    if turn_kind == "evidence_follow_up" and data.get("requires_reauthorization") is False:
        violations.append("evidence_follow_up:requires_reauthorization")
    if turn_kind == "answer_transformation" and data.get("requires_reauthorization") is True:
        violations.append("answer_transformation:must_not_require_evidence_reload")
    if turn_kind == "answer_transformation" and data.get("answer_state_boundary") == "evidence_grounded":
        violations.append("answer_transformation:misclassified_as_evidence_grounded")
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_continuable_evidence_session_runtime_claims(
    payload: Any,
) -> CandidateGuardResult:
    """Block product-level contracts from claiming ADK runtime backing."""

    violations = tuple(_runtime_claim_violations(_mapping(payload), path="$"))
    return CandidateGuardResult(passed=not violations, violations=violations)


def guard_continuable_evidence_session_metadata_safety(
    payload: Any,
) -> CandidateGuardResult:
    """Ensure metadata contains only safe scalar values and no sensitive keys."""

    data = _mapping(payload)
    violations: list[str] = []
    for field_name in ("metadata",):
        metadata = data.get(field_name)
        if metadata is None:
            continue
        violations.extend(_metadata_violations(metadata, path=f"$.{field_name}"))
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_continuable_evidence_session_artifact_index(
    payload: Any,
) -> CandidateGuardResult:
    """Ensure artifact indexes are refs-only and have no ArtifactService binding."""

    data = _mapping(payload)
    violations: list[str] = []
    if data.get("artifact_service_binding_refs"):
        violations.append("artifact_service_binding_refs:must_be_empty")
    violations.extend(_raw_boundary_violations(data, path="$"))
    for field_name in (
        "answer_run_refs",
        "answer_artifact_refs",
        "trace_inspect_refs",
        "observability_summary_refs",
        "export_package_refs",
    ):
        for value in _sequence(data.get(field_name)):
            if not isinstance(value, str) or not _has_safe_ref_prefix(value):
                violations.append(f"{field_name}:unsupported_ref_prefix")
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_continuable_evidence_session_storage_policy(
    payload: Any,
) -> CandidateGuardResult:
    """Ensure storage policies require opt-in and do not claim runtime/config backing."""

    data = _mapping(payload)
    if not _is_payload(data, "continuable_evidence_session_storage_policy"):
        return CandidateGuardResult(passed=True, violations=())
    violations: list[str] = []
    if data.get("save_policy") != "explicit_user_opt_in":
        violations.append("save_policy:must_be_explicit_user_opt_in")
    if data.get("auto_save_default") is True:
        violations.append("auto_save_default:must_be_false")
    if data.get("requires_user_confirmation_on_save") is False:
        violations.append("requires_user_confirmation_on_save:must_be_true")
    if data.get("requires_user_confirmation_on_resume") is False:
        violations.append("requires_user_confirmation_on_resume:must_be_true")
    if data.get("config_backed") is True:
        violations.append("config_backed:must_be_false")
    if data.get("runtime_backed") is True:
        violations.append("runtime_backed:must_be_false")
    if data.get("memory_enabled") is True:
        violations.append("memory_enabled:must_be_false")
    violations.extend(_raw_boundary_violations(data, path="$"))
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_continuable_evidence_session_local_state_root_policy(
    payload: Any,
) -> CandidateGuardResult:
    """Keep local state root as a platform policy, not repo outputs or package data."""

    data = _mapping(payload)
    if not _is_payload(data, "continuable_evidence_session_local_state_root_policy"):
        return CandidateGuardResult(passed=True, violations=())
    violations: list[str] = []
    if data.get("reads_environment") is True:
        violations.append("reads_environment:must_be_false")
    if data.get("resolves_user_home") is True:
        violations.append("resolves_user_home:must_be_false")
    if data.get("uses_repo_outputs") is True:
        violations.append("uses_repo_outputs:must_be_false")
    if data.get("packaged_resource") is True:
        violations.append("packaged_resource:must_be_false")
    if data.get("public_repo_synced") is True:
        violations.append("public_repo_synced:must_be_false")
    violations.extend(_raw_boundary_violations(data, path="$"))
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_continuable_evidence_session_record_manifest(
    payload: Any,
) -> CandidateGuardResult:
    """Ensure manifests remain logical contracts and do not claim local I/O."""

    data = _mapping(payload)
    if not _is_payload(data, "continuable_evidence_session_record_manifest"):
        return CandidateGuardResult(passed=True, violations=())
    violations: list[str] = []
    if data.get("contains_raw_payload") is True:
        violations.append("contains_raw_payload:must_be_false")
    if data.get("io_performed") is True:
        violations.append("io_performed:must_be_false")
    violations.extend(_raw_boundary_violations(data, path="$"))
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_continuable_evidence_session_index_entry(
    payload: Any,
) -> CandidateGuardResult:
    """Ensure session index entries are safe summaries, not question or answer bodies."""

    data = _mapping(payload)
    if not _is_payload(data, "continuable_evidence_session_index_entry"):
        return CandidateGuardResult(passed=True, violations=())
    violations: list[str] = []
    if data.get("session_status") in {"expired", "deleted", "blocked", "unavailable"}:
        if data.get("resumable") is True:
            violations.append(f"{data.get('session_status')}:must_not_be_resumable")
    if data.get("session_status") == "resumable" and data.get("resumable") is False:
        violations.append("resumable:requires_resumable_true")
    violations.extend(_raw_boundary_violations(data, path="$"))
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_continuable_evidence_session_delete_policy(
    payload: Any,
) -> CandidateGuardResult:
    """Ensure delete policy requires confirmation and deleted sessions stay unrecoverable."""

    data = _mapping(payload)
    if not _is_payload(data, "continuable_evidence_session_delete_policy"):
        return CandidateGuardResult(passed=True, violations=())
    violations: list[str] = []
    if data.get("requires_user_confirmation") is False:
        violations.append("requires_user_confirmation:must_be_true")
    if data.get("removes_local_record") is False:
        violations.append("removes_local_record:must_be_true")
    if data.get("removes_from_resumable_index") is False:
        violations.append("removes_from_resumable_index:must_be_true")
    if data.get("deletion_receipt_contains_raw_payload") is True:
        violations.append("deletion_receipt_contains_raw_payload:must_be_false")
    if data.get("deleted_session_resumable") is True:
        violations.append("deleted_session_resumable:must_be_false")
    violations.extend(_raw_boundary_violations(data, path="$"))
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_continuable_evidence_session_expiration_policy(
    payload: Any,
) -> CandidateGuardResult:
    """Ensure expiration does not become direct resume or immediate cleanup."""

    data = _mapping(payload)
    if not _is_payload(data, "continuable_evidence_session_expiration_policy"):
        return CandidateGuardResult(passed=True, violations=())
    violations: list[str] = []
    if data.get("expired_session_resumable") is True:
        violations.append("expired_session_resumable:must_be_false")
    if data.get("expired_equals_deleted") is True:
        violations.append("expired_equals_deleted:must_be_false")
    if data.get("cleanup_immediate") is True:
        violations.append("cleanup_immediate:must_be_false")
    violations.extend(_raw_boundary_violations(data, path="$"))
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_continuable_evidence_session_export_policy(
    payload: Any,
) -> CandidateGuardResult:
    """Ensure exports remain refs-and-summaries packages, not evidence archives."""

    data = _mapping(payload)
    if not _is_payload(data, "continuable_evidence_session_export_policy"):
        return CandidateGuardResult(passed=True, violations=())
    violations: list[str] = []
    if data.get("export_package_kind") != "refs_and_summaries":
        violations.append("export_package_kind:must_be_refs_and_summaries")
    if data.get("export_package_is_evidence_archive") is True:
        violations.append("export_package_is_evidence_archive:must_be_false")
    for field_name in (
        "includes_raw_evidence",
        "includes_raw_prompt",
        "includes_raw_provider_response",
        "includes_full_answer",
        "includes_secret",
        "includes_full_config_context",
        "includes_adk_raw_object",
    ):
        if data.get(field_name) is True:
            violations.append(f"{field_name}:must_be_false")
    if data.get("warns_refs_may_not_resolve") is False:
        violations.append("warns_refs_may_not_resolve:must_be_true")
    if data.get("import_requires_confirmation") is False:
        violations.append("import_requires_confirmation:must_be_true")
    if data.get("import_requires_authorization") is False:
        violations.append("import_requires_authorization:must_be_true")
    violations.extend(_raw_boundary_violations(data, path="$"))
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_continuable_evidence_session_runtime_binding(
    payload: Any,
) -> CandidateGuardResult:
    """Ensure runtime binding remains product-level refs and safe summaries."""

    data = _mapping(payload)
    if not _is_payload(data, "continuable_evidence_session_runtime_binding"):
        return CandidateGuardResult(passed=True, violations=())
    violations: list[str] = []
    runtime_binding_ref = data.get("runtime_binding_ref")
    if not isinstance(runtime_binding_ref, str) or not runtime_binding_ref.startswith(
        CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_REF_PREFIX
    ):
        violations.append("runtime_binding_ref:invalid_ref_prefix")
    session_ref = data.get("continuable_evidence_session_ref")
    if not isinstance(session_ref, str) or not session_ref.startswith(
        CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX
    ):
        violations.append("continuable_evidence_session_ref:invalid_ref_prefix")
    if data.get("runtime_binding_status") not in {
        "unavailable",
        "probed",
        "bindable",
        "bound",
        "failed",
    }:
        violations.append("runtime_binding_status:invalid")
    if data.get("runtime_binding_scope") not in {
        "agent_session_event_artifactservice"
    }:
        violations.append("runtime_binding_scope:invalid")
    for field_name in RUNTIME_BINDING_FORBIDDEN_TRUE_FIELDS:
        if data.get(field_name) is True:
            violations.append(f"{field_name}:must_be_false")
    for field_name in (
        "runtime_binding_summary_ref",
        "agent_binding_ref",
        "session_binding_ref",
        "runtime_binding_evaluation_summary_ref",
    ):
        value = data.get(field_name)
        if value is not None and (
            not isinstance(value, str) or not _has_safe_ref_prefix(value)
        ):
            violations.append(f"{field_name}:unsupported_ref_prefix")
    for field_name in ("event_review_refs", "artifact_binding_summary_refs"):
        for value in _sequence(data.get(field_name)):
            if not isinstance(value, str) or not _has_safe_ref_prefix(value):
                violations.append(f"{field_name}:unsupported_ref_prefix")
    violations.extend(_raw_boundary_violations(data, path="$"))
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_continuable_evidence_session_runtime_visible_summary(
    payload: Any,
) -> CandidateGuardResult:
    """Ensure user-visible runtime summaries stay refs-only and non-executing."""

    data = _mapping(payload)
    if not _is_payload(data, "continuable_evidence_session_runtime_visible_summary"):
        return CandidateGuardResult(passed=True, violations=())
    violations: list[str] = []
    summary_ref = data.get("runtime_visible_summary_ref")
    if not isinstance(summary_ref, str) or not summary_ref.startswith(
        CONTINUABLE_EVIDENCE_SESSION_SUMMARY_REF_PREFIX
    ):
        violations.append("runtime_visible_summary_ref:invalid_ref_prefix")
    session_ref = data.get("continuable_evidence_session_ref")
    if not isinstance(session_ref, str) or not session_ref.startswith(
        CONTINUABLE_EVIDENCE_SESSION_REF_PREFIX
    ):
        violations.append("continuable_evidence_session_ref:invalid_ref_prefix")
    runtime_binding_ref = data.get("runtime_binding_ref")
    if runtime_binding_ref is not None and (
        not isinstance(runtime_binding_ref, str)
        or not runtime_binding_ref.startswith(
            CONTINUABLE_EVIDENCE_SESSION_RUNTIME_BINDING_REF_PREFIX
        )
    ):
        violations.append("runtime_binding_ref:invalid_ref_prefix")
    if data.get("runtime_binding_status") not in {
        "unavailable",
        "probed",
        "bindable",
        "bound",
        "failed",
    }:
        violations.append("runtime_binding_status:invalid")
    for field_name in RUNTIME_VISIBLE_SUMMARY_FORBIDDEN_TRUE_FIELDS:
        if data.get(field_name) is True:
            violations.append(f"{field_name}:must_be_false")
    evaluation_summary_ref = data.get("evaluation_summary_ref")
    if evaluation_summary_ref is not None and (
        not isinstance(evaluation_summary_ref, str)
        or not _has_safe_ref_prefix(evaluation_summary_ref)
    ):
        violations.append("evaluation_summary_ref:unsupported_ref_prefix")
    if data.get("artifact_index") in (None, []):
        violations.append("artifact_index:required")
    for index, item in enumerate(_sequence(data.get("artifact_index"))):
        item_mapping = _mapping(item)
        ref = item_mapping.get("ref")
        if not isinstance(ref, str) or not _has_safe_ref_prefix(ref):
            violations.append(f"artifact_index[{index}].ref:unsupported_ref_prefix")
    violations.extend(_raw_boundary_violations(data, path="$"))
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


DEFAULT_CONTINUABLE_EVIDENCE_SESSION_GUARDS = (
    guard_continuable_evidence_session_raw_boundary,
    guard_continuable_evidence_session_ref_prefixes,
    guard_continuable_evidence_session_resume_policy,
    guard_continuable_evidence_session_turn_kind,
    guard_continuable_evidence_session_runtime_claims,
    guard_continuable_evidence_session_metadata_safety,
    guard_continuable_evidence_session_artifact_index,
    guard_continuable_evidence_session_storage_policy,
    guard_continuable_evidence_session_local_state_root_policy,
    guard_continuable_evidence_session_record_manifest,
    guard_continuable_evidence_session_index_entry,
    guard_continuable_evidence_session_delete_policy,
    guard_continuable_evidence_session_expiration_policy,
    guard_continuable_evidence_session_export_policy,
    guard_continuable_evidence_session_runtime_binding,
    guard_continuable_evidence_session_runtime_visible_summary,
)


def validate_continuable_evidence_session_guards(payload: Any) -> CandidateGuardResult:
    """Run the default non-executing continuable evidence session guards."""

    violations: list[str] = []
    for guard in DEFAULT_CONTINUABLE_EVIDENCE_SESSION_GUARDS:
        result = guard(payload)
        violations.extend(result.violations)
    unique_violations = tuple(dict.fromkeys(violations))
    return CandidateGuardResult(
        passed=not unique_violations,
        violations=unique_violations,
    )


def _mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items() if isinstance(key, str)}
    if is_dataclass(value) and not isinstance(value, type):
        return _mapping(asdict(value))
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        if isinstance(dumped, Mapping):
            return _mapping(dumped)
    return {}


def _sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list | tuple):
        return list(value)
    return []


def _has_safe_ref_prefix(value: str) -> bool:
    return any(value.startswith(prefix) for prefix in SAFE_REF_PREFIXES)


def _is_payload(data: Mapping[str, Any], payload_type: str) -> bool:
    return data.get("payload_type") == payload_type


def _raw_boundary_violations(value: Any, *, path: str) -> list[str]:
    violations: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            normalized_key = key_text.lower()
            if normalized_key in FORBIDDEN_CONTINUABLE_EVIDENCE_SESSION_KEYS:
                violations.append(f"{path}.{key_text}:forbidden_raw_boundary_key")
            violations.extend(
                _raw_boundary_violations(item, path=f"{path}.{key_text}")
            )
        return violations
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            violations.extend(_raw_boundary_violations(item, path=f"{path}[{index}]"))
        return violations
    if isinstance(value, str):
        normalized = value.lower()
        for marker in SENSITIVE_TEXT_MARKERS:
            if marker in normalized:
                violations.append(f"{path}:forbidden_raw_boundary_marker:{marker}")
                break
    return violations


def _runtime_claim_violations(value: Any, *, path: str) -> list[str]:
    violations: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if key_text in RUNTIME_CLAIM_FIELDS and item is True:
                violations.append(f"{path}.{key_text}:runtime_claim_forbidden")
            violations.extend(_runtime_claim_violations(item, path=f"{path}.{key_text}"))
        return violations
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            violations.extend(_runtime_claim_violations(item, path=f"{path}[{index}]"))
    return violations


def _metadata_violations(value: Any, *, path: str) -> list[str]:
    violations: list[str] = []
    if not isinstance(value, Mapping):
        return [f"{path}:metadata_must_be_mapping"]
    for key, item in value.items():
        key_text = str(key)
        normalized_key = key_text.lower()
        if normalized_key in FORBIDDEN_CONTINUABLE_EVIDENCE_SESSION_KEYS:
            violations.append(f"{path}.{key_text}:forbidden_metadata_key")
        if not isinstance(item, SAFE_SCALAR_TYPES):
            violations.append(f"{path}.{key_text}:metadata_value_must_be_scalar")
        if isinstance(item, str):
            normalized = item.lower()
            if any(marker in normalized for marker in SENSITIVE_TEXT_MARKERS):
                violations.append(f"{path}.{key_text}:forbidden_metadata_value")
    return violations


__all__ = [
    "DEFAULT_CONTINUABLE_EVIDENCE_SESSION_GUARDS",
    "guard_continuable_evidence_session_artifact_index",
    "guard_continuable_evidence_session_delete_policy",
    "guard_continuable_evidence_session_expiration_policy",
    "guard_continuable_evidence_session_export_policy",
    "guard_continuable_evidence_session_index_entry",
    "guard_continuable_evidence_session_local_state_root_policy",
    "guard_continuable_evidence_session_metadata_safety",
    "guard_continuable_evidence_session_raw_boundary",
    "guard_continuable_evidence_session_record_manifest",
    "guard_continuable_evidence_session_ref_prefixes",
    "guard_continuable_evidence_session_resume_policy",
    "guard_continuable_evidence_session_runtime_binding",
    "guard_continuable_evidence_session_runtime_claims",
    "guard_continuable_evidence_session_runtime_visible_summary",
    "guard_continuable_evidence_session_storage_policy",
    "guard_continuable_evidence_session_turn_kind",
    "validate_continuable_evidence_session_guards",
]
