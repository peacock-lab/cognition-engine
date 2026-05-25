from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas import (
    EvidenceSummaryAnswerContextSchema as RootEvidenceSummaryAnswerContextSchema,
    EvidenceSummaryAnswerArtifactSchema as RootEvidenceSummaryAnswerArtifactSchema,
    EvidenceSummaryAnswerFollowUpSeedSchema as RootEvidenceSummaryAnswerFollowUpSeedSchema,
    EvidenceSummaryAnswerObservabilitySummarySchema as RootEvidenceSummaryAnswerObservabilitySummarySchema,
    EvidenceSummaryAnswerRunSchema as RootEvidenceSummaryAnswerRunSchema,
    EvidenceSummaryAnswerTraceSchema as RootEvidenceSummaryAnswerTraceSchema,
    EvidenceSummaryAnswerTraceInspectSchema as RootEvidenceSummaryAnswerTraceInspectSchema,
    GovernedEvidenceDigestSchema as RootGovernedEvidenceDigestSchema,
    validate_evidence_summary_answer_artifact as root_validate_artifact,
    validate_evidence_summary_answer_follow_up_seed as root_validate_follow_up_seed,
    validate_evidence_summary_answer_observability_summary as root_validate_observability_summary,
    validate_evidence_summary_answer_run as root_validate_run,
    validate_evidence_summary_answer_trace as root_validate_trace,
    validate_evidence_summary_answer_trace_inspect as root_validate_trace_inspect,
    validate_governed_evidence_digest as root_validate_governed_evidence_digest,
)
from schemas.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX,
    EVIDENCE_SUMMARY_ANSWER_ARTIFACT_VERSION,
    EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION,
    EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SEED_VERSION,
    EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_REF_PREFIX,
    EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_VERSION,
    EVIDENCE_SUMMARY_ANSWER_PRODUCT,
    EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION,
    EVIDENCE_SUMMARY_ANSWER_RUN_REF_PREFIX,
    EVIDENCE_SUMMARY_ANSWER_RUN_VERSION,
    EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_REF_PREFIX,
    EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_VERSION,
    EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX,
    EVIDENCE_SUMMARY_ANSWER_TRACE_VERSION,
    GOVERNED_EVIDENCE_DIGEST_VERSION,
    EvidenceSummaryAnswerArtifactSchema,
    EvidenceSummaryAnswerContextSchema,
    EvidenceSummaryAnswerFollowUpSeedSchema,
    EvidenceSummaryAnswerObservabilitySummarySchema,
    EvidenceSummaryAnswerResultSchema,
    EvidenceSummaryAnswerRunSchema,
    EvidenceSummaryAnswerTraceInspectSchema,
    EvidenceSummaryAnswerTraceSchema,
    GovernedEvidenceDigestSchema,
    validate_evidence_summary_answer_artifact,
    validate_evidence_summary_answer_context,
    validate_evidence_summary_answer_follow_up_seed,
    validate_evidence_summary_answer_observability_summary,
    validate_evidence_summary_answer_result,
    validate_evidence_summary_answer_run,
    validate_evidence_summary_answer_trace,
    validate_evidence_summary_answer_trace_inspect,
    validate_governed_evidence_digest,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_SOURCE_ROOT = REPO_ROOT / "packages" / "schemas" / "src" / "schemas"


def test_governed_evidence_digest_accepts_minimal_public_shape() -> None:
    digest = validate_governed_evidence_digest(_digest())

    assert isinstance(digest, GovernedEvidenceDigestSchema)
    assert digest.product == EVIDENCE_SUMMARY_ANSWER_PRODUCT
    assert digest.payload_type == "governed_evidence_digest"
    assert digest.payload_version == GOVERNED_EVIDENCE_DIGEST_VERSION
    assert digest.digest_ref == "governed-evidence-digest://request-1/digest-1"
    assert digest.evidence_ref == "evidence://external-readonly/request-1/fetch-1"
    assert digest.source_url_host == "example.com"
    assert digest.raw_boundary_flags.raw_payload_included is False
    assert digest.summary_facts == ["The source describes a governed answer context."]


def test_evidence_summary_answer_context_accepts_minimal_public_shape() -> None:
    context = validate_evidence_summary_answer_context(_context())

    assert isinstance(context, EvidenceSummaryAnswerContextSchema)
    assert context.product == EVIDENCE_SUMMARY_ANSWER_PRODUCT
    assert context.payload_type == "evidence_summary_answer_context"
    assert context.payload_version == EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION
    assert context.digests[0].digest_id == "digest-1"
    assert context.evidence_refs[0].ref == "evidence://external-readonly/request-1/fetch-1"


def test_evidence_summary_answer_result_accepts_success_with_citation() -> None:
    result = validate_evidence_summary_answer_result(_result())

    assert isinstance(result, EvidenceSummaryAnswerResultSchema)
    assert result.product == EVIDENCE_SUMMARY_ANSWER_PRODUCT
    assert result.payload_type == "evidence_summary_answer_result"
    assert result.payload_version == EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION
    assert result.status == "success"
    assert result.evidence_refs_used[0].ref == "evidence://external-readonly/request-1/fetch-1"
    assert result.digest_refs_used == ["governed-evidence-digest://request-1/digest-1"]


def test_evidence_summary_answer_follow_up_seed_accepts_temporary_public_shape() -> None:
    seed = validate_evidence_summary_answer_follow_up_seed(_follow_up_seed())

    assert isinstance(seed, EvidenceSummaryAnswerFollowUpSeedSchema)
    assert seed.product == EVIDENCE_SUMMARY_ANSWER_PRODUCT
    assert seed.payload_type == "evidence_summary_answer_follow_up_seed"
    assert seed.payload_version == EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SEED_VERSION
    assert seed.follow_up_allowed is True
    assert seed.temporary_only is True
    assert seed.durable_session is False
    assert seed.memory_enabled is False
    assert seed.digest_refs == ["governed-evidence-digest://request-1/digest-1"]


def test_evidence_summary_answer_trace_accepts_operation_flow_compatible_shape() -> None:
    trace = validate_evidence_summary_answer_trace(_trace())

    assert isinstance(trace, EvidenceSummaryAnswerTraceSchema)
    assert trace.payload_version == EVIDENCE_SUMMARY_ANSWER_TRACE_VERSION
    assert trace.trace_ref.startswith(EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX)
    assert trace.answer_status == "success"
    assert trace.task_compatible is True
    assert trace.workflow_compatible is True
    assert trace.backed_by_adk_task_runtime is False
    assert trace.backed_by_adk_workflow_runtime is False
    assert trace.provider_profile_ref == "local_ollama"
    assert trace.model_profile_ref == "gemma4_pro_local"
    assert trace.output_governance_profile_ref == "adk_output_schema_gemma4_baseline"
    assert trace.durable_session is False
    assert trace.memory_enabled is False


def test_evidence_summary_answer_artifact_accepts_operation_flow_compatible_shape() -> None:
    artifact = validate_evidence_summary_answer_artifact(_artifact())

    assert isinstance(artifact, EvidenceSummaryAnswerArtifactSchema)
    assert artifact.payload_version == EVIDENCE_SUMMARY_ANSWER_ARTIFACT_VERSION
    assert artifact.artifact_ref.startswith(EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX)
    assert artifact.trace_ref.startswith(EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX)
    assert artifact.answer_status == "success"
    assert artifact.artifact_status == "success"
    assert artifact.answer == "The governed evidence supports using a schema first."
    assert artifact.export_allowed is False
    assert artifact.delete_supported is True
    assert artifact.task_compatible is True
    assert artifact.workflow_compatible is True
    assert artifact.backed_by_adk_task_runtime is False
    assert artifact.backed_by_adk_workflow_runtime is False
    assert artifact.durable_session is False
    assert artifact.memory_enabled is False


def test_evidence_summary_answer_observability_summary_accepts_safe_shape() -> None:
    summary = validate_evidence_summary_answer_observability_summary(
        _observability_summary()
    )

    assert isinstance(summary, EvidenceSummaryAnswerObservabilitySummarySchema)
    assert summary.payload_version == (
        EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_VERSION
    )
    assert summary.summary_ref.startswith(
        EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_REF_PREFIX
    )
    assert summary.status == "success"
    assert summary.task_compatible is True
    assert summary.workflow_compatible is True
    assert summary.runtime_backed is False
    assert summary.backed_by_adk_task_runtime is False
    assert summary.backed_by_adk_workflow_runtime is False
    assert summary.raw_boundary_summary.restricted_payload_absent is True


def test_evidence_summary_answer_trace_inspect_accepts_safe_shape() -> None:
    trace_inspect = validate_evidence_summary_answer_trace_inspect(_trace_inspect())

    assert isinstance(trace_inspect, EvidenceSummaryAnswerTraceInspectSchema)
    assert trace_inspect.payload_version == EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_VERSION
    assert trace_inspect.trace_inspect_ref.startswith(
        EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_REF_PREFIX
    )
    assert trace_inspect.inspect_status == "success"
    assert trace_inspect.task_compatible is True
    assert trace_inspect.workflow_compatible is True
    assert trace_inspect.runtime_backed is False
    assert trace_inspect.backed_by_adk_task_runtime is False
    assert trace_inspect.backed_by_adk_workflow_runtime is False
    assert trace_inspect.durable_session is False
    assert trace_inspect.memory_enabled is False


def test_evidence_summary_answer_run_accepts_product_aggregate_shape() -> None:
    answer_run = validate_evidence_summary_answer_run(_run())

    assert isinstance(answer_run, EvidenceSummaryAnswerRunSchema)
    assert answer_run.payload_version == EVIDENCE_SUMMARY_ANSWER_RUN_VERSION
    assert answer_run.answer_run_ref.startswith(EVIDENCE_SUMMARY_ANSWER_RUN_REF_PREFIX)
    assert answer_run.answer_run_status == "success"
    assert answer_run.answer_status == "success"
    assert answer_run.answer_trace_ref == f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX}trace-1"
    assert answer_run.answer_artifact_ref == (
        f"{EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX}artifact-1"
    )
    assert answer_run.task_compatible is True
    assert answer_run.workflow_compatible is True
    assert answer_run.runtime_backed is False
    assert answer_run.backed_by_adk_task_runtime is False
    assert answer_run.backed_by_adk_workflow_runtime is False
    assert answer_run.backed_by_adk_artifact_service is False
    assert answer_run.backed_by_adk_event_stream is False
    assert answer_run.durable_session is False
    assert answer_run.memory_enabled is False


def test_follow_up_seed_rejects_durable_session_or_memory_runtime() -> None:
    durable_seed = _follow_up_seed()
    durable_seed["durable_session"] = True
    memory_seed = _follow_up_seed()
    memory_seed["memory_enabled"] = True

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_follow_up_seed(durable_seed)
    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_follow_up_seed(memory_seed)


@pytest.mark.parametrize(
    ("payload_kind", "field", "value"),
    [
        ("digest", "product", "other"),
        ("digest", "payload_type", "other"),
        ("digest", "payload_version", "other"),
        ("context", "product", "other"),
        ("context", "payload_type", "other"),
        ("context", "payload_version", "other"),
        ("result", "product", "other"),
        ("result", "payload_type", "other"),
        ("result", "payload_version", "other"),
        ("trace", "product", "other"),
        ("trace", "payload_type", "other"),
        ("trace", "payload_version", "other"),
        ("artifact", "product", "other"),
        ("artifact", "payload_type", "other"),
        ("artifact", "payload_version", "other"),
        ("trace_inspect", "product", "other"),
        ("trace_inspect", "payload_type", "other"),
        ("trace_inspect", "payload_version", "other"),
        ("run", "product", "other"),
        ("run", "payload_type", "other"),
        ("run", "payload_version", "other"),
        ("follow_up_seed", "product", "other"),
        ("follow_up_seed", "payload_type", "other"),
        ("follow_up_seed", "payload_version", "other"),
    ],
)
def test_evidence_summary_answer_rejects_invalid_payload_headers(
    payload_kind: str,
    field: str,
    value: str,
) -> None:
    payload = _payload_for_kind(payload_kind)
    payload[field] = value

    with pytest.raises(ValidationError):
        _validate_payload(payload)


def test_digest_rejects_invalid_digest_ref() -> None:
    digest = _digest()
    digest["digest_ref"] = "digest://request-1/digest-1"

    with pytest.raises(ValidationError):
        validate_governed_evidence_digest(digest)


def test_digest_rejects_invalid_evidence_ref() -> None:
    digest = _digest()
    digest["evidence_ref"] = "evidence://other/request-1/fetch-1"

    with pytest.raises(ValidationError):
        validate_governed_evidence_digest(digest)


def test_digest_rejects_source_url_host_with_path_or_query() -> None:
    digest = _digest()
    digest["source_url_host"] = "example.com/path?x=1"

    with pytest.raises(ValidationError):
        validate_governed_evidence_digest(digest)


def test_digest_rejects_blocked_without_reasons() -> None:
    digest = _digest()
    digest["status"] = "blocked"
    digest["answerability"] = "blocked"
    digest["allowed_for_model_context"] = False
    digest["blocking_reasons"] = []

    with pytest.raises(ValidationError):
        validate_governed_evidence_digest(digest)


def test_digest_rejects_raw_boundary_flags_when_answerable() -> None:
    digest = _digest()
    digest["raw_boundary_flags"] = {"raw_provider_response_included": True}

    with pytest.raises(ValidationError):
        validate_governed_evidence_digest(digest)


@pytest.mark.parametrize(
    "summary_fact",
    [
        "sanitized_excerpt_preview: body text",
        "raw provider response contained facts",
        "config_context value leaked into context",
    ],
)
def test_digest_rejects_raw_markers_in_summary_facts(summary_fact: str) -> None:
    digest = _digest()
    digest["summary_facts"] = [summary_fact]

    with pytest.raises(ValidationError):
        validate_governed_evidence_digest(digest)


def test_digest_allows_public_package_names_in_summary_facts() -> None:
    digest = _digest()
    digest["summary_facts"] = [
        "README mentions config_contexts and config_assembly as public package names."
    ]

    model = validate_governed_evidence_digest(digest)

    assert "config_contexts" in model.summary_facts[0]
    assert "config_assembly" in model.summary_facts[0]


def test_context_rejects_evidence_refs_that_do_not_cover_digest_refs() -> None:
    context = _context()
    context["evidence_refs"] = [{"ref": "evidence://external-readonly/other", "kind": "evidence"}]

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_context(context)


@pytest.mark.parametrize("key", ["prompt", "messages", "config_context"])
def test_context_rejects_forbidden_metadata_keys(key: str) -> None:
    context = _context()
    context["metadata"] = {key: "forbidden"}

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_context(context)


def test_result_success_rejects_missing_evidence_refs_used() -> None:
    result = _result()
    result["evidence_refs_used"] = []

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_result(result)


def test_result_insufficient_evidence_requires_reason() -> None:
    result = _result(status="insufficient_evidence")
    result["answer"] = None
    result["answer_preview"] = None
    result["evidence_refs_used"] = []
    result["digest_refs_used"] = []
    result["insufficient_evidence_reason"] = None
    result["llm_runtime_call_performed"] = False

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_result(result)


def test_result_blocked_requires_blocking_reason() -> None:
    result = _result(status="blocked")
    result["answer"] = None
    result["answer_preview"] = None
    result["evidence_refs_used"] = []
    result["digest_refs_used"] = []
    result["blocking_reasons"] = []
    result["llm_runtime_call_performed"] = False

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_result(result)


def test_result_rejects_llm_runtime_flag_inconsistency() -> None:
    result = _result()
    result["llm_call_allowed"] = False
    result["llm_call_attempted"] = True
    result["llm_runtime_call_performed"] = True

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_result(result)


def test_result_rejects_raw_provider_output_metadata() -> None:
    result = _result()
    result["metadata"] = {"response_text": "raw provider output"}

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_result(result)


def test_trace_rejects_runtime_backing_or_durable_state() -> None:
    trace = _trace()
    trace["backed_by_adk_workflow_runtime"] = True

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_trace(trace)

    trace = _trace()
    trace["durable_session"] = True

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_trace(trace)


def test_run_rejects_runtime_backing_or_missing_success_refs() -> None:
    answer_run = _run()
    answer_run["backed_by_adk_task_runtime"] = True

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_run(answer_run)

    answer_run = _run()
    answer_run["answer_trace_ref"] = None

    with pytest.raises(ValidationError):
        validate_evidence_summary_answer_run(answer_run)


def test_evidence_summary_answer_schema_has_no_execution_layer_imports() -> None:
    source = (SCHEMA_SOURCE_ROOT / "evidence_summary_answer.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|cognition_cli|behavior_contracts|config_contexts|"
        r"runtime_container|composition|product_runtime_assembly|observability_hub|"
        r"adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None


def test_schemas_root_exports_evidence_summary_answer_contracts() -> None:
    assert RootGovernedEvidenceDigestSchema is GovernedEvidenceDigestSchema
    assert RootEvidenceSummaryAnswerContextSchema is EvidenceSummaryAnswerContextSchema
    assert RootEvidenceSummaryAnswerFollowUpSeedSchema is EvidenceSummaryAnswerFollowUpSeedSchema
    assert RootEvidenceSummaryAnswerTraceSchema is EvidenceSummaryAnswerTraceSchema
    assert RootEvidenceSummaryAnswerArtifactSchema is EvidenceSummaryAnswerArtifactSchema
    assert (
        RootEvidenceSummaryAnswerObservabilitySummarySchema
        is EvidenceSummaryAnswerObservabilitySummarySchema
    )
    assert RootEvidenceSummaryAnswerTraceInspectSchema is EvidenceSummaryAnswerTraceInspectSchema
    assert RootEvidenceSummaryAnswerRunSchema is EvidenceSummaryAnswerRunSchema
    assert root_validate_governed_evidence_digest(_digest()).digest_id == "digest-1"
    assert root_validate_follow_up_seed(_follow_up_seed()).seed_id == "seed-1"
    assert root_validate_trace(_trace()).trace_id == "trace-1"
    assert root_validate_artifact(_artifact()).artifact_id == "artifact-1"
    assert (
        root_validate_observability_summary(_observability_summary()).summary_id
        == "summary-1"
    )
    assert root_validate_trace_inspect(_trace_inspect()).trace_inspect_id == (
        "trace-inspect-1"
    )
    assert root_validate_run(_run()).run_id == "run-1"


def _validate_payload(payload: dict[str, object]) -> object:
    payload_type = payload.get("payload_type")
    if payload_type == "governed_evidence_digest":
        return validate_governed_evidence_digest(payload)
    if payload_type == "evidence_summary_answer_context":
        return validate_evidence_summary_answer_context(payload)
    if payload_type == "evidence_summary_answer_result":
        return validate_evidence_summary_answer_result(payload)
    if payload_type == "evidence_summary_answer_follow_up_seed":
        return validate_evidence_summary_answer_follow_up_seed(payload)
    if payload_type == "evidence_summary_answer_artifact":
        return validate_evidence_summary_answer_artifact(payload)
    if payload_type == "evidence_summary_answer_observability_summary":
        return validate_evidence_summary_answer_observability_summary(payload)
    if payload_type == "evidence_summary_answer_trace_inspect":
        return validate_evidence_summary_answer_trace_inspect(payload)
    if payload_type == "evidence_summary_answer_run":
        return validate_evidence_summary_answer_run(payload)
    if "digest_ref" in payload:
        return validate_governed_evidence_digest(payload)
    if "digests" in payload:
        return validate_evidence_summary_answer_context(payload)
    if "seed_ref" in payload:
        return validate_evidence_summary_answer_follow_up_seed(payload)
    if "artifact_ref" in payload:
        return validate_evidence_summary_answer_artifact(payload)
    if "summary_ref" in payload:
        return validate_evidence_summary_answer_observability_summary(payload)
    if "trace_inspect_ref" in payload:
        return validate_evidence_summary_answer_trace_inspect(payload)
    if "answer_run_ref" in payload:
        return validate_evidence_summary_answer_run(payload)
    return validate_evidence_summary_answer_result(payload)


def _payload_for_kind(payload_kind: str) -> dict[str, object]:
    if payload_kind == "digest":
        return _digest()
    if payload_kind == "context":
        return _context()
    if payload_kind == "result":
        return _result()
    if payload_kind == "trace":
        return _trace()
    if payload_kind == "artifact":
        return _artifact()
    if payload_kind == "follow_up_seed":
        return _follow_up_seed()
    if payload_kind == "trace_inspect":
        return _trace_inspect()
    if payload_kind == "run":
        return _run()
    raise AssertionError(f"unknown payload kind: {payload_kind}")


def _follow_up_seed() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_follow_up_seed",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_SEED_VERSION,
        "seed_id": "seed-1",
        "seed_ref": "evidence-summary-answer-follow-up://seed-1",
        "source_request_id": "request-1",
        "source_result_status": "success",
        "digest_refs": ["governed-evidence-digest://request-1/digest-1"],
        "evidence_refs": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "answer_context",
            }
        ],
        "additional_refs": [
            {
                "ref": "governed-evidence-digest://request-1/digest-1",
                "kind": "governed_evidence_digest",
                "purpose": "digest_context",
            }
        ],
        "follow_up_allowed": True,
        "temporary_only": True,
        "durable_session": False,
        "memory_enabled": False,
        "blocking_reasons": [],
        "warnings": [],
        "metadata": {"source": "schemas.test"},
    }


def _digest() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "governed_evidence_digest",
        "payload_version": GOVERNED_EVIDENCE_DIGEST_VERSION,
        "digest_id": "digest-1",
        "digest_ref": "governed-evidence-digest://request-1/digest-1",
        "evidence_ref": "evidence://external-readonly/request-1/fetch-1",
        "evidence_output_ref": "external-readonly-output://request-1/fetch-1",
        "source_url_host": "example.com",
        "source_url_scheme": "https",
        "runtime_status": "success",
        "status": "ready",
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "evidence_written": True,
        "content_hash": "sha256:abc123",
        "total_excerpt_chars": 128,
        "raw_boundary_flags": {},
        "blocking_reasons": [],
        "warnings": [],
        "summary_facts": ["The source describes a governed answer context."],
        "topic_labels": ["contracts"],
        "risk_labels": [],
        "answerability": "answerable",
        "digest_generation_policy_ref": (
            "policy://evidence-summary-answer/digest-generation-v1"
        ),
        "digest_budget": 4000,
        "metadata": {"source": "schemas.test"},
    }


def _context() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_context",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION,
        "request_id": "request-1",
        "user_question": "What does the governed evidence say?",
        "digests": [copy.deepcopy(_digest())],
        "evidence_refs": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "answer_context",
            }
        ],
        "additional_refs": [
            {
                "ref": "governed-evidence-digest://request-1/digest-1",
                "kind": "governed_evidence_digest",
                "purpose": "digest_context",
            }
        ],
        "answer_policy_ref": "policy://evidence-summary-answer/answer-v1",
        "citation_policy_ref": "policy://evidence-summary-answer/citation-v1",
        "model_context_budget": 4000,
        "metadata": {"source": "schemas.test"},
    }


def _result(*, status: str = "success") -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_result",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION,
        "request_id": "request-1",
        "status": status,
        "answer": "The governed evidence supports using a schema first.",
        "answer_preview": "The governed evidence supports using a schema first.",
        "evidence_refs_used": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "citation",
            }
        ],
        "digest_refs_used": ["governed-evidence-digest://request-1/digest-1"],
        "additional_refs_used": [],
        "insufficient_evidence_reason": None,
        "citation_failures": [],
        "blocking_reasons": [],
        "warnings": [],
        "llm_call_allowed": True,
        "llm_call_attempted": True,
        "llm_runtime_call_performed": True,
        "raw_boundary_flags": {},
        "metadata": {"source": "schemas.test"},
    }


def _trace() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_trace",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_TRACE_VERSION,
        "trace_id": "trace-1",
        "trace_ref": f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX}trace-1",
        "request_id": "request-1",
        "answer_status": "success",
        "readonly_refs_status": "ready",
        "evidence_ref_count": 1,
        "additional_ref_count": 1,
        "digest_ref_count": 1,
        "evidence_refs": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "answer_context",
            }
        ],
        "additional_refs": [
            {
                "ref": "governed-evidence-digest://request-1/digest-1",
                "kind": "governed_evidence_digest",
                "purpose": "digest_context",
            }
        ],
        "digest_refs": ["governed-evidence-digest://request-1/digest-1"],
        "blocking_reasons": [],
        "warnings": [],
        "insufficient_evidence_reason": None,
        "citation_failures": [],
        "llm_call_allowed": True,
        "llm_call_attempted": True,
        "llm_runtime_call_performed": True,
        "llm_route_provider": "litellm",
        "llm_route_model": "ollama/gemma4-pro:latest",
        "provider_profile_ref": "local_ollama",
        "model_profile_ref": "gemma4_pro_local",
        "output_governance_profile_ref": "adk_output_schema_gemma4_baseline",
        "answerability_preflight_applied": False,
        "answerability_preflight_reason": None,
        "answer_ref": f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX}trace-1/answer",
        "answer_preview": "The governed evidence supports using a schema first.",
        "follow_up": False,
        "temporary_follow_up": True,
        "durable_session": False,
        "memory_enabled": False,
        "task_compatible": True,
        "workflow_compatible": True,
        "backed_by_adk_task_runtime": False,
        "backed_by_adk_workflow_runtime": False,
        "raw_boundary_flags": {},
        "metadata": {"source": "schemas.test"},
    }


def _artifact() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_artifact",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_ARTIFACT_VERSION,
        "artifact_id": "artifact-1",
        "artifact_ref": f"{EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX}artifact-1",
        "request_id": "request-1",
        "answer_status": "success",
        "artifact_status": "success",
        "trace_ref": f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX}trace-1",
        "artifact_policy_ref": (
            "policy://product-application-assembly/evidence-summary-answer/"
            "artifact-v1"
        ),
        "evidence_ref_count": 1,
        "additional_ref_count": 1,
        "digest_ref_count": 1,
        "evidence_refs": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "answer_context",
            }
        ],
        "additional_refs": [
            {
                "ref": "governed-evidence-digest://request-1/digest-1",
                "kind": "governed_evidence_digest",
                "purpose": "digest_context",
            }
        ],
        "digest_refs": ["governed-evidence-digest://request-1/digest-1"],
        "blocking_reasons": [],
        "warnings": [],
        "insufficient_evidence_reason": None,
        "citation_failures": [],
        "llm_call_allowed": True,
        "llm_call_attempted": True,
        "llm_runtime_call_performed": True,
        "llm_route_provider": "litellm",
        "llm_route_model": "ollama/gemma4-pro:latest",
        "provider_profile_ref": "local_ollama",
        "model_profile_ref": "gemma4_pro_local",
        "output_governance_profile_ref": "adk_output_schema_gemma4_baseline",
        "answerability_preflight_applied": False,
        "answerability_preflight_reason": None,
        "answer_ref": f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX}trace-1/answer",
        "answer": "The governed evidence supports using a schema first.",
        "answer_preview": "The governed evidence supports using a schema first.",
        "export_allowed": False,
        "delete_supported": True,
        "retention_policy_ref": None,
        "durable_session": False,
        "memory_enabled": False,
        "task_compatible": True,
        "workflow_compatible": True,
        "backed_by_adk_task_runtime": False,
        "backed_by_adk_workflow_runtime": False,
        "raw_boundary_flags": {},
        "metadata": {"source": "schemas.test"},
    }


def _observability_summary() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_observability_summary",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_VERSION,
        "summary_id": "summary-1",
        "summary_ref": (
            f"{EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_REF_PREFIX}summary-1"
        ),
        "request_id": "request-1",
        "status": "success",
        "reason": "answer_ready",
        "user_explanation": "本轮受治理资料问答已形成可返回答案。",
        "recovery_hints": [],
        "refs": [
            {
                "ref": f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX}trace-1",
                "kind": "evidence_summary_answer_trace",
                "purpose": "answer_trace",
            }
        ],
        "raw_boundary_summary": {
            "restricted_payload_absent": True,
            "restricted_boundary_intact": True,
            "blocked_field_count": 0,
        },
        "evaluation_findings_summary": {
            "finding_count": 0,
            "quality_blocked": False,
            "model_called": True,
        },
        "task_compatible": True,
        "workflow_compatible": True,
        "runtime_backed": False,
        "backed_by_adk_task_runtime": False,
        "backed_by_adk_workflow_runtime": False,
        "durable_session": False,
        "memory_enabled": False,
        "metadata": {"source": "schemas.test"},
    }


def _trace_inspect() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_trace_inspect",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_VERSION,
        "trace_inspect_id": "trace-inspect-1",
        "trace_inspect_ref": (
            f"{EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_REF_PREFIX}trace-inspect-1"
        ),
        "request_id": "request-1",
        "inspect_status": "success",
        "inspect_reason": "answer_ready",
        "answer_status": "success",
        "user_explanation": "本轮受治理资料问答已形成可复查解释。",
        "developer_facts_summary": {
            "answer_trace_available": True,
            "answer_artifact_available": True,
            "observability_summary_available": True,
        },
        "refs_summary": {
            "trace_ref": f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX}trace-1",
            "artifact_ref": (
                f"{EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX}artifact-1"
            ),
            "evidence_ref_count": 1,
            "additional_ref_count": 1,
        },
        "event_facts_summary": {
            "event_summary_kind": "product_level_summary",
            "event_stream_enabled": False,
            "adk_event_runtime_enabled": False,
        },
        "artifact_handoff_summary": {
            "artifact_summary_kind": "product_level_summary",
            "artifact_service_enabled": False,
            "export_enabled": False,
        },
        "raw_boundary_summary": {
            "restricted_payload_absent": True,
            "restricted_boundary_intact": True,
            "blocked_field_count": 0,
        },
        "evaluation_summary": {
            "evaluation_only": True,
            "finding_count": 0,
            "quality_blocked": False,
        },
        "governance_summary": {
            "governance_summary_only": True,
            "decision_reason": "answer_ready",
        },
        "unavailable_reason": None,
        "recovery_hints": [],
        "task_compatible": True,
        "workflow_compatible": True,
        "runtime_backed": False,
        "backed_by_adk_task_runtime": False,
        "backed_by_adk_workflow_runtime": False,
        "durable_session": False,
        "memory_enabled": False,
        "metadata": {"source": "schemas.test"},
    }


def _run() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_run",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_RUN_VERSION,
        "run_id": "run-1",
        "answer_run_ref": f"{EVIDENCE_SUMMARY_ANSWER_RUN_REF_PREFIX}run-1",
        "request_id": "request-1",
        "source_request_id": "request-1",
        "parent_answer_run_ref": None,
        "answer_run_status": "success",
        "answer_status": "success",
        "readonly_refs_status": "ready",
        "answer_trace_ref": f"{EVIDENCE_SUMMARY_ANSWER_TRACE_REF_PREFIX}trace-1",
        "answer_artifact_ref": (
            f"{EVIDENCE_SUMMARY_ANSWER_ARTIFACT_REF_PREFIX}artifact-1"
        ),
        "observability_summary_ref": (
            f"{EVIDENCE_SUMMARY_ANSWER_OBSERVABILITY_SUMMARY_REF_PREFIX}summary-1"
        ),
        "trace_inspect_ref": (
            f"{EVIDENCE_SUMMARY_ANSWER_TRACE_INSPECT_REF_PREFIX}trace-inspect-1"
        ),
        "follow_up_seed_ref": None,
        "evidence_ref_count": 1,
        "additional_ref_count": 1,
        "evidence_refs": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "answer_context",
            }
        ],
        "additional_refs": [
            {
                "ref": "governed-evidence-digest://request-1/digest-1",
                "kind": "governed_evidence_digest",
                "purpose": "digest_context",
            }
        ],
        "blocking_reasons": [],
        "warnings": [],
        "recovery_hints": [],
        "unavailable_reason": None,
        "follow_up": False,
        "follow_up_turn_index": None,
        "answer_scoped_transformation": False,
        "task_compatible": True,
        "workflow_compatible": True,
        "runtime_backed": False,
        "backed_by_adk_task_runtime": False,
        "backed_by_adk_workflow_runtime": False,
        "backed_by_adk_artifact_service": False,
        "backed_by_adk_event_stream": False,
        "durable_session": False,
        "memory_enabled": False,
        "raw_boundary_summary": {
            "restricted_payload_absent": True,
            "restricted_boundary_intact": True,
            "blocked_field_count": 0,
        },
        "metadata": {"source": "schemas.test"},
    }
